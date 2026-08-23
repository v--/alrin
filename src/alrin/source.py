import logging
import pathlib
import subprocess

import pygit2
from alpm.alpm_srcinfo import SourceInfoError, source_info_from_file
from alpm.type_aliases import SourceInfo

from alrin.exceptions import AlrinPackageMetadataError
from alrin.logging import bind_logger_to_subject
from alrin.metadata import AlrinPackageVersion, AlrinPkgbuildMetadata
from alrin.state import AlrinSharedState
from alrin.wrappers import alpm_srcinfo_create


logger = logging.getLogger(__name__)


# ruff: ignore[unused-lambda-argument]
@bind_logger_to_subject(logger, lambda shared, pkgname: pkgname)
def read_srcinfo_with_retry(shared: AlrinSharedState, pkgname: str) -> SourceInfo:
    pkg_path = shared.resolver.get_pkg(pkgname)

    try:
        return source_info_from_file(pkg_path / '.SRCINFO')
    except SourceInfoError:
        pass

    logger.warning('Could not read .SRCINFO. Trying to recreate it...')

    try:
        alpm_srcinfo_create(
            pkg_path / 'PKGBUILD',
            pkg_path / '.SRCINFO',
        )
    except subprocess.CalledProcessError as err:
        raise AlrinPackageMetadataError('Failed to recreate .SRCINFO') from err

    try:
        return source_info_from_file(pkg_path / '.SRCINFO')
    except SourceInfoError as err:
        raise AlrinPackageMetadataError('Failed to read recreated .SRCINFO') from err


class AlrinPackageSource:
    shared: AlrinSharedState
    pkgbase: str

    repo: pygit2.Repository
    version: AlrinPackageVersion
    viat_meta: AlrinPkgbuildMetadata

    def __init__(self, shared: AlrinSharedState, pkgbase: str) -> None:
        self.shared = shared
        self.pkgbase = pkgbase
        pkg_path = self.get_abs_path()

        if not shared.vault.tracker.is_tracked(pkg_path):
            raise AlrinPackageMetadataError(f'Unrecognized package name {pkgbase}')

        with shared.vault.storage as conn, conn.get_reader(pkg_path) as reader:
            self.viat_meta = AlrinPkgbuildMetadata.from_json(reader)

        git_path = pkg_path if self.viat_meta.git_root is None else shared.resolver.get_root() / self.viat_meta.git_root

        try:
            self.repo = pygit2.Repository(pkg_path)
        except pygit2.GitError as err:
            git_rel_path = shared.resolver.relativize(git_path)
            raise AlrinPackageMetadataError(f'Path {git_rel_path} is not a valid git repository') from err

        self.reread_version()

    def get_abs_path(self) -> pathlib.Path:
        return self.shared.resolver.get_pkg(self.pkgbase)

    def get_rel_path(self) -> pathlib.Path:
        return self.shared.vault.resolver.relativize(self.get_abs_path())

    def read_srcinfo(self) -> SourceInfo:
        return read_srcinfo_with_retry(self.shared, self.pkgbase)

    def reread_version(self) -> None:
        self.version = AlrinPackageVersion.from_srcinfo(self.read_srcinfo())
