import pytest
from click.testing import CliRunner
from src.clients.database_client import DatabaseClient
from src.database.session_manager import DatabaseSessionManager

@pytest.fixture
def db_url():
    """Fixture for in-memory SQLite database URL."""
    return "sqlite:///:memory:"

@pytest.fixture
def db_client(db_url):
    """Fixture for DatabaseClient using in-memory SQLite."""
    client = DatabaseClient(db_url)
    return client

@pytest.fixture
def session_manager(db_url):
    """Fixture for DatabaseSessionManager."""
    return DatabaseSessionManager(db_url)

@pytest.fixture
def cli_runner():
    """Fixture for Click CliRunner."""
    return CliRunner()
