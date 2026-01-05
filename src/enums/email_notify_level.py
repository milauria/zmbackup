from enum import Enum


class EmailNotifyLevel(Enum):
    """Email notification levels."""

    ALL = "all"
    START = "start"
    FINISH = "finish"
    ERROR = "error"
    NONE = "none"
