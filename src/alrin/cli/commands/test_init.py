import pathlib

from click.testing import CliRunner

from alrin.cli import alrin_cli


def test_init_success(temp_state_repo_path: pathlib.Path, click_runner: CliRunner) -> None:
    temp_state_repo_path.mkdir()
    result = click_runner.invoke(alrin_cli, ['init'])

    assert result.stdout == ''
    assert result.stderr == ''

    # Verify that a Viat vault with a schema has been initialized
    assert temp_state_repo_path.joinpath('.viat', 'config.toml').exists()
    assert temp_state_repo_path.joinpath('.viat', 'schema.json').exists()

    # Verify that a git repository has been initialized
    assert temp_state_repo_path.joinpath('.git', 'HEAD').exists()


def test_init_nonexistent_dir(temp_state_repo_path: pathlib.Path, click_runner: CliRunner) -> None:
    result = click_runner.invoke(alrin_cli, ['init'])

    assert result.stdout == ''
    assert result.stderr == f'Error: Invalid directory {temp_state_repo_path}.\n'


def test_init_nonempty_dir(temp_state_repo_path: pathlib.Path, click_runner: CliRunner) -> None:
    temp_state_repo_path.mkdir()
    temp_state_repo_path.joinpath('test').touch()
    result = click_runner.invoke(alrin_cli, ['init'])

    assert result.stdout == ''
    assert result.stderr == f'Error: Cannot initialize nonempty directory {temp_state_repo_path}.\n'

    assert not temp_state_repo_path.joinpath('.viat').exists()
    assert not temp_state_repo_path.joinpath('.git').exists()
