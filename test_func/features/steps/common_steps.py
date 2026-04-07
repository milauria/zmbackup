"""Common step implementations for functional tests."""

import shlex
import re
from typing import Optional

from pathlib import Path
from behave import when, then
from behave.runner import Context

from zmbackup import cli
from test_func.helpers.output_parser import parse_prettytable_output


@when('I run the {command} command with {parameters}')
@when('I run the {command} command')
def step_run_command_with_parameters(
    context: Context, command: str, parameters: str = ""
) -> None:
    """
    Execute any zmbackup command with optional parameters.
    
    This generic step can run any CLI command with flags and options.
    Examples:
    - When I run the init command
    - When I run the list command
    - When I run the migrate command with --force --dry-run
    - When I run the migrate command with --output /path/to/file --backup-suffix .old
    
    :param context: Behave context
    :param command: Command name (e.g., init, list, migrate, backup, restore)
    :param parameters: Space-separated parameters/flags (e.g., "--force --dry-run")
    """
    # Build command arguments
    args = ["--config-path", str(context.config_file), command]
    
    # Parse and add parameters if provided
    if parameters:
        # Use shlex to properly handle quoted strings and spaces
        param_list = shlex.split(parameters)
        args.extend(param_list)
        
        # For migrate command, extract custom output path if specified
        if "--output" in parameters:
            output_match = re.search(r'--output\s+"?([^"\s]+)"?', parameters)
            if output_match:
                custom_output = output_match.group(1)
                # Store path as-is (same way ConfigMigrator will receive it)
                context.custom_output_path = Path(custom_output)
    
    # Execute the command
    result = context.cli_runner.invoke(cli, args, catch_exceptions=False)
    
    # Store result in context
    context.result = result
    
    # Parse table output if this is a list command
    if command == "list":
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
        f"Output does not contain '{text}'. Output was: {context.result.output}"
    )


@then("the exit code should be {code:d}")
def step_verify_exit_code(context: Context, code: int) -> None:
    """
    Verify command exit code.
    
    :param context: Behave context
    :param code: Expected exit code
    """
    assert context.result is not None, "No command has been run"
    assert context.result.exit_code == code, (
        f"Expected exit code {code}, got {context.result.exit_code}. "
        f"Output: {context.result.output}"
    )
