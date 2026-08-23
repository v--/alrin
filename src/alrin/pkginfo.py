import pathlib
import tarfile
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import NamedTuple, get_type_hints

from alrin.exceptions import AlrinPackageMetadataError
from alrin.resolver import AlrinPathResolver
from alrin.source import AlrinPackageSource


@dataclass(frozen=True)
class AlrinBuildPkgInfo:
    pkgbase: str
    pkgname: str
    pkgver: str
    arch: str
    builddate: int


class AlrinBuiltPackage:
    path: pathlib.Path
    info: AlrinBuildPkgInfo

    def __init__(self, path: pathlib.Path) -> None:
        self.path = path
        self.info = extract_pkginfo(self.path)

    def get_signature_path(self) -> pathlib.Path:
        return self.path.with_name(self.path.name + '.sig')

    def iter_arch(self) -> Iterator[str]:
        yield self.info.arch

        if self.info.arch == 'any':
            yield 'x86_64'


class PackageArchPair(NamedTuple):
    built: AlrinBuiltPackage
    arch: str

    def is_copy(self) -> bool:
        return self.built.info.arch != self.arch


class PackageNameArchPair(NamedTuple):
    pkgname: str
    arch: str


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
            try:
                key, value = map(str.strip, line.decode(encoding='utf-8').split('=', maxsplit=1))
            except ValueError:
                continue

            if key in hints:
                fields[key] = value

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


def get_existing_built(resolver: AlrinPathResolver) -> Sequence[PackageArchPair]:
    return [
        PackageArchPair(AlrinBuiltPackage(pkg_path), pkg_path.parent.name)
        for pkg_path in resolver.get_dest().rglob('*.pkg.*')
        if pkg_path.suffix not in {'.sig', '.db'}
    ]
