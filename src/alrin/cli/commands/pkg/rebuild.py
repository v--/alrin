import click

from alrin.exceptions import AlrinPackageMetadataError
from alrin.logging import setup_logging
from alrin.source import AlrinPackageSource
from alrin.state import AlrinSharedState
from alrin.workflow import (
    alpmdb_add_packages,
    clean_worktree,
    makepkg_inside_jail,
    postprocess_pkgbuild,
    preprocess_pkgbuild,
    process_built_files,
)

from .group import pkg as pkg_cli


@pkg_cli.command()
@click.argument('pkgname')
@click.option('-v', '--verbose', is_flag=True)
@click.pass_obj
def rebuild(shared: AlrinSharedState, pkgname: str, verbose: bool) -> None:
    setup_logging(shared.verbose_logging or verbose)

    pkg = AlrinPackageSource(shared, pkgname)

    clean_worktree(pkg)
    preprocess_pkgbuild(pkg)
    makepkg_inside_jail(pkg, builddate=pkg.viat_meta.builddate)
    postprocess_pkgbuild(pkg)

    if pkg.version > pkg.viat_meta.version:
        raise AlrinPackageMetadataError(f'Package {pkgname} has dynamically updated its version and needs to be properly updated')

    dest_files = process_built_files(pkg)
    clean_worktree(pkg)
    alpmdb_add_packages(pkg.shared, dest_files)
