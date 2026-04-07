from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from database.models import BackupSession, generate_session_uuid


def create_test_session(
    backup_type: str = "full",
    description: str = "Test backup",
    start: Optional[datetime] = None,
    ending: Optional[datetime] = None,
    size: Optional[str] = None,
    status: str = "completed",
    accounts_count: Optional[int] = None,
    error_message: Optional[str] = None,
    unique_id: Optional[int] = None,
) -> BackupSession:
    """
    Factory function to create test BackupSession instances.

    This function helps in generating consistent BackupSession objects for testing
    purposes, automatically generating session names using the standard format.

    :param backup_type: Type of backup (e.g., 'full', 'incremental', 'mailbox')
    :param description: Human-readable description of the backup
    :param start: Start timestamp (defaults to current time if None)
    :param ending: End timestamp (optional)
    :param size: Human-readable size string (optional, e.g., '2.5 GB')
    :param status: Session status (e.g., 'completed', 'failed', 'in_progress')
    :param accounts_count: Number of accounts processed (optional)
    :param error_message: Error message if the session failed (optional)
    :param unique_id: Optional offset for timestamp to ensure unique UUID (optional)
    :return: A new BackupSession instance
    """
    if start is None:
        start = datetime.now()

    if unique_id is not None:
        start = start + timedelta(seconds=unique_id)

    session_name = generate_session_uuid(backup_type, start)

    return BackupSession(
        session_name=session_name,
        start=start,
        ending=ending,
        backup_type=backup_type,
        description=description,
        size=size,
        status=status,
        accounts_count=accounts_count,
        error_message=error_message,
    )


def create_test_session_from_dict(data: Dict[str, Any]) -> BackupSession:
    """
    Create BackupSession from dictionary (e.g., from behave table).

    This helper facilitates creating sessions directly from Gherkin table rows
    by handling string-to-datetime conversions and providing defaults.

    :param data: Dictionary with session attributes
    :return: A new BackupSession instance
    """
    # Parse datetime strings if provided
    start = None
    if "start" in data and data["start"]:
        start = (
            datetime.fromisoformat(data["start"])
            if isinstance(data["start"], str)
            else data["start"]
        )

    ending = None
    if "ending" in data and data["ending"]:
        ending = (
            datetime.fromisoformat(data["ending"])
            if isinstance(data["ending"], str)
            else data["ending"]
        )

    return create_test_session(
        backup_type=data.get("backup_type", "full"),
        description=data.get("description", "Test backup"),
        start=start,
        ending=ending,
        size=data.get("size"),
        status=data.get("status", "completed"),
        accounts_count=data.get("accounts_count"),
        error_message=data.get("error_message"),
    )


__all__ = ["create_test_session", "create_test_session_from_dict"]
