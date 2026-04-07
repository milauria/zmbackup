"""Configuration migration operations for zmbackup."""

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

import click

from src.exceptions import (
    ConfigurationParseError,
    ConfigurationValidationError,
)
from src.lib.config import ZmbackupConfig


class ConfigMigrator:
    """
    Handles migration of legacy KEY=VALUE configuration to JSON format.

    This class provides methods to parse a legacy configuration file,
    convert it to the new JSON schema, and write it to a target path
    atomically.

    :param config_path: Path to the source legacy configuration file
    :param output_path: Optional path for the output JSON file
    :param backup_suffix: Suffix for the backup of the original file
    :param force: Whether to overwrite the target file if it already exists
    :param dry_run: If True, do not actually write files or create backups
    :param is_root_func: Callable returning True if running as root
    """

    def __init__(
        self,
        config_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        backup_suffix: str = ".bak",
        force: bool = False,
        dry_run: bool = False,
        is_root_func: Callable[[], bool] = lambda: os.geteuid() == 0,
    ) -> None:
        """Initialize the ConfigMigrator."""
        self.config_path = Path(config_path)
        self.output_path = Path(output_path) if output_path else self._determine_target_path()
        self.backup_suffix = backup_suffix
        self.force = force
        self.dry_run = dry_run
        self.is_root = is_root_func

    def _determine_target_path(self) -> Path:
        """
        Determine the default target path for the JSON configuration.

        If the source is 'zmbackup.conf', the target will be 'zmbackup.json'.

        :return: Path to the target JSON file
        """
        if self.config_path.suffix == ".conf":
            return self.config_path.with_suffix(".json")
        return self.config_path.with_suffix(self.config_path.suffix + ".json")

    def migrate(self) -> int:
        """
        Perform the migration.

        Checks for root privileges if writing to /etc/zmbackup/, validates the
        source exists, parses the legacy format, converts it to JSON, validates
        the resulting configuration, and writes it atomically.

        :return: Exit code (0 for success, 1 for failure)
        """
        # Root check if writing to /etc/zmbackup/
        if str(self.output_path.absolute()).startswith("/etc/zmbackup") and not self.is_root():
            click.echo("Error: This command must be executed as root to write to /etc/zmbackup/", err=True)
            return 1

        # Source check
        if not self.config_path.exists():
            click.echo(f"Error: Configuration file not found: {self.config_path}", err=True)
            return 1

        # Skip if already JSON
        if self._is_json_format(self.config_path):
            click.echo(f"Configuration file {self.config_path} is already in JSON format. No migration needed.")
            return 0

        # Check if target exists
        if self.output_path.exists() and not self.force:
            click.echo(f"Error: Target file {self.output_path} already exists. Use --force to overwrite.", err=True)
            return 1

        try:
            # Parse legacy config
            click.echo(f"Parsing legacy configuration from {self.config_path}...")
            # We use the existing static method from ZmbackupConfig
            legacy_config = ZmbackupConfig._parse_config_file(self.config_path)

            # Convert to JSON schema
            click.echo("Converting to JSON format (version 1.0)...")
            json_config = self._convert_to_json_schema(legacy_config)

            # Validate before writing
            click.echo("Validating new configuration...")
            self._validate_config_dict(json_config)

            if self.dry_run:
                click.echo(f"[Dry Run] Would migrate {self.config_path} to {self.output_path}")
                if not self.output_path.exists() or self.force:
                    click.echo("[Dry Run] Would create backup of original file.")
                return 0

            # Create backup
            backup_path = Path(str(self.config_path) + self.backup_suffix)
            click.echo(f"Creating backup: {backup_path}")
            shutil.copy2(self.config_path, backup_path)

            # Write JSON file atomically
            click.echo(f"Writing JSON configuration to {self.output_path}...")
            self._atomic_write_json(json_config)

            click.echo("✓ Migration completed successfully!")
            click.echo(f"  Source: {self.config_path}")
            click.echo(f"  Backup: {backup_path}")
            click.echo(f"  Target: {self.output_path}")
            return 0

        except (ConfigurationParseError, ConfigurationValidationError) as e:
            click.echo(f"Configuration Error: {e}", err=True)
            return 1
        except Exception as e:
            click.echo(f"Unexpected Error during migration: {e}", err=True)
            return 1

    def _is_json_format(self, path: Path) -> bool:
        """
        Detect if file is JSON format by checking the first character.

        :param path: Path to the file
        :return: True if it looks like JSON
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read(1024).strip()
                return content.startswith("{")
        except Exception:
            return False

    def _convert_to_json_schema(self, legacy_config: Dict[str, str]) -> Dict[str, Any]:
        """
        Convert legacy KEY=VALUE pairs to JSON schema v1.0.

        :param legacy_config: Dictionary of raw KEY=VALUE pairs
        :return: Dictionary matching the JSON schema
        """
        return {
            "version": "1.0",
            "zimbra": {
                "backup_user": legacy_config.get("BACKUPUSER", "zimbra"),
                "workdir": legacy_config.get("WORKDIR", "/opt/zimbra/backup"),
                "ldap_server": legacy_config.get("LDAPSERVER", "ldap://localhost:389"),
                "ldap_admin": legacy_config.get("LDAPADMIN", "uid=zimbra,cn=admins,cn=zimbra"),
                "ldap_password": legacy_config.get("LDAPPASS", ""),
            },
            "logging": {
                "log_file": legacy_config.get("LOGFILE", "/opt/zimbra/log/zmbackup.log"),
            },
            "email": {
                "enable_notify": legacy_config.get("ENABLE_EMAIL_NOTIFY", "all"),
                "notify_address": legacy_config.get("EMAIL_NOTIFY", ""),
                "sender_address": legacy_config.get("EMAIL_SENDER", ""),
            },
            "backup": {
                "max_parallel_process": int(legacy_config.get("MAX_PARALLEL_PROCESS", "3")),
                "rotate_time": int(legacy_config.get("ROTATE_TIME", "30")),
                "lock_backup": self._parse_bool(legacy_config.get("LOCK_BACKUP", "true")),
                "backup_inactive_accounts": self._parse_bool(legacy_config.get("BACKUP_INACTIVE_ACCOUNTS", "true")),
                "ssl_enable": self._parse_bool(legacy_config.get("SSL_ENABLE", "true")),
            },
            "session": {
                "type": legacy_config.get("SESSION_TYPE", "TXT"),
            },
            "binaries": {
                "zmmailbox": legacy_config.get("ZMMAILBOX", "/opt/zimbra/bin/zmmailbox"),
            },
        }

    def _parse_bool(self, value: str) -> bool:
        """
        Parse boolean from string.

        :param value: String to parse
        :return: Boolean value
        """
        return value.lower().strip() in ("true", "yes", "1")

    def _validate_config_dict(self, config_dict: Dict[str, Any]) -> None:
        """
        Validate config by attempting to load it using ZmbackupConfig.

        :param config_dict: Dictionary to validate
        :raises ConfigurationValidationError: If validation fails
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_dict, f)
            temp_path = Path(f.name)

        try:
            # This will trigger all validation logic in ZmbackupConfig.load
            ZmbackupConfig.load(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def _atomic_write_json(self, config_dict: Dict[str, Any]) -> None:
        """
        Write JSON atomically using a temporary file and rename.

        :param config_dict: Dictionary to write
        """
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create temp file in the same directory as the target
        with tempfile.NamedTemporaryFile(
            mode="w", dir=self.output_path.parent, delete=False, suffix=".tmp", encoding="utf-8"
        ) as temp_file:
            json.dump(config_dict, temp_file, indent=2)
            temp_path = Path(temp_file.name)

        try:
            # Set permissions before moving (readable by owner and group)
            os.chmod(temp_path, 0o640)
            # Atomic rename (on Unix)
            os.rename(temp_path, self.output_path)
        except Exception:
            # Clean up temp file on failure
            temp_path.unlink(missing_ok=True)
            raise


def migrate_config(
    config_path: str,
    output_path: Optional[str] = None,
    backup_suffix: str = ".bak",
    force: bool = False,
    dry_run: bool = False,
) -> None:
    """
    CLI entry point for configuration migration.

    :param config_path: Path to source configuration file
    :param output_path: Path for output JSON file
    :param backup_suffix: Suffix for backup file
    :param force: Force overwrite if target exists
    :param dry_run: If True, do not perform actual migration
    :raises click.Abort: If the migration fails
    """
    migrator = ConfigMigrator(
        config_path=config_path, output_path=output_path, backup_suffix=backup_suffix, force=force, dry_run=dry_run
    )
    exit_code = migrator.migrate()
    if exit_code != 0:
        raise click.Abort()
