import importlib.resources
import pathlib

import pygit2
from viat import ViatVault


def initialize_state_repo(repo_path: pathlib.Path) -> None:
    vault = ViatVault.initialize(repo_path)
    viat_path = vault.resolver.get_viat()

    for res in importlib.resources.files('alrin.viat_template').iterdir():
        viat_path.joinpath(res.name).write_text(res.read_text())

    pygit2.init_repository(repo_path)
