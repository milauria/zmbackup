"""SQLAlchemy ORM models for zmbackup."""

from datetime import datetime
from typing import Optional
from uuid import NAMESPACE_DNS, uuid5

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


def generate_session_uuid(backup_type: str, timestamp: datetime) -> str:
    """
    Generate a deterministic UUID for a backup session.

    Uses UUID v5 (name-based with SHA-1 hash) to create a unique identifier
    from the backup type and timestamp combination.

    :param backup_type: Type of backup ('full', 'incremental', 'mailbox')
    :param timestamp: Backup start timestamp
    :return: Deterministic UUID string
    """
    timestamp_str = timestamp.strftime("%Y%m%d%H%M%S")
    source_string = f"{backup_type}-{timestamp_str}"

    # Generate UUID v5 from source string
    session_uuid = uuid5(NAMESPACE_DNS, source_string)

    return str(session_uuid)


class BackupSession(Base):
    """
    ORM model for backup sessions.

    Represents a single backup execution with metadata about the backup
    process and results.
    """

    __tablename__ = "backup_sessions"

    # Primary identifier
    session_name: Mapped[str] = mapped_column(
        String(100), primary_key=True, comment="Unique session identifier: {type}-{timestamp}"
    )

    # Temporal information
    start: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="Backup start timestamp"
    )
    ending: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="Backup completion timestamp")

    # Backup metadata
    backup_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Backup type (full, incremental, mailbox)"
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False, comment="Human-readable backup description")

    # Size and statistics
    size: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="Human-readable size string (e.g., '1.2 GB')"
    )
    accounts_count: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Number of accounts backed up"
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="in_progress",
        comment="Session status (in_progress, completed, failed)",
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Error details if backup failed")

    # Timestamps for record maintenance
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="Database record creation timestamp"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
        comment="Database record update timestamp",
    )

    def __repr__(self) -> str:
        """
        Return string representation of the model.

        :return: String representation
        """
        return (
            f"<BackupSession(session_name='{self.session_name}', "
            f"backup_type='{self.backup_type}', status='{self.status}')>"
        )

    def to_dict(self) -> dict:
        """
        Convert model to dictionary for serialization.

        :return: Dictionary representation of the session
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
        }
