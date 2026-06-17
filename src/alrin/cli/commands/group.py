import contextlib
import os
import pathlib
lazy from collections.abc import Generator

import click
from viat import ViatError, ViatVault
from viat.vault import locate_existing_vault_root

from alrin.exceptions import AlrinPackageError
from alrin.resolver import AlrinPathResolver
from alrin.state import AlrinSharedState


@contextlib.contextmanager
def with_cli_exception_handler() -> Generator[None]:
    """Set up an handler that pretty alrints viat exceptions."""
    try:
        yield
    except AlrinPackageError as err:
        raise click.ClickException(f'{err}.') from err
    except ViatError as err:
        raise click.ClickException(err.get_human_readable_string()) from err


@click.group()
@click.pass_context
@click.option('-v', '--verbose', is_flag=True)
def alrin(ctx: click.Context, verbose: bool) -> None:
    with with_cli_exception_handler():
        vault = ViatVault(
            locate_existing_vault_root(
                pathlib.Path(os.environ.get('ALRIN_STATE_REPO', pathlib.Path.cwd())),
            ),
        )

    ctx.obj = AlrinSharedState(
        vault,
        AlrinPathResolver(vault),
        verbose_logging=verbose,
    )

    ctx.with_resource(with_cli_exception_handler())
