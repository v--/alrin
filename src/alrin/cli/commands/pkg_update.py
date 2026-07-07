import logging

import click

from alrin.logging import bind_logger_to_subject, setup_logging
from alrin.source import AlrinPackageSource
from alrin.workflow import (
    alpmdb_add_packages,
    clean_worktree,
    makepkg_inside_jail,
    postprocess_pkgbuild,
    preprocess_pkgbuild,
    process_built_files,
    update_repo,
)

from .group import AlrinSharedState, alrin


logger = logging.getLogger(__name__)


@alrin.command()
@click.argument('pkgname')
@click.option('-v', '--verbose', is_flag=True)
@click.pass_obj
# ruff: ignore[unused-lambda-argument]
@bind_logger_to_subject(logger, lambda shared, pkgname, verbose: pkgname)
def pkg_update(shared: AlrinSharedState, pkgname: str, verbose: bool) -> None:
    setup_logging(shared.verbose_logging or verbose)

    pkg = AlrinPackageSource(shared, pkgname)
    update_repo(pkg)
    preprocess_pkgbuild(pkg)

    if pkg.version == pkg.viat_meta.version:
        logger.info('Package is up-to-date.')
        clean_worktree(pkg)
        return

    makepkg_inside_jail(pkg)
    postprocess_pkgbuild(pkg)

    dest_files = process_built_files(pkg)
    clean_worktree(pkg)
    alpmdb_add_packages(pkg.shared, dest_files)
