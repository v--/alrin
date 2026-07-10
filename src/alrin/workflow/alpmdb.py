import logging
import pathlib
import subprocess
lazy from collections.abc import Sequence

from alrin.buildinfo import AlrinBuiltPackage, get_existing_built
from alrin.exceptions import AlrinPackageMetadataError
from alrin.wrappers import repo_add, repo_remove
lazy from alrin.state import AlrinSharedState


DEFAULT_REPOSITORY_NAME = 'ivasilev'
logger = logging.getLogger(__name__)


def alpmdb_add_packages(
    shared: AlrinSharedState,
    new_packages: Sequence[AlrinBuiltPackage],
    repo_name: str = DEFAULT_REPOSITORY_NAME,
) -> None:
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

        path_to_db = pathlib.Path(arch) / f'{repo_name}.db.tar.zst'
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


def alpmdb_remove_packages(
    shared: AlrinSharedState,
    *pkgnames: str,
    repo_name: str = DEFAULT_REPOSITORY_NAME,
) -> None:
    existing_built = get_existing_built(shared)
    architectures = {built.info.pkgarch for built in existing_built}

    for arch in architectures:
        package_names = list({
            built.info.pkgname for built in existing_built
            if built.info.pkgbase in pkgnames and built.info.pkgarch == arch
        })

        pkg_len = len(package_names)
        path_to_db = pathlib.Path(arch) / f'{repo_name}.db.tar.zst'
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
