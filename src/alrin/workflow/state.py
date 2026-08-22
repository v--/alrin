import importlib.resources
import pathlib

import pygit2
from viat import ViatVault
from viat.vault import locate_existing_vault_root

from alrin.resolver import AlrinPathResolver
from alrin.state import AlrinSharedState, get_state_repo_path
from alrin.workflow.gnupg import initialize_keyring


def initialize_state_repo(repo_path: pathlib.Path) -> None:
    vault = ViatVault.initialize(repo_path)
    viat_path = vault.resolver.get_viat()

    for res in importlib.resources.files('alrin.viat_template').iterdir():
        viat_path.joinpath(res.name).write_text(res.read_text())

    pygit2.init_repository(repo_path)


def initialize_shared_state(verbose: bool) -> AlrinSharedState:
    vault = ViatVault(
        locate_existing_vault_root(get_state_repo_path()),
    )

    resolver = AlrinPathResolver(vault)
    initialize_keyring(resolver)

    return AlrinSharedState(vault, resolver, verbose_logging=verbose)
