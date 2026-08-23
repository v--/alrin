import click

from alrin.exceptions import AlrinPackageMetadataError
from alrin.logging import setup_logging
from alrin.source import AlrinPackageSource
from alrin.state import AlrinSharedState
from alrin.workflow import (
    clean_worktree,
    makepkg_inside_jail,
    preprocess_pkgbuild,
    process_built_files,
    update_version_from_build_files,
)

from .group import pkg as pkg_cli


@pkg_cli.command()
@click.argument('pkgbase')
@click.option('-v', '--verbose', is_flag=True)
@click.pass_obj
def rebuild(shared: AlrinSharedState, pkgbase: str, verbose: bool) -> None:
    setup_logging(shared.verbose_logging or verbose)

    pkg = AlrinPackageSource(shared, pkgbase)

    clean_worktree(pkg)
    preprocess_pkgbuild(pkg)
    makepkg_inside_jail(pkg, builddate=pkg.viat_meta.builddate)
    update_version_from_build_files(pkg)

    if pkg.version > pkg.viat_meta.version:
        raise AlrinPackageMetadataError(f'Package {pkgbase} has dynamically updated its version and needs to be properly updated')

    process_built_files(pkg)
    clean_worktree(pkg)
