import logging
import pathlib
import subprocess
from collections.abc import Sequence

from alrin.exceptions import AlrinPackageMetadataError
from alrin.pkginfo import AlrinBuiltPackage, PackageNameArchPair
from alrin.state import AlrinSharedState
from alrin.wrappers import repo_add, repo_remove


logger = logging.getLogger(__name__)


def alpmdb_add_package_files(shared: AlrinSharedState, new_packages: Sequence[AlrinBuiltPackage]) -> None:
    dest = shared.resolver.get_dest()
    new_package_paths = [built.path for built in new_packages]

    for subdir in dest.iterdir():
        if not subdir.is_dir():
            continue

        arch = subdir.name
        package_paths = [
            path.relative_to(dest)
            for path in subdir.iterdir() if path in new_package_paths
        ]
        pkg_len = len(package_paths)

        if pkg_len == 0:
            continue

        path_to_db = pathlib.Path(arch) / shared.meta.database.get_db_file_name()
        logger.info(f'Adding {pkg_len} {'package' if pkg_len == 1 else 'packages'} to {path_to_db}.')

        try:
            repo_add(
                path_to_db=path_to_db,
                package_paths=package_paths,
                quiet=True,
                sign=True,
                cwd=dest,
            )
        except subprocess.CalledProcessError as err:
            raise AlrinPackageMetadataError('Repository update failed') from err


def alpmdb_remove_packages(shared: AlrinSharedState, arch: str, pkgnames: Sequence[str]) -> None:
    path_to_db = pathlib.Path(arch) / shared.meta.database.get_db_file_name()

    pkg_len = len(pkgnames)
    logger.info(f'Adding {pkg_len} {'package' if pkg_len == 1 else 'packages'} to {path_to_db}.')

    try:
        repo_remove(
            path_to_db=path_to_db,
            package_names=pkgnames,
            quiet=True,
            sign=True,
            cwd=shared.resolver.get_dest(),
        )
    except subprocess.CalledProcessError as err:
        raise AlrinPackageMetadataError('Repository update failed') from err


def alpmdb_bulk_remove_packages(shared: AlrinSharedState, pairs: Sequence[PackageNameArchPair]) -> None:
    for arch in {arch for pkgname, arch in pairs}:
        alpmdb_remove_packages(
            shared,
            arch,
            [pkgname for pkgname, a in pairs if a == arch],
        )
