import logging
import shutil

import click

from alrin.buildinfo import get_existing_built
from alrin.logging import setup_logging
from alrin.resolver import AlrinPathResolver
from alrin.workflow import alpmdb_remove_packages, remove_built_file, unregister_submodule

from .group import AlrinSharedState, alrin


logger = logging.getLogger(__name__)


@alrin.command()
@click.argument('pkgname')
@click.pass_obj
def pkg_remove(shared: AlrinSharedState, pkgname: str) -> None:
    setup_logging()

    resolver = AlrinPathResolver(shared.vault)
    pkg_path = resolver.get_pkg(pkgname)

    bound_logger = logging.LoggerAdapter(logger, extra=dict(subject=pkgname))
    bound_logger.info('Unregistering git submodule.')
    unregister_submodule(shared, pkgname)

    if pkg_path.exists():
        rel_path = resolver.relativize(pkg_path)
        bound_logger.info(f'Removing {rel_path.as_posix()!r}.')
        shutil.rmtree(pkg_path)

    with shared.vault.storage as conn, conn.get_mutator(pkg_path) as mut:
        if len(mut) > 0:
            bound_logger.info('Clearing Viat metadata.')
            mut.clear()

    existing_built = [existing for existing in get_existing_built(shared) if existing.info.pkgbase == pkgname]

    if len(existing_built) > 0:
        bound_logger.info('Updating ALPM database.')
        alpmdb_remove_packages(shared, pkgname)

    for existing in existing_built:
        bound_logger.info(f'Removing {existing.info.pkgarch}/{existing.path.name}.')
        remove_built_file(existing)
