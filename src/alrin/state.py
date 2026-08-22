import os
import pathlib
from dataclasses import dataclass

from viat import ViatVault

from alrin.metadata import AlrinVaultMetadata
from alrin.resolver import AlrinPathResolver


@dataclass(frozen=True)
class AlrinSharedState:
    vault: ViatVault
    resolver: AlrinPathResolver
    meta: AlrinVaultMetadata
    verbose_logging: bool


def get_vault_path() -> pathlib.Path:
    return pathlib.Path(os.environ.get('ALRIN_VAULT', pathlib.Path.cwd()))
