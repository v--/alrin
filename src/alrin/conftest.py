import pathlib
import shutil
import tempfile
from collections.abc import Generator

import pytest
from click.testing import CliRunner

from fixtures.manager import AlrinFixtureManager


@pytest.fixture
def temp_path() -> Generator[pathlib.Path]:
    tmpdir = pathlib.Path(tempfile.mkdtemp(prefix='alrin_test_'))

    try:
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir)


@pytest.fixture
def temp_state_repo_path(temp_path: pathlib.Path) -> pathlib.Path:
    return temp_path / 'alrin-state'


@pytest.fixture
def temp_sources_path(temp_path: pathlib.Path) -> pathlib.Path:
    return temp_path / 'sources'


@pytest.fixture
def click_runner(temp_state_repo_path: pathlib.Path) -> CliRunner:
    return CliRunner(
        env={
            'ALRIN_SKIP_DEPENDENCY_CHECK': 'true',
            'ALRIN_STATE_REPO': temp_state_repo_path.as_posix(),
        },
    )


@pytest.fixture
def fixture_manager() -> AlrinFixtureManager:
    return AlrinFixtureManager()
