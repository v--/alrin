import pathlib

import pygit2
import pytest
from click.testing import CliRunner
from viat import ViatVault

from alrin.cli import alrin_cli
from alrin.pkginfo import get_existing_built
from alrin.resolver import AlrinPathResolver
from alrin.workflow.pkgbuild import PYTHON_VERSION_SUFFIX
from fixtures.manager import AlrinFixtureManager
from fixtures.read_database import read_database


def test_add_success(
    temp_vault_path: pathlib.Path,
    temp_sources_path: pathlib.Path,
    fixture_manager: AlrinFixtureManager,
    click_runner: CliRunner,
) -> None:
    fixture_manager.initialize_alrin_vault(temp_vault_path)
    fixture_manager.source.initialize_at('dummy', temp_sources_path)

    with pytest.MonkeyPatch.context() as monkeypatch:
        fixture_manager.mock_jail_manager(monkeypatch)

        result = click_runner.invoke(
            alrin_cli,
            ['pkg', 'add', 'dummy', '--url-template', f'{temp_sources_path}/{{pkgname}}'],
        )

    assert 'Error' not in result.stderr
    assert temp_vault_path.joinpath('pkgbuild', 'dummy', 'PKGBUILD').exists()

    vault = ViatVault(temp_vault_path)

    with vault.storage as conn, conn.get_reader('pkgbuild/dummy') as reader:
        assert reader['pkgver'] == '1'
        assert reader['pkgrel'] == '1'
        assert 'add_pkgrel_suffix' not in reader

    resolver = AlrinPathResolver(vault)
    original_built = get_existing_built(resolver)

    assert len(original_built) == 2
    assert original_built[0].built.info.pkgname == 'dummy'
    assert original_built[0].built.info.arch == 'any'

    db_packages = read_database(
        temp_vault_path.joinpath('pkgdest', 'any', 'alrin.db.tar'),
    )

    assert len(db_packages) == 1
    assert db_packages[0].name == 'dummy'
    assert db_packages[0].version == '1-1'


def test_add_invalid_path(
    temp_vault_path: pathlib.Path,
    temp_sources_path: pathlib.Path,
    fixture_manager: AlrinFixtureManager,
    click_runner: CliRunner,
) -> None:
    fixture_manager.initialize_alrin_vault(temp_vault_path)

    with pytest.MonkeyPatch.context() as monkeypatch:
        fixture_manager.mock_jail_manager(monkeypatch)

        result = click_runner.invoke(
            alrin_cli,
            ['pkg', 'add', 'empty', '--url-template', f'{temp_sources_path}/{{pkgname}}'],
        )

    assert 'Removing invalid repository' in result.stderr

    git_repo = pygit2.Repository(temp_vault_path)
    assert len(git_repo.index) == 0


def test_add_bad_pkgbuild(
    temp_vault_path: pathlib.Path,
    temp_sources_path: pathlib.Path,
    fixture_manager: AlrinFixtureManager,
    click_runner: CliRunner,
) -> None:
    fixture_manager.initialize_alrin_vault(temp_vault_path)
    fixture_manager.source.initialize_at('bad-pkgbuild', temp_sources_path)

    with pytest.MonkeyPatch.context() as monkeypatch:
        fixture_manager.mock_jail_manager(monkeypatch)

        result = click_runner.invoke(
            alrin_cli,
            ['pkg', 'add', 'bad-pkgbuild', '--url-template', f'{temp_sources_path}/{{pkgname}}'],
            env={'ALRIN_VAULT': temp_vault_path.as_posix()},
        )

    assert 'Error reading .SRCINFO' in result.stderr

    git_repo = pygit2.Repository(temp_vault_path)
    git_repo.index.remove('.gitmodules')

    assert len(git_repo.index) == 0


def test_add_pypi_success(
    temp_vault_path: pathlib.Path,
    temp_sources_path: pathlib.Path,
    fixture_manager: AlrinFixtureManager,
    click_runner: CliRunner,
) -> None:
    fixture_manager.initialize_alrin_vault(temp_vault_path)
    fixture_manager.source.initialize_at('python-dummy', temp_sources_path)

    with pytest.MonkeyPatch.context() as monkeypatch:
        fixture_manager.mock_jail_manager(monkeypatch)

        result = click_runner.invoke(
            alrin_cli,
            ['pkg', 'add', 'python-dummy', '--url-template', f'{temp_sources_path}/{{pkgname}}'],
            input=b'yes\n',
        )

    assert 'Error' not in result.stderr

    vault = ViatVault(temp_vault_path)

    with vault.storage as conn, conn.get_reader('pkgbuild/python-dummy') as reader:
        assert reader['pkgver'] == '1'
        assert reader['pkgrel'] == '1' + PYTHON_VERSION_SUFFIX
        assert reader['add_pkgrel_suffix'] is True

    db_packages = read_database(
        temp_vault_path.joinpath('pkgdest', 'any', 'alrin.db.tar'),
    )

    assert len(db_packages) == 1
    assert db_packages[0].name == 'python-dummy'
    assert db_packages[0].version == '1-1' + PYTHON_VERSION_SUFFIX


def test_add_subpackages_success(
    temp_vault_path: pathlib.Path,
    temp_sources_path: pathlib.Path,
    fixture_manager: AlrinFixtureManager,
    click_runner: CliRunner,
) -> None:
    fixture_manager.initialize_alrin_vault(temp_vault_path)
    fixture_manager.source.initialize_at('dummy-subpackages', temp_sources_path)

    with pytest.MonkeyPatch.context() as monkeypatch:
        fixture_manager.mock_jail_manager(monkeypatch)

        result = click_runner.invoke(
            alrin_cli,
            ['pkg', 'add', 'dummy-subpackages', '--url-template', f'{temp_sources_path}/{{pkgname}}'],
        )

    assert 'Error' not in result.stderr

    vault = ViatVault(temp_vault_path)

    with vault.storage as conn, conn.get_reader('pkgbuild/dummy-subpackages') as reader:
        assert reader['pkgver'] == '1'
        assert reader['pkgrel'] == '1'

    db_packages = read_database(
        temp_vault_path.joinpath('pkgdest', 'any', 'alrin.db.tar'),
    )

    assert len(db_packages) == 2
    assert db_packages[0].name == 'a'
    assert db_packages[0].version == '1-1'
    assert db_packages[1].name == 'b'
    assert db_packages[1].version == '1-1'
