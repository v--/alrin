import pathlib
import re
import tarfile
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import get_type_hints

from alrin.exceptions import AlrinPackageMetadataError
from alrin.metadata import AlrinPackageVersion
from alrin.source import AlrinPackageSource
from alrin.state import AlrinSharedState


def parse_version(version_str: str) -> AlrinPackageVersion:
    if match := re.match(r'((?P<epoch>\d+):)?(?P<pkgver>\d+)-(?P<pkgrel>\d+(.\d+)?)', version_str):
        groups = match.groupdict()

        return AlrinPackageVersion(
            pkgver=groups['pkgver'],
            pkgrel=groups['pkgrel'],
            epoch=int(groups['epoch']) if groups.get('epoch') else None,
        )

    raise AlrinPackageMetadataError(f'Could not parse version {version_str!r}')


@dataclass(frozen=True)
class AlrinBuildPkgInfo:
    pkgbase: str
    pkgname: str
    pkgver: str
    pkgarch: str
    builddate: int

    def parse_version(self) -> AlrinPackageVersion:
        return parse_version(self.pkgver)


class AlrinBuiltPackage:
    path: pathlib.Path
    info: AlrinBuildPkgInfo

    def __init__(self, path: pathlib.Path) -> None:
        self.path = path
        self.info = extract_pkginfo(self.path)

    def get_signature_path(self) -> pathlib.Path:
        return self.path.with_name(self.path.name + '.sig')

    def iter_arch(self) -> Iterator[str]:
        yield self.info.pkgarch

        if self.info.pkgarch == 'any':
            yield 'x86_64'


def extract_pkginfo(pkg_path: pathlib.Path) -> AlrinBuildPkgInfo:
    fields = dict[str, str]()
    hints = get_type_hints(AlrinBuildPkgInfo)

    with tarfile.open(pkg_path) as file:
        try:
            pkginfo = file.extractfile('.PKGINFO')
        except KeyError as err:
            raise AlrinPackageMetadataError(f'No .PKGINFO file in {pkg_path}') from err

        if pkginfo is None:
            raise AlrinPackageMetadataError(f'.PKGINFO of {pkg_path} is not a file')

        while line := pkginfo.readline():
            key, value = line.decode(encoding='utf-8').split(' = ', maxsplit=2)

            if key in hints:
                fields[key] = value.strip()

    for key in hints:
        if key not in fields:
            raise AlrinPackageMetadataError(f'Could not read {key!r} from {pkg_path}')

    builddate = int(fields.pop('builddate'))
    return AlrinBuildPkgInfo(**fields, builddate=builddate)


def get_newly_built(pkg: AlrinPackageSource) -> Sequence[AlrinBuiltPackage]:
    return [
        AlrinBuiltPackage(pkg_path)
        for pkg_path in pkg.get_abs_path().glob('*.pkg.*')
        if pkg_path.suffix not in {'.sig', '.db'}
    ]


def get_existing_built(shared: AlrinSharedState) -> Sequence[AlrinBuiltPackage]:
    return [
        AlrinBuiltPackage(pkg_path)
        for pkg_path in shared.resolver.get_dest().rglob('*.pkg.*')
        if pkg_path.suffix not in {'.sig', '.db'}
    ]
