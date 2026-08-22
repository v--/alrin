import os
import pathlib
from dataclasses import dataclass

from viat.vault import locate_existing_vault_root
lazy from viat import ViatVault

from alrin.workflow.gnupg import initialize_keyring
lazy from alrin.resolver import AlrinPathResolver


@dataclass(frozen=True)
class AlrinSharedState:
    vault: ViatVault
    resolver: AlrinPathResolver
    verbose_logging: bool


def get_state_repo_path() -> pathlib.Path:
    return pathlib.Path(os.environ.get('ALRIN_STATE_REPO', pathlib.Path.cwd()))


def initialize_shared_state(verbose: bool) -> AlrinSharedState:
    vault = ViatVault(
        locate_existing_vault_root(get_state_repo_path()),
    )

    resolver = AlrinPathResolver(vault)
    initialize_keyring(resolver)

    return AlrinSharedState(vault, resolver, verbose_logging=verbose)
