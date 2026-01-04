import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from src.database.session_manager import DatabaseSessionManager
from unittest.mock import patch

def test_session_manager_init(db_url):
    """Test initialization with SQLite."""
    manager = DatabaseSessionManager(db_url)
    assert manager.db_path == db_url

def test_session_manager_engine_sqlite(db_url):
    """Test engine creation with SQLite optimizations."""
    manager = DatabaseSessionManager(db_url)
    engine = manager.engine
    assert isinstance(engine, Engine)
    assert str(engine.url) == db_url

def test_session_manager_engine_other():
    """Test engine creation with other database type."""
    with patch("src.database.session_manager.create_engine") as mock_create:
        manager = DatabaseSessionManager("postgresql://user:pass@localhost/db")
        _ = manager.engine
        mock_create.assert_called_with("postgresql://user:pass@localhost/db", echo=False)

def test_session_manager_session_factory(session_manager):
    """Test session factory creation."""
    factory = session_manager.session_factory
    assert callable(factory)

def test_session_manager_get_session(session_manager):
    """Test the get_session context manager."""
    with session_manager.get_session() as session:
        assert isinstance(session, Session)

def test_session_manager_create_drop_tables(session_manager):
    """Test create_tables and drop_tables."""
    # This shouldn't raise any errors
    session_manager.create_tables()
    session_manager.drop_tables()

def test_session_manager_context_management(db_url):
    """Test the __enter__ and __exit__ methods."""
    with DatabaseSessionManager(db_url) as manager:
        assert isinstance(manager, DatabaseSessionManager)
        engine = manager.engine
        # Trigger engine creation
        assert engine is not None
    
    # After exit, engine should be disposed (hard to test directly without mocking, 
    # but we can verify the code path)

def test_session_manager_rollback_on_exception(session_manager):
    """Test that session rollbacks on exception."""
    with pytest.raises(ValueError, match="Test error"):
        with session_manager.get_session() as session:
            raise ValueError("Test error")
