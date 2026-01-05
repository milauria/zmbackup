from datetime import datetime, timedelta
import json
from typing import List

from behave import given, when, then
from behave.runner import Context

from src.database.models import generate_session_uuid
from test_func.fixtures.backup_session_factory import (
    create_test_session,
    create_test_session_from_dict,
)
from test_func.helpers.config_generator import (
    generate_test_config,
    delete_config_file,
)
from test_func.helpers.output_parser import (
    parse_prettytable_output,
    assert_table_has_columns,
    assert_row_contains,
)
from src.zmbackup import cli


@given("a clean zmbackup environment")
def step_clean_environment(context: Context) -> None:
    """
    Ensure clean test environment with test database.

    :param context: Behave context
    """
    # Database already created in before_scenario hook
    assert context.db_client is not None
    assert context.db_manager is not None


@given("a valid configuration file")
def step_valid_config(context: Context) -> None:
    """
    Create a temporary configuration file pointing to test database.

    :param context: Behave context
    """
    config_path = generate_test_config(context.temp_path)
    context.config_file = config_path


@given("the database has no sessions")
def step_empty_database(context: Context) -> None:
    """
    Verify database is empty.

    :param context: Behave context
    """
    sessions = context.db_client.list_sessions()
    assert len(sessions) == 0, "Database should be empty"


@given('the database has {count:d} session from "{file_path}"')
@given('the database has {count:d} sessions from "{file_path}"')
def step_create_sessions_from_json(context: Context, count: int, file_path: str) -> None:
    """
    Create session(s) from JSON file data.

    :param context: Behave context
    :param count: Expected number of sessions
    :param file_path: Path to JSON file
    """
    with open(file_path, "r") as f:
        data_list = json.load(f)

    assert len(data_list) == count, f"Expected {count} sessions in JSON, found {len(data_list)}"

    with context.db_manager.get_session() as db_session:
        for i, data in enumerate(data_list):
            # Create session using test data factory
            session = create_test_session_from_dict(data)
            
            # Ensure unique timestamp for session name generation
            session.start = session.start + timedelta(seconds=i)
            session.session_name = generate_session_uuid(session.backup_type, session.start)

            # Add to database
            db_session.add(session)
        db_session.commit()


@given('the database has sessions by type from "{file_path}"')
def step_create_sessions_by_type_json(context: Context, file_path: str) -> None:
    """
    Create sessions grouped by backup type from JSON file.

    :param context: Behave context
    :param file_path: Path to JSON file
    """
    with open(file_path, "r") as f:
        data_list = json.load(f)

    with context.db_manager.get_session() as db_session:
        global_index = 0
        for data in data_list:
            backup_type = data["backup_type"]
            count = int(data["count"])

            for i in range(count):
                session = create_test_session(
                    backup_type=backup_type,
                    description=f"{backup_type} backup {i}",
                    unique_id=global_index,
                )
                db_session.add(session)
                global_index += 1
        db_session.commit()


@given('the database has sessions by status from "{file_path}"')
def step_create_sessions_by_status_json(context: Context, file_path: str) -> None:
    """
    Create sessions grouped by status from JSON file.

    :param context: Behave context
    :param file_path: Path to JSON file
    """
    with open(file_path, "r") as f:
        data_list = json.load(f)

    with context.db_manager.get_session() as db_session:
        global_index = 0
        for data in data_list:
            status = data["status"]
            count = int(data["count"])

            for i in range(count):
                session = create_test_session(
                    status=status,
                    description=f"{status} backup {i}",
                    unique_id=global_index,
                )
                db_session.add(session)
                global_index += 1
        db_session.commit()


@given("the database has a session with null ending and size")
def step_create_session_with_nulls(context: Context) -> None:
    """
    Create session with null optional fields.

    :param context: Behave context
    """
    with context.db_manager.get_session() as db_session:
        session = create_test_session(
            ending=None,
            size=None,
            description="Session with nulls",
        )
        db_session.add(session)
        db_session.commit()


@given('the database has a session with start "{start_time}" and ending "{end_time}"')
def step_create_session_with_times(
    context: Context, start_time: str, end_time: str
) -> None:
    """
    Create session with specific timestamps.

    :param context: Behave context
    :param start_time: Start timestamp string
    :param end_time: End timestamp string
    """
    with context.db_manager.get_session() as db_session:
        session = create_test_session(
            start=datetime.fromisoformat(start_time),
            ending=datetime.fromisoformat(end_time),
            description="Timed session",
        )
        db_session.add(session)
        db_session.commit()


@given("no configuration file exists")
def step_no_config_file(context: Context) -> None:
    """
    Remove config file to test error handling.

    :param context: Behave context
    """
    delete_config_file(context.config_file)


@given("a configuration with invalid database path")
def step_invalid_database_config(context: Context) -> None:
    """
    Create config with invalid database path.

    :param context: Behave context
    """
    config_path = generate_test_config(context.temp_path, invalid_db_path=True)
    context.config_file = config_path


@when("I run the list command")
def step_run_list_command(context: Context) -> None:
    """
    Execute zmbackup list command with test config.

    :param context: Behave context
    """
    result = context.cli_runner.invoke(
        cli, ["--config-path", str(context.config_file), "list"], catch_exceptions=False
    )

    context.result = result

    # Parse table output if present
    context.parsed_table = parse_prettytable_output(result.output)


@then('the output should contain "{text}"')
def step_output_contains(context: Context, text: str) -> None:
    """
    Verify output contains expected text.

    :param context: Behave context
    :param text: Expected text
    """
    assert context.result is not None, "No command has been run"
    assert text in context.result.output, (
        f"Output does not contain '{text}'. " f"Output was: {context.result.output}"
    )


@then("the output should contain a table with {count:d} row")
@then("the output should contain a table with {count:d} rows")
def step_verify_table_row_count(context: Context, count: int) -> None:
    """
    Verify PrettyTable has expected number of data rows.

    :param context: Behave context
    :param count: Expected row count
    """
    assert context.parsed_table is not None, (
        f"No table found in output: {context.result.output}"
    )

    actual_count = context.parsed_table.get_row_count()
    assert actual_count == count, f"Expected {count} rows, got {actual_count}"


@then("the table should have columns {columns}")
def step_verify_table_columns(context: Context, columns: str) -> None:
    """
    Verify table has expected column headers.

    :param context: Behave context
    :param columns: Comma-separated column names
    """
    assert context.parsed_table is not None, "No table found in output"

    expected_columns = [c.strip().strip('"') for c in columns.split(",")]
    assert_table_has_columns(context.parsed_table, expected_columns)


@then('row {row_num:d} should contain data from "{file_path}"')
def step_verify_row_data_json(context: Context, row_num: int, file_path: str) -> None:
    """
    Verify specific row contains expected data from JSON file.

    :param context: Behave context
    :param row_num: Row index (1-based for Gherkin)
    :param file_path: Path to JSON file
    """
    assert context.parsed_table is not None, "No table found in output"

    with open(file_path, "r") as f:
        data_list = json.load(f)

    # Convert 1-based row_num to 0-based index
    row_index = row_num - 1

    for expected_values in data_list:
        assert_row_contains(context.parsed_table, row_index, expected_values)


@then("the exit code should be {code:d}")
def step_verify_exit_code(context: Context, code: int) -> None:
    """
    Verify command exit code.

    :param context: Behave context
    :param code: Expected exit code
    """
    assert context.result is not None, "No command has been run"
    assert context.result.exit_code == code, (
        f"Expected exit code {code}, got {context.result.exit_code}"
    )


@then('the output should contain "N/A" for missing fields')
def step_verify_na_fields(context: Context) -> None:
    """
    Verify N/A appears for null values.

    :param context: Behave context
    """
    assert context.parsed_table is not None, "No table found in output"

    # Check the first row for N/A in Ending or Size
    row = context.parsed_table.get_row(0)
    assert row is not None, "Table has no data rows"

    assert row.get("Ending") == "N/A" or row.get("Size") == "N/A", (
        f"Row does not contain N/A for missing fields. Row: {row}"
    )
