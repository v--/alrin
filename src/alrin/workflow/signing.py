from typing import TYPE_CHECKING

import gnupg


if TYPE_CHECKING:
    import pathlib


def create_signature_file(path: pathlib.Path) -> None:
    gpg = gnupg.GPG()

    with path.open('rb') as file:
        gpg.sign_file(file, output=path.as_posix() + '.sig', detach=True, binary=True)
