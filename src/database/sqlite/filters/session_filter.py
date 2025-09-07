import datetime
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple


@dataclass
class SessionFilter:
    session_id: Optional[str] = None
    starting_date: Optional[datetime.datetime] = None
    end_date: Optional[datetime.datetime] = None
    account_email: Optional[str] = None

    def build_select_query(self) -> Tuple[str, List[Any]]:
        base_query = "SELECT data FROM sessions"
        conditions = []
        params = []

        if self.session_id:
            conditions.append("session_id = ?")
            params.append(self.session_id)
        if self.starting_date:
            conditions.append("json_extract(data, '$.starting_date') >= ?")
            params.append(self.starting_date.isoformat())
        if self.end_date:
            conditions.append("json_extract(data, '$.end_date') <= ?")
            params.append(self.end_date.isoformat())
        if self.account_email:
            conditions.append(
                "EXISTS (SELECT 1 FROM json_each(data, '$.accounts') WHERE json_extract(value, '$.email') = ?)"
            )
            params.append(self.account_email)

        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)

        return base_query, params
