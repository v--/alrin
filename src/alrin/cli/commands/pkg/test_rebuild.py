import pathlib

import pygit2
import pytest
from click.testing import CliRunner
from viat import ViatVault

from alrin.cli import alrin_cli
from alrin.resolver import AlrinPathResolver
from alrin.wrappers import alpm_srcinfo_create
from fixtures.git import git_commit
from fixtures.manager import AlrinFixtureManager


def test_rebuild_full_match(
    temp_vault_path: pathlib.Path,
    temp_sources_path: pathlib.Path,
    fixture_manager: AlrinFixtureManager,
    click_runner: CliRunner,
) -> None:
    # Initialize the vault and sources
    fixture_manager.initialize_alrin_vault(temp_vault_path)
    fixture_manager.source.initialize_at('dummy', temp_sources_path)

    # Add a dummy package
    with pytest.MonkeyPatch.context() as monkeypatch:
        fixture_manager.mock_jail_manager(monkeypatch)

        click_runner.invoke(
            alrin_cli,
            ['pkg', 'add', 'dummy', '--url-template', f'{temp_sources_path}/{{pkgbase}}'],
        )

    # Run a rebuild
    with pytest.MonkeyPatch.context() as monkeypatch:
        fixture_manager.mock_jail_manager(monkeypatch)

        result = click_runner.invoke(
            alrin_cli,
            ['pkg', 'rebuild', 'dummy'],
        )

    assert 'Package file dummy-1-1-any.pkg.tar has not changed.' in result.stderr


def test_rebuild_incomplete_match(
    temp_vault_path: pathlib.Path,
    temp_sources_path: pathlib.Path,
    fixture_manager: AlrinFixtureManager,
    click_runner: CliRunner,
) -> None:
    # Initialize the vault and sources
    fixture_manager.initialize_alrin_vault(temp_vault_path)
    fixture_manager.source.initialize_at('dummy', temp_sources_path)

    # Add a dummy package
    with pytest.MonkeyPatch.context() as monkeypatch:
        fixture_manager.mock_jail_manager(monkeypatch)

        click_runner.invoke(
            alrin_cli,
            ['pkg', 'add', 'dummy', '--url-template', f'{temp_sources_path}/{{pkgbase}}'],
        )

    # Modify cloned package
    vault = ViatVault(temp_vault_path)
    resolver = AlrinPathResolver(vault)
    dummy_repo_root = resolver.get_pkg('dummy')
    dummy_repo = pygit2.Repository(dummy_repo_root)

    with open(dummy_repo_root / 'PKGBUILD', 'r+', encoding='utf-8') as file:
        replaced = file.read().replace("license=('MIT')", "license=('ISC')")
        file.seek(0)
        file.write(replaced)

    alpm_srcinfo_create(
        dummy_repo_root / 'PKGBUILD',
        dummy_repo_root / '.SRCINFO',
    )

    dummy_repo.index.add_all()
    git_commit(dummy_repo, 'v2', [dummy_repo.head.target])

    # Run a rebuild
    with pytest.MonkeyPatch.context() as monkeypatch:
        fixture_manager.mock_jail_manager(monkeypatch)

        result = click_runner.invoke(
            alrin_cli,
            ['pkg', 'rebuild', 'dummy'],
        )

    assert 'Package file dummy-1-1-any.pkg.tar has been rebuilt with the same version, but is different from the old one.' in result.stderr
