"""Unit tests for configuration migration operation."""

import json
from pathlib import Path
from typing import Any, Dict

import click
import pytest

from src.exceptions import ConfigurationParseError, ConfigurationValidationError
from src.operations.migrate_config import ConfigMigrator, migrate_config


@pytest.fixture
def legacy_config_data() -> Dict[str, str]:
    """
    Provide legacy configuration dictionary.

    :return: Dictionary of legacy KEY=VALUE pairs
    """
    return {
        "BACKUPUSER": "zimbra",
        "WORKDIR": "/opt/zimbra/backup",
        "LDAPSERVER": "ldap://localhost:389",
        "LDAPADMIN": "uid=zimbra,cn=admins,cn=zimbra",
        "LDAPPASS": "secret",
        "LOGFILE": "/opt/zimbra/log/zmbackup.log",
        "ENABLE_EMAIL_NOTIFY": "all",
        "EMAIL_NOTIFY": "admin@example.com",
        "EMAIL_SENDER": "zmbackup@example.com",
        "MAX_PARALLEL_PROCESS": "5",
        "ROTATE_TIME": "30",
        "LOCK_BACKUP": "true",
        "SESSION_TYPE": "SQLITE3",
        "BACKUP_INACTIVE_ACCOUNTS": "false",
        "SSL_ENABLE": "yes",
        "ZMMAILBOX": "/opt/zimbra/bin/zmmailbox",
    }


# Tests for ConfigMigrator._determine_target_path()


def test_determine_target_path_with_conf_extension(tmp_path: Path) -> None:
    """
    Test target path determination for .conf files.

    :param tmp_path: Pytest temporary path fixture
    """
    config_file = tmp_path / "zmbackup.conf"
    config_file.write_text("BACKUPUSER=zimbra\n")

    migrator = ConfigMigrator(config_path=config_file, is_root_func=lambda: True)
    assert migrator.output_path == tmp_path / "zmbackup.json"


def test_determine_target_path_with_other_extension(tmp_path: Path) -> None:
    """
    Test target path determination for non-.conf files.

    :param tmp_path: Pytest temporary path fixture
    """
    config_file = tmp_path / "config.txt"
    config_file.write_text("BACKUPUSER=zimbra\n")

    migrator = ConfigMigrator(config_path=config_file, is_root_func=lambda: True)
    assert migrator.output_path == tmp_path / "config.txt.json"


def test_determine_target_path_with_custom_output(tmp_path: Path) -> None:
    """
    Test target path with custom output path specified.

    :param tmp_path: Pytest temporary path fixture
    """
    config_file = tmp_path / "zmbackup.conf"
    config_file.write_text("BACKUPUSER=zimbra\n")
    custom_output = tmp_path / "custom.json"

    migrator = ConfigMigrator(config_path=config_file, output_path=custom_output, is_root_func=lambda: True)
    assert migrator.output_path == custom_output


# Tests for ConfigMigrator._is_json_format()


def test_is_json_format_detects_json(tmp_path: Path) -> None:
    """
    Test JSON format detection for valid JSON file.

    :param tmp_path: Pytest temporary path fixture
    """
    json_file = tmp_path / "config.json"
    json_file.write_text('{"version": "1.0"}')

    migrator = ConfigMigrator(config_path=json_file, is_root_func=lambda: True)
    assert migrator._is_json_format(json_file) is True


def test_is_json_format_detects_legacy(tmp_path: Path) -> None:
    """
    Test JSON format detection for legacy KEY=VALUE file.

    :param tmp_path: Pytest temporary path fixture
    """
    legacy_file = tmp_path / "config.conf"
    legacy_file.write_text("BACKUPUSER=zimbra\n")

    migrator = ConfigMigrator(config_path=legacy_file, is_root_func=lambda: True)
    assert migrator._is_json_format(legacy_file) is False


def test_is_json_format_with_whitespace(tmp_path: Path) -> None:
    """
    Test JSON format detection with leading whitespace.

    :param tmp_path: Pytest temporary path fixture
    """
    json_file = tmp_path / "config.json"
    json_file.write_text('  \n\n  {\n  "version": "1.0"\n}')

    migrator = ConfigMigrator(config_path=json_file, is_root_func=lambda: True)
    assert migrator._is_json_format(json_file) is True


def test_is_json_format_handles_nonexistent_file(tmp_path: Path) -> None:
    """
    Test JSON format detection for nonexistent file.

    :param tmp_path: Pytest temporary path fixture
    """
    nonexistent_file = tmp_path / "nonexistent.conf"

    migrator = ConfigMigrator(config_path=nonexistent_file, is_root_func=lambda: True)
    assert migrator._is_json_format(nonexistent_file) is False


# Tests for ConfigMigrator._parse_bool()


@pytest.mark.parametrize(
    "value,expected",
    [
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("yes", True),
        ("Yes", True),
        ("YES", True),
        ("1", True),
        ("false", False),
        ("False", False),
        ("FALSE", False),
        ("no", False),
        ("No", False),
        ("NO", False),
        ("0", False),
        ("  true  ", True),
        ("  false  ", False),
    ],
)
def test_parse_bool(tmp_path: Path, value: str, expected: bool) -> None:
    """
    Test boolean parsing from various string formats.

    :param tmp_path: Pytest temporary path fixture
    :param value: String value to parse
    :param expected: Expected boolean result
    """
    config_file = tmp_path / "test.conf"
    config_file.write_text("BACKUPUSER=zimbra\n")

    migrator = ConfigMigrator(config_path=config_file, is_root_func=lambda: True)
    assert migrator._parse_bool(value) == expected


# Tests for ConfigMigrator._convert_to_json_schema()


def test_convert_to_json_schema_with_complete_config(tmp_path: Path, legacy_config_data: Dict[str, str]) -> None:
    """
    Test conversion of complete legacy config to JSON schema.

    :param tmp_path: Pytest temporary path fixture
    :param legacy_config_data: Legacy configuration fixture
    """
    config_file = tmp_path / "test.conf"
    config_file.write_text("BACKUPUSER=zimbra\n")

    migrator = ConfigMigrator(config_path=config_file, is_root_func=lambda: True)
    result = migrator._convert_to_json_schema(legacy_config_data)

    assert result["version"] == "1.0"
    assert result["zimbra"]["backup_user"] == "zimbra"
    assert result["zimbra"]["workdir"] == "/opt/zimbra/backup"
    assert result["zimbra"]["ldap_server"] == "ldap://localhost:389"
    assert result["zimbra"]["ldap_admin"] == "uid=zimbra,cn=admins,cn=zimbra"
    assert result["zimbra"]["ldap_password"] == "secret"
    assert result["logging"]["log_file"] == "/opt/zimbra/log/zmbackup.log"
    assert result["email"]["enable_notify"] == "all"
    assert result["email"]["notify_address"] == "admin@example.com"
    assert result["email"]["sender_address"] == "zmbackup@example.com"
    assert result["backup"]["max_parallel_process"] == 5
    assert result["backup"]["rotate_time"] == 30
    assert result["backup"]["lock_backup"] is True
    assert result["backup"]["backup_inactive_accounts"] is False
    assert result["backup"]["ssl_enable"] is True
    assert result["session"]["type"] == "SQLITE3"
    assert result["binaries"]["zmmailbox"] == "/opt/zimbra/bin/zmmailbox"


def test_convert_to_json_schema_with_missing_keys(tmp_path: Path) -> None:
    """
    Test conversion with missing optional keys uses defaults.

    :param tmp_path: Pytest temporary path fixture
    """
    config_file = tmp_path / "test.conf"
    config_file.write_text("BACKUPUSER=zimbra\n")

    migrator = ConfigMigrator(config_path=config_file, is_root_func=lambda: True)
    minimal_config = {
        "LDAPSERVER": "ldap://test:389",
        "LDAPPASS": "pass",
        "EMAIL_NOTIFY": "test@example.com",
        "EMAIL_SENDER": "sender@example.com",
    }
    result = migrator._convert_to_json_schema(minimal_config)

    # Check defaults are applied
    assert result["zimbra"]["backup_user"] == "zimbra"
    assert result["zimbra"]["workdir"] == "/opt/zimbra/backup"
    assert result["zimbra"]["ldap_admin"] == "uid=zimbra,cn=admins,cn=zimbra"
    assert result["logging"]["log_file"] == "/opt/zimbra/log/zmbackup.log"
    assert result["email"]["enable_notify"] == "all"
    assert result["backup"]["max_parallel_process"] == 3
    assert result["backup"]["rotate_time"] == 30
    assert result["backup"]["lock_backup"] is True
    assert result["session"]["type"] == "TXT"
    assert result["binaries"]["zmmailbox"] == "/opt/zimbra/bin/zmmailbox"


def test_convert_to_json_schema_type_conversions(tmp_path: Path) -> None:
    """
    Test type conversions during schema conversion.

    :param tmp_path: Pytest temporary path fixture
    """
    config_file = tmp_path / "test.conf"
    config_file.write_text("BACKUPUSER=zimbra\n")

    migrator = ConfigMigrator(config_path=config_file, is_root_func=lambda: True)
    config_data = {
        "MAX_PARALLEL_PROCESS": "10",
        "ROTATE_TIME": "60",
        "LOCK_BACKUP": "false",
        "BACKUP_INACTIVE_ACCOUNTS": "yes",
        "SSL_ENABLE": "1",
    }
    result = migrator._convert_to_json_schema(config_data)

    # Check type conversions
    assert isinstance(result["backup"]["max_parallel_process"], int)
    assert result["backup"]["max_parallel_process"] == 10
    assert isinstance(result["backup"]["rotate_time"], int)
    assert result["backup"]["rotate_time"] == 60
    assert isinstance(result["backup"]["lock_backup"], bool)
    assert result["backup"]["lock_backup"] is False
    assert isinstance(result["backup"]["backup_inactive_accounts"], bool)
    assert result["backup"]["backup_inactive_accounts"] is True
    assert isinstance(result["backup"]["ssl_enable"], bool)
    assert result["backup"]["ssl_enable"] is True


# Tests for ConfigMigrator._validate_config_dict()


def test_validate_config_dict_with_valid_config(tmp_path: Path, config_test_file) -> None:
    """
    Test validation of valid configuration dictionary.

    :param tmp_path: Pytest temporary path fixture
    :param config_test_file: Factory fixture to get test config file paths
    """
    config_file = tmp_path / "test.conf"
    config_file.write_text("BACKUPUSER=zimbra\n")

    migrator = ConfigMigrator(config_path=config_file, is_root_func=lambda: True)

    # Load valid config from test file
    import json

    valid_config_path = config_test_file("valid_config.json")
    with open(valid_config_path) as f:
        valid_config = json.load(f)

    # Should not raise
    migrator._validate_config_dict(valid_config)


def test_validate_config_dict_with_invalid_email(tmp_path: Path, config_test_file) -> None:
    """
    Test validation fails for invalid email.

    :param tmp_path: Pytest temporary path fixture
    :param config_test_file: Factory fixture to get test config file paths
    """
    config_file = tmp_path / "test.conf"
    config_file.write_text("BACKUPUSER=zimbra\n")

    migrator = ConfigMigrator(config_path=config_file, is_root_func=lambda: True)

    # Load invalid email config from test file
    import json

    invalid_config_path = config_test_file("invalid_email.json")
    with open(invalid_config_path) as f:
        invalid_config = json.load(f)

    with pytest.raises(ConfigurationValidationError):
        migrator._validate_config_dict(invalid_config)


def test_validate_config_dict_with_out_of_range_values(tmp_path: Path, config_test_file) -> None:
    """
    Test validation fails for out of range values.

    :param tmp_path: Pytest temporary path fixture
    :param config_test_file: Factory fixture to get test config file paths
    """
    config_file = tmp_path / "test.conf"
    config_file.write_text("BACKUPUSER=zimbra\n")

    migrator = ConfigMigrator(config_path=config_file, is_root_func=lambda: True)

    # Load out of range config from test file
    import json

    invalid_config_path = config_test_file("out_of_range_parallel.json")
    with open(invalid_config_path) as f:
        invalid_config = json.load(f)

    with pytest.raises(ConfigurationValidationError):
        migrator._validate_config_dict(invalid_config)


# Tests for ConfigMigrator._atomic_write_json()


def test_atomic_write_json_creates_file(tmp_path: Path) -> None:
    """
    Test atomic write creates JSON file correctly.

    :param tmp_path: Pytest temporary path fixture
    """
    config_file = tmp_path / "source.conf"
    config_file.write_text("BACKUPUSER=zimbra\n")
    output_file = tmp_path / "output.json"

    migrator = ConfigMigrator(config_path=config_file, output_path=output_file, is_root_func=lambda: True)

    test_config = {"version": "1.0", "test": "data"}
    migrator._atomic_write_json(test_config)

    assert output_file.exists()
    with open(output_file) as f:
        written_data = json.load(f)
    assert written_data == test_config


def test_atomic_write_json_creates_parent_directories(tmp_path: Path) -> None:
    """
    Test atomic write creates parent directories if needed.

    :param tmp_path: Pytest temporary path fixture
    """
    config_file = tmp_path / "source.conf"
    config_file.write_text("BACKUPUSER=zimbra\n")
    nested_output = tmp_path / "subdir" / "nested" / "output.json"

    migrator = ConfigMigrator(config_path=config_file, output_path=nested_output, is_root_func=lambda: True)

    test_config = {"version": "1.0"}
    migrator._atomic_write_json(test_config)

    assert nested_output.exists()
    assert nested_output.parent.exists()


def test_atomic_write_json_overwrites_existing(tmp_path: Path) -> None:
    """
    Test atomic write overwrites existing file.

    :param tmp_path: Pytest temporary path fixture
    """
    config_file = tmp_path / "source.conf"
    config_file.write_text("BACKUPUSER=zimbra\n")
    output_file = tmp_path / "output.json"
    output_file.write_text('{"old": "data"}')

    migrator = ConfigMigrator(config_path=config_file, output_path=output_file, is_root_func=lambda: True)

    new_config = {"version": "1.0", "new": "data"}
    migrator._atomic_write_json(new_config)

    with open(output_file) as f:
        written_data = json.load(f)
    assert written_data == new_config
    assert "old" not in written_data


def test_atomic_write_json_formats_with_indentation(tmp_path: Path) -> None:
    """
    Test atomic write formats JSON with proper indentation.

    :param tmp_path: Pytest temporary path fixture
    """
    config_file = tmp_path / "source.conf"
    config_file.write_text("BACKUPUSER=zimbra\n")
    output_file = tmp_path / "output.json"

    migrator = ConfigMigrator(config_path=config_file, output_path=output_file, is_root_func=lambda: True)

    test_config = {"version": "1.0", "nested": {"key": "value"}}
    migrator._atomic_write_json(test_config)

    content = output_file.read_text()
    # Check it's formatted (has newlines and indentation)
    assert "\n" in content
    assert "  " in content


# Tests for ConfigMigrator.migrate() - Root Privilege Tests


def test_migrate_requires_root_for_etc_zmbackup(tmp_path: Path) -> None:
    """
    Test migration requires root when writing to /etc/zmbackup/.

    :param tmp_path: Pytest temporary path fixture
    """
    config_file = tmp_path / "zmbackup.conf"
    config_file.write_text("BACKUPUSER=zimbra\n")
    # Create a path that starts with /etc/zmbackup
    etc_zmbackup_path = Path("/etc/zmbackup/zmbackup.json")

    migrator = ConfigMigrator(
        config_path=config_file, output_path=etc_zmbackup_path, is_root_func=lambda: False  # Non-root
    )

    exit_code = migrator.migrate()
    assert exit_code == 1


def test_migrate_allows_non_root_for_other_paths(tmp_path: Path) -> None:
    """
    Test migration allows non-root for paths outside /etc/zmbackup/.

    :param tmp_path: Pytest temporary path fixture
    """
    config_file = tmp_path / "zmbackup.conf"
    config_file.write_text(
        "BACKUPUSER=zimbra\n"
        "WORKDIR=/opt/zimbra/backup\n"
        "LDAPSERVER=ldap://localhost:389\n"
        "LDAPADMIN=uid=zimbra,cn=admins,cn=zimbra\n"
        "LDAPPASS=secret\n"
        "LOGFILE=/opt/zimbra/log/zmbackup.log\n"
        "ENABLE_EMAIL_NOTIFY=all\n"
        "EMAIL_NOTIFY=admin@example.com\n"
        "EMAIL_SENDER=zmbackup@example.com\n"
        "MAX_PARALLEL_PROCESS=5\n"
        "ROTATE_TIME=30\n"
        "LOCK_BACKUP=true\n"
        "SESSION_TYPE=SQLITE3\n"
        "BACKUP_INACTIVE_ACCOUNTS=false\n"
        "SSL_ENABLE=yes\n"
        "ZMMAILBOX=/opt/zimbra/bin/zmmailbox\n"
    )
    output_file = tmp_path / "zmbackup.json"

    migrator = ConfigMigrator(config_path=config_file, output_path=output_file, is_root_func=lambda: False)  # Non-root

    exit_code = migrator.migrate()
    assert exit_code == 0
    assert output_file.exists()


def test_migrate_allows_root_for_etc_zmbackup(tmp_path: Path) -> None:
    """
    Test migration allows root for /etc/zmbackup/ paths.

    :param tmp_path: Pytest temporary path fixture
    """
    config_file = tmp_path / "zmbackup.conf"
    config_file.write_text(
        "BACKUPUSER=zimbra\n"
        "WORKDIR=/opt/zimbra/backup\n"
        "LDAPSERVER=ldap://localhost:389\n"
        "LDAPADMIN=uid=zimbra,cn=admins,cn=zimbra\n"
        "LDAPPASS=secret\n"
        "LOGFILE=/opt/zimbra/log/zmbackup.log\n"
        "ENABLE_EMAIL_NOTIFY=all\n"
        "EMAIL_NOTIFY=admin@example.com\n"
        "EMAIL_SENDER=zmbackup@example.com\n"
        "MAX_PARALLEL_PROCESS=5\n"
        "ROTATE_TIME=30\n"
        "LOCK_BACKUP=true\n"
        "SESSION_TYPE=SQLITE3\n"
        "BACKUP_INACTIVE_ACCOUNTS=false\n"
        "SSL_ENABLE=yes\n"
        "ZMMAILBOX=/opt/zimbra/bin/zmmailbox\n"
    )
    output_file = tmp_path / "zmbackup.json"

    migrator = ConfigMigrator(config_path=config_file, output_path=output_file, is_root_func=lambda: True)

    exit_code = migrator.migrate()
    assert exit_code == 0
    assert output_file.exists()


# Tests for ConfigMigrator.migrate() - Error Handling


def test_migrate_fails_if_source_not_found(tmp_path: Path) -> None:
    """
    Test migration fails if source file doesn't exist.

    :param tmp_path: Pytest temporary path fixture
    """
    nonexistent_file = tmp_path / "nonexistent.conf"

    migrator = ConfigMigrator(config_path=nonexistent_file, is_root_func=lambda: True)

    exit_code = migrator.migrate()
    assert exit_code == 1


def test_migrate_skips_if_already_json(tmp_path: Path) -> None:
    """
    Test migration skips if source is already JSON format.

    :param tmp_path: Pytest temporary path fixture
    """
    json_file = tmp_path / "zmbackup.json"
    json_file.write_text('{"version": "1.0"}')

    migrator = ConfigMigrator(config_path=json_file, is_root_func=lambda: True)

    exit_code = migrator.migrate()
    assert exit_code == 0


def test_migrate_fails_if_target_exists_without_force(tmp_path: Path) -> None:
    """
    Test migration fails if target exists and force is False.

    :param tmp_path: Pytest temporary path fixture
    """
    config_file = tmp_path / "zmbackup.conf"
    config_file.write_text("BACKUPUSER=zimbra\n")
    target_file = tmp_path / "zmbackup.json"
    target_file.write_text('{"existing": "data"}')

    migrator = ConfigMigrator(config_path=config_file, force=False, is_root_func=lambda: True)

    exit_code = migrator.migrate()
    assert exit_code == 1
    # Original file should be unchanged
    with open(target_file) as f:
        data = json.load(f)
    assert data == {"existing": "data"}


def test_migrate_overwrites_if_force_true(tmp_path: Path) -> None:
    """
    Test migration overwrites target if force is True.

    :param tmp_path: Pytest temporary path fixture
    """
    config_file = tmp_path / "zmbackup.conf"
    config_file.write_text(
        "BACKUPUSER=zimbra\n"
        "WORKDIR=/opt/zimbra/backup\n"
        "LDAPSERVER=ldap://localhost:389\n"
        "LDAPADMIN=uid=zimbra,cn=admins,cn=zimbra\n"
        "LDAPPASS=secret\n"
        "LOGFILE=/opt/zimbra/log/zmbackup.log\n"
        "ENABLE_EMAIL_NOTIFY=all\n"
        "EMAIL_NOTIFY=admin@example.com\n"
        "EMAIL_SENDER=zmbackup@example.com\n"
        "MAX_PARALLEL_PROCESS=5\n"
        "ROTATE_TIME=30\n"
        "LOCK_BACKUP=true\n"
        "SESSION_TYPE=SQLITE3\n"
        "BACKUP_INACTIVE_ACCOUNTS=false\n"
        "SSL_ENABLE=yes\n"
        "ZMMAILBOX=/opt/zimbra/bin/zmmailbox\n"
    )
    target_file = tmp_path / "zmbackup.json"
    target_file.write_text('{"old": "data"}')

    migrator = ConfigMigrator(config_path=config_file, force=True, is_root_func=lambda: True)

    exit_code = migrator.migrate()
    assert exit_code == 0

    # Check file was overwritten
    with open(target_file) as f:
        data = json.load(f)
    assert "old" not in data
    assert data["version"] == "1.0"


def test_migrate_handles_invalid_legacy_config(tmp_path: Path) -> None:
    """
    Test migration handles invalid legacy configuration.

    :param tmp_path: Pytest temporary path fixture
    """
    config_file = tmp_path / "invalid.conf"
    # Create a config that will fail validation (missing required fields)
    config_file.write_text("INVALID_KEY=value\n")

    migrator = ConfigMigrator(config_path=config_file, is_root_func=lambda: True)

    exit_code = migrator.migrate()
    assert exit_code == 1


# Tests for ConfigMigrator.migrate() - Edge Cases


def test_migrate_creates_backup(tmp_path: Path) -> None:
    """
    Test migration creates backup of original file.

    :param tmp_path: Pytest temporary path fixture
    """
    config_file = tmp_path / "zmbackup.conf"
    content = (
        "BACKUPUSER=zimbra\n"
        "WORKDIR=/opt/zimbra/backup\n"
        "LDAPSERVER=ldap://localhost:389\n"
        "LDAPADMIN=uid=zimbra,cn=admins,cn=zimbra\n"
        "LDAPPASS=secret\n"
        "LOGFILE=/opt/zimbra/log/zmbackup.log\n"
        "ENABLE_EMAIL_NOTIFY=all\n"
        "EMAIL_NOTIFY=admin@example.com\n"
        "EMAIL_SENDER=zmbackup@example.com\n"
        "MAX_PARALLEL_PROCESS=5\n"
        "ROTATE_TIME=30\n"
        "LOCK_BACKUP=true\n"
        "SESSION_TYPE=SQLITE3\n"
        "BACKUP_INACTIVE_ACCOUNTS=false\n"
        "SSL_ENABLE=yes\n"
        "ZMMAILBOX=/opt/zimbra/bin/zmmailbox\n"
    )
    config_file.write_text(content)

    migrator = ConfigMigrator(config_path=config_file, is_root_func=lambda: True)

    exit_code = migrator.migrate()
    assert exit_code == 0

    # Check backup was created
    backup_file = Path(str(config_file) + ".bak")
    assert backup_file.exists()
    assert backup_file.read_text() == content


def test_migrate_with_custom_backup_suffix(tmp_path: Path) -> None:
    """
    Test migration with custom backup suffix.

    :param tmp_path: Pytest temporary path fixture
    """
    config_file = tmp_path / "zmbackup.conf"
    config_file.write_text(
        "BACKUPUSER=zimbra\n"
        "WORKDIR=/opt/zimbra/backup\n"
        "LDAPSERVER=ldap://localhost:389\n"
        "LDAPADMIN=uid=zimbra,cn=admins,cn=zimbra\n"
        "LDAPPASS=secret\n"
        "LOGFILE=/opt/zimbra/log/zmbackup.log\n"
        "ENABLE_EMAIL_NOTIFY=all\n"
        "EMAIL_NOTIFY=admin@example.com\n"
        "EMAIL_SENDER=zmbackup@example.com\n"
        "MAX_PARALLEL_PROCESS=5\n"
        "ROTATE_TIME=30\n"
        "LOCK_BACKUP=true\n"
        "SESSION_TYPE=SQLITE3\n"
        "BACKUP_INACTIVE_ACCOUNTS=false\n"
        "SSL_ENABLE=yes\n"
        "ZMMAILBOX=/opt/zimbra/bin/zmmailbox\n"
    )
    custom_suffix = ".backup"

    migrator = ConfigMigrator(config_path=config_file, backup_suffix=custom_suffix, is_root_func=lambda: True)

    exit_code = migrator.migrate()
    assert exit_code == 0

    backup_file = Path(str(config_file) + custom_suffix)
    assert backup_file.exists()


def test_migrate_dry_run_does_not_write_files(tmp_path: Path) -> None:
    """
    Test dry run mode doesn't write any files.

    :param tmp_path: Pytest temporary path fixture
    """
    config_file = tmp_path / "zmbackup.conf"
    config_file.write_text(
        "BACKUPUSER=zimbra\n"
        "WORKDIR=/opt/zimbra/backup\n"
        "LDAPSERVER=ldap://localhost:389\n"
        "LDAPADMIN=uid=zimbra,cn=admins,cn=zimbra\n"
        "LDAPPASS=secret\n"
        "LOGFILE=/opt/zimbra/log/zmbackup.log\n"
        "ENABLE_EMAIL_NOTIFY=all\n"
        "EMAIL_NOTIFY=admin@example.com\n"
        "EMAIL_SENDER=zmbackup@example.com\n"
        "MAX_PARALLEL_PROCESS=5\n"
        "ROTATE_TIME=30\n"
        "LOCK_BACKUP=true\n"
        "SESSION_TYPE=SQLITE3\n"
        "BACKUP_INACTIVE_ACCOUNTS=false\n"
        "SSL_ENABLE=yes\n"
        "ZMMAILBOX=/opt/zimbra/bin/zmmailbox\n"
    )
    output_file = tmp_path / "zmbackup.json"

    migrator = ConfigMigrator(config_path=config_file, dry_run=True, is_root_func=lambda: True)

    exit_code = migrator.migrate()
    assert exit_code == 0

    # No files should be created
    assert not output_file.exists()
    backup_file = Path(str(config_file) + ".bak")
    assert not backup_file.exists()


def test_migrate_end_to_end(tmp_path: Path) -> None:
    """
    Test complete end-to-end migration flow.

    :param tmp_path: Pytest temporary path fixture
    """
    config_file = tmp_path / "zmbackup.conf"
    config_file.write_text(
        "BACKUPUSER=zimbra\n"
        "WORKDIR=/opt/zimbra/backup\n"
        "LDAPSERVER=ldap://localhost:389\n"
        "LDAPADMIN=uid=zimbra,cn=admins,cn=zimbra\n"
        "LDAPPASS=secret\n"
        "LOGFILE=/opt/zimbra/log/zmbackup.log\n"
        "ENABLE_EMAIL_NOTIFY=all\n"
        "EMAIL_NOTIFY=admin@example.com\n"
        "EMAIL_SENDER=zmbackup@example.com\n"
        "MAX_PARALLEL_PROCESS=5\n"
        "ROTATE_TIME=30\n"
        "LOCK_BACKUP=true\n"
        "SESSION_TYPE=SQLITE3\n"
        "BACKUP_INACTIVE_ACCOUNTS=false\n"
        "SSL_ENABLE=yes\n"
        "ZMMAILBOX=/opt/zimbra/bin/zmmailbox\n"
    )

    migrator = ConfigMigrator(config_path=config_file, is_root_func=lambda: True)

    exit_code = migrator.migrate()
    assert exit_code == 0

    # Check all expected files exist
    json_file = tmp_path / "zmbackup.json"
    backup_file = Path(str(config_file) + ".bak")

    assert json_file.exists()
    assert backup_file.exists()

    # Verify JSON content is valid
    with open(json_file) as f:
        config_data = json.load(f)

    assert config_data["version"] == "1.0"
    assert config_data["zimbra"]["backup_user"] == "zimbra"
    assert config_data["zimbra"]["ldap_server"] == "ldap://localhost:389"
    assert config_data["email"]["notify_address"] == "admin@example.com"
    assert config_data["backup"]["max_parallel_process"] == 5
    assert config_data["backup"]["lock_backup"] is True


def test_migrate_with_real_legacy_test_file(config_test_file, tmp_path: Path) -> None:
    """
    Test migration using the real legacy_config.conf test file.

    :param config_test_file: Config test file factory fixture
    :param tmp_path: Pytest temporary path fixture
    """
    # Get the real legacy config file
    legacy_config = config_test_file("legacy_config.conf")
    output_file = tmp_path / "zmbackup.json"

    migrator = ConfigMigrator(config_path=legacy_config, output_path=output_file, is_root_func=lambda: True)

    exit_code = migrator.migrate()
    assert exit_code == 0

    # Verify the output
    assert output_file.exists()
    with open(output_file) as f:
        config_data = json.load(f)

    assert config_data["version"] == "1.0"
    assert config_data["zimbra"]["backup_user"] == "zimbra"
    assert config_data["zimbra"]["ldap_server"] == "ldap://localhost:389"
    assert config_data["backup"]["max_parallel_process"] == 5
    assert config_data["backup"]["backup_inactive_accounts"] is False
    assert config_data["backup"]["ssl_enable"] is True


# Tests for migrate_config() CLI function


def test_migrate_config_cli_success(tmp_path: Path) -> None:
    """
    Test migrate_config CLI function with successful migration.

    :param tmp_path: Pytest temporary path fixture
    """
    config_file = tmp_path / "zmbackup.conf"
    config_file.write_text(
        "BACKUPUSER=zimbra\n"
        "WORKDIR=/opt/zimbra/backup\n"
        "LDAPSERVER=ldap://localhost:389\n"
        "LDAPADMIN=uid=zimbra,cn=admins,cn=zimbra\n"
        "LDAPPASS=secret\n"
        "LOGFILE=/opt/zimbra/log/zmbackup.log\n"
        "ENABLE_EMAIL_NOTIFY=all\n"
        "EMAIL_NOTIFY=admin@example.com\n"
        "EMAIL_SENDER=zmbackup@example.com\n"
        "MAX_PARALLEL_PROCESS=5\n"
        "ROTATE_TIME=30\n"
        "LOCK_BACKUP=true\n"
        "SESSION_TYPE=SQLITE3\n"
        "BACKUP_INACTIVE_ACCOUNTS=false\n"
        "SSL_ENABLE=yes\n"
        "ZMMAILBOX=/opt/zimbra/bin/zmmailbox\n"
    )

    # Should not raise
    migrate_config(config_path=str(config_file), output_path=None, backup_suffix=".bak", force=False, dry_run=False)

    json_file = tmp_path / "zmbackup.json"
    assert json_file.exists()


def test_migrate_config_cli_raises_on_failure(tmp_path: Path) -> None:
    """
    Test migrate_config CLI function raises on failure.

    :param tmp_path: Pytest temporary path fixture
    """
    nonexistent_file = tmp_path / "nonexistent.conf"

    with pytest.raises(click.Abort):
        migrate_config(config_path=str(nonexistent_file))


def test_migrate_config_cli_with_all_options(tmp_path: Path) -> None:
    """
    Test migrate_config CLI function with all options specified.

    :param tmp_path: Pytest temporary path fixture
    """
    config_file = tmp_path / "zmbackup.conf"
    config_file.write_text(
        "BACKUPUSER=zimbra\n"
        "WORKDIR=/opt/zimbra/backup\n"
        "LDAPSERVER=ldap://localhost:389\n"
        "LDAPADMIN=uid=zimbra,cn=admins,cn=zimbra\n"
        "LDAPPASS=secret\n"
        "LOGFILE=/opt/zimbra/log/zmbackup.log\n"
        "ENABLE_EMAIL_NOTIFY=all\n"
        "EMAIL_NOTIFY=admin@example.com\n"
        "EMAIL_SENDER=zmbackup@example.com\n"
        "MAX_PARALLEL_PROCESS=5\n"
        "ROTATE_TIME=30\n"
        "LOCK_BACKUP=true\n"
        "SESSION_TYPE=SQLITE3\n"
        "BACKUP_INACTIVE_ACCOUNTS=false\n"
        "SSL_ENABLE=yes\n"
        "ZMMAILBOX=/opt/zimbra/bin/zmmailbox\n"
    )
    custom_output = tmp_path / "custom_output.json"
    custom_suffix = ".backup"

    migrate_config(
        config_path=str(config_file),
        output_path=str(custom_output),
        backup_suffix=custom_suffix,
        force=True,
        dry_run=False,
    )

    assert custom_output.exists()


# Tests for exception handling coverage


def test_migrate_handles_unexpected_exception_during_backup(tmp_path: Path, monkeypatch) -> None:
    """
    Test migration handles unexpected exceptions during backup creation.

    :param tmp_path: Pytest temporary path fixture
    :param monkeypatch: Pytest monkeypatch fixture
    """
    config_file = tmp_path / "zmbackup.conf"
    config_file.write_text(
        "BACKUPUSER=zimbra\n"
        "WORKDIR=/opt/zimbra/backup\n"
        "LDAPSERVER=ldap://localhost:389\n"
        "LDAPADMIN=uid=zimbra,cn=admins,cn=zimbra\n"
        "LDAPPASS=secret\n"
        "LOGFILE=/opt/zimbra/log/zmbackup.log\n"
        "ENABLE_EMAIL_NOTIFY=all\n"
        "EMAIL_NOTIFY=admin@example.com\n"
        "EMAIL_SENDER=zmbackup@example.com\n"
        "MAX_PARALLEL_PROCESS=5\n"
        "ROTATE_TIME=30\n"
        "LOCK_BACKUP=true\n"
        "SESSION_TYPE=SQLITE3\n"
        "BACKUP_INACTIVE_ACCOUNTS=false\n"
        "SSL_ENABLE=yes\n"
        "ZMMAILBOX=/opt/zimbra/bin/zmmailbox\n"
    )

    # Monkey patch shutil.copy2 to raise a generic exception
    def mock_copy2(*args, **kwargs):
        raise OSError("Simulated disk error")

    monkeypatch.setattr("shutil.copy2", mock_copy2)

    migrator = ConfigMigrator(config_path=config_file, is_root_func=lambda: True)

    exit_code = migrator.migrate()
    assert exit_code == 1


def test_atomic_write_json_handles_rename_failure(tmp_path: Path, monkeypatch) -> None:
    """
    Test atomic write handles rename failure and cleans up temp file.

    :param tmp_path: Pytest temporary path fixture
    :param monkeypatch: Pytest monkeypatch fixture
    """
    config_file = tmp_path / "source.conf"
    config_file.write_text("BACKUPUSER=zimbra\n")
    output_file = tmp_path / "output.json"

    migrator = ConfigMigrator(config_path=config_file, output_path=output_file, is_root_func=lambda: True)

    # Track temp files created
    original_mkstemp = __import__("tempfile").mkstemp
    created_temp_files = []

    def tracking_mkstemp(*args, **kwargs):
        fd, name = original_mkstemp(*args, **kwargs)
        created_temp_files.append(name)
        return fd, name

    # Monkey patch os.rename to raise exception
    def mock_rename(*args, **kwargs):
        raise OSError("Simulated rename failure")

    monkeypatch.setattr("tempfile.mkstemp", tracking_mkstemp)
    monkeypatch.setattr("os.rename", mock_rename)

    test_config = {"version": "1.0", "test": "data"}

    # Should raise OSError
    with pytest.raises(OSError):
        migrator._atomic_write_json(test_config)

    # Verify temp file was cleaned up
    for temp_file in created_temp_files:
        assert not Path(temp_file).exists()
