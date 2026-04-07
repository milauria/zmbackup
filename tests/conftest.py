import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from src.clients.database_client import DatabaseClient
from src.database.session_manager import DatabaseSessionManager
from src.enums import EmailNotifyLevel, SessionType
from src.lib.config import ZmbackupConfig

# Test files directory
TEST_FILES_DIR = Path(__file__).parent / "test-files" / "config"


@pytest.fixture
def config_test_file():
    """
    Factory fixture to get path to test configuration files.

    :return: Function that returns path to test config file
    """

    def _get_path(filename: str) -> Path:
        """
        Get path to test configuration file.

        :param filename: Name of the test file
        :return: Path to test file
        :raises FileNotFoundError: If test file doesn't exist
        """
        file_path = TEST_FILES_DIR / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Test file not found: {file_path}")
        return file_path

    return _get_path


@pytest.fixture
def mock_config(config_test_file) -> ZmbackupConfig:
    """
    Fixture for a real ZmbackupConfig instance for testing.

    :param config_test_file: Factory fixture to get test config file paths
    :return: ZmbackupConfig instance
    """
    config_path = config_test_file("valid_config.json")
    return ZmbackupConfig.load(config_path)


@pytest.fixture
def db_url() -> str:
    """
    Fixture for in-memory SQLite database URL.

    :return: In-memory SQLite connection string
    """
    return "sqlite:///:memory:"


@pytest.fixture
def session_manager(db_url: str) -> DatabaseSessionManager:
    """
    Fixture for DatabaseSessionManager.

    :param db_url: Database URL fixture
    :return: DatabaseSessionManager instance
    """
    return DatabaseSessionManager(db_url)


@pytest.fixture
def db_client(session_manager: DatabaseSessionManager) -> DatabaseClient:
    """
    Fixture for DatabaseClient.

    :param session_manager: DatabaseSessionManager fixture
    :return: DatabaseClient instance
    """
    return DatabaseClient(session_manager)


@pytest.fixture
def cli_runner() -> CliRunner:
    """
    Fixture for Click CliRunner.

    :return: CliRunner instance
    """
    return CliRunner()
