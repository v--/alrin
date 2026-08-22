import pathlib

import pygit2
import pytest
from click.testing import CliRunner
from viat import ViatVault

from alrin.cli import alrin_cli
from alrin.workflow.pkgbuild import find_pkgbuild_value
from fixtures.manager import AlrinFixtureManager


def test_add_success(
    temp_directory: pathlib.Path,
    fixture_manager: AlrinFixtureManager,
    click_runner: CliRunner,
) -> None:
    state_repo = temp_directory / 'state'
    fixture_manager.initialize_state_repo(state_repo)

    source_path = temp_directory / 'sources'
    fixture_manager.pkgbuild.initialize_at('dummy', source_path)

    with pytest.MonkeyPatch.context() as monkeypatch:
        fixture_manager.mock_jail_manager(monkeypatch)

        result = click_runner.invoke(
            alrin_cli,
            ['pkg', 'add', 'dummy', '--url-template', f'{source_path}/{{pkgname}}'],
            env={'ALRIN_STATE_REPO': state_repo.as_posix()},
        )

    assert 'Error' not in result.stderr
    assert state_repo.joinpath('pkgbuild', 'dummy', 'PKGBUILD').exists()

    vault = ViatVault(state_repo)

    with vault.storage as conn, conn.get_reader('pkgbuild/dummy') as reader:
        assert reader['pkgver'] == '0'
        assert reader['pkgrel'] == '0'
        assert 'add_pkgrel_suffix' not in reader


def test_add_invalid_path(
    temp_directory: pathlib.Path,
    fixture_manager: AlrinFixtureManager,
    click_runner: CliRunner,
) -> None:
    state_repo = temp_directory / 'state'
    fixture_manager.initialize_state_repo(state_repo)

    source_path = temp_directory / 'sources'

    with pytest.MonkeyPatch.context() as monkeypatch:
        fixture_manager.mock_jail_manager(monkeypatch)

        result = click_runner.invoke(
            alrin_cli,
            ['pkg', 'add', 'empty', '--url-template', f'{source_path}/{{pkgname}}'],
            env={'ALRIN_STATE_REPO': state_repo.as_posix()},
        )

    assert 'Removing invalid repository' in result.stderr

    git_repo = pygit2.Repository(state_repo)
    assert len(git_repo.index) == 0


def test_add_no_scrinfo(
    temp_directory: pathlib.Path,
    fixture_manager: AlrinFixtureManager,
    click_runner: CliRunner,
) -> None:
    state_repo = temp_directory / 'state'
    fixture_manager.initialize_state_repo(state_repo)

    source_path = temp_directory / 'sources'
    fixture_manager.pkgbuild.initialize_at('no_srcinfo', source_path)

    with pytest.MonkeyPatch.context() as monkeypatch:
        fixture_manager.mock_jail_manager(monkeypatch)

        result = click_runner.invoke(
            alrin_cli,
            ['pkg', 'add', 'no_srcinfo', '--url-template', f'{source_path}/{{pkgname}}'],
            env={'ALRIN_STATE_REPO': state_repo.as_posix()},
        )

    assert 'Error reading .SRCINFO' in result.stderr

    git_repo = pygit2.Repository(state_repo)
    git_repo.index.remove('.gitmodules')

    assert len(git_repo.index) == 0


def test_add_pypi_success(
    temp_directory: pathlib.Path,
    fixture_manager: AlrinFixtureManager,
    click_runner: CliRunner,
) -> None:
    state_repo = temp_directory / 'state'
    fixture_manager.initialize_state_repo(state_repo)

    source_path = temp_directory / 'sources'
    fixture_manager.pkgbuild.initialize_at('dummy-pypi', source_path)

    with pytest.MonkeyPatch.context() as monkeypatch:
        fixture_manager.mock_jail_manager(monkeypatch)

        result = click_runner.invoke(
            alrin_cli,
            ['pkg', 'add', 'dummy-pypi', '--url-template', f'{source_path}/{{pkgname}}'],
            env={'ALRIN_STATE_REPO': state_repo.as_posix()},
            input=b'yes\n',
        )

    assert 'Error' not in result.stderr

    vault = ViatVault(state_repo)

    with vault.storage as conn, conn.get_reader('pkgbuild/dummy-pypi') as reader:
        assert reader['add_pkgrel_suffix'] is True

    pkgrel = find_pkgbuild_value(
        state_repo.joinpath('pkgbuild', 'dummy-pypi', 'PKGBUILD').read_text(),
        'pkgrel',
    )

    # The PYTHON_VERSION_SUFFIX has been cleared after the build
    assert pkgrel == '1'
