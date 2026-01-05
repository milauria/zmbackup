"""High-level database client for backup session management."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import asc, desc
from sqlalchemy.exc import IntegrityError

from src.database.models import BackupSession, generate_session_uuid
from src.database.session_manager import DatabaseSessionManager


class DatabaseClient:
    """
    Repository for backup session CRUD operations.

    Provides high-level interface for managing backup sessions with
    automatic connection handling and error management.
    """

    def __init__(self, db_manager: DatabaseSessionManager, auto_create_tables: bool = True):
        """
        Initialize the database client.

        :param db_manager: DatabaseSessionManager instance for session handling
        :param auto_create_tables: Whether to auto-create tables if they don't exist
        """
        self.db_manager = db_manager

        if auto_create_tables:
            self.db_manager.create_tables()

    def create_session(
        self,
        backup_type: str,
        description: str,
        start: Optional[datetime] = None,
        accounts_count: Optional[int] = None,
    ) -> BackupSession:
        """
        Create a new backup session record.

        Automatically generates a UUID-based session name from the backup type
        and timestamp.

        :param backup_type: Type of backup ('full', 'incremental', 'mailbox')
        :param description: Human-readable description
        :param start: Backup start time (defaults to now)
        :param accounts_count: Number of accounts to backup
        :return: Created BackupSession instance with generated session_name UUID
        :raises ValueError: If session generation fails or UUID collision (extremely rare)
        """
        if start is None:
            start = datetime.now()

        # Generate UUID-based session name
        session_name = generate_session_uuid(backup_type, start)

        session_record = BackupSession(
            session_name=session_name,
            start=start,
            backup_type=backup_type,
            description=description,
            status="in_progress",
            accounts_count=accounts_count,
        )

        with self.db_manager.get_session() as session:
            try:
                session.add(session_record)
                session.commit()
                session.refresh(session_record)
                return session_record
            except IntegrityError as e:
                raise ValueError(f"Session UUID collision (extremely rare): '{session_name}'") from e

    def get_session(self, session_name: str) -> Optional[BackupSession]:
        """
        Retrieve a backup session by name.

        :param session_name: Session identifier to retrieve
        :return: BackupSession instance or None if not found
        """
        with self.db_manager.get_session() as session:
            return session.query(BackupSession).filter_by(session_name=session_name).first()

    def list_sessions(
        self,
        backup_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        order_by: str = "start",
        ascending: bool = False,
    ) -> List[BackupSession]:
        """
        List backup sessions with optional filtering.

        :param backup_type: Filter by backup type ('full', 'incremental', 'mailbox')
        :param status: Filter by status ('in_progress', 'completed', 'failed')
        :param limit: Maximum number of results to return
        :param order_by: Field to sort by ('start', 'ending', 'session_name')
        :param ascending: Sort order (True for ascending, False for descending)
        :return: List of BackupSession instances matching criteria
        """
        with self.db_manager.get_session() as session:
            query = session.query(BackupSession)

            # Apply filters
            if backup_type:
                query = query.filter_by(backup_type=backup_type)
            if status:
                query = query.filter_by(status=status)

            # Apply sorting
            order_func = asc if ascending else desc
            order_field = getattr(BackupSession, order_by, BackupSession.start)
            query = query.order_by(order_func(order_field))

            # Apply limit
            if limit:
                query = query.limit(limit)

            return list(query.all())

    def update_session(
        self,
        session_name: str,
        ending: Optional[datetime] = None,
        size: Optional[str] = None,
        status: Optional[str] = None,
        accounts_count: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> Optional[BackupSession]:
        """
        Update an existing backup session.

        :param session_name: Session identifier to update
        :param ending: Backup completion timestamp
        :param size: Human-readable size string
        :param status: New status value
        :param accounts_count: Updated account count
        :param error_message: Error details if failed
        :return: Updated BackupSession or None if not found
        """
        with self.db_manager.get_session() as session:
            backup_session = session.query(BackupSession).filter_by(session_name=session_name).first()

            if not backup_session:
                return None

            # Update provided fields
            if ending is not None:
                backup_session.ending = ending
            if size is not None:
                backup_session.size = size
            if status is not None:
                backup_session.status = status
            if accounts_count is not None:
                backup_session.accounts_count = accounts_count
            if error_message is not None:
                backup_session.error_message = error_message

            session.commit()
            session.refresh(backup_session)
            return backup_session

    def complete_session(
        self,
        session_name: str,
        size: str,
        accounts_count: Optional[int] = None,
    ) -> Optional[BackupSession]:
        """
        Mark a backup session as completed.

        Convenience method that sets ending time and status to 'completed'.

        :param session_name: Session identifier to complete
        :param size: Final backup size
        :param accounts_count: Final account count
        :return: Updated BackupSession or None if not found
        """
        return self.update_session(
            session_name=session_name,
            ending=datetime.now(),
            size=size,
            status="completed",
            accounts_count=accounts_count,
        )

    def fail_session(
        self,
        session_name: str,
        error_message: str,
    ) -> Optional[BackupSession]:
        """
        Mark a backup session as failed.

        :param session_name: Session identifier to mark as failed
        :param error_message: Error description
        :return: Updated BackupSession or None if not found
        """
        return self.update_session(
            session_name=session_name,
            ending=datetime.now(),
            status="failed",
            error_message=error_message,
        )

    def delete_session(self, session_name: str) -> bool:
        """
        Delete a backup session record.

        :param session_name: Session identifier to delete
        :return: True if deleted, False if not found
        """
        with self.db_manager.get_session() as session:
            backup_session = session.query(BackupSession).filter_by(session_name=session_name).first()

            if not backup_session:
                return False

            session.delete(backup_session)
            session.commit()
            return True

    def delete_sessions_by_type(self, backup_type: str) -> int:
        """
        Delete all sessions of a specific backup type.

        :param backup_type: Type of backups to delete
        :return: Number of sessions deleted
        """
        with self.db_manager.get_session() as session:
            result = session.query(BackupSession).filter_by(backup_type=backup_type).delete()
            session.commit()
            return int(result)

    def delete_sessions_older_than(self, days: int) -> int:
        """
        Delete sessions older than specified number of days.

        Used for housekeeping operations based on retention policy.

        :param days: Delete sessions older than this many days
        :return: Number of sessions deleted
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        with self.db_manager.get_session() as session:
            result = session.query(BackupSession).filter(BackupSession.start < cutoff_date).delete()
            session.commit()
            return int(result)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get aggregate statistics about backup sessions.

        :return: Dictionary with statistics (total, by type, by status)
        """
        with self.db_manager.get_session() as session:
            total = session.query(BackupSession).count()

            # Count by backup type
            full = session.query(BackupSession).filter_by(backup_type="full").count()
            incremental = session.query(BackupSession).filter_by(backup_type="incremental").count()
            mailbox = session.query(BackupSession).filter_by(backup_type="mailbox").count()

            # Count by status
            completed = session.query(BackupSession).filter_by(status="completed").count()
            in_progress = session.query(BackupSession).filter_by(status="in_progress").count()
            failed = session.query(BackupSession).filter_by(status="failed").count()

            return {
                "total": total,
                "by_type": {
                    "full": full,
                    "incremental": incremental,
                    "mailbox": mailbox,
                },
                "by_status": {
                    "completed": completed,
                    "in_progress": in_progress,
                    "failed": failed,
                },
            }
