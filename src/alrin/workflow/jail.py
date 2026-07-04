import logging
import subprocess

from alrin.exceptions import AlrinPackageMetadataError
from alrin.logging import inject_subject
lazy from alrin.source import AlrinPackageSource


logger = logging.getLogger(__name__)


def makepkg_inside_jail(pkg: AlrinPackageSource, builddate: int | None = None) -> None:
    jail_path = pkg.shared.resolver.get_jail()
    pacman_conf_src = pkg.shared.resolver.get_root().joinpath('pacman.conf')

    # This variable will get reused
    extra_args = list[str]()

    if pacman_conf_src.exists():
        logger.debug('Synchronizing pacman.conf.')
        extra_args = ['-C', pacman_conf_src.as_posix()]

    if jail_path.exists():
        logger.info('Preparing existing jail.')

        try:
            subprocess.run(
                [
                    'arch-nspawn', *extra_args, jail_path.joinpath('root').as_posix(),
                    'pacman', '--sync', '--refresh', '--sysupgrade',
                ],
                check=True,
                cwd=pkg.shared.resolver.get_dest(),
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
                    *extra_args,
                    jail_path.joinpath('root').as_posix(),
                    'base-devel',
                ],
                check=True,
            )
        except subprocess.CalledProcessError as err:
            raise AlrinPackageMetadataError('Jail creation failed') from err

    with inject_subject(logger, pkg.pkgname):
        logger.info('Building inside jail.')

    extra_args = []

    if pkg.viat_meta.skip_pgp:
        extra_args = ['--', '--skippgpcheck']

    try:
        subprocess.run(
            [
                'makechrootpkg',
                '-c',  # Clean before building
                '-r', jail_path.as_posix(),
                '-l', 'build',  # The directory to use as a working copy
                'base-devel',
                *extra_args,
            ],
            check=True,
            cwd=pkg.get_abs_path(),
            env={'SOURCE_DATE_EPOCH': str(builddate)} if builddate is not None else {},
        )
    except subprocess.CalledProcessError as err:
        raise AlrinPackageMetadataError('Build failed') from err
