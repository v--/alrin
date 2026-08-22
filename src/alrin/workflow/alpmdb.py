import logging
import pathlib
import subprocess
from collections.abc import Sequence
from typing import no_type_check

from alrin.buildinfo import AlrinBuiltPackage, get_existing_built
from alrin.exceptions import AlrinPackageMetadataError
from alrin.state import AlrinSharedState
from alrin.wrappers import repo_add, repo_remove


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


@no_type_check  # mypy does not yet support comprehension unpacking; see https://github.com/python/mypy/issues/21447
def alpmdb_remove_packages(
    shared: AlrinSharedState,
    *pkgnames: str,
    repo_name: str = DEFAULT_REPOSITORY_NAME,
) -> None:
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
        path_to_db = pathlib.Path(arch) / f'{repo_name}.db.tar.zst'
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
