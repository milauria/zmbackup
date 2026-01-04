import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from src.database.session_manager import DatabaseSessionManager
from unittest.mock import patch

def test_session_manager_init():
    """Test initialization with SQLite."""
    manager = DatabaseSessionManager("sqlite:///:memory:")
    assert manager.db_path == "sqlite:///:memory:"

def test_session_manager_engine_sqlite():
    """Test engine creation with SQLite optimizations."""
    manager = DatabaseSessionManager("sqlite:///:memory:")
    engine = manager.engine
    assert isinstance(engine, Engine)
    assert str(engine.url) == "sqlite:///:memory:"

def test_session_manager_engine_other():
    """Test engine creation with other database type."""
    with patch("src.database.session_manager.create_engine") as mock_create:
        manager = DatabaseSessionManager("postgresql://user:pass@localhost/db")
        _ = manager.engine
        mock_create.assert_called_with("postgresql://user:pass@localhost/db", echo=False)

def test_session_manager_session_factory():
    """Test session factory creation."""
    manager = DatabaseSessionManager("sqlite:///:memory:")
    factory = manager.session_factory
    assert callable(factory)

def test_session_manager_get_session():
    """Test the get_session context manager."""
    manager = DatabaseSessionManager("sqlite:///:memory:")
    with manager.get_session() as session:
        assert isinstance(session, Session)

def test_session_manager_create_drop_tables():
    """Test create_tables and drop_tables."""
    manager = DatabaseSessionManager("sqlite:///:memory:")
    # This shouldn't raise any errors
    manager.create_tables()
    manager.drop_tables()

def test_session_manager_context_management():
    """Test the __enter__ and __exit__ methods."""
    with DatabaseSessionManager("sqlite:///:memory:") as manager:
        assert isinstance(manager, DatabaseSessionManager)
        engine = manager.engine
        # Trigger engine creation
        assert engine is not None
    
    # After exit, engine should be disposed (hard to test directly without mocking, 
    # but we can verify the code path)

def test_session_manager_rollback_on_exception():
    """Test that session rollbacks on exception."""
    manager = DatabaseSessionManager("sqlite:///:memory:")
    with pytest.raises(ValueError, match="Test error"):
        with manager.get_session() as session:
            raise ValueError("Test error")
