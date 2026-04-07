"""Step implementations for migrate-config functional tests."""

import json
import shutil
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from behave import given, when, then
from behave.runner import Context
from click.testing import CliRunner

from operations.migrate_config import migrate_config


@given("I have a temporary directory for testing")
def step_have_temp_directory(context: Context) -> None:
    """
    Ensure temporary directory is available (already created in environment.py).
    
    :param context: Behave context
    """
    assert context.temp_path.exists(), "Temporary directory not found"


@given("I have a legacy config file")
def step_create_legacy_config(context: Context) -> None:
    """
    Create a legacy KEY=VALUE configuration file.
    
    :param context: Behave context
    """
    context.legacy_config_path = context.temp_path / "zmbackup.conf"
    legacy_content = """# Legacy configuration
BACKUPUSER=zimbra
WORKDIR=/opt/zimbra/backup
LDAPSERVER=ldap://localhost:389
LDAPADMIN=uid=zimbra,cn=admins,cn=zimbra
LDAPPASS=secretpassword
LOGFILE=/opt/zimbra/log/zmbackup.log
ENABLE_EMAIL_NOTIFY=all
EMAIL_NOTIFY=admin@example.com
EMAIL_SENDER=zmbackup@example.com
MAX_PARALLEL_PROCESS=5
ROTATE_TIME=30
LOCK_BACKUP=true
SESSION_TYPE=SQLITE3
BACKUP_INACTIVE_ACCOUNTS=false
SSL_ENABLE=true
ZMMAILBOX=/opt/zimbra/bin/zmmailbox
"""
    context.legacy_config_path.write_text(legacy_content)
    context.expected_json_path = context.temp_path / "zmbackup.json"


@given("I have a JSON config file")
def step_create_json_config(context: Context) -> None:
    """
    Create a JSON configuration file.
    
    :param context: Behave context
    """
    context.json_config_path = context.temp_path / "zmbackup.json"
    json_content = {
        "version": "1.0",
        "zimbra": {
            "backup_user": "zimbra",
            "workdir": "/opt/zimbra/backup",
            "ldap_server": "ldap://localhost:389",
            "ldap_admin": "uid=zimbra,cn=admins,cn=zimbra",
            "ldap_password": "secret"
        },
        "logging": {
            "log_file": "/opt/zimbra/log/zmbackup.log"
        },
        "email": {
            "enable_notify": "all",
            "notify_address": "admin@example.com",
            "sender_address": "zmbackup@example.com"
        },
        "backup": {
            "max_parallel_process": 5,
            "rotate_time": 30,
            "lock_backup": True,
            "backup_inactive_accounts": False,
            "ssl_enable": True
        },
        "session": {
            "type": "SQLITE3"
        },
        "binaries": {
            "zmmailbox": "/opt/zimbra/bin/zmmailbox"
        }
    }
    with open(context.json_config_path, "w") as f:
        json.dump(json_content, f, indent=2)
    context.legacy_config_path = context.json_config_path


@given("the config file does not exist")
def step_config_does_not_exist(context: Context) -> None:
    """
    Set up context for non-existent config file.
    
    :param context: Behave context
    """
    context.legacy_config_path = context.temp_path / "nonexistent.conf"
    context.expected_json_path = context.temp_path / "nonexistent.json"


@given("the target JSON file already exists")
def step_target_json_exists(context: Context) -> None:
    """
    Create an existing target JSON file.
    
    :param context: Behave context
    """
    context.expected_json_path.write_text('{"version": "1.0", "old": "data"}')


@given("I have an invalid legacy config file")
def step_create_invalid_legacy_config(context: Context) -> None:
    """
    Create an invalid legacy configuration file.
    
    :param context: Behave context
    """
    context.legacy_config_path = context.temp_path / "invalid.conf"
    # Invalid email will trigger validation error
    invalid_content = """BACKUPUSER=zimbra
WORKDIR=/opt/zimbra/backup
LDAPSERVER=ldap://localhost:389
LDAPADMIN=uid=zimbra,cn=admins,cn=zimbra
LDAPPASS=secret
LOGFILE=/opt/zimbra/log/zmbackup.log
ENABLE_EMAIL_NOTIFY=all
EMAIL_NOTIFY=invalid-email-format
EMAIL_SENDER=also-invalid
MAX_PARALLEL_PROCESS=5
ROTATE_TIME=30
LOCK_BACKUP=true
SESSION_TYPE=SQLITE3
BACKUP_INACTIVE_ACCOUNTS=false
SSL_ENABLE=true
ZMMAILBOX=/opt/zimbra/bin/zmmailbox
"""
    context.legacy_config_path.write_text(invalid_content)
    context.expected_json_path = context.temp_path / "invalid.json"


@given("I have a legacy config file in /etc/zmbackup/")
def step_create_legacy_in_etc(context: Context) -> None:
    """
    Set up context for /etc/zmbackup/ path (won't actually create in /etc).
    
    :param context: Behave context
    """
    # For testing, we'll use a temp path but tell the migrator it's /etc/zmbackup/
    context.legacy_config_path = context.temp_path / "zmbackup.conf"
    legacy_content = """BACKUPUSER=zimbra
WORKDIR=/opt/zimbra/backup
LDAPSERVER=ldap://localhost:389
LDAPADMIN=uid=zimbra,cn=admins,cn=zimbra
LDAPPASS=secret
LOGFILE=/opt/zimbra/log/zmbackup.log
ENABLE_EMAIL_NOTIFY=all
EMAIL_NOTIFY=admin@example.com
EMAIL_SENDER=zmbackup@example.com
MAX_PARALLEL_PROCESS=5
ROTATE_TIME=30
LOCK_BACKUP=true
SESSION_TYPE=SQLITE3
BACKUP_INACTIVE_ACCOUNTS=false
SSL_ENABLE=true
ZMMAILBOX=/opt/zimbra/bin/zmmailbox
"""
    context.legacy_config_path.write_text(legacy_content)
    # Simulate /etc/zmbackup/ path
    context.etc_path = Path("/etc/zmbackup/zmbackup.json")


@given("I have a legacy config file in user directory")
def step_create_legacy_in_user_dir(context: Context) -> None:
    """
    Create a legacy config in user (non-privileged) directory.
    
    :param context: Behave context
    """
    context.user_dir = context.temp_path / "user_config"
    context.user_dir.mkdir(exist_ok=True)
    context.legacy_config_path = context.user_dir / "zmbackup.conf"
    legacy_content = """BACKUPUSER=zimbra
WORKDIR=/opt/zimbra/backup
LDAPSERVER=ldap://localhost:389
LDAPADMIN=uid=zimbra,cn=admins,cn=zimbra
LDAPPASS=secret
LOGFILE=/opt/zimbra/log/zmbackup.log
ENABLE_EMAIL_NOTIFY=all
EMAIL_NOTIFY=admin@example.com
EMAIL_SENDER=zmbackup@example.com
MAX_PARALLEL_PROCESS=5
ROTATE_TIME=30
LOCK_BACKUP=true
SESSION_TYPE=SQLITE3
BACKUP_INACTIVE_ACCOUNTS=false
SSL_ENABLE=true
ZMMAILBOX=/opt/zimbra/bin/zmmailbox
"""
    context.legacy_config_path.write_text(legacy_content)
    context.expected_json_path = context.user_dir / "zmbackup.json"


@when("I run the migrate-config command")
def step_run_migrate_config(context: Context) -> None:
    """
    Execute the migrate-config operation.
    
    :param context: Behave context
    """
    from operations.migrate_config import ConfigMigrator
    
    # Capture stdout and stderr
    stdout_capture = StringIO()
    stderr_capture = StringIO()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    try:
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture
        
        migrator = ConfigMigrator(
            config_path=context.legacy_config_path,
            output_path=None,
            backup_suffix=".bak",
            force=False,
            dry_run=False
        )
        
        exit_code = migrator.migrate()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    
    # Create a mock result object similar to Click's CliResult
    class MockResult:
        def __init__(self, exit_code, output):
            self.exit_code = exit_code
            self.output = output
    
    combined_output = stdout_capture.getvalue() + stderr_capture.getvalue()
    context.result = MockResult(exit_code, combined_output)


@when("I run the migrate-config command with --force flag")
def step_run_migrate_config_force(context: Context) -> None:
    """
    Execute migrate-config with --force flag.
    
    :param context: Behave context
    """
    from operations.migrate_config import ConfigMigrator
    
    stdout_capture = StringIO()
    stderr_capture = StringIO()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    try:
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture
        
        migrator = ConfigMigrator(
            config_path=context.legacy_config_path,
            output_path=None,
            backup_suffix=".bak",
            force=True,
            dry_run=False
        )
        
        exit_code = migrator.migrate()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    
    class MockResult:
        def __init__(self, exit_code, output):
            self.exit_code = exit_code
            self.output = output
    
    combined_output = stdout_capture.getvalue() + stderr_capture.getvalue()
    context.result = MockResult(exit_code, combined_output)


@when("I run the migrate-config command with --dry-run flag")
def step_run_migrate_config_dry_run(context: Context) -> None:
    """
    Execute migrate-config with --dry-run flag.
    
    :param context: Behave context
    """
    from operations.migrate_config import ConfigMigrator
    
    stdout_capture = StringIO()
    stderr_capture = StringIO()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    try:
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture
        
        migrator = ConfigMigrator(
            config_path=context.legacy_config_path,
            output_path=None,
            backup_suffix=".bak",
            force=False,
            dry_run=True
        )
        
        exit_code = migrator.migrate()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    
    class MockResult:
        def __init__(self, exit_code, output):
            self.exit_code = exit_code
            self.output = output
    
    combined_output = stdout_capture.getvalue() + stderr_capture.getvalue()
    context.result = MockResult(exit_code, combined_output)


@when("I run the migrate-config command with custom output path")
def step_run_migrate_config_custom_output(context: Context) -> None:
    """
    Execute migrate-config with custom output path.
    
    :param context: Behave context
    """
    from operations.migrate_config import ConfigMigrator
    
    context.custom_output_path = context.temp_path / "custom" / "config.json"
    
    stdout_capture = StringIO()
    stderr_capture = StringIO()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    try:
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture
        
        migrator = ConfigMigrator(
            config_path=context.legacy_config_path,
            output_path=context.custom_output_path,
            backup_suffix=".bak",
            force=False,
            dry_run=False
        )
        
        exit_code = migrator.migrate()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    
    class MockResult:
        def __init__(self, exit_code, output):
            self.exit_code = exit_code
            self.output = output
    
    combined_output = stdout_capture.getvalue() + stderr_capture.getvalue()
    context.result = MockResult(exit_code, combined_output)


@when("I run the migrate-config command for /etc/zmbackup/")
def step_run_migrate_config_etc(context: Context) -> None:
    """
    Execute migrate-config targeting /etc/zmbackup/ (will check root).
    
    :param context: Behave context
    """
    from operations.migrate_config import ConfigMigrator
    
    stdout_capture = StringIO()
    stderr_capture = StringIO()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    try:
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture
        
        migrator = ConfigMigrator(
            config_path=context.legacy_config_path,
            output_path=context.etc_path,
            backup_suffix=".bak",
            force=False,
            dry_run=False
        )
        
        exit_code = migrator.migrate()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    
    class MockResult:
        def __init__(self, exit_code, output):
            self.exit_code = exit_code
            self.output = output
    
    combined_output = stdout_capture.getvalue() + stderr_capture.getvalue()
    context.result = MockResult(exit_code, combined_output)


@when("I run the migrate-config command for user directory")
def step_run_migrate_config_user_dir(context: Context) -> None:
    """
    Execute migrate-config for user directory (non-privileged).
    
    :param context: Behave context
    """
    from operations.migrate_config import ConfigMigrator
    
    stdout_capture = StringIO()
    stderr_capture = StringIO()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    try:
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture
        
        migrator = ConfigMigrator(
            config_path=context.legacy_config_path,
            output_path=None,
            backup_suffix=".bak",
            force=False,
            dry_run=False
        )
        
        exit_code = migrator.migrate()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    
    class MockResult:
        def __init__(self, exit_code, output):
            self.exit_code = exit_code
            self.output = output
    
    combined_output = stdout_capture.getvalue() + stderr_capture.getvalue()
    context.result = MockResult(exit_code, combined_output)


@when('I run the migrate-config command with backup suffix "{suffix}"')
def step_run_migrate_config_custom_suffix(context: Context, suffix: str) -> None:
    """
    Execute migrate-config with custom backup suffix.
    
    :param context: Behave context
    :param suffix: Backup file suffix
    """
    from operations.migrate_config import ConfigMigrator
    
    context.backup_suffix = suffix
    
    stdout_capture = StringIO()
    stderr_capture = StringIO()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    try:
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture
        
        migrator = ConfigMigrator(
            config_path=context.legacy_config_path,
            output_path=None,
            backup_suffix=suffix,
            force=False,
            dry_run=False
        )
        
        exit_code = migrator.migrate()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    
    class MockResult:
        def __init__(self, exit_code, output):
            self.exit_code = exit_code
            self.output = output
    
    combined_output = stdout_capture.getvalue() + stderr_capture.getvalue()
    context.result = MockResult(exit_code, combined_output)


@then("the JSON config file should exist")
def step_json_config_exists(context: Context) -> None:
    """
    Verify the JSON config file was created.
    
    :param context: Behave context
    """
    assert context.expected_json_path.exists(), f"JSON config {context.expected_json_path} was not created"


@then("the JSON config file should not exist")
def step_json_config_not_exists(context: Context) -> None:
    """
    Verify the JSON config file was NOT created.
    
    :param context: Behave context
    """
    assert not context.expected_json_path.exists(), f"JSON config {context.expected_json_path} should not exist"


@then('the backup file should exist with suffix "{suffix}"')
def step_backup_exists(context: Context, suffix: str) -> None:
    """
    Verify the backup file was created with the expected suffix.
    
    :param context: Behave context
    :param suffix: Expected backup suffix
    """
    backup_path = Path(str(context.legacy_config_path) + suffix)
    assert backup_path.exists(), f"Backup file {backup_path} was not created"
    context.backup_path = backup_path


@then("the backup file should not exist")
def step_backup_not_exists(context: Context) -> None:
    """
    Verify the backup file was NOT created.
    
    :param context: Behave context
    """
    backup_path = Path(str(context.legacy_config_path) + ".bak")
    assert not backup_path.exists(), f"Backup file {backup_path} should not exist"


@then('the JSON config should contain version "{version}"')
def step_json_contains_version(context: Context, version: str) -> None:
    """
    Verify the JSON config contains the expected version.
    
    :param context: Behave context
    :param version: Expected version string
    """
    with open(context.expected_json_path, "r") as f:
        config_data = json.load(f)
    assert config_data.get("version") == version, f"Expected version {version}, got {config_data.get('version')}"


@then("the JSON config should have correct values from legacy config")
def step_json_has_correct_values(context: Context) -> None:
    """
    Verify the JSON config has correctly migrated values from legacy.
    
    :param context: Behave context
    """
    with open(context.expected_json_path, "r") as f:
        config_data = json.load(f)
    
    # Verify key values
    assert config_data["version"] == "1.0"
    assert config_data["zimbra"]["backup_user"] == "zimbra"
    assert config_data["zimbra"]["workdir"] == "/opt/zimbra/backup"
    assert config_data["zimbra"]["ldap_server"] == "ldap://localhost:389"
    assert config_data["zimbra"]["ldap_password"] == "secretpassword"
    assert config_data["email"]["notify_address"] == "admin@example.com"
    assert config_data["email"]["sender_address"] == "zmbackup@example.com"
    assert config_data["backup"]["max_parallel_process"] == 5
    assert config_data["backup"]["rotate_time"] == 30
    assert config_data["backup"]["lock_backup"] is True
    assert config_data["backup"]["backup_inactive_accounts"] is False
    assert config_data["backup"]["ssl_enable"] is True
    assert config_data["session"]["type"] == "SQLITE3"


@then("the custom JSON config file should exist")
def step_custom_json_exists(context: Context) -> None:
    """
    Verify the custom JSON config file was created.
    
    :param context: Behave context
    """
    assert context.custom_output_path.exists(), f"Custom JSON config {context.custom_output_path} was not created"


@then("the custom JSON config should have correct values from legacy config")
def step_custom_json_has_correct_values(context: Context) -> None:
    """
    Verify the custom JSON config has correctly migrated values.
    
    :param context: Behave context
    """
    with open(context.custom_output_path, "r") as f:
        config_data = json.load(f)
    
    # Verify key values
    assert config_data["version"] == "1.0"
    assert config_data["zimbra"]["backup_user"] == "zimbra"
    assert config_data["email"]["notify_address"] == "admin@example.com"


@then("the JSON config file should exist in user directory")
def step_json_exists_in_user_dir(context: Context) -> None:
    """
    Verify the JSON config was created in the user directory.
    
    :param context: Behave context
    """
    assert context.expected_json_path.exists(), f"JSON config {context.expected_json_path} was not created in user directory"
