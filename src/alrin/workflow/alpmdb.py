import logging
import pathlib
import subprocess
from collections.abc import Sequence

from alrin.exceptions import AlrinPackageMetadataError
from alrin.pkginfo import AlrinBuiltPackage, get_existing_built
from alrin.state import AlrinSharedState
from alrin.wrappers import repo_add, repo_remove


logger = logging.getLogger(__name__)


def alpmdb_add_packages(shared: AlrinSharedState, new_packages: Sequence[AlrinBuiltPackage]) -> None:
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


def alpmdb_remove_packages(shared: AlrinSharedState, *pkgnames: str) -> None:
    existing_built = get_existing_built(shared)

    package_names = list({
        built.info.pkgname for built in existing_built if built.info.pkgbase in pkgnames
    })

    architectures = list({
        arch
        for built in existing_built if built.info.pkgbase in pkgnames
        for arch in built.iter_arch()
    })

    for arch in architectures:
        path_to_db = pathlib.Path(arch) / shared.meta.database.get_db_file_name()
        logger.info(f'Removing {len(package_names)} {'package' if len(package_names) == 1 else 'packages'} from {path_to_db}.')

        try:
            repo_remove(
                path_to_db=path_to_db,
                package_names=package_names,
                quiet=True,
                sign=True,
                cwd=shared.resolver.get_dest(),
            )
        except subprocess.CalledProcessError as err:
            raise AlrinPackageMetadataError('Repository update failed') from err
