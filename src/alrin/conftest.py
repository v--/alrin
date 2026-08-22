import pathlib
import shutil
import tempfile
from textwrap import dedent
lazy from collections.abc import Generator

import pygit2
import pytest
from click.testing import CliRunner


@pytest.fixture
def click_runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def temp_directory() -> Generator[pathlib.Path]:
    tmpdir = pathlib.Path(tempfile.mkdtemp(prefix='alrin_test_'))

    try:
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir)
