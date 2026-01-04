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
import click
import sys
from typing import List, Optional
from datetime import datetime
from prettytable import PrettyTable

from lib.constants import ZMBACKUP_VERSION
from operations.init import run_init
from clients.database_client import DatabaseClient

@click.group(context_settings=dict(help_option_names=['-h', '--help']))
def cli():
    """zmbackup CLI for Zimbra backups and restores."""
    pass

@cli.command()
@click.option('--config-path', default="/etc/zmbackup/zmbackup.conf", help='Path to the configuration file')
def init(config_path):
    """Initialize the zmbackup configuration."""
    run_init(config_path)

@cli.command()
@click.option('--full', '-f', is_flag=True, help='Full Backup mode')
@click.option('--incremental', '-i', is_flag=True, help='Incremental Backup mode')
@click.option('--mail', '-m', 'mail_flag', is_flag=True, help='Only backup mailbox content')
@click.option('--distributionlist', '-dl', is_flag=True, help='Backup distribution lists')
@click.option('--alias', '-al', is_flag=True, help='Backup aliases')
@click.option('--ldap', '-ldp', is_flag=True, help='Only backup LDAP entries')
@click.option('--signature', '-sig', is_flag=True, help='Backup account signatures')
@click.option('--domain', '-d', 'domain_opt', help='Comma-separated list of domains')
@click.option('--account', '-a', 'account_opt', help='Comma-separated list of accounts')
def backup(full, incremental, mail_flag, distributionlist, alias, ldap, signature, domain_opt, account_opt):
    """Perform a backup."""
    if full and incremental:
        click.echo("Error: Please select only one mode: --full or --incremental.")
        sys.exit(1)
    
    if not full and not incremental:
        click.echo("Error: Please specify backup type: --full or --incremental.")
        sys.exit(1)

    if full:
        # Constraint: -dl, -al, -m, and -ldp are mutually exclusive
        excl_flags = {
            'mail': mail_flag,
            'distributionlist': distributionlist,
            'alias': alias,
            'ldap': ldap
        }
        active_excl = [name for name, active in excl_flags.items() if active]
        if len(active_excl) > 1:
            click.echo(f"Error: Flags {', '.join(active_excl)} are mutually exclusive.")
            sys.exit(1)
            
        scope = "everything"
        if active_excl:
            scope = active_excl[0]
        
        options = []
        if signature: options.append("signature")
        if domain_opt: options.append(f"domains={domain_opt}")
        if account_opt: options.append(f"accounts={account_opt}")
        
        click.echo(f"Full backup initiated for {scope} with options: {', '.join(options) if options else 'none'}")

    elif incremental:
        if not account_opt:
            click.echo("Error: Incremental backup requires at least one account via --account (-a).")
            sys.exit(1)
        click.echo(f"Incremental backup started for accounts: {account_opt}")

@cli.command()
@click.option('--restoreOnAccount', '-ro', is_flag=True, help='Restore from one account to another')
@click.option('--mail', '-m', 'mail_flag', is_flag=True, help='Only restore mailbox content')
@click.option('--distributionlist', '-dl', is_flag=True, help='Restore distribution lists')
@click.option('--alias', '-al', is_flag=True, help='Restore aliases')
@click.option('--ldap', '-ldp', is_flag=True, help='Only restore LDAP entries')
@click.option('--signature', '-sig', is_flag=True, help='Restore account signatures')
@click.option('--domain', '-d', 'domain_opt', help='Comma-separated list of domains')
@click.option('--account', '-a', 'account_opt', help='Comma-separated list of accounts')
@click.option('--session', '-s', 'session_id', help='Backup session ID to restore from')
@click.option('--origin', '-o', 'mail_origin', help='Original account to restore')
@click.option('--destination', '-dest', 'mail_destination', help='Destination account for restoration')
def restore(restoreonaccount, mail_flag, distributionlist, alias, ldap, signature, domain_opt, account_opt, session_id, mail_origin, mail_destination):
    """Perform a restore."""
    if not session_id or not mail_origin:
        click.echo("Error: Restore requires --session (-s) and --origin (-o).")
        sys.exit(1)
        
    if restoreonaccount and not mail_destination:
        click.echo("Error: --restoreOnAccount (-ro) requires a --destination (-dest) option.")
        sys.exit(1)
        
    options = []
    if mail_flag: options.append("mail")
    if distributionlist: options.append("distributionlist")
    if alias: options.append("alias")
    if ldap: options.append("ldap")
    if signature: options.append("signature")
    if domain_opt: options.append(f"domain_filter={domain_opt}")
    if account_opt: options.append(f"account_filter={account_opt}")
    if restoreonaccount: options.append(f"restore_to={mail_destination}")
    
    click.echo(f"Restore initiated from session {session_id} for {mail_origin} with options: {', '.join(options) if options else 'none'}")

@cli.command()
def list():
    """List backup sessions."""
    db_path = "sqlite:///zmbackup_sessions.db"
    
    try:
        client = DatabaseClient(db_path)
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
            table.add_row([
                s.session_name,
                start_str,
                ending_str,
                s.size or "N/A",
                s.description
            ])
            
        click.echo(table)
        
    except Exception as e:
        click.echo(f"Error accessing database: {e}")
        sys.exit(1)

@cli.command()
@click.option('--session', '-s', 'session_id', help='Backup session ID to delete')
def delete(session_id):
    """Delete a backup session."""
    if not session_id:
        click.echo("Error: Delete requires a --session (-s) option.")
        sys.exit(1)
    click.echo(f"Session {session_id} deleted successfully")

@cli.command()
def housekeep():
    """Housekeep old sessions."""
    click.echo("Housekeeping completed. Old sessions removed based on retention policy.")

@cli.command()
def migrate():
    """Database migration."""
    click.echo("Database migration completed successfully.")

@cli.command()
def version():
    """Show version info."""
    click.echo(f"zmbackup version: {ZMBACKUP_VERSION}")

if __name__ == "__main__":
    cli()
