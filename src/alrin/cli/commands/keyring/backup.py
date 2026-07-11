import logging

import click
import gnupg

from alrin.exceptions import AlrinKeyringError
from alrin.logging import setup_logging
from alrin.state import AlrinSharedState

from .group import keyring as keyring_cli


logger = logging.getLogger(__name__)


@keyring_cli.command()
@click.option('-v', '--verbose', is_flag=True)
@click.pass_obj
def backup(shared: AlrinSharedState, verbose: bool) -> None:
    setup_logging(shared.verbose_logging or verbose)
    gpg = gnupg.GPG(gnupghome=shared.resolver.get_keyring().as_posix())
    keys = gpg.list_keys(secret=False)
    logger.info(f'Exporting {len(keys)} public keys.')
    file_contents = gpg.export_keys(
        armor=True,
        keyids=[key['fingerprint'] for key in keys],
    )

    if len(file_contents) == 0:
        raise AlrinKeyringError('GPG failed to export keys')

    shared.resolver.get_keyring_backup().write_text(
        file_contents,
        encoding='utf-8',
    )
