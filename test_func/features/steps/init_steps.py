import json
import os
from unittest.mock import patch

from behave import given, when, then
from behave.runner import Context

from src.zmbackup import cli


@given("I am running as root")
def step_running_as_root(context: Context) -> None:
    """
    Mock os.geteuid to return 0 (root).
    
    :param context: Behave context
    """
    patcher = patch("os.geteuid", return_value=0)
    patcher.start()
    context.add_cleanup(patcher.stop)


@given("I am not running as root")
def step_not_running_as_root(context: Context) -> None:
    """
    Mock os.geteuid to return 1000 (non-root).
    
    :param context: Behave context
    """
    patcher = patch("os.geteuid", return_value=1000)
    patcher.start()
    context.add_cleanup(patcher.stop)


@when("I run the init command")
def step_run_init_no_input(context: Context) -> None:
    """
    Execute zmbackup init command.
    
    :param context: Behave context
    """
    result = context.cli_runner.invoke(
        cli, ["--config-path", str(context.config_file), "init"], catch_exceptions=False
    )
    context.result = result


@when('I run the init command and provide inputs from "{file_path}"')
def step_run_init_with_inputs(context: Context, file_path: str) -> None:
    """
    Execute zmbackup init command with mocked user inputs from JSON.
    
    :param context: Behave context
    :param file_path: Path to JSON file containing inputs
    """
    with open(file_path, "r") as f:
        inputs_dict = json.load(f)

    # The order of inputs matters and must match the order in src/operations/init.py
    # ose_user, ose_default_bkp_dir, ose_install_address, ose_install_ldappass,
    # zmbkp_mail_alert, zmbkp_mail_sender, max_parallel_process, rotate_time,
    # lock_backup, session_type
    
    ordered_inputs = [
        str(inputs_dict["ose_user"]),
        str(inputs_dict["ose_default_bkp_dir"]),
        str(inputs_dict["ose_install_address"]),
        str(inputs_dict["ose_install_ldappass"]),
        str(inputs_dict["zmbkp_mail_alert"]),
        str(inputs_dict["zmbkp_mail_sender"]),
        str(inputs_dict["max_parallel_process"]),
        str(inputs_dict["rotate_time"]),
        str(inputs_dict["lock_backup"]),
        str(inputs_dict["session_type"]),
    ]
    
    input_str = "\n".join(ordered_inputs) + "\n"

    result = context.cli_runner.invoke(
        cli, ["--config-path", str(context.config_file), "init"], input=input_str, catch_exceptions=False
    )
    context.result = result


@when('I run the init command and provide an invalid email "{invalid_email}"')
def step_run_init_invalid_email(context: Context, invalid_email: str) -> None:
    """
    Execute zmbackup init command providing an invalid email to see validation error.
    
    :param context: Behave context
    :param invalid_email: Invalid email string
    """
    # Provide inputs until the first email field (zmbkp_mail_alert)
    ordered_inputs = [
        "zimbra",           # ose_user
        "/opt/zimbra/backup",# ose_default_bkp_dir
        "127.0.0.1",        # ose_install_address
        "password",         # ose_install_ldappass
        invalid_email,      # zmbkp_mail_alert (This should trigger validation error)
    ]
    
    input_str = "\n".join(ordered_inputs) + "\n"

    # We use catch_exceptions=True because click.Abort might be raised if it gets stuck
    # but here we just want to see the error message in output.
    # Click.prompt will re-prompt if validation fails, so we might need to be careful.
    # To avoid infinite loop in tests, we only provide one invalid input.
    result = context.cli_runner.invoke(
        cli, ["--config-path", str(context.config_file), "init"], input=input_str
    )
    context.result = result


@then("the configuration file should exist")
def step_config_file_exists(context: Context) -> None:
    """
    Verify the configuration file was created.
    
    :param context: Behave context
    """
    assert context.config_file.exists(), f"Config file {context.config_file} was not created"


@then('the configuration file should contain "{text}"')
def step_config_file_contains(context: Context, text: str) -> None:
    """
    Verify the configuration file contains specific text.
    
    :param context: Behave context
    :param text: Text to look for
    """
    content = context.config_file.read_text()
    assert text in content, f"Config file does not contain '{text}'. Content:\n{content}"
