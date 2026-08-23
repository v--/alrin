import logging

import click

from alrin.exceptions import AlrinPackageMetadataError
from alrin.logging import inject_subject, setup_logging
from alrin.pkginfo import AlrinBuiltPackage, PackageNameArchPair
from alrin.source import AlrinPackageSource
from alrin.state import AlrinSharedState
from alrin.workflow import (
    alpmdb_add_package_files,
    alpmdb_bulk_remove_packages,
    clean_worktree,
    makepkg_inside_jail,
    preprocess_pkgbuild,
    update_repo,
)
from alrin.workflow.dest import process_built_files

from .group import bulk as bulk_cli


logger = logging.getLogger(__name__)


@bulk_cli.command()
@click.option('-v', '--verbose', is_flag=True)
@click.pass_obj
def update(shared: AlrinSharedState, verbose: bool) -> None:
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
                # ruff: ignore[error-instead-of-exception]
                logger.error('Build error.')

                if click.confirm('Abort?', default=True):
                    raise click.ClickException('Update aborted') from err
            else:
                updated.append(pkg)

    built_files_in_dest = list[AlrinBuiltPackage]()
    obsolete_architectures = list[PackageNameArchPair]()

    for pkg in updated:
        processor = process_built_files(pkg)
        built_files_in_dest.extend(processor.built_files_in_dest)
        obsolete_architectures.extend(processor.obsolete_architectures)
        clean_worktree(pkg)

    if len(updated) > 0:
        alpmdb_add_package_files(pkg.shared, processor.built_files_in_dest)
        alpmdb_bulk_remove_packages(pkg.shared, obsolete_architectures)
    else:
        logger.info('No package updates.')
