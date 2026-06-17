import logging

import click

from alrin.buildinfo import AlrinBuiltPackage
from alrin.exceptions import AlrinPackageMetadataError
from alrin.logging import inject_subject, setup_logging
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
@click.option('-v', '--verbose', is_flag=True)
@click.pass_obj
def bulk_update(shared: AlrinSharedState, verbose: bool) -> None:
    setup_logging(shared.verbose_logging or verbose)
    updated = list[AlrinPackageSource]()

    for pkg_path in shared.vault.tracker.iter_paths():
        pkg = AlrinPackageSource(shared, pkg_path.name)

        with inject_subject(logger, pkg_path.name):
            update_repo(pkg)
            preprocess_pkgbuild(pkg)

            if pkg.version == pkg.viat_meta.version:
                logger.info('Package is up-to-date.')
                clean_worktree(pkg)
                continue

            logger.info('Rebuilding updated package.')

            try:
                makepkg_inside_jail(pkg)
            except AlrinPackageMetadataError as err:
                logger.error('Build error.')  # noqa: TRY400

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
        logger.info('No package updates.')
