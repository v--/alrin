import click

from alrin.buildinfo import AlrinBuiltPackage
from alrin.exceptions import AlrinPackageMetadataError
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
@click.pass_obj
def bulk_update(shared: AlrinSharedState) -> None:
    updated = list[AlrinPackageSource]()

    for pkg_path in shared.vault.tracker.iter_paths():
        pkgname = pkg_path.name
        pkg = AlrinPackageSource(shared, pkgname)

        update_repo(pkg)
        preprocess_pkgbuild(pkg)

        if pkg.version == pkg.viat_meta.version:
            shared.logger.info(f'Package {pkgname!r} is up-to-date.')
            clean_worktree(pkg)
            continue

        shared.logger.info(f'Rebuilding updated package {pkgname!r}.')

        try:
            makepkg_inside_jail(pkg)
        except AlrinPackageMetadataError as err:
            shared.logger.error(f'Error building {pkgname!r}.')  # noqa: TRY400

            if click.confirm('Abort?', default=True):
                raise click.ClickException('Update aborted') from err
        else:
            updated.append(pkg)

    dest_files = list[AlrinBuiltPackage]()

    for pkg in updated:
        postprocess_pkgbuild(pkg)
        dest_files.extend(
            process_built_files(pkg),
        )
        clean_worktree(pkg)

    if len(updated) > 0:
        alpmdb_add_packages(shared, dest_files)
    else:
        shared.logger.info('No package updates')
