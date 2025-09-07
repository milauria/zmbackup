import datetime
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.database.sqlite.models.account import Account


@dataclass
class Session:
    session_id: uuid.UUID = field(default_factory=uuid.uuid4)
    starting_date: datetime.datetime = field(default_factory=datetime.datetime.now)
    end_date: datetime.datetime = field(default_factory=datetime.datetime.now)
    accounts: List[Account] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": str(self.session_id),
            "starting_date": self.starting_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "accounts": [account.__dict__ for account in self.accounts],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        return cls(
            session_id=uuid.UUID(data["session_id"]),
            starting_date=datetime.datetime.fromisoformat(data["starting_date"]),
            end_date=datetime.datetime.fromisoformat(data["end_date"]),
            accounts=[Account(**account_data) for account_data in data["accounts"]],
        )
