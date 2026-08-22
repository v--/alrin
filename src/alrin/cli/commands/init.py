import click

from alrin.exceptions import AlrinVaultError
from alrin.logging import setup_logging
from alrin.state import get_vault_path
from alrin.workflow.state import initialize_alrin_vault

from .group import alrin_cli


@click.option('-v', '--verbose', is_flag=True)
@alrin_cli.command()
@click.pass_context
def init(ctx: click.Context, verbose: bool) -> None:
    setup_logging(verbose or ctx.meta['verbose'])
    repo_path = get_vault_path()

    try:
        is_empty = sum(1 for subpath in repo_path.iterdir()) == 0
    except FileNotFoundError as err:
        raise AlrinVaultError(f'Invalid directory {repo_path}') from err

    if not is_empty:
        raise AlrinVaultError(f'Cannot initialize nonempty directory {repo_path}')

    initialize_alrin_vault(repo_path)
