import logging
lazy import pathlib

import pygit2
from alpm.alpm_srcinfo import SourceInfoError, source_info_from_file
lazy from alpm.type_aliases import SourceInfo

from alrin.exceptions import AlrinPackageMetadataError
from alrin.logging import inject_subject
from alrin.metadata import AlrinMetadata, AlrinPackageVersion
from alrin.workflow.pkgbuild import extract_pkgbuild_version
lazy from alrin.state import AlrinSharedState


logger = logging.getLogger(__name__)


class AlrinPackageSource:
    shared: AlrinSharedState
    pkgname: str

    repo: pygit2.Repository
    version: AlrinPackageVersion
    viat_meta: AlrinMetadata

    def __init__(self, shared: AlrinSharedState, pkgname: str) -> None:
        self.shared = shared
        self.pkgname = pkgname
        pkg_path = self.get_abs_path()

        if not shared.vault.tracker.is_tracked(pkg_path):
            raise AlrinPackageMetadataError(f'Unrecognized package name {pkgname!r}')

        with shared.vault.storage as conn, conn.get_reader(pkg_path) as reader:
            self.viat_meta = AlrinMetadata.from_json(reader)

        git_path = pkg_path if self.viat_meta.git_root is None else shared.resolver.get_root() / self.viat_meta.git_root

        try:
            self.repo = pygit2.Repository(pkg_path)
        except pygit2.GitError as err:
            git_rel_path = shared.resolver.relativize(git_path)
            raise AlrinPackageMetadataError(f'Path {git_rel_path.as_posix()!r} is not a valid git repository') from err

        try:
            self.version = AlrinPackageVersion.from_srcinfo(self.read_srcinfo())
        except SourceInfoError:
            with inject_subject(logger, pkgname):
                logger.info('Could not read .SRCINFO. Using PKGBUILD instead.')

            with self.get_abs_path().joinpath('PKGBUILD').open() as file:
                self.version = extract_pkgbuild_version(file)

    def get_abs_path(self) -> pathlib.Path:
        return self.shared.resolver.get_pkg(self.pkgname)

    def get_rel_path(self) -> pathlib.Path:
        return self.shared.vault.resolver.relativize(self.get_abs_path())

    def read_srcinfo(self) -> SourceInfo:
        return source_info_from_file(self.get_abs_path().joinpath('.SRCINFO'))
