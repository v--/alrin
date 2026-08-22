import io
import tarfile
import time
from collections.abc import Iterable, Mapping, Sequence

from alpm.alpm_srcinfo.source_info.v1.package import Package
from alpm.alpm_srcinfo.source_info.v1.package_base import PackageBase

from alrin.source import AlrinPackageSource


def generate_buildinfo(**kwargs: str | Sequence[str] | None) -> Iterable[str]:
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

    for chunk in generate_buildinfo(**contents):
        buffer.write(chunk.encode('utf-8'))
        buffer.write(b'\n')

    info = tarfile.TarInfo(name)
    info.size = len(buffer.getbuffer())
    buffer.seek(0)

    tar_file.addfile(info, buffer)


def mock_makepkg_subpackage(
    pkg: AlrinPackageSource,
    base: PackageBase,
    subpackage: Package | None,
    arch: str,
    builddate: int | None = None,
) -> None:
    output_file = pkg.get_abs_path().joinpath(f'{subpackage.name if subpackage else base.name}-{pkg.version}-{arch}.pkg.tar.zst')

    with tarfile.open(output_file, 'w') as file:
        common_data = {
            'pkgbase': pkg.pkgname,
            'pkgname': str(subpackage.name if subpackage else base.name),
            'pkgdesc': str((subpackage.description if subpackage else None) or base.description),
            # ruff: ignore[builtin-variable-shadowing]
            'license': [str(license) for license in ((subpackage.licenses.value if (subpackage and subpackage.licenses) else None) or base.licenses)],
            'pkgver': str(pkg.version),
            'builddate': str(time.time_ns() // 1_000_000) if builddate is None else str(builddate),
            'pkgarch': str(arch),
            'depend': [str(dep) for dep in ((subpackage.dependencies.value if (subpackage and subpackage.dependencies) else None) or base.licenses)],
        }

        pkginfo_data = {
            **common_data,
            'xdata': 'pkgtype=split' if subpackage else 'pkgtype=pkg',
        }

        write_package_file(file, '.PKGINFO', pkginfo_data)

        buildinfo_data = {
            **common_data,
            'format': '2',
        }

        write_package_file(file, '.BUILDINFO', buildinfo_data)


# ruff: ignore[missing-type-function-argument, unused-function-argument]
def mock_makepkg(self, pkg: AlrinPackageSource, builddate: int | None = None) -> None:
    srcinfo = pkg.read_srcinfo()

    for arch in srcinfo.base.architectures:
        mock_makepkg_subpackage(pkg, srcinfo.base, subpackage=None, arch=str(arch), builddate=builddate)

    for subpackage in srcinfo.packages:
        for arch in subpackage.architectures or srcinfo.base.architectures:
            mock_makepkg_subpackage(pkg, srcinfo.base, subpackage=subpackage, arch=str(arch), builddate=builddate)
