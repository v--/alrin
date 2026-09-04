import logging
import shutil

import click

from alrin.logging import bind_logger_to_subject, setup_logging
from alrin.pkginfo import get_existing_built
from alrin.resolver import AlrinPathResolver
from alrin.state import AlrinSharedState
from alrin.workflow import alpmdb_bulk_remove_packages, remove_built_file, unregister_submodule

from .group import pkg as pkg_cli


logger = logging.getLogger(__name__)


@pkg_cli.command()
@click.argument('pkgbase')
@click.option('-v', '--verbose', is_flag=True)
@click.pass_obj
# ruff: ignore[unused-lambda-argument]
@bind_logger_to_subject(logger, lambda shared, pkgbase, verbose: pkgbase)
def remove(shared: AlrinSharedState, pkgbase: str, verbose: bool) -> None:
    setup_logging(shared.verbose_logging or verbose)

    resolver = AlrinPathResolver(shared.vault)
    pkg_path = resolver.get_pkg(pkgbase)

    unregister_submodule(shared, pkgbase)

    if pkg_path.exists():
        rel_path = resolver.relativize(pkg_path)
        logger.info(f'Removing {rel_path}.')
        shutil.rmtree(pkg_path)

    with shared.vault.storage as conn, conn.get_mutator(pkg_path) as mut:
        if len(mut) > 0:
            logger.info('Clearing Viat metadata.')
            mut.clear()

    existing_built = [pair for pair in get_existing_built(shared.resolver) if pair.built.info.pkgbase == pkgbase]

    if len(existing_built) > 0:
        logger.info('Updating ALPM database.')
        alpmdb_bulk_remove_packages(shared, [], existing_built)

    for existing, arch in existing_built:
        logger.info(f'Removing {arch}/{existing.path.name}.')
        remove_built_file(existing)
