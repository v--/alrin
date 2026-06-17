import tarfile
from dataclasses import dataclass
from typing import get_type_hints
lazy import pathlib
lazy from collections.abc import Iterator, Sequence

from alrin.exceptions import AlrinPackageMetadataError
lazy from alrin.source import AlrinPackageSource
lazy from alrin.state import AlrinSharedState


@dataclass(frozen=True)
class AlrinBuildInfo:
    pkgbase: str
    pkgname: str
    pkgver: str
    pkgarch: str
    builddate: int


class AlrinBuiltPackage:
    path: pathlib.Path
    info: AlrinBuildInfo

    def __init__(self, path: pathlib.Path) -> None:
        self.path = path
        self.info = extract_buildinfo(self.path)

    def get_signature_path(self) -> pathlib.Path:
        return self.path.with_name(self.path.name + '.sig')

    def iter_arch(self) -> Iterator[str]:
        yield self.info.pkgarch

        if self.info.pkgarch == 'any':
            yield 'x86_64'


def extract_buildinfo(pkg_path: pathlib.Path) -> AlrinBuildInfo:
    fields = dict[str, str]()
    hints = get_type_hints(AlrinBuildInfo)

    with tarfile.open(pkg_path) as file:
        buildinfo = file.extractfile('.BUILDINFO')

        if buildinfo is None:
            raise AlrinPackageMetadataError(f'No .BUILDINFO file in {pkg_path.as_posix()!r}')

        while line := buildinfo.readline():
            key, value = map(str.strip, line.decode(encoding='utf-8').split('=', maxsplit=2))

            if key in hints:
                fields[key] = value

    for key in hints:
        if key not in fields:
            raise AlrinPackageMetadataError(f'Could not read {key!r} from {pkg_path.as_posix()!r}')

    builddate = int(fields.pop('builddate'))
    return AlrinBuildInfo(**fields, builddate=builddate)


def get_newly_built(pkg: AlrinPackageSource) -> Sequence[AlrinBuiltPackage]:
    return [
        AlrinBuiltPackage(pkg_path)
        for pkg_path in pkg.get_abs_path().glob('*.pkg.*')
    ]


def get_existing_built(shared: AlrinSharedState) -> Sequence[AlrinBuiltPackage]:
    return [
        AlrinBuiltPackage(pkg_path)
        for pkg_path in shared.resolver.get_dest().rglob('*.pkg.*')
        if pkg_path.suffix not in {'.sig', '.db'}
    ]
