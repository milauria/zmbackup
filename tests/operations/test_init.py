from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, mock_open, patch

import click
import pytest

from src.operations.init import run_init


@pytest.fixture
def mock_env_setup():
    """Fixture to mock Jinja2 environment and file operations."""
    with (
        patch("src.operations.init.Environment") as mock_env_class,
        patch("src.operations.init.open", mock_open()) as mocked_file,
        patch("src.operations.init.Path.mkdir") as mock_mkdir,
    ):

        mock_env = mock_env_class.return_value
        mock_template = MagicMock()
        mock_env.get_template.return_value = mock_template

        yield {"env": mock_env, "template": mock_template, "file": mocked_file, "mkdir": mock_mkdir}


@pytest.mark.parametrize(
    "inputs, expected_context",
    [
        (
            [
                "zimbra",
                "/opt/zimbra/backup",
                "127.0.0.1",
                "secretpassword",
                "admin@example.com",
                "backup@example.com",
                5,
                15,
                "true",
                "SQLITE3",
            ],
            {
                "ose_user": "zimbra",
                "ose_default_bkp_dir": "/opt/zimbra/backup",
                "ose_install_address": "127.0.0.1",
                "ose_install_ldappass": "secretpassword",
                "zmbkp_mail_alert": "admin@example.com",
                "zmbkp_mail_sender": "backup@example.com",
                "max_parallel_process": 5,
                "rotate_time": 15,
                "lock_backup": "true",
                "session_type": "SQLITE3",
            },
        ),
        (
            ["customuser", "/backup", "10.0.0.1", "pass", "user@test.com", "sender@test.com", 1, 7, "false", "TXT"],
            {
                "ose_user": "customuser",
                "ose_default_bkp_dir": "/backup",
                "ose_install_address": "10.0.0.1",
                "ose_install_ldappass": "pass",
                "zmbkp_mail_alert": "user@test.com",
                "zmbkp_mail_sender": "sender@test.com",
                "max_parallel_process": 1,
                "rotate_time": 7,
                "lock_backup": "false",
                "session_type": "TXT",
            },
        ),
    ],
)
@patch("src.operations.init.os.geteuid", return_value=0)
def test_run_init_success_parametrized(
    mock_geteuid: MagicMock,
    mock_env_setup: Dict[str, Any],
    inputs: List[Any],
    expected_context: Dict[str, Any],
) -> None:
    """
    Test run_init with different input sets.

    :param mock_geteuid: Mocked geteuid
    :param mock_env_setup: Mocked environment fixture
    :param inputs: List of inputs for prompts
    :param expected_context: Expected context for template rendering
    """
    config_path = "/etc/zmbackup/zmbackup.conf"
    mock_env_setup["template"].render.return_value = "rendered_content"

    with patch("click.prompt", side_effect=inputs) as mocked_prompt:
        run_init(config_path)

        assert mocked_prompt.call_count == 10
        mock_env_setup["template"].render.assert_called_once_with(**expected_context)
        mock_env_setup["mkdir"].assert_called_once_with(parents=True, exist_ok=True)
        mock_env_setup["file"].assert_called_once_with(Path(config_path), "w")
        mock_env_setup["file"]().write.assert_called_once_with("rendered_content")


@pytest.mark.parametrize(
    "exception_to_raise, expected_log",
    [
        (Exception("Template error"), "Error initializing configuration: Template error"),
        (PermissionError("Access denied"), "Error initializing configuration: Access denied"),
        (IOError("Disk full"), "Error initializing configuration: Disk full"),
    ],
)
@patch("src.operations.init.os.geteuid", return_value=0)
def test_run_init_errors_parametrized(
    mock_geteuid: MagicMock,
    mock_env_setup: Dict[str, Any],
    exception_to_raise: Exception,
    expected_log: str,
) -> None:
    """
    Test run_init error handling for various failure scenarios.

    :param mock_geteuid: Mocked geteuid
    :param mock_env_setup: Mocked environment fixture
    :param exception_to_raise: Exception to simulate
    :param expected_log: Expected error message in logs
    """
    mock_env_setup["template"].render.side_effect = exception_to_raise

    # Fill enough inputs for prompts to proceed
    inputs = ["zimbra", "/tmp", "127.0.0.1", "p", "a@b.com", "a@b.com", 1, 1, "true", "TXT"]

    with patch("click.prompt", side_effect=inputs), patch("click.echo") as mock_echo:

        with pytest.raises(click.Abort):
            run_init("/tmp/test.conf")

        mock_echo.assert_any_call(expected_log)


@patch("src.operations.init.os.geteuid", return_value=0)
def test_run_init_template_load_failure(mock_geteuid: MagicMock, mock_env_setup: Dict[str, Any]) -> None:
    """
    Test behavior when the template file cannot be found or loaded.

    :param mock_geteuid: Mocked geteuid
    :param mock_env_setup: Mocked environment fixture
    """
    mock_env_setup["env"].get_template.side_effect = Exception("File not found")

    with (
        patch(
            "click.prompt", side_effect=["zimbra", "/tmp", "127.0.0.1", "p", "a@b.com", "a@b.com", 1, 1, "true", "TXT"]
        ),
        pytest.raises(click.Abort),
    ):
        run_init("/tmp/test.conf")


def test_run_init_non_root() -> None:
    """Test that run_init aborts if not executed by root."""
    with patch("src.operations.init.os.geteuid", return_value=1000), patch("click.echo") as mock_echo:

        with pytest.raises(click.Abort):
            run_init()

        mock_echo.assert_called_with("Error: This command can only be executed by root user.", err=True)


def test_validate_email_success() -> None:
    """Test validate_email with valid email."""
    from src.operations.init import validate_email

    email = "test@example.com"
    assert validate_email(email) == email


def test_validate_email_failure() -> None:
    """Test validate_email with invalid email."""
    from src.operations.init import validate_email

    with pytest.raises(click.BadParameter) as excinfo:
        validate_email("invalid-email")
    assert "'invalid-email' is not a valid email address." in str(excinfo.value)


@pytest.mark.parametrize("address", ["127.0.0.1", "::1", "ldap.example.com", "server1.local"])
def test_validate_address_success(address: str) -> None:
    """
    Test validate_address with valid IP or FQDN.

    :param address: Address to validate
    """
    from src.operations.init import validate_address

    assert validate_address(address) == address


@pytest.mark.parametrize("address", ["invalid_address", "http://server", "1.2.3.4.5"])
def test_validate_address_failure(address: str) -> None:
    """
    Test validate_address with invalid address.

    :param address: Address to validate
    """
    from src.operations.init import validate_address

    with pytest.raises(click.BadParameter) as excinfo:
        validate_address(address)
    assert f"'{address}' is not a valid IP or FQDN." in str(excinfo.value)
