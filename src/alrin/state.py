import os
import pathlib
from dataclasses import dataclass

from viat import ViatVault

from alrin.resolver import AlrinPathResolver


@dataclass(frozen=True)
class AlrinSharedState:
    vault: ViatVault
    resolver: AlrinPathResolver
    verbose_logging: bool


def get_state_repo_path() -> pathlib.Path:
    return pathlib.Path(os.environ.get('ALRIN_STATE_REPO', pathlib.Path.cwd()))
