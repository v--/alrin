import pathlib

import pygit2
import pytest
from click.testing import CliRunner
from viat import ViatVault

from alrin.cli import alrin_cli
from alrin.pkginfo import get_existing_built
from alrin.resolver import AlrinPathResolver
from alrin.wrappers import alpm_srcinfo_create
from fixtures.git import git_commit
from fixtures.manager import AlrinFixtureManager
from fixtures.read_database import read_database


def test_update_success(
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
            ['pkg', 'add', 'dummy', '--url-template', f'{temp_sources_path}/{{pkgname}}'],
        )

    # Save the files originally built
    vault = ViatVault(temp_vault_path)
    resolver = AlrinPathResolver(vault)
    original_built = get_existing_built(resolver)

    # Update source package
    dummy_repo_root = temp_sources_path / 'dummy'
    dummy_repo = pygit2.Repository(dummy_repo_root)

    with open(dummy_repo_root / 'PKGBUILD', 'r+', encoding='utf-8') as file:
        replaced = file.read().replace('pkgver=1', 'pkgver=2')
        file.seek(0)
        file.write(replaced)

    alpm_srcinfo_create(
        dummy_repo_root / 'PKGBUILD',
        dummy_repo_root / '.SRCINFO',
    )

    dummy_repo.index.add_all()
    git_commit(dummy_repo, 'v2', [dummy_repo.head.target])

    # Run an update
    with pytest.MonkeyPatch.context() as monkeypatch:
        fixture_manager.mock_jail_manager(monkeypatch)

        result = click_runner.invoke(
            alrin_cli,
            ['pkg', 'update', 'dummy'],
        )

    assert 'Error' not in result.stderr

    # Verify that the metadata is updated
    with vault.storage as conn, conn.get_reader('pkgbuild/dummy') as reader:
        assert reader['pkgver'] == '2'
        assert reader['pkgrel'] == '1'

    # Verify that the old files are deleted
    updated_built = get_existing_built(resolver)
    assert set.isdisjoint({b.path for b in original_built}, {b.path for b in updated_built})

    # Verify that the database contains only the new files
    db_packages = read_database(
        temp_vault_path.joinpath('pkgdest', 'any', 'alrin.db.tar'),
    )

    assert len(db_packages) == 1
    assert db_packages[0].name == 'dummy'
    assert db_packages[0].version == '2-1'
