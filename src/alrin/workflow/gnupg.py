import logging
lazy import pathlib

import gnupg

from alrin.resolver import AlrinPathResolver


logger = logging.getLogger(__name__)


def create_signature_file(path: pathlib.Path) -> None:
    """Sign a package file using user's GPG keyring."""
    gpg = gnupg.GPG()

    with path.open('rb') as file:
        gpg.sign_file(file, output=path.as_posix() + '.sig', detach=True, binary=True)


def initialize_keyring(resolver: AlrinPathResolver) -> None:
    """Initialize Alrin's custom keyring if needed."""
    path = resolver.get_keyring()

    if not path.exists():
        path.mkdir(mode=0o700)
        gpg = gnupg.GPG(gnupghome=path.as_posix())
        gpg.list_keys()  # Any void operation should be sufficient
