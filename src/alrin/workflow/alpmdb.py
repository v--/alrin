import logging
import pathlib
import subprocess
from collections.abc import Sequence

from alrin.exceptions import AlrinPackageMetadataError
from alrin.pkginfo import AlrinBuiltPackage, PackageArchPair
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
    logger.info(f'Removing {pkg_len} {'package' if pkg_len == 1 else 'packages'} from {path_to_db}.')

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


def alpmdb_bulk_remove_packages(
    shared: AlrinSharedState,
    valid_built: Sequence[AlrinBuiltPackage],
    obsolete_pairs: Sequence[PackageArchPair],
) -> None:
    for arch in {arch for built, arch in obsolete_pairs}:
        to_remove = list({
            built.info.pkgname for built, a in obsolete_pairs
            if a == arch and not any(valid_built.info.pkgname == built.info.pkgname and arch in valid_built.iter_arch() for valid_built in valid_built)
        })

        alpmdb_remove_packages(shared, arch, to_remove)
