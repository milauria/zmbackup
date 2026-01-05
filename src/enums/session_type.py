from enum import Enum


class SessionType(Enum):
    """Session storage backend types."""

    TXT = "TXT"
    SQLITE3 = "SQLITE3"
