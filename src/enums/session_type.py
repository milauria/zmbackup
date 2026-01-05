from enum import Enum


class SessionType(Enum):  # pragma: no cover
    """Session storage backend types."""

    TXT = "TXT"
    SQLITE3 = "SQLITE3"
