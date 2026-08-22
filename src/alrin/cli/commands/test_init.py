import pathlib

from click.testing import CliRunner

from alrin.cli import alrin


def test_init_success(temp_directory: pathlib.Path, click_runner: CliRunner) -> None:
    result = click_runner.invoke(alrin, ['init'], env={'ALRIN_STATE_REPO': temp_directory.as_posix()})

    assert result.stdout == ''
    assert result.stderr == ''

    # Verify that a Viat vault with a schema has been initialized
    assert temp_directory.joinpath('.viat', 'config.toml').exists()
    assert temp_directory.joinpath('.viat', 'schema.json').exists()

    # Verify that a git repository has been initialized
    assert temp_directory.joinpath('.git', 'HEAD').exists()


def test_init_nonexistent_dir(temp_directory: pathlib.Path, click_runner: CliRunner) -> None:
    result = click_runner.invoke(alrin, ['init'], env={'ALRIN_STATE_REPO': temp_directory.joinpath('nonexistent').as_posix()})

    assert result.stdout == ''
    assert result.stderr == f'Error: Invalid directory {temp_directory}/nonexistent.\n'


def test_init_nonempty_dir(temp_directory: pathlib.Path, click_runner: CliRunner) -> None:
    temp_directory.joinpath('test').touch()
    result = click_runner.invoke(alrin, ['init'], env={'ALRIN_STATE_REPO': temp_directory.as_posix()})

    assert result.stdout == ''
    assert result.stderr == f'Error: Cannot initialize nonempty directory {temp_directory}.\n'

    assert not temp_directory.joinpath('.viat').exists()
    assert not temp_directory.joinpath('.git').exists()
