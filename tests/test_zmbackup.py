from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.database.models import BackupSession
from src.zmbackup import cli


@pytest.fixture(autouse=True)
def mock_get_config(mock_config):
    """Auto-mock get_config for all CLI tests."""
    with patch("src.zmbackup.get_config") as mocked:
        mocked.return_value = mock_config
        yield mocked


@patch("src.zmbackup.DatabaseClient")
def test_list_command_empty(mock_client_class, cli_runner):
    """Test list command when no sessions exist."""
    mock_client = mock_client_class.return_value
    mock_client.list_sessions.return_value = []

    result = cli_runner.invoke(cli, ["list"])

    assert result.exit_code == 0
    assert "No backup sessions found." in result.output


@patch("src.zmbackup.DatabaseClient")
def test_list_command_with_data(mock_client_class, cli_runner):
    """Test list command with sessions."""
    mock_client = mock_client_class.return_value

    # Create mock session objects
    s1 = MagicMock(spec=BackupSession)
    s1.session_name = "full-20260101"
    s1.start = datetime(2026, 1, 1, 12, 0)
    s1.ending = datetime(2026, 1, 1, 13, 0)
    s1.size = "1.2G"
    s1.description = "Full backup"

    s2 = MagicMock(spec=BackupSession)
    s2.session_name = "incr-20260102"
    s2.start = datetime(2026, 1, 2, 12, 0)
    s2.ending = None
    s2.size = None
    s2.description = "Incr backup"

    mock_client.list_sessions.return_value = [s1, s2]

    result = cli_runner.invoke(cli, ["list"])

    assert result.exit_code == 0
    assert "full-20260101" in result.output
    assert "1.2G" in result.output
    assert "Full backup" in result.output
    assert "incr-20260102" in result.output
    assert "N/A" in result.output  # for missing ending/size


@patch("src.zmbackup.DatabaseClient")
def test_list_command_error(mock_client_class, cli_runner):
    """Test list command error handling."""
    mock_client = mock_client_class.return_value
    mock_client.list_sessions.side_effect = Exception("DB Error")

    result = cli_runner.invoke(cli, ["list"])

    assert result.exit_code == 1
    assert "Error accessing database: DB Error" in result.output
