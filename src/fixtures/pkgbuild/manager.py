# ruff: file-ignore[no-self-use]

import importlib.resources
import pathlib

import pygit2

from alrin.workflow.state import copy_resource_traversible
from fixtures.git import git_commit


class PkgbuildFixtureManager:
    def initialize_at(self, name: str, target_path: pathlib.Path) -> None:
        copy_resource_traversible(
            importlib.resources.files('fixtures.pkgbuild').joinpath(name),
            target_path.joinpath(name),
        )

        repo = pygit2.init_repository(target_path.joinpath(name))
        repo.index.add_all()
        git_commit(repo, 'Initial commit')
