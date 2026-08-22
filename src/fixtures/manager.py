# ruff: file-ignore[no-self-use]

import pathlib

import pygit2
import pytest

from alrin.workflow.jail import AlrinJailManager
from alrin.workflow.state import initialize_alrin_vault
from fixtures.git import git_commit
from fixtures.mock_makepkg import mock_makepkg
from fixtures.source import SourceFixtureManager


class AlrinFixtureManager:
    source: SourceFixtureManager

    def __init__(self) -> None:
        self.source = SourceFixtureManager()

    def initialize_alrin_vault(self, path: pathlib.Path) -> None:
        path.mkdir()
        initialize_alrin_vault(path)

        repo = pygit2.init_repository(path)
        repo.index.add_all()
        git_commit(repo, 'Initial commit')

    def mock_jail_manager(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # ruff: disable[unused-lambda-argument]
        monkeypatch.setattr(AlrinJailManager, 'create_new', lambda self: None)
        monkeypatch.setattr(AlrinJailManager, 'update_packages', lambda self: None)
        monkeypatch.setattr(AlrinJailManager, 'makepkg', mock_makepkg)
        # ruff: enable[unused-lambda-argument]
