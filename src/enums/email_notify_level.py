from enum import Enum


class EmailNotifyLevel(Enum):  # pragma: no cover
    """Email notification levels."""

    ALL = "all"
    START = "start"
    FINISH = "finish"
    ERROR = "error"
    NONE = "none"
