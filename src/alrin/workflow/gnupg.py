lazy import pathlib

import gnupg


def create_signature_file(path: pathlib.Path) -> None:
    gpg = gnupg.GPG()

    with path.open('rb') as file:
        gpg.sign_file(file, output=path.as_posix() + '.sig', detach=True, binary=True)


def initialize_keyring(path: pathlib.Path) -> None:
    if not path.exists():
        path.mkdir()
        gpg = gnupg.GPG(gnupghome=path.as_posix())
        gpg.list_keys()  # Any void operation should be sufficient
