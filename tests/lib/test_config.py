import os
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


def test_load_valid_config(create_config_file, valid_config_dict: Dict[str, str]) -> None:
    """
    Test loading a valid configuration file.

    :param create_config_file: Factory fixture to create config file
    :param valid_config_dict: Dictionary with valid config values
    """
    config_path = create_config_file(valid_config_dict)
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


def test_load_config_jinja2_template_variables(create_config_file, valid_config_dict: Dict[str, str]) -> None:
    """
    Test that Jinja2 template variables are treated as empty.

    :param create_config_file: Factory fixture to create config file
    :param valid_config_dict: Dictionary with valid config values
    """
    valid_config_dict["LDAPPASS"] = "{{ zimbra_ldap_password }}"
    config_path = create_config_file(valid_config_dict)
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


def test_validate_parallel_process_range(create_config_file, valid_config_dict: Dict[str, str]) -> None:
    """
    Test MAX_PARALLEL_PROCESS range validation.

    :param create_config_file: Factory fixture to create config file
    :param valid_config_dict: Dictionary with valid config values
    """
    valid_config_dict["MAX_PARALLEL_PROCESS"] = "0"
    config_path = create_config_file(valid_config_dict)
    with pytest.raises(ConfigurationValidationError, match="MAX_PARALLEL_PROCESS must be between 1 and 20"):
        ZmbackupConfig.load(config_path)

    valid_config_dict["MAX_PARALLEL_PROCESS"] = "21"
    config_path = create_config_file(valid_config_dict)
    with pytest.raises(ConfigurationValidationError, match="MAX_PARALLEL_PROCESS must be between 1 and 20"):
        ZmbackupConfig.load(config_path)


def test_validate_rotate_time_range(create_config_file, valid_config_dict: Dict[str, str]) -> None:
    """
    Test ROTATE_TIME range validation.

    :param create_config_file: Factory fixture to create config file
    :param valid_config_dict: Dictionary with valid config values
    """
    valid_config_dict["ROTATE_TIME"] = "0"
    config_path = create_config_file(valid_config_dict)
    with pytest.raises(ConfigurationValidationError, match="ROTATE_TIME must be between 1 and 3650"):
        ZmbackupConfig.load(config_path)

    valid_config_dict["ROTATE_TIME"] = "3651"
    config_path = create_config_file(valid_config_dict)
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


def test_get_config_singleton(reset_config_singleton, create_config_file, valid_config_dict: Dict[str, str]) -> None:
    """
    Test that get_config returns the same instance.

    :param reset_config_singleton: Fixture to reset singleton
    :param create_config_file: Factory fixture to create config file
    :param valid_config_dict: Dictionary with valid config values
    """
    config_path = create_config_file(valid_config_dict)

    config1 = get_config(config_path)
    config2 = get_config()

    assert config1 is config2


def test_get_config_reload(reset_config_singleton, create_config_file, valid_config_dict: Dict[str, str]) -> None:
    """
    Test that get_config with reload=True returns a new instance.

    :param reset_config_singleton: Fixture to reset singleton
    :param create_config_file: Factory fixture to create config file
    :param valid_config_dict: Dictionary with valid config values
    """
    config_path = create_config_file(valid_config_dict)

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
