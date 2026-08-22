import click

from alrin.exceptions import AlrinRepositoryError
from alrin.logging import setup_logging
from alrin.state import get_state_repo_path
from alrin.workflow.state import initialize_state_repo

from .group import alrin


@click.option('-v', '--verbose', is_flag=True)
@alrin.command()
@click.pass_context
def init(ctx: click.Context, verbose: bool) -> None:
    setup_logging(verbose or ctx.meta['verbose'])
    repo_path = get_state_repo_path()

    try:
        is_empty = sum(1 for subpath in repo_path.iterdir()) == 0
    except FileNotFoundError as err:
        raise AlrinRepositoryError(f'Invalid directory {repo_path}') from err

    if not is_empty:
        raise AlrinRepositoryError(f'Cannot initialize nonempty directory {repo_path}')

    initialize_state_repo(repo_path)
