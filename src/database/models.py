"""SQLAlchemy ORM models for zmbackup."""

from datetime import datetime
from typing import Optional
from uuid import NAMESPACE_DNS, uuid5

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


def generate_session_uuid(backup_type: str, timestamp: datetime) -> str:
    """
    Generate a deterministic UUID for a backup session.

    Uses UUID v5 (name-based with SHA-1 hash) to create a unique identifier
    from the backup type and timestamp combination.

    Args:
        backup_type: Type of backup ('full', 'incremental', 'mailbox')
        timestamp: Backup start timestamp

    Returns:
        UUID string in format: 018b2f19-e79e-7d6a-a56d-29feb6211b04
    """
    # Create source string: {type}-{timestamp}
    timestamp_str = timestamp.strftime("%Y%m%d%H%M%S")
    source_string = f"{backup_type}-{timestamp_str}"

    # Generate UUID v5 from source string
    session_uuid = uuid5(NAMESPACE_DNS, source_string)
    return str(session_uuid)


class BackupSession(Base):
    """
    ORM model for backup sessions.

    Represents a single backup execution with metadata about the backup
    process, including timing, size, and status information.
    """

    __tablename__ = "backup_sessions"

    # Primary identifier
    session_name = Column(String(100), primary_key=True, comment="Unique session identifier: {type}-{timestamp}")

    # Temporal information
    start = Column(DateTime, nullable=False, comment="Backup start timestamp")
    ending = Column(DateTime, nullable=True, comment="Backup completion timestamp")

    # Backup metadata
    backup_type = Column(String(20), nullable=False, comment="Type: full, incremental, or mailbox")
    description = Column(String(255), nullable=False, comment="Human-readable backup description")

    # Size and statistics
    size = Column(String(20), nullable=True, comment="Human-readable size (e.g., '76K', '1.2G')")
    accounts_count = Column(Integer, nullable=True, comment="Number of accounts backed up")

    # Status tracking
    status = Column(
        String(20),
        nullable=False,
        default="in_progress",
        server_default="in_progress",
        comment="Status: in_progress, completed, or failed",
    )
    error_message = Column(Text, nullable=True, comment="Error details if backup failed")

    # Timestamps for record maintenance
    created_at = Column(DateTime, default=datetime.now, nullable=False, comment="Record creation timestamp")
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False, comment="Record last update timestamp"
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<BackupSession(session_name='{self.session_name}', "
            f"type='{self.backup_type}', status='{self.status}')>"
        )

    def to_dict(self) -> dict:
        """
        Convert model to dictionary for serialization.

        Returns:
            Dictionary representation of the backup session.
        """
        return {
            "session_name": self.session_name,
            "start": self.start.isoformat() if self.start else None,
            "ending": self.ending.isoformat() if self.ending else None,
            "backup_type": self.backup_type,
            "description": self.description,
            "size": self.size,
            "accounts_count": self.accounts_count,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
