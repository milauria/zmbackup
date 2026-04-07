import os
import warnings
from pathlib import Path
from typing import Any, Dict, Generator, Optional

import pytest

from src.enums import EmailNotifyLevel, SessionType
from src.exceptions import (
    ConfigurationFileNotFoundError,
    ConfigurationParseError,
    ConfigurationValidationError,
)
from src.lib import config as config_module
from src.lib.config import ZmbackupConfig, get_config


@pytest.fixture
def reset_config_singleton() -> Generator[None, None, None]:
    """Reset the configuration singleton before and after tests."""
    config_module._config_instance = None
    yield
    config_module._config_instance = None


@pytest.fixture
def valid_config_dict() -> Dict[str, str]:
    """
    Provides a dictionary with valid configuration values.

    :return: Dictionary of valid configuration parameters
    """
    return {
        "BACKUPUSER": "zimbra",
        "WORKDIR": "/opt/zimbra/backup",
        "LDAPSERVER": "ldap://localhost:389",
        "LDAPADMIN": "uid=admin,cn=admins,cn=zimbra",
        "LDAPPASS": "secret",
        "LOGFILE": "/var/log/zmbackup.log",
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


@pytest.fixture
def create_config_file(tmp_path: Path):
    """
    Factory fixture to create a configuration file.

    :param tmp_path: Temporary directory path
    :return: Function that creates a config file
    """

    def _create(content_dict: Dict[str, str]) -> Path:
        config_file = tmp_path / "zmbackup.conf"
        with open(config_file, "w") as f:
            for key, value in content_dict.items():
                f.write(f"{key}={value}\n")
        return config_file

    return _create


def test_email_notify_level_enum() -> None:
    """Test EmailNotifyLevel enum values."""
    assert EmailNotifyLevel.ALL.value == "all"
    assert EmailNotifyLevel.START.value == "start"
    assert EmailNotifyLevel.FINISH.value == "finish"
    assert EmailNotifyLevel.ERROR.value == "error"
    assert EmailNotifyLevel.NONE.value == "none"


def test_session_type_enum() -> None:
    """Test SessionType enum values."""
    assert SessionType.TXT.value == "TXT"
    assert SessionType.SQLITE3.value == "SQLITE3"


def test_load_valid_config(config_test_file) -> None:
    """
    Test loading a valid configuration file.

    :param config_test_file: Factory fixture to get test config file paths
    """
    config_path = config_test_file("legacy_config.conf")
    config = ZmbackupConfig.load(config_path)

    assert config.backup_user == "zimbra"
    assert config.workdir == Path("/opt/zimbra/backup")
    assert config.ldap_server == "ldap://localhost:389"
    assert config.enable_email_notify == EmailNotifyLevel.ALL
    assert config.max_parallel_process == 5
    assert config.lock_backup is True
    assert config.session_type == SessionType.SQLITE3
    assert config.backup_inactive_accounts is False
    assert config.ssl_enable is True


def test_load_config_with_comments_and_whitespace(tmp_path: Path) -> None:
    """
    Test loading config with comments, empty lines, and extra whitespace.

    :param tmp_path: Temporary directory path
    """
    config_file = tmp_path / "zmbackup_extra.conf"
    content = """
    # This is a comment
    BACKUPUSER = zimbra
    
    WORKDIR=/opt/zimbra/backup # inline comment not supported by current parser
    LDAPSERVER =  ldap://localhost:389  
    
    LDAPADMIN=uid=admin,cn=admins,cn=zimbra
    LDAPPASS=secret
    LOGFILE=/var/log/zmbackup.log
    ENABLE_EMAIL_NOTIFY=all
    EMAIL_NOTIFY=admin@example.com
    EMAIL_SENDER=zmbackup@example.com
    MAX_PARALLEL_PROCESS=5
    ROTATE_TIME=30
    LOCK_BACKUP=true
    SESSION_TYPE=SQLITE3
    BACKUP_INACTIVE_ACCOUNTS=false
    SSL_ENABLE=yes
    ZMMAILBOX=/opt/zimbra/bin/zmmailbox
    """
    config_file.write_text(content)
    config = ZmbackupConfig.load(config_file)
    assert config.backup_user == "zimbra"
    assert config.ldap_server == "ldap://localhost:389"


def test_load_config_missing_file() -> None:
    """Test ConfigurationFileNotFoundError when file does not exist."""
    with pytest.raises(ConfigurationFileNotFoundError):
        ZmbackupConfig.load("/non/existent/path/zmbackup.conf")


def test_load_config_malformed_line(tmp_path: Path) -> None:
    """
    Test ConfigurationParseError for malformed lines.

    :param tmp_path: Temporary directory path
    """
    config_file = tmp_path / "malformed.conf"
    config_file.write_text("INVALID_LINE_WITHOUT_EQUALS")
    with pytest.raises(ConfigurationParseError, match="line format at"):
        ZmbackupConfig.load(config_file)


def test_load_config_missing_required_field(create_config_file, valid_config_dict: Dict[str, str]) -> None:
    """
    Test ConfigurationValidationError when a required field is missing.

    :param create_config_file: Factory fixture to create config file
    :param valid_config_dict: Dictionary with valid config values
    """
    del valid_config_dict["LDAPPASS"]
    config_path = create_config_file(valid_config_dict)
    with pytest.raises(ConfigurationValidationError, match="Missing required configuration key: LDAPPASS"):
        ZmbackupConfig.load(config_path)


def test_load_config_jinja2_template_variables(config_test_file) -> None:
    """
    Test that Jinja2 template variables are treated as empty.

    :param config_test_file: Factory fixture to get test config file paths
    """
    config_path = config_test_file("legacy_config_with_jinja2.conf")
    with pytest.raises(ConfigurationValidationError, match="Missing required configuration key: LDAPPASS"):
        ZmbackupConfig.load(config_path)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("true", True),
        ("TRUE", True),
        ("yes", True),
        ("YES", True),
        ("on", None),  # Should raise error
        ("1", True),
        ("false", False),
        ("no", False),
        ("0", False),
    ],
)
def test_convert_to_bool_valid(value: str, expected: Optional[bool]) -> None:
    """
    Test valid boolean conversions.

    :param value: String to convert
    :param expected: Expected boolean result
    """
    if expected is None:
        with pytest.raises(ConfigurationParseError):
            ZmbackupConfig._convert_to_bool(value, "test_field")
    else:
        assert ZmbackupConfig._convert_to_bool(value, "test_field") == expected


def test_convert_to_bool_invalid() -> None:
    """Test invalid boolean conversion."""
    with pytest.raises(ConfigurationParseError, match="boolean value for"):
        ZmbackupConfig._convert_to_bool("maybe", "test_field")


@pytest.mark.parametrize(
    "value,enum_class,expected",
    [
        ("all", EmailNotifyLevel, EmailNotifyLevel.ALL),
        ("ALL", EmailNotifyLevel, EmailNotifyLevel.ALL),
        ("start", EmailNotifyLevel, EmailNotifyLevel.START),
        ("START", EmailNotifyLevel, EmailNotifyLevel.START),
        ("SQLITE3", SessionType, SessionType.SQLITE3),
        ("sqlite3", SessionType, SessionType.SQLITE3),
        ("TXT", SessionType, SessionType.TXT),
    ],
)
def test_convert_to_enum_valid(value: str, enum_class: Any, expected: Any) -> None:
    """
    Test valid enum conversions.

    :param value: String to convert
    :param enum_class: Enum class to convert to
    :param expected: Expected enum instance
    """
    assert ZmbackupConfig._convert_to_enum(value, enum_class, "test_field") == expected


def test_convert_to_enum_invalid() -> None:
    """Test invalid enum conversion."""
    with pytest.raises(ConfigurationValidationError, match="value for test_field"):
        ZmbackupConfig._convert_to_enum("invalid_val", EmailNotifyLevel, "test_field")


def test_validate_email_valid() -> None:
    """Test valid email validation."""
    ZmbackupConfig.validate_email("test@example.com", "TEST_EMAIL")
    ZmbackupConfig.validate_email("user.name+tag@sub.domain.co.uk", "TEST_EMAIL")


def test_validate_email_invalid() -> None:
    """Test invalid email validation."""
    with pytest.raises(ConfigurationValidationError, match="email format for"):
        ZmbackupConfig.validate_email("not-an-email", "TEST_EMAIL")


@pytest.mark.parametrize(
    "url", ["ldap://localhost", "ldaps://192.168.1.10", "ldap://ldap.example.com:389", "ldaps://secure.example.com:636"]
)
def test_validate_ldap_url_valid(url: str) -> None:
    """
    Test valid LDAP URL validation.

    :param url: URL to validate
    """
    ZmbackupConfig.validate_ldap_url(url, "LDAPSERVER")


@pytest.mark.parametrize("url", ["http://localhost", "ldap:/localhost", "ldap://invalid_chars_^", "not-a-url"])
def test_validate_ldap_url_invalid(url: str) -> None:
    """
    Test invalid LDAP URL validation.

    :param url: URL to validate
    """
    with pytest.raises(ConfigurationValidationError, match="LDAP URL for"):
        ZmbackupConfig.validate_ldap_url(url, "LDAPSERVER")


def test_validate_parallel_process_range(config_test_file) -> None:
    """
    Test MAX_PARALLEL_PROCESS range validation.

    :param config_test_file: Factory fixture to get test config file paths
    """
    config_path = config_test_file("out_of_range_parallel.json")
    with pytest.raises(ConfigurationValidationError, match="MAX_PARALLEL_PROCESS must be between 1 and 20"):
        ZmbackupConfig.load(config_path)


def test_validate_rotate_time_range(config_test_file) -> None:
    """
    Test ROTATE_TIME range validation.

    :param config_test_file: Factory fixture to get test config file paths
    """
    config_path = config_test_file("out_of_range_rotate.json")
    with pytest.raises(ConfigurationValidationError, match="ROTATE_TIME must be between 1 and 3650"):
        ZmbackupConfig.load(config_path)


def test_derived_properties(create_config_file, valid_config_dict: Dict[str, str]) -> None:
    """
    Test database_path and session_file_path properties.

    :param create_config_file: Factory fixture to create config file
    :param valid_config_dict: Dictionary with valid config values
    """
    valid_config_dict["WORKDIR"] = "/tmp/zmbackup"
    config_path = create_config_file(valid_config_dict)
    config = ZmbackupConfig.load(config_path)

    assert config.database_path == "sqlite:////tmp/zmbackup/zmbackup_sessions.db"
    assert config.session_file_path == Path("/tmp/zmbackup/sessions.txt")


def test_get_config_singleton(reset_config_singleton, config_test_file) -> None:
    """
    Test that get_config returns the same instance.

    :param reset_config_singleton: Fixture to reset singleton
    :param config_test_file: Factory fixture to get test config file paths
    """
    config_path = config_test_file("legacy_config.conf")

    config1 = get_config(config_path)
    config2 = get_config()

    assert config1 is config2


def test_get_config_reload(reset_config_singleton, config_test_file) -> None:
    """
    Test that get_config with reload=True returns a new instance.

    :param reset_config_singleton: Fixture to reset singleton
    :param config_test_file: Factory fixture to get test config file paths
    """
    config_path = config_test_file("legacy_config.conf")

    config1 = get_config(config_path)
    config2 = get_config(config_path, reload=True)

    assert config1 is not config2


def test_get_config_different_paths(
    reset_config_singleton, create_config_file, valid_config_dict: Dict[str, str], tmp_path: Path
) -> None:
    """
    Test that get_config with different paths returns different instances.

    :param reset_config_singleton: Fixture to reset singleton
    :param create_config_file: Factory fixture to create config file
    :param valid_config_dict: Dictionary with valid config values
    :param tmp_path: Temporary directory path
    """
    config_path1 = create_config_file(valid_config_dict)

    valid_config_dict["BACKUPUSER"] = "other"
    config_file2 = tmp_path / "zmbackup2.conf"
    with open(config_file2, "w") as f:
        for key, value in valid_config_dict.items():
            f.write(f"{key}={value}\n")

    config1 = get_config(config_path1)
    config2 = get_config(config_file2, reload=True)

    assert config1 is not config2
    assert config1.backup_user == "zimbra"
    assert config2.backup_user == "other"


# ============================================================================
# JSON Format Tests
# ============================================================================


def test_load_valid_json_config(config_test_file) -> None:
    """
    Test loading a valid JSON configuration file.

    :param config_test_file: Fixture to get test config file paths
    """
    config_path = config_test_file("valid_config.json")
    config = ZmbackupConfig.load(config_path)

    assert config.backup_user == "zimbra"
    assert config.workdir == Path("/opt/zimbra/backup")
    assert config.ldap_server == "ldap://localhost:389"
    assert config.ldap_admin == "uid=zimbra,cn=admins,cn=zimbra"
    assert config.ldap_password == "secret"
    assert config.log_file == Path("/opt/zimbra/log/zmbackup.log")
    assert config.enable_email_notify == EmailNotifyLevel.ALL
    assert config.email_notify == "admin@example.com"
    assert config.email_sender == "zmbackup@example.com"
    assert config.max_parallel_process == 5
    assert config.rotate_time == 30
    assert config.lock_backup is True
    assert config.session_type == SessionType.SQLITE3
    assert config.backup_inactive_accounts is False
    assert config.ssl_enable is True
    assert config.zmmailbox == Path("/opt/zimbra/bin/zmmailbox")


def test_load_valid_json_config_txt_session(config_test_file) -> None:
    """
    Test loading JSON config with TXT session type and different values.

    :param config_test_file: Fixture to get test config file paths
    """
    config_path = config_test_file("valid_config_txt_session.json")
    config = ZmbackupConfig.load(config_path)

    assert config.ldap_server == "ldaps://secure.example.com:636"
    assert config.session_type == SessionType.TXT
    assert config.enable_email_notify == EmailNotifyLevel.ERROR
    assert config.max_parallel_process == 10
    assert config.rotate_time == 60
    assert config.lock_backup is False
    assert config.backup_inactive_accounts is True
    assert config.ssl_enable is False


def test_load_invalid_json_format(config_test_file) -> None:
    """
    Test ConfigurationParseError for invalid JSON syntax.

    :param config_test_file: Fixture to get test config file paths
    """
    config_path = config_test_file("invalid_json.json")
    with pytest.raises(ConfigurationParseError, match="Invalid JSON format"):
        ZmbackupConfig.load(config_path)


def test_load_unsupported_version(config_test_file) -> None:
    """
    Test ConfigurationParseError for unsupported schema version.

    :param config_test_file: Fixture to get test config file paths
    """
    config_path = config_test_file("unsupported_version.json")
    with pytest.raises(ConfigurationParseError, match="Unsupported configuration version"):
        ZmbackupConfig.load(config_path)


def test_load_missing_version(config_test_file) -> None:
    """
    Test ConfigurationParseError when version field is missing.

    :param config_test_file: Fixture to get test config file paths
    """
    config_path = config_test_file("missing_version.json")
    with pytest.raises(ConfigurationParseError, match="Unsupported configuration version"):
        ZmbackupConfig.load(config_path)


# ============================================================================
# Format Detection Tests
# ============================================================================


def test_is_json_format_json_file(config_test_file) -> None:
    """
    Test JSON format detection for JSON files.

    :param config_test_file: Fixture to get test config file paths
    """
    json_path = config_test_file("valid_config.json")
    assert ZmbackupConfig._is_json_format(json_path) is True


def test_is_json_format_legacy_file(config_test_file) -> None:
    """
    Test JSON format detection for legacy KEY=VALUE files.

    :param config_test_file: Fixture to get test config file paths
    """
    legacy_path = config_test_file("legacy_config.conf")
    assert ZmbackupConfig._is_json_format(legacy_path) is False


def test_is_json_format_exception_handling(tmp_path: Path) -> None:
    """
    Test JSON format detection handles file read errors gracefully.

    :param tmp_path: Temporary directory path
    """
    nonexistent_file = tmp_path / "nonexistent.json"
    # Should return False instead of raising exception
    assert ZmbackupConfig._is_json_format(nonexistent_file) is False


# ============================================================================
# Property Access Tests
# ============================================================================


def test_json_property_types(config_test_file) -> None:
    """
    Test that all properties return correct types when loaded from JSON.

    :param config_test_file: Fixture to get test config file paths
    """
    config_path = config_test_file("valid_config.json")
    config = ZmbackupConfig.load(config_path)

    # String properties
    assert isinstance(config.backup_user, str)
    assert isinstance(config.ldap_server, str)
    assert isinstance(config.ldap_admin, str)
    assert isinstance(config.ldap_password, str)
    assert isinstance(config.email_notify, str)
    assert isinstance(config.email_sender, str)

    # Path properties
    assert isinstance(config.workdir, Path)
    assert isinstance(config.log_file, Path)
    assert isinstance(config.zmmailbox, Path)

    # Integer properties
    assert isinstance(config.max_parallel_process, int)
    assert isinstance(config.rotate_time, int)

    # Boolean properties
    assert isinstance(config.lock_backup, bool)
    assert isinstance(config.backup_inactive_accounts, bool)
    assert isinstance(config.ssl_enable, bool)

    # Enum properties
    assert isinstance(config.enable_email_notify, EmailNotifyLevel)
    assert isinstance(config.session_type, SessionType)


def test_json_derived_properties(config_test_file) -> None:
    """
    Test derived properties work correctly with JSON config.

    :param config_test_file: Fixture to get test config file paths
    """
    config_path = config_test_file("valid_config.json")
    config = ZmbackupConfig.load(config_path)

    assert config.database_path == "sqlite:////opt/zimbra/backup/zmbackup_sessions.db"
    assert config.session_file_path == Path("/opt/zimbra/backup/sessions.txt")


# ============================================================================
# Deprecation Warning Tests
# ============================================================================


def test_legacy_format_deprecation_warning(config_test_file) -> None:
    """
    Test that loading legacy format issues DeprecationWarning.

    :param config_test_file: Fixture to get test config file paths
    """
    legacy_path = config_test_file("legacy_config.conf")

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        config = ZmbackupConfig.load(legacy_path)

        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "KEY=VALUE format is deprecated" in str(w[0].message)
        assert "zmbackup migrate-config" in str(w[0].message)

    # Verify config loaded correctly despite warning
    assert config.backup_user == "zimbra"


def test_json_format_no_deprecation_warning(config_test_file) -> None:
    """
    Test that loading JSON format does not issue deprecation warning.

    :param config_test_file: Fixture to get test config file paths
    """
    json_path = config_test_file("valid_config.json")

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        config = ZmbackupConfig.load(json_path)

        # Filter for DeprecationWarnings only
        deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
        assert len(deprecation_warnings) == 0

    assert config.backup_user == "zimbra"


# ============================================================================
# Validation Tests with JSON Format
# ============================================================================


def test_json_invalid_email_validation(config_test_file) -> None:
    """
    Test email validation works with JSON format.

    :param config_test_file: Fixture to get test config file paths
    """
    config_path = config_test_file("invalid_email.json")
    with pytest.raises(ConfigurationValidationError, match="email format"):
        ZmbackupConfig.load(config_path)


def test_json_invalid_ldap_url_validation(config_test_file) -> None:
    """
    Test LDAP URL validation works with JSON format.

    :param config_test_file: Fixture to get test config file paths
    """
    config_path = config_test_file("invalid_ldap_url.json")
    with pytest.raises(ConfigurationValidationError, match="LDAP URL"):
        ZmbackupConfig.load(config_path)


def test_json_out_of_range_parallel_process(config_test_file) -> None:
    """
    Test MAX_PARALLEL_PROCESS range validation with JSON format.

    :param config_test_file: Fixture to get test config file paths
    """
    config_path = config_test_file("out_of_range_parallel.json")
    with pytest.raises(ConfigurationValidationError, match="MAX_PARALLEL_PROCESS must be between 1 and 20"):
        ZmbackupConfig.load(config_path)


def test_json_out_of_range_rotate_time(config_test_file) -> None:
    """
    Test ROTATE_TIME range validation with JSON format.

    :param config_test_file: Fixture to get test config file paths
    """
    config_path = config_test_file("out_of_range_rotate.json")
    with pytest.raises(ConfigurationValidationError, match="ROTATE_TIME must be between 1 and 3650"):
        ZmbackupConfig.load(config_path)


def test_json_invalid_enum_email_notify(config_test_file) -> None:
    """
    Test email notify level enum validation with JSON format.

    :param config_test_file: Fixture to get test config file paths
    """
    config_path = config_test_file("invalid_enum_email_notify.json")
    with pytest.raises(ConfigurationValidationError, match="value for email.enable_notify"):
        ZmbackupConfig.load(config_path)


def test_json_invalid_enum_session_type(config_test_file) -> None:
    """
    Test session type enum validation with JSON format.

    :param config_test_file: Fixture to get test config file paths
    """
    config_path = config_test_file("invalid_enum_session_type.json")
    with pytest.raises(ConfigurationValidationError, match="value for session.type"):
        ZmbackupConfig.load(config_path)


# ============================================================================
# Backward Compatibility Tests
# ============================================================================


def test_legacy_format_loads_correctly(config_test_file) -> None:
    """
    Test that legacy KEY=VALUE format still loads correctly.

    :param config_test_file: Fixture to get test config file paths
    """
    legacy_path = config_test_file("legacy_config.conf")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        config = ZmbackupConfig.load(legacy_path)

    assert config.backup_user == "zimbra"
    assert config.workdir == Path("/opt/zimbra/backup")
    assert config.ldap_server == "ldap://localhost:389"
    assert config.max_parallel_process == 5
    assert config.session_type == SessionType.SQLITE3


def test_legacy_to_json_conversion_equivalence(config_test_file) -> None:
    """
    Test that legacy and JSON formats produce equivalent configs.

    :param config_test_file: Fixture to get test config file paths
    """
    legacy_path = config_test_file("legacy_config.conf")
    json_path = config_test_file("valid_config.json")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        legacy_config = ZmbackupConfig.load(legacy_path)

    json_config = ZmbackupConfig.load(json_path)

    # Compare all properties
    assert legacy_config.backup_user == json_config.backup_user
    assert legacy_config.workdir == json_config.workdir
    assert legacy_config.ldap_server == json_config.ldap_server
    assert legacy_config.ldap_admin == json_config.ldap_admin
    assert legacy_config.ldap_password == json_config.ldap_password
    assert legacy_config.log_file == json_config.log_file
    assert legacy_config.enable_email_notify == json_config.enable_email_notify
    assert legacy_config.email_notify == json_config.email_notify
    assert legacy_config.email_sender == json_config.email_sender
    assert legacy_config.max_parallel_process == json_config.max_parallel_process
    assert legacy_config.rotate_time == json_config.rotate_time
    assert legacy_config.lock_backup == json_config.lock_backup
    assert legacy_config.session_type == json_config.session_type
    assert legacy_config.backup_inactive_accounts == json_config.backup_inactive_accounts
    assert legacy_config.ssl_enable == json_config.ssl_enable
    assert legacy_config.zmmailbox == json_config.zmmailbox


def test_legacy_jinja2_variables_treated_as_empty(config_test_file) -> None:
    """
    Test that Jinja2 template variables in legacy format are treated as empty.

    :param config_test_file: Fixture to get test config file paths
    """
    legacy_jinja2_path = config_test_file("legacy_config_with_jinja2.conf")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        with pytest.raises(ConfigurationValidationError, match="Missing required configuration key: LDAPPASS"):
            ZmbackupConfig.load(legacy_jinja2_path)


# ============================================================================
# Edge Case Tests for 100% Coverage
# ============================================================================


def test_enum_properties_with_enum_values(tmp_path: Path) -> None:
    """
    Test enum properties when values are already enum instances (not strings).

    This covers the isinstance checks in enable_email_notify and session_type properties.

    :param tmp_path: Temporary directory path
    """
    import json

    # Create config with enum instances directly in the dict
    config_dict = {
        "version": "1.0",
        "zimbra": {
            "backup_user": "zimbra",
            "workdir": "/opt/zimbra/backup",
            "ldap_server": "ldap://localhost:389",
            "ldap_admin": "uid=zimbra,cn=admins,cn=zimbra",
            "ldap_password": "secret",
        },
        "logging": {"log_file": "/opt/zimbra/log/zmbackup.log"},
        "email": {
            "enable_notify": EmailNotifyLevel.ERROR,  # Already an enum
            "notify_address": "admin@example.com",
            "sender_address": "zmbackup@example.com",
        },
        "backup": {
            "max_parallel_process": 5,
            "rotate_time": 30,
            "lock_backup": True,
            "backup_inactive_accounts": False,
            "ssl_enable": True,
        },
        "session": {"type": SessionType.TXT},  # Already an enum
        "binaries": {"zmmailbox": "/opt/zimbra/bin/zmmailbox"},
    }

    # Need to create instance directly since JSON can't serialize enums
    config = ZmbackupConfig(_config=config_dict, _config_path=tmp_path / "test.json")

    # Access properties to trigger isinstance checks
    assert config.enable_email_notify == EmailNotifyLevel.ERROR
    assert config.session_type == SessionType.TXT
