import contextlib
from collections.abc import Generator

import click
from viat import ViatError

from alrin.exceptions import AlrinError
from alrin.wrappers import check_binary_dependencies


@contextlib.contextmanager
def with_cli_exception_handler() -> Generator[None]:
    """Set up an handler that pretty alrints viat exceptions."""
    try:
        yield
    except AlrinError as err:
        raise click.ClickException(f'{err}.') from err
    except ViatError as err:
        raise click.ClickException(err.get_human_readable_string()) from err


@click.group()
@click.pass_context
@click.option('-v', '--verbose', is_flag=True)
@click.option('--skip-dependency-check', is_flag=True, envvar='ALRIN_SKIP_DEPENDENCY_CHECK')
def alrin_cli(ctx: click.Context, verbose: bool, skip_dependency_check: bool) -> None:
    if not skip_dependency_check:
        check_binary_dependencies()

    ctx.meta['verbose'] = verbose
    ctx.with_resource(with_cli_exception_handler())
