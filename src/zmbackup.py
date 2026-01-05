#!/usr/bin/python
################################################################################
# zmbackup - Bash script to hot backup and hot restore Zimbra Collaboration
#            Suite Opensource
#
# Copyright (C) 2026 Lucas Costa Beyeler
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of version 2 of the GNU General Public
# License as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#
################################################################################
# zmbkpose:
#
# 26/10/2010 - Version 1.0.5 - By Alan Nikitiuk Milani
#                                 Bruno Gurgel
#
# 24/05/2012 - Version 2.0 Beta - By William Felipe Welter
################################################################################
# zmbackup:
#
# 06/02/2021 - Version 1.2.6  - By The Zimbra Community
# 03/01/2026 - Version 2.0.0  - By The Zimbra Community
################################################################################

import sys
from datetime import datetime
from typing import List, Optional

import click
from prettytable import PrettyTable

from src.clients.database_client import DatabaseClient
from src.database.session_manager import DatabaseSessionManager
from src.exceptions import (
    ConfigurationFileNotFoundError,
    ConfigurationParseError,
    ConfigurationValidationError,
)
from src.lib.config import DEFAULT_CONFIG_PATH, get_config
from src.lib.constants import ZMBACKUP_VERSION
from src.operations.init import run_init


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
@click.option("--config-path", default=str(DEFAULT_CONFIG_PATH), help="Path to the configuration file")
@click.pass_context
def cli(ctx: click.Context, config_path: str) -> None:
    """
    zmbackup CLI for Zimbra backups and restores.

    :param ctx: Click context
    :param config_path: Path to the configuration file
    """
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path


@cli.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """
    Initialize the zmbackup configuration.

    :param ctx: Click context
    """
    run_init(ctx.obj["config_path"])


@cli.command()
@click.option("--full", "-f", is_flag=True, help="Full Backup mode")
@click.option("--incremental", "-i", is_flag=True, help="Incremental Backup mode")
@click.option("--mail", "-m", "mail_flag", is_flag=True, help="Only backup mailbox content")
@click.option("--distributionlist", "-dl", is_flag=True, help="Backup distribution lists")
@click.option("--alias", "-al", is_flag=True, help="Backup aliases")
@click.option("--ldap", "-ldp", is_flag=True, help="Only backup LDAP entries")
@click.option("--signature", "-sig", is_flag=True, help="Backup account signatures")
@click.option("--domain", "-d", "domain_opt", help="Comma-separated list of domains")
@click.option("--account", "-a", "account_opt", help="Comma-separated list of accounts")
@click.pass_context
def backup(
    ctx: click.Context,
    full: bool,
    incremental: bool,
    mail_flag: bool,
    distributionlist: bool,
    alias: bool,
    ldap: bool,
    signature: bool,
    domain_opt: Optional[str],
    account_opt: Optional[str],
) -> None:
    """
    Perform a backup.

    :param ctx: Click context
    :param full: Full Backup mode
    :param incremental: Incremental Backup mode
    :param mail_flag: Only backup mailbox content
    :param distributionlist: Backup distribution lists
    :param alias: Backup aliases
    :param ldap: Only backup LDAP entries
    :param signature: Backup account signatures
    :param domain_opt: Comma-separated list of domains
    :param account_opt: Comma-separated list of accounts
    """
    config_path = ctx.obj["config_path"]
    try:
        config = get_config(config_path)
    except (ConfigurationFileNotFoundError, ConfigurationParseError, ConfigurationValidationError) as e:
        click.echo(f"Configuration error: {e}")
        sys.exit(1)

    if full and incremental:
        click.echo("Error: Please select only one mode: --full or --incremental.")
        sys.exit(1)

    if not full and not incremental:
        click.echo("Error: Please specify backup type: --full or --incremental.")
        sys.exit(1)

    if full:
        # Constraint: -dl, -al, -m, and -ldp are mutually exclusive
        excl_flags = {"mail": mail_flag, "distributionlist": distributionlist, "alias": alias, "ldap": ldap}
        active_excl = [name for name, active in excl_flags.items() if active]
        if len(active_excl) > 1:
            click.echo(f"Error: Flags {', '.join(active_excl)} are mutually exclusive.")
            sys.exit(1)

        scope = "everything"
        if active_excl:
            scope = active_excl[0]

        options = []
        if signature:
            options.append("signature")
        if domain_opt:
            options.append(f"domains={domain_opt}")
        if account_opt:
            options.append(f"accounts={account_opt}")

        click.echo(f"Full backup initiated for {scope} with options: {', '.join(options) if options else 'none'}")

    elif incremental:
        if not account_opt:
            click.echo("Error: Incremental backup requires at least one account via --account (-a).")
            sys.exit(1)
        click.echo(f"Incremental backup started for accounts: {account_opt}")


@cli.command()
@click.option("--restoreOnAccount", "-ro", is_flag=True, help="Restore from one account to another")
@click.option("--mail", "-m", "mail_flag", is_flag=True, help="Only restore mailbox content")
@click.option("--distributionlist", "-dl", is_flag=True, help="Restore distribution lists")
@click.option("--alias", "-al", is_flag=True, help="Restore aliases")
@click.option("--ldap", "-ldp", is_flag=True, help="Only restore LDAP entries")
@click.option("--signature", "-sig", is_flag=True, help="Restore account signatures")
@click.option("--domain", "-d", "domain_opt", help="Comma-separated list of domains")
@click.option("--account", "-a", "account_opt", help="Comma-separated list of accounts")
@click.option("--session", "-s", "session_id", help="Backup session ID to restore from")
@click.option("--origin", "-o", "mail_origin", help="Original account to restore")
@click.option("--destination", "-dest", "mail_destination", help="Destination account for restoration")
@click.pass_context
def restore(
    ctx: click.Context,
    restoreonaccount: bool,
    mail_flag: bool,
    distributionlist: bool,
    alias: bool,
    ldap: bool,
    signature: bool,
    domain_opt: Optional[str],
    account_opt: Optional[str],
    session_id: Optional[str],
    mail_origin: Optional[str],
    mail_destination: Optional[str],
) -> None:
    """
    Perform a restore.

    :param ctx: Click context
    :param restoreonaccount: Restore from one account to another
    :param mail_flag: Only restore mailbox content
    :param distributionlist: Restore distribution lists
    :param alias: Restore aliases
    :param ldap: Only restore LDAP entries
    :param signature: Restore account signatures
    :param domain_opt: Comma-separated list of domains
    :param account_opt: Comma-separated list of accounts
    :param session_id: Backup session ID to restore from
    :param mail_origin: Original account to restore
    :param mail_destination: Destination account for restoration
    """
    config_path = ctx.obj["config_path"]
    try:
        config = get_config(config_path)
    except (ConfigurationFileNotFoundError, ConfigurationParseError, ConfigurationValidationError) as e:
        click.echo(f"Configuration error: {e}")
        sys.exit(1)

    if not session_id or not mail_origin:
        click.echo("Error: Restore requires --session (-s) and --origin (-o).")
        sys.exit(1)

    if restoreonaccount and not mail_destination:
        click.echo("Error: --restoreOnAccount (-ro) requires a --destination (-dest) option.")
        sys.exit(1)

    options = []
    if mail_flag:
        options.append("mail")
    if distributionlist:
        options.append("distributionlist")
    if alias:
        options.append("alias")
    if ldap:
        options.append("ldap")
    if signature:
        options.append("signature")
    if domain_opt:
        options.append(f"domain_filter={domain_opt}")
    if account_opt:
        options.append(f"account_filter={account_opt}")
    if restoreonaccount:
        options.append(f"restore_to={mail_destination}")

    click.echo(
        f"Restore initiated from session {session_id} for {mail_origin} with options: {', '.join(options) if options else 'none'}"
    )


@cli.command()
@click.pass_context
def list(ctx: click.Context) -> None:
    """
    List backup sessions.

    :param ctx: Click context
    """
    config_path = ctx.obj["config_path"]
    try:
        config = get_config(config_path)
    except (ConfigurationFileNotFoundError, ConfigurationParseError, ConfigurationValidationError) as e:
        click.echo(f"Configuration error: {e}")
        sys.exit(1)

    try:
        db_manager = DatabaseSessionManager(config.database_path)
        client = DatabaseClient(db_manager)
        sessions = client.list_sessions()

        if not sessions:
            click.echo("No backup sessions found.")
            return

        table = PrettyTable()
        table.field_names = ["Session Name", "Start", "Ending", "Size", "Description"]
        table.align = "l"  # Left align columns

        for s in sessions:
            start_str = s.start.strftime("%Y-%m-%d %H:%M") if s.start else "N/A"
            ending_str = s.ending.strftime("%Y-%m-%d %H:%M") if s.ending else "N/A"
            table.add_row([s.session_name, start_str, ending_str, s.size or "N/A", s.description])

        click.echo(table)

    except Exception as e:
        click.echo(f"Error accessing database: {e}")
        sys.exit(1)


@cli.command()
@click.option("--session", "-s", "session_id", help="Backup session ID to delete")
@click.pass_context
def delete(ctx: click.Context, session_id: Optional[str]) -> None:
    """
    Delete a backup session.

    :param ctx: Click context
    :param session_id: Backup session ID to delete
    """
    if not session_id:
        click.echo("Error: Delete requires a --session (-s) option.")
        sys.exit(1)

    config_path = ctx.obj["config_path"]
    try:
        config = get_config(config_path)
    except (ConfigurationFileNotFoundError, ConfigurationParseError, ConfigurationValidationError) as e:
        click.echo(f"Configuration error: {e}")
        sys.exit(1)

    try:
        db_manager = DatabaseSessionManager(config.database_path)
        client = DatabaseClient(db_manager)
        if client.delete_session(session_id):
            click.echo(f"Session {session_id} deleted successfully")
        else:
            click.echo(f"Session {session_id} not found")
    except Exception as e:
        click.echo(f"Error accessing database: {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def housekeep(ctx: click.Context) -> None:
    """
    Housekeep old sessions.

    :param ctx: Click context
    """
    config_path = ctx.obj["config_path"]
    try:
        config = get_config(config_path)
    except (ConfigurationFileNotFoundError, ConfigurationParseError, ConfigurationValidationError) as e:
        click.echo(f"Configuration error: {e}")
        sys.exit(1)

    try:
        db_manager = DatabaseSessionManager(config.database_path)
        client = DatabaseClient(db_manager)
        deleted_count = client.delete_sessions_older_than(config.rotate_time)
        click.echo(f"Housekeeping completed. {deleted_count} old sessions removed.")
    except Exception as e:
        click.echo(f"Error during housekeeping: {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def migrate(ctx: click.Context) -> None:
    """
    Database migration.

    :param ctx: Click context
    """
    config_path = ctx.obj["config_path"]
    try:
        config = get_config(config_path)
    except (ConfigurationFileNotFoundError, ConfigurationParseError, ConfigurationValidationError) as e:
        click.echo(f"Configuration error: {e}")
        sys.exit(1)

    try:
        # DatabaseClient constructor already calls create_tables()
        db_manager = DatabaseSessionManager(config.database_path)
        DatabaseClient(db_manager)
        click.echo("Database migration completed successfully.")
    except Exception as e:
        click.echo(f"Error during migration: {e}")
        sys.exit(1)


@cli.command()
def version() -> None:
    """Show version info."""
    click.echo(f"zmbackup version: {ZMBACKUP_VERSION}")


if __name__ == "__main__":
    cli()
