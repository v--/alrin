import logging
import subprocess

from alrin.exceptions import AlrinJailError, AlrinPackageMetadataError
from alrin.logging import inject_subject
from alrin.resolver import AlrinPathResolver
from alrin.source import AlrinPackageSource
from alrin.wrappers import arch_nspawn, makechrootpkg, mkarchroot


logger = logging.getLogger(__name__)


class AlrinJailManager:
    resolver: AlrinPathResolver

    def __init__(self, resolver: AlrinPathResolver) -> None:
        self.resolver = resolver

    def exists(self) -> bool:
        return self.resolver.get_jail().exists()

    def create_new(self) -> None:
        jail_path = self.resolver.get_jail()

        if jail_path.exists():
            raise AlrinJailError('Jail already exists')

        logger.info('Creating new jail.')
        jail_path.mkdir()

        try:
            mkarchroot(
                working_dir=jail_path / 'root',
                package_list=['base-devel'],
            )
        except subprocess.CalledProcessError as err:
            raise AlrinPackageMetadataError('Jail creation failed') from err

    def update_packages(self) -> None:
        logger.info('Updating packages in existing jail.')

        try:
            arch_nspawn(
                working_dir=self.resolver.get_jail() / 'root',
                command=['pacman', '--sync', '--refresh', '--sysupgrade', '--noconfirm'],
                pacman_config=self.resolver.get_root().joinpath('pacman.conf'),
                cwd=self.resolver.get_dest(),
            )
        except subprocess.CalledProcessError as err:
            raise AlrinPackageMetadataError('Jail update failed') from err

    def makepkg(self, pkg: AlrinPackageSource, builddate: int | None = None) -> None:
        with inject_subject(logger, pkg.pkgname):
            logger.info('Building inside jail.')

        try:
            makechrootpkg(
                chrootdir=self.resolver.get_jail(),
                clean_before_building=True,
                working_dir_name='build',
                cwd=pkg.get_abs_path(),
                SOURCE_DATE_EPOCH=builddate,
                GNUPGHOME=pkg.shared.resolver.get_keyring(),
            )
        except subprocess.CalledProcessError as err:
            raise AlrinPackageMetadataError('Build failed') from err


def makepkg_inside_jail(pkg: AlrinPackageSource, builddate: int | None = None) -> None:
    jail = AlrinJailManager(pkg.shared.resolver)

    if jail.exists():
        jail.update_packages()
    else:
        jail.create_new()

    jail.makepkg(pkg, builddate)
