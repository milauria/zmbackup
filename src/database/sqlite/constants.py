class SqlManipulationStrings:
    CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        data TEXT NOT NULL,
        size INTEGER DEFAULT 0,
        description TEXT DEFAULT ''
    )
    """
    INSERT_SESSION_SQL = "INSERT INTO sessions (session_id, data, size, description) VALUES (?, ?, ?, ?)"
    SELECT_SESSION_SQL = "SELECT data, size, description FROM sessions WHERE session_id = ?"
    UPDATE_SESSION_SQL = "UPDATE sessions SET data = ?, size = ?, description = ? WHERE session_id = ?"
    DELETE_SESSION_SQL = "DELETE FROM sessions WHERE session_id = ?"
    SELECT_ALL_SESSIONS_SQL = "SELECT data, size, description FROM sessions"
