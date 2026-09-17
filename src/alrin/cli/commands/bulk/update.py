import json
import logging
import pathlib

import click

from alrin.exceptions import AlrinPackageMetadataError
from alrin.logging import inject_subject, setup_logging
from alrin.source import AlrinPackageSource
from alrin.state import AlrinSharedState
from alrin.workflow import (
    clean_worktree,
    makepkg_inside_jail,
    preprocess_pkgbuild,
    process_built_files,
    update_repo,
)

from .group import bulk as bulk_cli


logger = logging.getLogger(__name__)


@bulk_cli.command()
@click.option('-v', '--verbose', is_flag=True)
@click.option('--summary-path', type=click.Path(writable=True, dir_okay=False, path_type=pathlib.Path))
@click.pass_obj
def update(shared: AlrinSharedState, summary_path: pathlib.Path | None, verbose: bool) -> None:
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

    if summary_path:
        with summary_path.open('w') as json_file:
            json.dump(
                [
                    {
                        'pkgbase': pkg.pkgbase,
                        'oldVersion': str(pkg.viat_meta.version),
                        'newVersion': str(pkg.version),
                    } for pkg in updated
                ],
                json_file,
            )

    if len(updated) == 0:
        logger.info('No package updates.')
        return

    process_built_files(*updated)

    for pkg in updated:
        clean_worktree(pkg)
