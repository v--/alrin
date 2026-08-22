import click

from alrin.cli.commands.group import alrin_cli
from alrin.workflow import initialize_shared_state


@alrin_cli.group()
@click.pass_context
@click.option('-v', '--verbose', is_flag=True)
def pkg(ctx: click.Context, verbose: bool) -> None:
    ctx.obj = initialize_shared_state(verbose=verbose or ctx.meta['verbose'])
