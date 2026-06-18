import logging
import shutil

import click

from alrin.buildinfo import get_existing_built
from alrin.logging import bind_logger_to_subject, setup_logging
from alrin.resolver import AlrinPathResolver
from alrin.workflow import alpmdb_remove_packages, remove_built_file, unregister_submodule

from .group import AlrinSharedState, alrin


logger = logging.getLogger(__name__)


@alrin.command()
@click.argument('pkgname')
@click.option('-v', '--verbose', is_flag=True)
@click.pass_obj
@bind_logger_to_subject(logger, lambda shared, pkgname, verbose: pkgname)  # noqa: ARG005
def pkg_remove(shared: AlrinSharedState, pkgname: str, verbose: bool) -> None:
    setup_logging(shared.verbose_logging or verbose)

    resolver = AlrinPathResolver(shared.vault)
    pkg_path = resolver.get_pkg(pkgname)

    logger.info('Unregistering git submodule.')

    unregister_submodule(shared, pkgname)

    if pkg_path.exists():
        rel_path = resolver.relativize(pkg_path)
        logger.info(f'Removing {rel_path}.')
        shutil.rmtree(pkg_path)

    with shared.vault.storage as conn, conn.get_mutator(pkg_path) as mut:
        if len(mut) > 0:
            logger.info('Clearing Viat metadata.')
            mut.clear()

    existing_built = [existing for existing in get_existing_built(shared) if existing.info.pkgbase == pkgname]

    if len(existing_built) > 0:
        logger.info('Updating ALPM database.')
        alpmdb_remove_packages(shared, pkgname)

    for existing in existing_built:
        logger.info(f'Removing {existing.info.pkgarch}/{existing.path.name}.')
        remove_built_file(existing)
