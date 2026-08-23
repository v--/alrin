import io
import tarfile
import time
from collections.abc import Iterable, Mapping, Sequence

from alpm.alpm_srcinfo.source_info.v1.package import Package
from alpm.alpm_srcinfo.source_info.v1.package_base import PackageBase

from alrin.source import AlrinPackageSource


# ruff: ignore[missing-type-function-argument, unused-function-argument]
def mock_makepkg(self, pkg: AlrinPackageSource, builddate: int | None = None) -> None:
    srcinfo = pkg.read_srcinfo()

    for package in srcinfo.packages:
        for arch in package.architectures or srcinfo.base.architectures:
            mock_makepkg_package(
                pkg,
                srcinfo.base,
                package,
                str(arch),
                is_split=len(srcinfo.packages) > 1,
                builddate=builddate,
            )


def mock_makepkg_package(
    pkg: AlrinPackageSource,
    base: PackageBase,
    package: Package,
    arch: str,
    is_split: bool = False,
    builddate: int | None = None,
) -> None:
    output_file = pkg.get_abs_path().joinpath(f'{package.name if package else base.name}-{pkg.version}-{arch}.pkg.tar')

    with tarfile.open(output_file, 'w') as file:
        pkginfo_data = {
            'xdata': 'pkgtype=split' if is_split else 'pkgtype=pkg',
            'pkgbase': pkg.pkgbase,
            'pkgname': str(package.name or base.name),
            'pkgdesc': str(package.description or base.description),
            # ruff: ignore[builtin-variable-shadowing]
            'license': [str(license) for license in ((package.licenses.value if package.licenses else None) or base.licenses)],
            'pkgver': str(pkg.version),
            'builddate': str(time.time_ns() // 1_000_000) if builddate is None else str(builddate),
            'arch': str(arch),
            'depend': [str(dep) for dep in ((package.dependencies.value if package.dependencies else None) or base.dependencies)],
        }

        write_package_file(file, '.PKGINFO', pkginfo_data)


def generate_pkginfo_lines(**kwargs: str | Sequence[str] | None) -> Iterable[str]:
    for key, value in kwargs.items():
        if isinstance(value, str):
            yield f'{key} = {value}'

        elif isinstance(value, Sequence):
            for v in value:
                yield f'{key} = {v}'


def write_package_file(
    tar_file: tarfile.TarFile,
    name: str,
    contents: Mapping[str, str | Sequence[str] | None],
) -> None:
    buffer = io.BytesIO()

    for chunk in generate_pkginfo_lines(**contents):
        buffer.write(chunk.encode('utf-8'))
        buffer.write(b'\n')

    info = tarfile.TarInfo(name)
    info.size = len(buffer.getbuffer())
    buffer.seek(0)

    tar_file.addfile(info, buffer)
