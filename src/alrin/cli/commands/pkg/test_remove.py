import pathlib

import pygit2
import pytest
from click.testing import CliRunner

from alrin.cli import alrin_cli
from fixtures.manager import AlrinFixtureManager


def test_remove_success(
    temp_vault_path: pathlib.Path,
    temp_sources_path: pathlib.Path,
    fixture_manager: AlrinFixtureManager,
    click_runner: CliRunner,
) -> None:
    fixture_manager.initialize_alrin_vault(temp_vault_path)
    fixture_manager.source.initialize_at('dummy', temp_sources_path)

    with pytest.MonkeyPatch.context() as monkeypatch:
        fixture_manager.mock_jail_manager(monkeypatch)

        click_runner.invoke(
            alrin_cli,
            ['pkg', 'add', 'dummy', '--url-template', f'{temp_sources_path}/{{pkgname}}'],
        )

    result = click_runner.invoke(
        alrin_cli,
        ['pkg', 'remove', 'dummy'],
    )

    assert 'Error' not in result.stderr

    git_repo = pygit2.Repository(temp_vault_path)
    git_repo.index.remove('.gitmodules')

    assert len(git_repo.index) == 0
