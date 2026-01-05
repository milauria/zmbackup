import os
from pathlib import Path

import click
import validators
from jinja2 import Environment, FileSystemLoader

from lib.config import DEFAULT_CONFIG_PATH


def validate_email(value):
    if validators.email(value):
        return value
    raise click.BadParameter(f"'{value}' is not a valid email address.")


def validate_address(value):
    if validators.ip_address.ipv4(value) or validators.ip_address.ipv6(value) or validators.domain(value):
        return value
    raise click.BadParameter(f"'{value}' is not a valid IP or FQDN.")


def run_init(config_path: str = str(DEFAULT_CONFIG_PATH)):
    """
    Initialize the zmbackup configuration by prompting the user for values
     and rendering a Jinja2 template.

    Args:
        config_path (str): The path where the configuration file will be saved.
    """
    # Check if user is root
    if os.geteuid() != 0:
        click.echo("Error: This command can only be executed by root user.", err=True)
        raise click.Abort()

    click.echo("Initializing zmbackup configuration...")

    # Define variables to be prompted
    config_values = {}

    config_values["ose_user"] = click.prompt("Zimbra backup user", default="zimbra")
    config_values["ose_default_bkp_dir"] = click.prompt("Backup directory", default="/opt/zimbra/backup")
    config_values["ose_install_address"] = click.prompt(
        "LDAP server address", default="127.0.0.1", value_proc=validate_address
    )
    config_values["ose_install_ldappass"] = click.prompt("LDAP admin password", hide_input=True)
    config_values["zmbkp_mail_alert"] = click.prompt("Email for alerts", value_proc=validate_email)
    config_values["zmbkp_mail_sender"] = click.prompt("Email sender address", value_proc=validate_email)
    config_values["max_parallel_process"] = click.prompt("Maximum parallel processes", default=3, type=int)
    config_values["rotate_time"] = click.prompt("Retention time (days)", default=30, type=int)
    config_values["lock_backup"] = click.prompt(
        "Lock backup (true/false)", default="true", type=click.Choice(["true", "false"], case_sensitive=False)
    ).lower()
    config_values["session_type"] = click.prompt(
        "Session storage type (TXT/SQLITE3)", default="TXT", type=click.Choice(["TXT", "SQLITE3"], case_sensitive=False)
    ).upper()

    # Define template path
    template_dir = Path(__file__).parent.parent / "templates"
    template_file = "zmbackup.conf"

    try:
        # Set up Jinja2 environment
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
        click.echo(f"Error initializing configuration: {e}", err=True)
        raise click.Abort()
