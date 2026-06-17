import logging
import subprocess

from alrin.exceptions import AlrinPackageMetadataError
from alrin.logging import inject_subject
lazy from alrin.source import AlrinPackageSource


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

    with inject_subject(logger, pkg.pkgname):
        logger.info('Building inside jail.')

    extra_args = list[str]()

    if pkg.viat_meta.skip_pgp:
        extra_args.append('--skippgpcheck')

    if len(extra_args) > 0:
        extra_args.insert(0, '--')

    try:
        subprocess.run(
            [
                'makechrootpkg',
                '-c', # Clean before building
                '-r', jail_path.as_posix(),
                '-l', 'build', # The directory to use as a working copy
                'base-devel',
                *extra_args,
            ],
            check=True,
            cwd=pkg.get_abs_path(),
            env={'SOURCE_DATE_EPOCH': str(builddate)} if builddate is not None else {},
        )
    except subprocess.CalledProcessError as err:
        raise AlrinPackageMetadataError('Build failed') from err
