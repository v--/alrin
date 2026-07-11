import logging

import click
import gnupg

from alrin.logging import setup_logging
from alrin.state import AlrinSharedState

from .group import keyring as keyring_cli


logger = logging.getLogger(__name__)


@keyring_cli.command()
@click.option('-v', '--verbose', is_flag=True)
@click.pass_obj
def restore(shared: AlrinSharedState, verbose: bool) -> None:
    setup_logging(shared.verbose_logging or verbose)

    if shared.resolver.get_keyring_backup().exists():
        logger.info('Importing the keyring backup.')
        gpg = gnupg.GPG(gnupghome=shared.resolver.get_keyring().as_posix())
        import_result = gpg.import_keys_file(shared.resolver.get_keyring_backup().as_posix())
        click.echo(import_result.stderr, nl=False, err=True)
    else:
        logger.info('No keyring backup to import.')
