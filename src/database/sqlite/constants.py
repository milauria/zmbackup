class SqlManipulationStrings:
    CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        data TEXT NOT NULL
    )
    """
    INSERT_SESSION_SQL = "INSERT INTO sessions (session_id, data) VALUES (?, ?)"
    SELECT_SESSION_SQL = "SELECT data FROM sessions WHERE session_id = ?"
    UPDATE_SESSION_SQL = "UPDATE sessions SET data = ? WHERE session_id = ?"
    DELETE_SESSION_SQL = "DELETE FROM sessions WHERE session_id = ?"
    SELECT_ALL_SESSIONS_SQL = "SELECT data FROM sessions"
