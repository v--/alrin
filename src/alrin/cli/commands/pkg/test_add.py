import pathlib

import pygit2
import pytest
from click.testing import CliRunner
from viat import ViatVault

from alrin.cli import alrin_cli
from alrin.workflow.pkgbuild import find_pkgbuild_value
from fixtures.manager import AlrinFixtureManager


def test_add_success(
    temp_state_repo_path: pathlib.Path,
    temp_sources_path: pathlib.Path,
    fixture_manager: AlrinFixtureManager,
    click_runner: CliRunner,
) -> None:
    fixture_manager.initialize_state_repo(temp_state_repo_path)
    fixture_manager.pkgbuild.initialize_at('dummy', temp_sources_path)

    with pytest.MonkeyPatch.context() as monkeypatch:
        fixture_manager.mock_jail_manager(monkeypatch)

        result = click_runner.invoke(
            alrin_cli,
            ['pkg', 'add', 'dummy', '--url-template', f'{temp_sources_path}/{{pkgname}}'],
        )

    assert 'Error' not in result.stderr
    assert temp_state_repo_path.joinpath('pkgbuild', 'dummy', 'PKGBUILD').exists()

    vault = ViatVault(temp_state_repo_path)

    with vault.storage as conn, conn.get_reader('pkgbuild/dummy') as reader:
        assert reader['pkgver'] == '0'
        assert reader['pkgrel'] == '0'
        assert 'add_pkgrel_suffix' not in reader


def test_add_invalid_path(
    temp_state_repo_path: pathlib.Path,
    temp_sources_path: pathlib.Path,
    fixture_manager: AlrinFixtureManager,
    click_runner: CliRunner,
) -> None:
    fixture_manager.initialize_state_repo(temp_state_repo_path)

    with pytest.MonkeyPatch.context() as monkeypatch:
        fixture_manager.mock_jail_manager(monkeypatch)

        result = click_runner.invoke(
            alrin_cli,
            ['pkg', 'add', 'empty', '--url-template', f'{temp_sources_path}/{{pkgname}}'],
        )

    assert 'Removing invalid repository' in result.stderr

    git_repo = pygit2.Repository(temp_state_repo_path)
    assert len(git_repo.index) == 0


def test_add_no_scrinfo(
    temp_state_repo_path: pathlib.Path,
    temp_sources_path: pathlib.Path,
    fixture_manager: AlrinFixtureManager,
    click_runner: CliRunner,
) -> None:
    fixture_manager.initialize_state_repo(temp_state_repo_path)
    fixture_manager.pkgbuild.initialize_at('no_srcinfo', temp_sources_path)

    with pytest.MonkeyPatch.context() as monkeypatch:
        fixture_manager.mock_jail_manager(monkeypatch)

        result = click_runner.invoke(
            alrin_cli,
            ['pkg', 'add', 'no_srcinfo', '--url-template', f'{temp_sources_path}/{{pkgname}}'],
            env={'ALRIN_STATE_REPO': temp_state_repo_path.as_posix()},
        )

    assert 'Error reading .SRCINFO' in result.stderr

    git_repo = pygit2.Repository(temp_state_repo_path)
    git_repo.index.remove('.gitmodules')

    assert len(git_repo.index) == 0


def test_add_pypi_success(
    temp_state_repo_path: pathlib.Path,
    temp_sources_path: pathlib.Path,
    fixture_manager: AlrinFixtureManager,
    click_runner: CliRunner,
) -> None:
    fixture_manager.initialize_state_repo(temp_state_repo_path)
    fixture_manager.pkgbuild.initialize_at('dummy-pypi', temp_sources_path)

    with pytest.MonkeyPatch.context() as monkeypatch:
        fixture_manager.mock_jail_manager(monkeypatch)

        result = click_runner.invoke(
            alrin_cli,
            ['pkg', 'add', 'dummy-pypi', '--url-template', f'{temp_sources_path}/{{pkgname}}'],
            input=b'yes\n',
        )

    assert 'Error' not in result.stderr

    vault = ViatVault(temp_state_repo_path)

    with vault.storage as conn, conn.get_reader('pkgbuild/dummy-pypi') as reader:
        assert reader['add_pkgrel_suffix'] is True

    pkgrel = find_pkgbuild_value(
        temp_state_repo_path.joinpath('pkgbuild', 'dummy-pypi', 'PKGBUILD').read_text(),
        'pkgrel',
    )

    # The PYTHON_VERSION_SUFFIX has been cleared after the build
    assert pkgrel == '1'
