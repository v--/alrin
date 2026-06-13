import contextlib
import os
import pathlib
from typing import TYPE_CHECKING

import click
from viat import ViatError, ViatVault
from viat.vault import locate_existing_vault_root

from alrin.exceptions import AlrinPackageError
from alrin.logging import AlrinLogger
from alrin.resolver import AlrinPathResolver
from alrin.state import AlrinSharedState


if TYPE_CHECKING:
    from collections.abc import Generator


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
@click.version_option()
@click.pass_context
def alrin(ctx: click.Context) -> None:
    with with_cli_exception_handler():
        vault = ViatVault(
            locate_existing_vault_root(
                pathlib.Path(os.environ.get('ALRIN_STATE_REPO', pathlib.Path.cwd())),
            ),
        )

    ctx.obj = AlrinSharedState(
        vault,
        AlrinPathResolver(vault),
        AlrinLogger('alrin'),
    )

    ctx.with_resource(with_cli_exception_handler())
