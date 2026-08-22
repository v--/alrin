import importlib.resources
import pathlib

import pygit2
from viat import ViatVault
from viat.vault import locate_existing_vault_root

from alrin.resolver import AlrinPathResolver
from alrin.state import AlrinSharedState, get_state_repo_path
from alrin.workflow.gnupg import initialize_keyring


def copy_resource_traversible(res: importlib.resources.abc.Traversable, target_path: pathlib.Path) -> None:
    if res.is_dir():
        target_path.mkdir(exist_ok=True, parents=True)

        for sub in res.iterdir():
            copy_resource_traversible(sub, target_path / sub.name)

    if res.is_file():
        target_path.write_bytes(res.read_bytes())


def initialize_state_repo(repo_path: pathlib.Path) -> None:
    vault = ViatVault.initialize(repo_path)

    copy_resource_traversible(
        importlib.resources.files('alrin.viat_template'),
        vault.resolver.get_viat(),
    )

    pygit2.init_repository(repo_path)


def initialize_shared_state(*, state_repo: pathlib.Path | None = None, verbose: bool = False) -> AlrinSharedState:
    vault = ViatVault(
        locate_existing_vault_root(state_repo or get_state_repo_path()),
    )

    resolver = AlrinPathResolver(vault)
    initialize_keyring(resolver)

    return AlrinSharedState(vault, resolver, verbose_logging=verbose)
