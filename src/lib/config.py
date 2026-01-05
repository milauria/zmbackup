"""
Centralized configuration management for zmbackup.

This module provides the ZmbackupConfig class which handles loading,
parsing, and validating configuration settings from the zmbackup.conf file.
It uses the attrs library for a clean, immutable configuration object.
"""

import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar, Union

import attrs
import validators

from src.exceptions import (
    ConfigurationFileNotFoundError,
    ConfigurationParseError,
    ConfigurationValidationError,
)

# --- Enumeration Types ---


class EmailNotifyLevel(Enum):
    """Email notification levels."""

    ALL = "all"
    START = "start"
    FINISH = "finish"
    ERROR = "error"
    NONE = "none"


class SessionType(Enum):
    """Session storage backend types."""

    TXT = "TXT"
    SQLITE3 = "SQLITE3"


# --- Constants ---

DEFAULT_CONFIG_PATH = Path("/etc/zmbackup/zmbackup.conf")

T = TypeVar("T", bound=Enum)


@attrs.frozen(slots=True)
class ZmbackupConfig:
    """
    Centralized configuration management for zmbackup.

    Loads configuration from zmbackup.conf file and provides
    type-safe access to all configuration parameters.
    """

    # Zimbra Configuration
    backup_user: str
    workdir: Path = attrs.field(converter=Path)
    ldap_server: str
    ldap_admin: str
    ldap_password: str

    # Logging Configuration
    log_file: Path = attrs.field(converter=Path)

    # Email Configuration
    enable_email_notify: EmailNotifyLevel
    email_notify: str
    email_sender: str

    # Backup Configuration
    max_parallel_process: int = attrs.field(converter=int)
    rotate_time: int = attrs.field(converter=int)
    lock_backup: bool
    backup_inactive_accounts: bool
    ssl_enable: bool

    # Session Configuration
    session_type: SessionType

    # Binary Paths
    zmmailbox: Path = attrs.field(converter=Path)

    @classmethod
    def load(cls, config_path: Optional[Union[str, Path]] = None) -> "ZmbackupConfig":
        """
        Load configuration from file.

        Args:
            config_path: Path to zmbackup.conf file. If None, uses default path.

        Returns:
            ZmbackupConfig instance

        Raises:
            ConfigurationFileNotFoundError: If configuration file doesn't exist.
            ConfigurationParseError: If file format is invalid.
            ConfigurationValidationError: If configuration validation fails.
        """
        path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH

        if not path.exists():
            raise ConfigurationFileNotFoundError(str(path))

        raw_config = cls._parse_config_file(path)

        # Mapping from config file keys to attribute names
        key_map = {
            "BACKUPUSER": "backup_user",
            "WORKDIR": "workdir",
            "LDAPSERVER": "ldap_server",
            "LDAPADMIN": "ldap_admin",
            "LDAPPASS": "ldap_password",
            "LOGFILE": "log_file",
            "ENABLE_EMAIL_NOTIFY": "enable_email_notify",
            "EMAIL_NOTIFY": "email_notify",
            "EMAIL_SENDER": "email_sender",
            "MAX_PARALLEL_PROCESS": "max_parallel_process",
            "ROTATE_TIME": "rotate_time",
            "LOCK_BACKUP": "lock_backup",
            "SESSION_TYPE": "session_type",
            "BACKUP_INACTIVE_ACCOUNTS": "backup_inactive_accounts",
            "SSL_ENABLE": "ssl_enable",
            "ZMMAILBOX": "zmmailbox",
        }

        config_args: Dict[str, Any] = {}
        for config_key, attr_name in key_map.items():
            if config_key not in raw_config or not raw_config[config_key]:
                raise ConfigurationValidationError(f"Missing required configuration key: {config_key}")

            val = raw_config[config_key]

            # Type specific conversions before passing to attrs constructor
            if attr_name == "enable_email_notify":
                config_args[attr_name] = cls._convert_to_enum(val, EmailNotifyLevel, config_key)
            elif attr_name == "session_type":
                config_args[attr_name] = cls._convert_to_enum(val, SessionType, config_key)
            elif attr_name in ("lock_backup", "backup_inactive_accounts", "ssl_enable"):
                config_args[attr_name] = cls._convert_to_bool(val, config_key)
            else:
                config_args[attr_name] = val

        try:
            instance = cls(**config_args)
            instance._validate()
            return instance
        except (ValueError, TypeError) as e:
            raise ConfigurationParseError(f"Initializing configuration: {str(e)}")

    @staticmethod
    def _parse_config_file(path: Path) -> Dict[str, str]:
        """
        Parse configuration file and return raw key-value pairs.

        Args:
            path: Path to configuration file

        Returns:
            Dictionary of configuration key-value pairs (all strings)

        Raises:
            ConfigurationParseError: If file format is invalid
        """
        config = {}
        try:
            with open(path, "r") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue

                    if "=" not in line:
                        raise ConfigurationParseError(f"line format at {path}:{line_num}: {line}")

                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # Handle Jinja2 template variables as empty values
                    if value.startswith("{{") and value.endswith("}}"):
                        value = ""

                    config[key] = value
            return config
        except Exception as e:
            raise ConfigurationParseError(f"reading configuration file {path}: {str(e)}")

    @staticmethod
    def _convert_to_bool(value: str, field_name: str) -> bool:
        """Convert string to boolean."""
        val = value.lower()
        if val in ("true", "yes", "1"):
            return True
        if val in ("false", "no", "0"):
            return False
        raise ConfigurationParseError(f"boolean value for {field_name}: {value}")

    @staticmethod
    def _convert_to_enum(value: str, enum_class: Type[T], field_name: str) -> T:
        """Convert string to enum value."""
        try:
            # Try to match by value (string)
            return enum_class(value)
        except ValueError:
            # Try to match by name (case-insensitive)
            for item in enum_class:
                if item.name.lower() == value.lower():
                    return item

            valid_values = [e.value for e in enum_class]
            raise ConfigurationValidationError(f"value for {field_name}: {value}. Must be one of {valid_values}")

    def _validate(self) -> None:
        """
        Validate the complete configuration.

        Raises:
            ConfigurationValidationError: If validation fails
        """
        self.validate_email(self.email_notify, "EMAIL_NOTIFY")
        self.validate_email(self.email_sender, "EMAIL_SENDER")
        self.validate_ldap_url(self.ldap_server, "LDAPSERVER")

        if self.max_parallel_process < 1 or self.max_parallel_process > 20:
            raise ConfigurationValidationError(
                f"MAX_PARALLEL_PROCESS must be between 1 and 20, got {self.max_parallel_process}"
            )

        if self.rotate_time < 1 or self.rotate_time > 3650:
            raise ConfigurationValidationError(f"ROTATE_TIME must be between 1 and 3650, got {self.rotate_time}")

    @staticmethod
    def validate_email(email: str, field_name: str) -> None:
        """Validate email format."""
        if not validators.email(email):
            raise ConfigurationValidationError(f"email format for {field_name}: {email}")

    @staticmethod
    def validate_ldap_url(url: str, field_name: str) -> None:
        """Validate LDAP URL format."""
        if not (url.startswith("ldap://") or url.startswith("ldaps://")):
            raise ConfigurationValidationError(f"LDAP URL for {field_name}: {url}")

        if not re.match(r"^ldaps?://[a-zA-Z0-9\.-]+(:\d+)?$", url):
            if not validators.url(url):
                raise ConfigurationValidationError(f"LDAP URL for {field_name}: {url}")

    # --- Derived Properties ---

    @property
    def database_path(self) -> str:
        """Derived database path for SQLAlchemy."""
        return f"sqlite:///{self.workdir}/zmbackup_sessions.db"

    @property
    def session_file_path(self) -> Path:
        """Derived session file path."""
        return self.workdir / "sessions.txt"


# --- Singleton Pattern ---

_config_instance: Optional[ZmbackupConfig] = None


def get_config(config_path: Optional[Union[str, Path]] = None, reload: bool = False) -> ZmbackupConfig:
    """
    Get or create the global configuration instance.

    Args:
        config_path: Path to configuration file (only used on first call or if reload is True)
        reload: Force reload of configuration

    Returns:
        Global ZmbackupConfig instance

    Raises:
        ConfigurationFileNotFoundError: If configuration file doesn't exist.
        ConfigurationParseError: If file format is invalid.
        ConfigurationValidationError: If configuration validation fails.
    """
    global _config_instance

    if _config_instance is None or reload:
        _config_instance = ZmbackupConfig.load(config_path)

    return _config_instance
