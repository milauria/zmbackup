"""Initialization operations for zmbackup."""

import os
from pathlib import Path

import click
import validators
from jinja2 import Environment, FileSystemLoader

from lib.config import DEFAULT_CONFIG_PATH


def validate_email(value: str) -> str:
    """
    Validate email address format.

    :param value: Email address to validate
    :return: The validated email address
    :raises click.BadParameter: If email is invalid
    """
    if validators.email(value):
        return value
    raise click.BadParameter(f"'{value}' is not a valid email address.")


def validate_address(value: str) -> str:
    """
    Validate IP address or FQDN format.

    :param value: Address to validate
    :return: The validated address
    :raises click.BadParameter: If address is invalid
    """
    if validators.ip_address.ipv4(value) or validators.ip_address.ipv6(value) or validators.domain(value):
        return value
    raise click.BadParameter(f"'{value}' is not a valid IP or FQDN.")


def run_init(config_path: str = str(DEFAULT_CONFIG_PATH)) -> None:
    """
    Run the configuration initialization by prompting user for values
    and rendering a Jinja2 template.

    :param config_path: Path where the configuration file will be written
    :raises click.Abort: If user is not root or if process is aborted
    """
    # Check if user is root
    if os.geteuid() != 0:
        click.echo("Error: This command can only be executed by root user.", err=True)
        raise click.Abort()

    click.echo("Initializing zmbackup configuration...")

    # Define variables to be prompted
    config_values = {}

    config_values["ose_user"] = click.prompt("Zimbra backup user", default="zimbra")
    config_values["ose_default_bkp_dir"] = click.prompt("Backup working directory", default="/opt/zimbra/backup")
    config_values["ose_install_address"] = click.prompt(
        "Zimbra LDAP server address", default="127.0.0.1", value_proc=validate_address
    )
    config_values["ose_install_ldappass"] = click.prompt("Zimbra LDAP admin password", hide_input=True)
    config_values["zmbkp_mail_alert"] = click.prompt("Email for backup notifications", value_proc=validate_email)
    config_values["zmbkp_mail_sender"] = click.prompt("Email sender address", value_proc=validate_email)
    config_values["max_parallel_process"] = click.prompt("Max parallel processes", default=3, type=int)
    config_values["rotate_time"] = click.prompt("Retention time (days)", default=30, type=int)
    config_values["lock_backup"] = click.prompt(
        "Lock backup (true/false)", default="true", type=click.Choice(["true", "false"], case_sensitive=False)
    ).lower()
    config_values["session_type"] = click.prompt(
        "Session storage type", default="TXT", type=click.Choice(["TXT", "SQLITE"], case_sensitive=False)
    ).upper()

    # Define template path
    template_dir = Path(__file__).parent.parent / "templates"
    template_file = "zmbackup.conf"

    try:
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        template = env.get_template(template_file)

        # Render template
        rendered_config = template.render(**config_values)

        # Write to file
        output_path = Path(config_path)

        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            f.write(rendered_config)

        click.echo(f"Configuration successfully written to {config_path}")

    except Exception as e:
        click.echo(f"Error initializing configuration: {e}")
        raise click.Abort()
