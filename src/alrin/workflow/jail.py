import logging
import subprocess

from alrin.exceptions import AlrinPackageMetadataError
from alrin.logging import inject_subject
from alrin.wrappers import arch_nspawn, makechrootpkg, mkarchroot
lazy from alrin.source import AlrinPackageSource


logger = logging.getLogger(__name__)


def makepkg_inside_jail(pkg: AlrinPackageSource, builddate: int | None = None) -> None:
    jail_path = pkg.shared.resolver.get_jail()

    if jail_path.exists():
        logger.info('Preparing existing jail.')

        try:
            arch_nspawn(
                working_dir=jail_path / 'root',
                command=['pacman', '--sync', '--refresh', '--sysupgrade', '--noconfirm'],
                pacman_config=pkg.shared.resolver.get_root().joinpath('pacman.conf'),
                cwd=pkg.shared.resolver.get_dest(),
            )
        except subprocess.CalledProcessError as err:
            raise AlrinPackageMetadataError('Jail update failed') from err
    else:
        logger.info('Creating new jail.')
        jail_path.mkdir()

        try:
            mkarchroot(
                working_dir=jail_path / 'root',
                package_list=['base-devel'],
            )
        except subprocess.CalledProcessError as err:
            raise AlrinPackageMetadataError('Jail creation failed') from err

    with inject_subject(logger, pkg.pkgname):
        logger.info('Building inside jail.')

    try:
        makechrootpkg(
            chrootdir=jail_path,
            clean_before_building=True,
            working_dir_name='build',
            cwd=pkg.get_abs_path(),
            SOURCE_DATE_EPOCH=builddate,
            GNUPGHOME=pkg.shared.resolver.get_keyring(),
        )
    except subprocess.CalledProcessError as err:
        raise AlrinPackageMetadataError('Build failed') from err
