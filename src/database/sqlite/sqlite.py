import json
import sqlite3
from functools import cached_property
from typing import List, Optional

from src.database.sqlite.constants import SqlManipulationStrings
from src.database.sqlite.models import Session
from src.database.sqlite.filters.session_filter import SessionFilter


class SQLiteManager:
    def __init__(self, db_path: str = "sessions.db"):
        self.db_path = db_path
        self._create_table()

    @cached_property
    def _connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _create_table(self):
        with self._connection as conn:
            cursor = conn.cursor()
            cursor.execute(SqlManipulationStrings.CREATE_TABLE_SQL)
            conn.commit()

    def create_session(self, session: Session):
        with self._connection as conn:
            cursor = conn.cursor()
            cursor.execute(
                SqlManipulationStrings.INSERT_SESSION_SQL,
                (str(session.session_id), json.dumps(session.to_dict())),
            )
            conn.commit()

    def get_session(self, session_id: str) -> Optional[Session]:
        sessions = self.get_sessions(SessionFilter(session_id=session_id))
        return sessions[0] if sessions else None

    def get_sessions(self, filters: SessionFilter) -> List[Session]:
        with self._connection as conn:
            cursor = conn.cursor()
            query, params = filters.build_select_query()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [Session.from_dict(json.loads(row[0])) for row in rows]

    def update_session(self, session: Session):
        with self._connection as conn:
            cursor = conn.cursor()
            cursor.execute(
                SqlManipulationStrings.UPDATE_SESSION_SQL,
                (json.dumps(session.to_dict()), str(session.session_id)),
            )
            conn.commit()

    def delete_session(self, session_id: str):
        with self._connection as conn:
            cursor = conn.cursor()
            cursor.execute(SqlManipulationStrings.DELETE_SESSION_SQL, (session_id,))
            conn.commit()
