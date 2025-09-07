from dataclasses import dataclass


@dataclass
class Account:
    email: str
    size: int  # size in megabytes
