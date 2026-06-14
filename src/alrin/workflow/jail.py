import logging
import subprocess
from typing import TYPE_CHECKING

from alrin.exceptions import AlrinPackageMetadataError


if TYPE_CHECKING:
    from alrin.source import AlrinPackageSource


logger = logging.getLogger(__name__)


def makepkg_inside_jail(pkg: AlrinPackageSource, builddate: int | None = None) -> None:
    jail_path = pkg.shared.resolver.get_jail()

    if jail_path.exists():
        logger.info('Preparing existing jail.')

        try:
            subprocess.run(
                [
                    'arch-nspawn', jail_path.joinpath('root').as_posix(),
                    'pacman', '--sync', '--refresh', '--sysupgrade',
                ],
                check=True,
            )
        except subprocess.CalledProcessError as err:
            raise AlrinPackageMetadataError('Jail update failed') from err
    else:
        logger.info('Creating new jail.')
        jail_path.mkdir()

        try:
            subprocess.run(
                [
                    'mkarchroot',
                    '-C', '/etc/pacman.conf',
                    '-f', '/etc/pacman.d/mirrorlist.custom:/etc/pacman.d/mirrorlist.custom',
                    jail_path.joinpath('root').as_posix(),
                    'base-devel',
                ],
                check=True,
            )
        except subprocess.CalledProcessError as err:
            raise AlrinPackageMetadataError('Jail creation failed') from err


    pkg.bound_logger.info('Building inside jail.')

    try:
        subprocess.run(
            [
                'makechrootpkg',
                '-c', # Clean before building
                '-r', jail_path.as_posix(),
                '-l', 'build', # The directory to use as a working copy
                'base-devel',
            ],
            check=True,
            cwd=pkg.get_abs_path(),
            env={'SOURCE_DATE_EPOCH': str(builddate)} if builddate is not None else {},
        )
    except subprocess.CalledProcessError as err:
        raise AlrinPackageMetadataError('Build failed') from err
