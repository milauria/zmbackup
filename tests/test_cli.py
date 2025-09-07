import datetime
import os
import uuid
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from src.cli import cli
from src.database.sqlite.models import Session
from src.database.sqlite.sqlite import SQLiteManager


@pytest.fixture
def temp_db_path(tmp_path):
    """Provides a temporary database path for testing."""
    db_path = tmp_path / "test_sessions.db"
    return str(db_path)


@pytest.fixture
def sqlite_manager(temp_db_path):
    """Provides an SQLiteManager instance with a temporary database."""
    manager = SQLiteManager(db_path=temp_db_path)
    yield manager
    manager._connection.close() # Explicitly close the connection
    os.remove(temp_db_path)


@pytest.mark.parametrize(
    "session_data, expected_output_lines",
    [
        (
            [
                {
                    "session_id": str(uuid.uuid4()), # Use a valid UUID string
                    "starting_date": datetime.datetime(2018, 4, 8, 16, 2, 27),
                    "end_date": datetime.datetime(2018, 4, 8, 16, 2, 27),
                    "size": 76,
                    "description": "Full Account",
                },
                {
                    "session_id": str(uuid.uuid4()), # Use a valid UUID string
                    "starting_date": datetime.datetime(2018, 4, 8, 16, 8, 8),
                    "end_date": datetime.datetime(2018, 4, 8, 16, 8, 8),
                    "size": 40,
                    "description": "Mailbox",
                },
            ],
            [
                "+---------------------+------------+------------+------+--------------+",
                "| Session Name        | Start      | Ending     | Size | Description  |",
                "+---------------------+------------+------------+------+--------------+",
                "| full-20180408160227 | 04/08/2018 | 04/08/2018 | 76K  | Full Account |",
                "| mbox-20180408160808 | 04/08/2018 | 04/08/2018 | 40K  | Mailbox      |",
                "+---------------------+------------+------------+------+--------------+",
            ],
        ),
    ],
)
def test_list_sessions_command(sqlite_manager, session_data, expected_output_lines):
    """Tests the 'zmbackup list -l' command output."""
    for data in session_data:
        session = Session(
            session_id=uuid.UUID(data["session_id"]),
            starting_date=data["starting_date"],
            end_date=data["end_date"],
            size=data["size"],
            description=data["description"],
        )
        sqlite_manager.create_session(session)

    runner = CliRunner()
    with patch("src.cli.SQLiteManager", return_value=sqlite_manager):
        result = runner.invoke(cli, ["list", "-l"])

    assert result.exit_code == 0
    actual_output_lines = result.output.strip().splitlines()

    # Compare line by line, ignoring potential whitespace differences at the end of lines
    assert len(actual_output_lines) == len(expected_output_lines)
    for actual, expected in zip(actual_output_lines, expected_output_lines):
        assert actual.strip() == expected.strip()

def test_cli_main_entry_point():
    """Tests the main CLI entry point without subcommands."""
    runner = CliRunner()
    result = runner.invoke(cli)
    assert result.exit_code == 2
    assert "A CLI tool for managing zmbackup sessions." in result.output