from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from behave.runner import Context
from click.testing import CliRunner

from src.clients.database_client import DatabaseClient
from src.database.session_manager import DatabaseSessionManager


def before_all(context: Context) -> None:
    """
    Setup before all tests run.

    Initializes shared test infrastructure, specifically the CLI runner
    that will be reused across all scenarios.

    :param context: Behave context object
    """
    # Create CLI runner for all scenarios
    context.cli_runner = CliRunner()


def before_scenario(context: Context, scenario: Any) -> None:
    """
    Setup before each scenario.

    Creates an isolated test environment with:
    - A temporary directory for configuration and database files
    - A file-based SQLite database configured for the test
    - A DatabaseClient instance for pre-populating test data

    :param context: Behave context object
    :param scenario: Current scenario object
    """
    # Create temporary directory for this scenario
    context.temp_dir = TemporaryDirectory()
    context.temp_path = Path(context.temp_dir.name)

    # Database will be at workdir/zmbackup_sessions.db as per ZmbackupConfig
    context.db_path = context.temp_path / "zmbackup_sessions.db"
    context.db_url = f"sqlite:///{context.db_path}"

    # Setup database manager and client for pre-populating data
    context.db_manager = DatabaseSessionManager(context.db_url)
    context.db_client = DatabaseClient(context.db_manager, auto_create_tables=True)

    # Config file path (created by steps when needed)
    context.config_file = context.temp_path / "zmbackup.conf"

    # Store command result
    context.result = None

    # Parse table output (populated after command runs)
    context.parsed_table = None


def after_scenario(context: Context, scenario: Any) -> None:
    """
    Cleanup after each scenario.

    Ensures that database connections are closed and temporary files
    are removed to maintain isolation between scenarios.

    :param context: Behave context object
    :param scenario: Current scenario object
    """
    # Cleanup database
    if hasattr(context, "db_manager"):
        # Accessing private _engine to dispose of it and release file locks
        if hasattr(context.db_manager, "_engine") and context.db_manager._engine:
            context.db_manager._engine.dispose()

    # Cleanup temporary directory
    if hasattr(context, "temp_dir"):
        context.temp_dir.cleanup()


def after_all(context: Context) -> None:
    """
    Cleanup after all tests complete.

    :param context: Behave context object
    """
    pass
