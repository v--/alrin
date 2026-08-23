import logging
import shutil

import click
import pygit2

from alrin.exceptions import AlrinPackageMetadataError
from alrin.logging import bind_logger_to_subject, setup_logging
from alrin.resolver import AlrinPathResolver
from alrin.source import AlrinPackageSource, read_srcinfo_with_retry
from alrin.state import AlrinSharedState
from alrin.workflow import (
    clean_worktree,
    makepkg_inside_jail,
    preprocess_pkgbuild,
    process_built_files,
    unregister_submodule,
    update_version_from_build_files,
)

from .group import pkg as pkg_cli


logger = logging.getLogger(__name__)


@pkg_cli.command()
@click.argument('pkgbase')
@click.option('-v', '--verbose', is_flag=True)
@click.option('--url-template', type=str, default='https://aur.archlinux.org/{pkgbase}.git')
@click.pass_obj
# ruff: ignore[unused-lambda-argument]
@bind_logger_to_subject(logger, lambda shared, pkgbase, url_template, verbose: pkgbase)
def add(shared: AlrinSharedState, pkgbase: str, url_template: str, verbose: bool) -> None:
    setup_logging(shared.verbose_logging or verbose)

    url = url_template.format(pkgbase=pkgbase)
    resolver = AlrinPathResolver(shared.vault)
    pkg_path = resolver.get_pkg(pkgbase)
    rel_path = resolver.relativize(pkg_path)

    if pkg_path.exists():
        raise AlrinPackageMetadataError(f'Directory at {rel_path} already exists')

    logger.info(f'Adding {url} as a submodule into {rel_path}.')
    root_repo = pygit2.Repository(shared.resolver.get_root())

    try:
        root_repo.submodules.add(url, rel_path.as_posix())
    except pygit2.GitError as err:
        logger.exception('Git error')
        logger.info(f'Removing invalid repository from {rel_path}.')
        shutil.rmtree(rel_path, ignore_errors=True)
        unregister_submodule(shared, pkgbase)
        raise AlrinPackageMetadataError(f'Invalid git repository at {url!r}') from err

    try:
        srcinfo = read_srcinfo_with_retry(shared, pkgbase)
    except AlrinPackageMetadataError:
        logger.exception('Error reading .SRCINFO')
        logger.info(f'Removing invalid repository from {rel_path}.')
        shutil.rmtree(rel_path, ignore_errors=True)
        unregister_submodule(shared, pkgbase)
        raise

    logger.info('Adding mock Viat metadata.')
    with shared.vault.storage as conn, conn.get_mutator(pkg_path) as mut:
        mut['pkgver'] = '0'
        mut['pkgrel'] = '0'

        if any(str(dep) == 'python' for dep in srcinfo.base.dependencies) and click.confirm('Add a Python version suffix to pkgrel?', True):
            mut['add_pkgrel_suffix'] = True

    logger.info('Building.')
    pkg = AlrinPackageSource(shared, pkgbase)

    preprocess_pkgbuild(pkg)
    makepkg_inside_jail(pkg)
    update_version_from_build_files(pkg)
    process_built_files(pkg)
    clean_worktree(pkg)
