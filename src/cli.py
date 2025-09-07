import click
from src.database.sqlite.sqlite import SQLiteManager
from src.database.sqlite.models import Session
from prettytable import PrettyTable
import datetime

@click.group()
def cli():
    """A CLI tool for managing zmbackup sessions."""
    pass

@cli.command("list")
@click.option("-l", "--list", is_flag=True, help="List all backup sessions.")
def list_sessions(list):
    """Lists all backup sessions."""
    if list:
        manager = SQLiteManager()
        sessions = manager.get_sessions(filters=None) # No filters for listing all

        table = PrettyTable()
        table.field_names = ["Session Name", "Start", "Ending", "Size", "Description"]
        table.align = "l"

        for session in sessions:
            # Format session name to match example: type-YYYYMMDDHHMMSS
            # For now, we'll use a generic "session" prefix and the starting date
            session_name_prefix = "full-" if session.description == "Full Account" else "mbox-" if session.description == "Mailbox" else "session-"
            session_name = f"{session_name_prefix}{session.starting_date.strftime('%Y%m%d%H%M%S')}"
            start_date = session.starting_date.strftime("%m/%d/%Y")
            end_date = session.end_date.strftime("%m/%d/%Y")
            size = f"{session.size}K"
            description = session.description if session.description else "N/A"
            table.add_row([session_name, start_date, end_date, size, description])
        
        click.echo(table)
