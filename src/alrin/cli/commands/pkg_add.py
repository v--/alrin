import logging
import shutil

import click
import pygit2
from alpm.alpm_srcinfo import SourceInfoError, source_info_from_file

from alrin.exceptions import AlrinPackageMetadataError
from alrin.logging import bind_logger_to_subject, setup_logging
from alrin.resolver import AlrinPathResolver
from alrin.source import AlrinPackageSource
from alrin.workflow import (
    alpmdb_add_packages,
    clean_worktree,
    makepkg_inside_jail,
    postprocess_pkgbuild,
    preprocess_pkgbuild,
    process_built_files,
    unregister_submodule,
)

from .group import AlrinSharedState, alrin


URL_PATTERN = 'https://aur.archlinux.org/{pkgname}.git'
logger = logging.getLogger(__name__)


@alrin.command()
@click.argument('pkgname')
@click.pass_obj
@bind_logger_to_subject(logger, lambda _, pkgname: pkgname)
def pkg_add(shared: AlrinSharedState, pkgname: str) -> None:
    setup_logging()

    url = URL_PATTERN.format(pkgname=pkgname)
    resolver = AlrinPathResolver(shared.vault)
    pkg_path = resolver.get_pkg(pkgname)
    rel_path = resolver.relativize(pkg_path)

    if pkg_path.exists():
        raise AlrinPackageMetadataError(f'Directory at {rel_path.as_posix()!r} already exists')

    logger.info(f'Adding {url} as a submodule into {rel_path.as_posix()!r}.')
    root_repo = pygit2.Repository(shared.resolver.get_root())

    try:
        root_repo.submodules.add(url, rel_path.as_posix())
    except pygit2.GitError as err:
        logger.error(f'Removing invalid repository from {rel_path.as_posix()!r}.')  # noqa: TRY400
        shutil.rmtree(rel_path)
        unregister_submodule(shared, pkgname)
        raise AlrinPackageMetadataError(f'Invalid git repository at {url!r}') from err

    try:
        srcinfo = source_info_from_file(pkg_path.joinpath('.SRCINFO'))
    except SourceInfoError as err:
        logger.error(f'Removing invalid repository from {rel_path.as_posix()!r}.')  # noqa: TRY400
        shutil.rmtree(rel_path)
        unregister_submodule(shared, pkgname)
        raise AlrinPackageMetadataError(f'Could not read .SRCINFO at {rel_path.as_posix()!r}') from err

    logger.info('Adding mock Viat metadata.')
    with shared.vault.storage as conn, conn.get_mutator(pkg_path) as mut:
        mut['pkgver'] = '0'
        mut['pkgrel'] = '0'

        if any(str(dep) == 'python' for dep in srcinfo.base.dependencies) and click.confirm('Mark as Python package?', True):
            mut['add_python_suffix'] = True

    logger.info('Building.')
    pkg = AlrinPackageSource(shared, pkgname)
    preprocess_pkgbuild(pkg)
    makepkg_inside_jail(pkg)
    postprocess_pkgbuild(pkg)

    dest_files = process_built_files(pkg)
    clean_worktree(pkg)
    alpmdb_add_packages(pkg.shared, dest_files)
