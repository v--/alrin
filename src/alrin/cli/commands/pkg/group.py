import click

from alrin.cli.commands.group import alrin


@alrin.group()
@click.pass_context
@click.option('-v', '--verbose', is_flag=True)
def pkg(ctx: click.Context, verbose: bool) -> None:
    if verbose:
        ctx.obj.verbose = verbose
