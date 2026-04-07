"""Centralized configuration management for zmbackup."""

import json
import re
import warnings
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar, Union

import attrs
import validators

from src.enums import EmailNotifyLevel, SessionType
from src.exceptions import (
    ConfigurationFileNotFoundError,
    ConfigurationParseError,
    ConfigurationValidationError,
)

# --- Constants ---

DEFAULT_CONFIG_PATH = Path("/etc/zmbackup/zmbackup.conf")

T = TypeVar("T", bound=Enum)


@attrs.frozen(slots=True)
class ZmbackupConfig:
    """
    Centralized configuration management for zmbackup.

    Configuration is loaded from JSON file and accessed via properties.
    The underlying configuration dictionary is stored in _config attribute
    and remains immutable through the attrs.frozen decorator.

    .. note::
       Starting from zmbackup v2.1, JSON format is the standard configuration
       format. The old KEY=VALUE format is deprecated and support will be
       removed in v3.0.
    """

    # Core attributes - store the raw configuration
    _config: Dict[str, Any] = attrs.field(alias="_config")
    _config_path: Path = attrs.field(converter=Path, alias="_config_path")

    # --- Properties ---

    @property
    def backup_user(self) -> str:
        """
        Zimbra backup user account.

        :return: Zimbra backup user
        """
        return str(self._config["zimbra"]["backup_user"])

    @property
    def workdir(self) -> Path:
        """
        Working directory for backups.

        :return: Path to working directory
        """
        return Path(self._config["zimbra"]["workdir"])

    @property
    def ldap_server(self) -> str:
        """
        Zimbra LDAP server URL.

        :return: LDAP server URL
        """
        return str(self._config["zimbra"]["ldap_server"])

    @property
    def ldap_admin(self) -> str:
        """
        Zimbra LDAP admin DN.

        :return: LDAP admin DN
        """
        return str(self._config["zimbra"]["ldap_admin"])

    @property
    def ldap_password(self) -> str:
        """
        Zimbra LDAP admin password.

        :return: LDAP admin password
        """
        return str(self._config["zimbra"]["ldap_password"])

    @property
    def log_file(self) -> Path:
        """
        Path to log file.

        :return: Path to log file
        """
        return Path(self._config["logging"]["log_file"])

    @property
    def enable_email_notify(self) -> EmailNotifyLevel:
        """
        Email notification level.

        :return: Email notification level enum
        """
        val = self._config["email"]["enable_notify"]
        if isinstance(val, EmailNotifyLevel):
            return val
        return self._convert_to_enum(str(val), EmailNotifyLevel, "email.enable_notify")

    @property
    def email_notify(self) -> str:
        """
        Email address for notifications.

        :return: Email address for notifications
        """
        return str(self._config["email"]["notify_address"])

    @property
    def email_sender(self) -> str:
        """
        Email sender address.

        :return: Email sender address
        """
        return str(self._config["email"]["sender_address"])

    @property
    def max_parallel_process(self) -> int:
        """
        Maximum parallel backup processes.

        :return: Maximum parallel processes
        """
        return int(self._config["backup"]["max_parallel_process"])

    @property
    def rotate_time(self) -> int:
        """
        Retention time in days.

        :return: Retention time in days
        """
        return int(self._config["backup"]["rotate_time"])

    @property
    def lock_backup(self) -> bool:
        """
        Lock backup to one per day.

        :return: True if backup lock is enabled
        """
        val = self._config["backup"]["lock_backup"]
        if isinstance(val, bool):
            return val
        return self._convert_to_bool(str(val), "backup.lock_backup")

    @property
    def backup_inactive_accounts(self) -> bool:
        """
        Include inactive accounts in backup.

        :return: True if inactive accounts should be backed up
        """
        val = self._config["backup"]["backup_inactive_accounts"]
        if isinstance(val, bool):
            return val
        return self._convert_to_bool(str(val), "backup.backup_inactive_accounts")

    @property
    def ssl_enable(self) -> bool:
        """
        Enable SSL communication with Zimbra.

        :return: True if SSL is enabled
        """
        val = self._config["backup"]["ssl_enable"]
        if isinstance(val, bool):
            return val
        return self._convert_to_bool(str(val), "backup.ssl_enable")

    @property
    def session_type(self) -> SessionType:
        """
        Session storage backend.

        :return: Session storage backend enum
        """
        val = self._config["session"]["type"]
        if isinstance(val, SessionType):
            return val
        return self._convert_to_enum(str(val), SessionType, "session.type")

    @property
    def zmmailbox(self) -> Path:
        """
        Path to zmmailbox binary.

        :return: Path to zmmailbox binary
        """
        return Path(self._config["binaries"]["zmmailbox"])

    @classmethod
    def load(cls, config_path: Optional[Union[str, Path]] = None) -> "ZmbackupConfig":
        """
        Load configuration from JSON or legacy KEY=VALUE file.

        Automatically detects file format and parses accordingly.
        Legacy format support will be removed in v3.0.

        :param config_path: Path to configuration file. Uses default if None.
        :return: ZmbackupConfig instance
        :raises ConfigurationFileNotFoundError: If file doesn't exist
        :raises ConfigurationParseError: If file format is invalid
        :raises ConfigurationValidationError: If validation fails

        .. warning::
           Legacy KEY=VALUE format is deprecated. Use 'zmbackup migrate-config' to convert.
        """
        path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH

        if not path.exists():
            raise ConfigurationFileNotFoundError(str(path))

        # Detect format and parse
        if cls._is_json_format(path):
            raw_config = cls._parse_json_file(path)
        else:
            # Legacy format - issue deprecation warning
            warnings.warn(
                "KEY=VALUE format is deprecated. Use 'zmbackup migrate-config' to convert to JSON.",
                DeprecationWarning,
                stacklevel=2,
            )
            raw_config = cls._parse_legacy_file(path)

        try:
            # Create instance with validated config
            instance = cls(_config=raw_config, _config_path=path)
            instance._validate()
            return instance
        except (ValueError, TypeError) as e:
            raise ConfigurationParseError(f"Initializing configuration: {str(e)}")

    @staticmethod
    def _is_json_format(path: Path) -> bool:
        """
        Detect if file is JSON format.

        :param path: Path to configuration file
        :return: True if JSON format, False otherwise
        """
        try:
            with open(path, "r") as f:
                first_char = f.read(1).strip()
                return first_char == "{"
        except Exception:
            return False

    @staticmethod
    def _parse_json_file(path: Path) -> Dict[str, Any]:
        """
        Parse JSON configuration file.

        :param path: Path to JSON file
        :return: Parsed configuration dictionary
        :raises ConfigurationParseError: If JSON is invalid
        """
        try:
            with open(path, "r") as f:
                config: Dict[str, Any] = json.load(f)

            # Validate schema version
            if config.get("version") != "1.0":
                raise ConfigurationParseError(f"Unsupported configuration version: {config.get('version')}")

            return config
        except json.JSONDecodeError as e:
            raise ConfigurationParseError(f"Invalid JSON format in {path}: {str(e)}")
        except Exception as e:
            raise ConfigurationParseError(f"reading configuration file {path}: {str(e)}")

    @classmethod
    def _parse_legacy_file(cls, path: Path) -> Dict[str, Any]:
        """
        Parse legacy KEY=VALUE configuration file and convert to internal format.

        :param path: Path to legacy config file
        :return: Configuration dictionary in JSON schema format
        :raises ConfigurationParseError: If file format is invalid
        :raises ConfigurationValidationError: If required fields are missing
        """
        # Parse using existing logic
        raw_config = cls._parse_config_file(path)

        # Replicate original required field validation
        required_keys = [
            "BACKUPUSER",
            "WORKDIR",
            "LDAPSERVER",
            "LDAPADMIN",
            "LDAPPASS",
            "LOGFILE",
            "ENABLE_EMAIL_NOTIFY",
            "EMAIL_NOTIFY",
            "EMAIL_SENDER",
            "MAX_PARALLEL_PROCESS",
            "ROTATE_TIME",
            "LOCK_BACKUP",
            "SESSION_TYPE",
            "BACKUP_INACTIVE_ACCOUNTS",
            "SSL_ENABLE",
            "ZMMAILBOX",
        ]
        for key in required_keys:
            if key not in raw_config or not raw_config[key]:
                raise ConfigurationValidationError(f"Missing required configuration key: {key}")

        # Convert to new schema structure
        return {
            "version": "1.0",
            "zimbra": {
                "backup_user": raw_config["BACKUPUSER"],
                "workdir": raw_config["WORKDIR"],
                "ldap_server": raw_config["LDAPSERVER"],
                "ldap_admin": raw_config["LDAPADMIN"],
                "ldap_password": raw_config["LDAPPASS"],
            },
            "logging": {
                "log_file": raw_config["LOGFILE"],
            },
            "email": {
                "enable_notify": raw_config["ENABLE_EMAIL_NOTIFY"],
                "notify_address": raw_config["EMAIL_NOTIFY"],
                "sender_address": raw_config["EMAIL_SENDER"],
            },
            "backup": {
                "max_parallel_process": int(raw_config["MAX_PARALLEL_PROCESS"]),
                "rotate_time": int(raw_config["ROTATE_TIME"]),
                "lock_backup": raw_config["LOCK_BACKUP"],
                "backup_inactive_accounts": raw_config["BACKUP_INACTIVE_ACCOUNTS"],
                "ssl_enable": raw_config["SSL_ENABLE"],
            },
            "session": {
                "type": raw_config["SESSION_TYPE"],
            },
            "binaries": {
                "zmmailbox": raw_config["ZMMAILBOX"],
            },
        }

    @staticmethod
    def _parse_config_file(path: Path) -> Dict[str, str]:
        """
        Parse configuration file and return raw key-value pairs.

        :param path: Path to configuration file
        :return: Dictionary of configuration key-value pairs (all strings)
        :raises ConfigurationParseError: If file format is invalid
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
        """
        Convert string to boolean.

        :param value: String representation of boolean
        :param field_name: Name of the field for error reporting
        :return: Boolean value
        :raises ConfigurationParseError: If value cannot be converted
        """
        val = value.lower()
        if val in ("true", "yes", "1"):
            return True
        if val in ("false", "no", "0"):
            return False
        raise ConfigurationParseError(f"boolean value for {field_name}: {value}")

    @staticmethod
    def _convert_to_enum(value: str, enum_class: Type[T], field_name: str) -> T:
        """
        Convert string to enum value.

        :param value: String value to convert
        :param enum_class: Enum class to convert to
        :param field_name: Name of the field for error reporting
        :return: Enum instance
        :raises ConfigurationValidationError: If value is not valid for enum
        """
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

        :raises ConfigurationValidationError: If any validation fails
        """
        # Trigger property evaluation to validate types and trigger conversions
        self.validate_email(self.email_notify, "EMAIL_NOTIFY")
        self.validate_email(self.email_sender, "EMAIL_SENDER")
        self.validate_ldap_url(self.ldap_server, "LDAPSERVER")

        if self.max_parallel_process < 1 or self.max_parallel_process > 20:
            raise ConfigurationValidationError(
                f"MAX_PARALLEL_PROCESS must be between 1 and 20, got {self.max_parallel_process}"
            )

        if self.rotate_time < 1 or self.rotate_time > 3650:
            raise ConfigurationValidationError(f"ROTATE_TIME must be between 1 and 3650, got {self.rotate_time}")

        # Trigger enum validation
        _ = self.enable_email_notify
        _ = self.session_type

    @staticmethod
    def validate_email(email: str, field_name: str) -> None:
        """
        Validate email format.

        :param email: Email address to validate
        :param field_name: Name of the field for error reporting
        :raises ConfigurationValidationError: If email format is invalid
        """
        if not validators.email(email):
            raise ConfigurationValidationError(f"email format for {field_name}: {email}")

    @staticmethod
    def validate_ldap_url(url: str, field_name: str) -> None:
        """
        Validate LDAP URL format.

        :param url: LDAP URL to validate
        :param field_name: Name of the field for error reporting
        :raises ConfigurationValidationError: If LDAP URL format is invalid
        """
        if not (url.startswith("ldap://") or url.startswith("ldaps://")):
            raise ConfigurationValidationError(f"LDAP URL for {field_name}: {url}")

        if not re.match(r"^ldaps?://[a-zA-Z0-9\.-]+(:\d+)?$", url):
            if not validators.url(url):
                raise ConfigurationValidationError(f"LDAP URL for {field_name}: {url}")

    # --- Derived Properties ---

    @property
    def database_path(self) -> str:
        """
        Derived database path for SQLAlchemy.

        :return: Database connection string
        """
        return f"sqlite:///{self.workdir}/zmbackup_sessions.db"

    @property
    def session_file_path(self) -> Path:
        """
        Derived session file path.

        :return: Path to session file
        """
        return self.workdir / "sessions.txt"


# --- Singleton Pattern ---

_config_instance: Optional[ZmbackupConfig] = None


def get_config(config_path: Optional[Union[str, Path]] = None, reload: bool = False) -> ZmbackupConfig:
    """
    Get or create the global configuration instance.

    :param config_path: Path to configuration file (only used on first call or if reload is True)
    :param reload: Force reload of configuration
    :return: Global ZmbackupConfig instance
    :raises ConfigurationFileNotFoundError: If configuration file doesn't exist
    :raises ConfigurationParseError: If file format is invalid
    :raises ConfigurationValidationError: If configuration validation fails
    """
    global _config_instance

    if _config_instance is None or reload:
        _config_instance = ZmbackupConfig.load(config_path)

    return _config_instance
