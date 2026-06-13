import shutil

import click

from alrin.buildinfo import get_existing_built
from alrin.resolver import AlrinPathResolver
from alrin.workflow import alpmdb_remove_packages, remove_built_file, unregister_submodule

from .group import AlrinSharedState, alrin


@alrin.command()
@click.argument('pkgname')
@click.pass_obj
def pkg_remove(shared: AlrinSharedState, pkgname: str) -> None:
    resolver = AlrinPathResolver(shared.vault)
    pkg_path = resolver.pkg_get(pkgname)
    rel_path = resolver.relativize(pkg_path)

    shared.logger.info(f'Unregistering git submodule {rel_path.as_posix()!r}.')
    unregister_submodule(shared, rel_path)

    if pkg_path.exists():
        shared.logger.info(f'Removing {rel_path.as_posix()!r}.')
        shutil.rmtree(pkg_path)

    with shared.vault.storage as conn, conn.get_mutator(pkg_path) as mut:
        if len(mut) > 0:
            shared.logger.info(f'Clearing Viat metadata for {rel_path.as_posix()!r}.')
            mut.clear()

    existing_built = [existing for existing in get_existing_built(shared) if existing.info.pkgbase == pkgname]

    if len(existing_built) > 0:
        shared.logger.info('Rebuilding ALPM database.')
        alpmdb_remove_packages(shared, pkgname)

    for existing in existing_built:
        shared.logger.info(f'Removing {existing.path}.')
        remove_built_file(existing)
