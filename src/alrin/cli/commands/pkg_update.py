import click

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


@alrin.command()
@click.argument('pkgname')
@click.pass_obj
def pkg_update(shared: AlrinSharedState, pkgname: str) -> None:
    pkg = AlrinPackageSource(shared, pkgname)
    update_repo(pkg)
    preprocess_pkgbuild(pkg)

    if pkg.version == pkg.viat_meta.version:
        shared.logger.info(f'Package {pkgname!r} is up-to-date.')
        clean_worktree(pkg)
        return

    makepkg_inside_jail(pkg)
    postprocess_pkgbuild(pkg)

    dest_files = process_built_files(pkg)
    clean_worktree(pkg)
    alpmdb_add_packages(pkg.shared, dest_files)
