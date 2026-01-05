from pathlib import Path

import pytest
from click.testing import CliRunner

from src.clients.database_client import DatabaseClient
from src.database.session_manager import DatabaseSessionManager
from src.enums import EmailNotifyLevel, SessionType
from src.lib.config import ZmbackupConfig


@pytest.fixture
def mock_config() -> ZmbackupConfig:
    """
    Fixture for a real ZmbackupConfig instance for testing.

    :return: ZmbackupConfig instance
    """
    return ZmbackupConfig(
        backup_user="zimbra",
        workdir=Path("/tmp/zmbackup"),
        ldap_server="ldap://localhost:389",
        ldap_admin="uid=zimbra,cn=admins,cn=zimbra",
        ldap_password="password",
        log_file=Path("/tmp/zmbackup.log"),
        enable_email_notify=EmailNotifyLevel.ALL,
        email_notify="admin@example.com",
        email_sender="zmbackup@example.com",
        max_parallel_process=3,
        rotate_time=30,
        lock_backup=True,
        backup_inactive_accounts=True,
        ssl_enable=True,
        session_type=SessionType.TXT,
        zmmailbox=Path("/opt/zimbra/bin/zmmailbox"),
    )


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
