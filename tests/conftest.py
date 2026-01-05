from pathlib import Path
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from src.clients.database_client import DatabaseClient
from src.database.session_manager import DatabaseSessionManager
from src.lib.config import ZmbackupConfig


@pytest.fixture
def mock_config():
    """Fixture for a mocked ZmbackupConfig."""
    config = MagicMock(spec=ZmbackupConfig)
    config.database_path = "sqlite:///:memory:"
    config.workdir = Path("/tmp/zmbackup")
    config.rotate_time = 30
    return config


@pytest.fixture
def db_url():
    """Fixture for in-memory SQLite database URL."""
    return "sqlite:///:memory:"


@pytest.fixture
def db_client(mock_config):
    """Fixture for DatabaseClient using mocked config."""
    client = DatabaseClient(mock_config)
    return client


@pytest.fixture
def session_manager(db_url):
    """Fixture for DatabaseSessionManager."""
    return DatabaseSessionManager(db_url)


@pytest.fixture
def cli_runner():
    """Fixture for Click CliRunner."""
    return CliRunner()
