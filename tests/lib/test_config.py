import os
from pathlib import Path

import pytest

from src.exceptions import ConfigurationFileNotFoundError, ConfigurationParseError, ConfigurationValidationError
from src.lib import config as config_module
from src.lib.config import EmailNotifyLevel, SessionType, ZmbackupConfig, _config_instance, get_config


@pytest.fixture
def reset_config_singleton():
    """Reset the configuration singleton before and after tests."""
    config_module._config_instance = None
    yield
    config_module._config_instance = None


@pytest.fixture
def valid_config_dict():
    """Provides a dictionary with valid configuration values."""
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
def create_config_file(tmp_path):
    """Factory fixture to create a configuration file."""

    def _create(content_dict):
        config_file = tmp_path / "zmbackup.conf"
        with open(config_file, "w") as f:
            for key, value in content_dict.items():
                f.write(f"{key}={value}\n")
        return config_file

    return _create


# --- Enum Classes Tests ---


def test_email_notify_level_enum():
    """Test EmailNotifyLevel enum values."""
    assert EmailNotifyLevel.ALL.value == "all"
    assert EmailNotifyLevel.START.value == "start"
    assert EmailNotifyLevel.FINISH.value == "finish"
    assert EmailNotifyLevel.ERROR.value == "error"
    assert EmailNotifyLevel.NONE.value == "none"


def test_session_type_enum():
    """Test SessionType enum values."""
    assert SessionType.TXT.value == "TXT"
    assert SessionType.SQLITE3.value == "SQLITE3"


# --- Configuration Parsing Tests ---


def test_load_valid_config(create_config_file, valid_config_dict):
    """Test loading a valid configuration file."""
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


def test_load_config_with_comments_and_whitespace(tmp_path):
    """Test loading config with comments, empty lines, and extra whitespace."""
    config_file = tmp_path / "zmbackup_extra.conf"
    content = """
    # This is a comment
    BACKUPUSER = zimbra
    
    WORKDIR=/opt/zimbra/backup # inline comment not supported by current parser, but should be fine if not split
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


def test_load_config_missing_file():
    """Test ConfigurationFileNotFoundError when file does not exist."""
    with pytest.raises(ConfigurationFileNotFoundError):
        ZmbackupConfig.load("/non/existent/path/zmbackup.conf")


def test_load_config_malformed_line(tmp_path):
    """Test ConfigurationParseError for malformed lines (missing =)."""
    config_file = tmp_path / "malformed.conf"
    config_file.write_text("INVALID_LINE_WITHOUT_EQUALS")
    with pytest.raises(ConfigurationParseError, match="line format at"):
        ZmbackupConfig.load(config_file)


def test_load_config_missing_required_field(create_config_file, valid_config_dict):
    """Test ConfigurationValidationError when a required field is missing."""
    del valid_config_dict["LDAPPASS"]
    config_path = create_config_file(valid_config_dict)
    with pytest.raises(ConfigurationValidationError, match="Missing required configuration key: LDAPPASS"):
        ZmbackupConfig.load(config_path)


def test_load_config_jinja2_template_variables(create_config_file, valid_config_dict):
    """Test that Jinja2 template variables are treated as empty and raise validation error if required."""
    valid_config_dict["LDAPPASS"] = "{{ zimbra_ldap_password }}"
    config_path = create_config_file(valid_config_dict)
    # Since LDAPPASS becomes empty, it should raise ConfigurationValidationError
    with pytest.raises(ConfigurationValidationError, match="Missing required configuration key: LDAPPASS"):
        ZmbackupConfig.load(config_path)


# --- Type Conversions Tests ---


@pytest.mark.parametrize(
    "value,expected",
    [
        ("true", True),
        ("TRUE", True),
        ("yes", True),
        ("YES", True),
        ("on", False),  # "on" is not in current implementation but let's check what it does
        ("1", True),
        ("false", False),
        ("no", False),
        ("0", False),
    ],
)
def test_convert_to_bool_valid(value, expected):
    """Test valid boolean conversions."""
    if value == "on":
        with pytest.raises(ConfigurationParseError):
            ZmbackupConfig._convert_to_bool(value, "test_field")
    else:
        assert ZmbackupConfig._convert_to_bool(value, "test_field") == expected


def test_convert_to_bool_invalid():
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
def test_convert_to_enum_valid(value, enum_class, expected):
    """Test valid enum conversions (by value and case-insensitive name)."""
    assert ZmbackupConfig._convert_to_enum(value, enum_class, "test_field") == expected


def test_convert_to_enum_invalid():
    """Test invalid enum conversion."""
    with pytest.raises(ConfigurationValidationError, match="value for test_field"):
        ZmbackupConfig._convert_to_enum("invalid_val", EmailNotifyLevel, "test_field")


# --- Validation Tests ---


def test_validate_email_valid():
    """Test valid email validation."""
    ZmbackupConfig.validate_email("test@example.com", "TEST_EMAIL")
    ZmbackupConfig.validate_email("user.name+tag@sub.domain.co.uk", "TEST_EMAIL")


def test_validate_email_invalid():
    """Test invalid email validation."""
    with pytest.raises(ConfigurationValidationError, match="email format for"):
        ZmbackupConfig.validate_email("not-an-email", "TEST_EMAIL")


@pytest.mark.parametrize(
    "url", ["ldap://localhost", "ldaps://192.168.1.10", "ldap://ldap.example.com:389", "ldaps://secure.example.com:636"]
)
def test_validate_ldap_url_valid(url):
    """Test valid LDAP URL validation."""
    ZmbackupConfig.validate_ldap_url(url, "LDAPSERVER")


@pytest.mark.parametrize("url", ["http://localhost", "ldap:/localhost", "ldap://invalid_chars_^", "not-a-url"])
def test_validate_ldap_url_invalid(url):
    """Test invalid LDAP URL validation."""
    with pytest.raises(ConfigurationValidationError, match="LDAP URL for"):
        ZmbackupConfig.validate_ldap_url(url, "LDAPSERVER")


def test_validate_parallel_process_range(create_config_file, valid_config_dict):
    """Test MAX_PARALLEL_PROCESS range validation (1-20)."""
    valid_config_dict["MAX_PARALLEL_PROCESS"] = "0"
    config_path = create_config_file(valid_config_dict)
    with pytest.raises(ConfigurationValidationError, match="MAX_PARALLEL_PROCESS must be between 1 and 20"):
        ZmbackupConfig.load(config_path)

    valid_config_dict["MAX_PARALLEL_PROCESS"] = "21"
    config_path = create_config_file(valid_config_dict)
    with pytest.raises(ConfigurationValidationError, match="MAX_PARALLEL_PROCESS must be between 1 and 20"):
        ZmbackupConfig.load(config_path)


def test_validate_rotate_time_range(create_config_file, valid_config_dict):
    """Test ROTATE_TIME range validation (1-3650)."""
    valid_config_dict["ROTATE_TIME"] = "0"
    config_path = create_config_file(valid_config_dict)
    with pytest.raises(ConfigurationValidationError, match="ROTATE_TIME must be between 1 and 3650"):
        ZmbackupConfig.load(config_path)

    valid_config_dict["ROTATE_TIME"] = "3651"
    config_path = create_config_file(valid_config_dict)
    with pytest.raises(ConfigurationValidationError, match="ROTATE_TIME must be between 1 and 3650"):
        ZmbackupConfig.load(config_path)


# --- Derived Properties Tests ---


def test_derived_properties(create_config_file, valid_config_dict):
    """Test database_path and session_file_path properties."""
    valid_config_dict["WORKDIR"] = "/tmp/zmbackup"
    config_path = create_config_file(valid_config_dict)
    config = ZmbackupConfig.load(config_path)

    assert config.database_path == "sqlite:////tmp/zmbackup/zmbackup_sessions.db"
    assert config.session_file_path == Path("/tmp/zmbackup/sessions.txt")


# --- Singleton Pattern Tests ---


def test_get_config_singleton(reset_config_singleton, create_config_file, valid_config_dict):
    """Test that get_config returns the same instance."""
    config_path = create_config_file(valid_config_dict)

    config1 = get_config(config_path)
    config2 = get_config()

    assert config1 is config2


def test_get_config_reload(reset_config_singleton, create_config_file, valid_config_dict):
    """Test that get_config with reload=True returns a new instance."""
    config_path = create_config_file(valid_config_dict)

    config1 = get_config(config_path)
    config2 = get_config(config_path, reload=True)

    assert config1 is not config2


def test_get_config_different_paths(reset_config_singleton, create_config_file, valid_config_dict, tmp_path):
    """Test that get_config with different paths (and reload) returns different instances."""
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
