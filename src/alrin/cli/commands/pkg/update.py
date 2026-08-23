import logging

import click

from alrin.logging import bind_logger_to_subject, setup_logging
from alrin.source import AlrinPackageSource
from alrin.state import AlrinSharedState
from alrin.workflow import (
    clean_worktree,
    makepkg_inside_jail,
    preprocess_pkgbuild,
    process_built_files,
    update_repo,
    update_version_from_build_files,
)

from .group import pkg as pkg_cli


logger = logging.getLogger(__name__)


@pkg_cli.command()
@click.argument('pkgbase')
@click.option('-v', '--verbose', is_flag=True)
@click.pass_obj
# ruff: ignore[unused-lambda-argument]
@bind_logger_to_subject(logger, lambda shared, pkgbase, verbose: pkgbase)
def update(shared: AlrinSharedState, pkgbase: str, verbose: bool) -> None:
    setup_logging(shared.verbose_logging or verbose)

    pkg = AlrinPackageSource(shared, pkgbase)
    update_repo(pkg)
    preprocess_pkgbuild(pkg)

    if pkg.version == pkg.viat_meta.version:
        logger.info('Package is up-to-date.')
        clean_worktree(pkg)
        return

    makepkg_inside_jail(pkg)
    update_version_from_build_files(pkg)
    process_built_files(pkg)
    clean_worktree(pkg)
