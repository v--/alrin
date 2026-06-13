import subprocess
from typing import TYPE_CHECKING

from alrin.buildinfo import AlrinBuiltPackage, get_existing_built
from alrin.exceptions import AlrinPackageMetadataError


if TYPE_CHECKING:
    from collections.abc import Sequence

    from alrin.state import AlrinSharedState


DEFAULT_REPOSITORY_NAME = 'ivasilev'


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
            path.relative_to(dest).as_posix()
            for path in subdir.iterdir() if path in new_package_paths
        ]
        pkg_len = len(package_paths)

        if pkg_len == 0:
            continue

        db_name = f'{arch}/{repo_name}.db.tar.zst'
        shared.logger.info(f'Adding {pkg_len} {'package' if pkg_len == 1 else 'packages'} to {db_name!r}.')

        try:
            subprocess.run(
                [
                    'repo-add', '--quiet', '--sign', db_name,
                    *package_paths,
                ],
                check=True,
                cwd=shared.resolver.get_dest(),
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
        package_names = [
            built.info.pkgname for built in  existing_built
            if built.info.pkgbase in pkgnames and built.info.pkgarch == arch
        ]

        pkg_len = len(package_names)
        db_name = f'{arch}/{repo_name}.db.tar.zst'
        shared.logger.info(f'Removing {pkg_len} {'package' if pkg_len == 1 else 'packages'} from {db_name!r}.')

        try:
            subprocess.run(
                [
                    'repo-remove', '--quiet', '--sign', db_name,
                    *package_names,
                ],
                check=True,
                cwd=shared.resolver.get_dest(),
            )
        except subprocess.CalledProcessError as err:
            raise AlrinPackageMetadataError('Repository update failed') from err
