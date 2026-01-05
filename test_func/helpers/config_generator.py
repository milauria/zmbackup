from pathlib import Path


def generate_test_config(
    workdir: Path,
    config_filename: str = "zmbackup.conf",
    backup_user: str = "zimbra",
    ldap_server: str = "ldap://localhost:389",
    email_notify: str = "admin@example.com",
    invalid_db_path: bool = False,
) -> Path:
    """
    Generate temporary zmbackup configuration file for testing.

    This helper creates a standard configuration file in a temporary directory,
    ensuring that the list operation points to the correct test database.

    :param workdir: Working directory (database will be at workdir/zmbackup_sessions.db)
    :param config_filename: Name of config file to create
    :param backup_user: Backup user name to use in config
    :param ldap_server: LDAP server URL to use in config
    :param email_notify: Email notification address to use in config
    :param invalid_db_path: If True, generates config with invalid database path
    :return: Path to the generated configuration file
    """
    config_path = workdir / config_filename

    # For invalid database testing, use non-existent directory
    workdir_value = "/nonexistent/invalid/path" if invalid_db_path else str(workdir)

    config_content = f"""# Test Configuration for Behave
BACKUPUSER={backup_user}
WORKDIR={workdir_value}
LDAPSERVER={ldap_server}
LDAPADMIN=uid=zimbra,cn=admins,cn=zimbra
LDAPPASS=testpassword
LOGFILE={workdir}/zmbackup.log
ENABLE_EMAIL_NOTIFY=NONE
EMAIL_NOTIFY={email_notify}
EMAIL_SENDER=zmbackup@example.com
MAX_PARALLEL_PROCESS=3
ROTATE_TIME=30
LOCK_BACKUP=true
SESSION_TYPE=TXT
BACKUP_INACTIVE_ACCOUNTS=true
SSL_ENABLE=true
ZMMAILBOX=/opt/zimbra/bin/zmmailbox
"""

    config_path.write_text(config_content)
    return config_path


def delete_config_file(config_path: Path) -> None:
    """
    Delete configuration file if it exists.

    :param config_path: Path to the configuration file to delete
    """
    if config_path.exists():
        config_path.unlink()


__all__ = ["generate_test_config", "delete_config_file"]
