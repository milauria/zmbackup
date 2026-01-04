import pytest
from datetime import datetime, timedelta
from src.clients.database_client import DatabaseClient
from src.database.models import BackupSession

@pytest.fixture
def db_client():
    """Fixture for DatabaseClient using in-memory SQLite."""
    client = DatabaseClient("sqlite:///:memory:")
    return client

def test_create_session(db_client):
    """Test session creation."""
    session = db_client.create_session(
        backup_type="full",
        description="Test backup",
        accounts_count=5
    )
    assert session.session_name is not None
    assert session.backup_type == "full"
    assert session.description == "Test backup"
    assert session.accounts_count == 5
    assert session.status == "in_progress"

def test_create_session_collision(db_client):
    """Test session creation collision (highly improbable but covered in code)."""
    # Force a specific start time to generate same UUID
    fixed_time = datetime(2026, 1, 1, 12, 0, 0)
    db_client.create_session("full", "desc1", start=fixed_time)
    
    with pytest.raises(ValueError, match="Session UUID collision"):
        db_client.create_session("full", "desc2", start=fixed_time)

def test_get_session(db_client):
    """Test session retrieval."""
    created = db_client.create_session("full", "Test")
    retrieved = db_client.get_session(created.session_name)
    assert retrieved is not None
    assert retrieved.session_name == created.session_name
    
    assert db_client.get_session("non-existent") is None

def test_list_sessions(db_client):
    """Test listing sessions with various filters."""
    t1 = datetime(2026, 1, 1, 12, 0, 0)
    t2 = datetime(2026, 1, 1, 12, 0, 1)
    t3 = datetime(2026, 1, 1, 12, 0, 2)
    
    s1 = db_client.create_session("full", "Full 1", start=t1)
    db_client.update_session(s1.session_name, status="completed")
    
    s2 = db_client.create_session("incremental", "Incr 1", start=t2)
    # status is in_progress by default
    
    s3 = db_client.create_session("full", "Full 2", start=t3)
    db_client.update_session(s3.session_name, status="failed")
    
    # List all
    assert len(db_client.list_sessions()) == 3
    
    # Filter by type
    assert len(db_client.list_sessions(backup_type="full")) == 2
    assert len(db_client.list_sessions(backup_type="incremental")) == 1
    
    # Filter by status
    assert len(db_client.list_sessions(status="completed")) == 1
    assert len(db_client.list_sessions(status="failed")) == 1
    
    # Limit
    assert len(db_client.list_sessions(limit=1)) == 1

def test_list_sessions_ordering(db_client):
    """Test session listing order."""
    t1 = datetime(2026, 1, 1, 10, 0, 0)
    t2 = datetime(2026, 1, 1, 11, 0, 0)
    db_client.create_session("full", "Full 1", start=t1)
    db_client.create_session("full", "Full 2", start=t2)
    
    # Default desc (newest first)
    sessions = db_client.list_sessions(order_by="start", ascending=False)
    assert sessions[0].description == "Full 2"
    
    # Ascending
    sessions = db_client.list_sessions(order_by="start", ascending=True)
    assert sessions[0].description == "Full 1"

def test_update_session(db_client):
    """Test updating session fields."""
    s = db_client.create_session("full", "Test")
    end_time = datetime.now()
    updated = db_client.update_session(
        s.session_name,
        ending=end_time,
        size="100M",
        status="completed",
        accounts_count=10,
        error_message="None"
    )
    assert updated.ending == end_time
    assert updated.size == "100M"
    assert updated.status == "completed"
    assert updated.accounts_count == 10
    assert updated.error_message == "None"
    
    assert db_client.update_session("non-existent", status="completed") is None

def test_complete_session(db_client):
    """Test marking session as completed."""
    s = db_client.create_session("full", "Test")
    updated = db_client.complete_session(s.session_name, size="500M", accounts_count=20)
    assert updated.status == "completed"
    assert updated.size == "500M"
    assert updated.accounts_count == 20
    assert updated.ending is not None

def test_fail_session(db_client):
    """Test marking session as failed."""
    s = db_client.create_session("full", "Test")
    updated = db_client.fail_session(s.session_name, error_message="Disk full")
    assert updated.status == "failed"
    assert updated.error_message == "Disk full"
    assert updated.ending is not None

def test_delete_session(db_client):
    """Test deleting a session."""
    s = db_client.create_session("full", "Test")
    assert db_client.delete_session(s.session_name) is True
    assert db_client.get_session(s.session_name) is None
    assert db_client.delete_session(s.session_name) is False

def test_delete_sessions_by_type(db_client):
    """Test deleting sessions by type."""
    t1 = datetime.now() - timedelta(seconds=10)
    t2 = datetime.now()
    db_client.create_session("full", "F1", start=t1)
    db_client.create_session("full", "F2", start=t2)
    db_client.create_session("incremental", "I1")
    
    count = db_client.delete_sessions_by_type("full")
    assert count == 2
    assert len(db_client.list_sessions()) == 1

def test_delete_sessions_older_than(db_client):
    """Test deleting old sessions."""
    old_time = datetime.now() - timedelta(days=10)
    new_time = datetime.now()
    
    db_client.create_session("full", "Old", start=old_time)
    db_client.create_session("full", "New", start=new_time)
    
    count = db_client.delete_sessions_older_than(5)
    assert count == 1
    sessions = db_client.list_sessions()
    assert len(sessions) == 1
    assert sessions[0].description == "New"

def test_get_statistics(db_client):
    """Test statistics aggregation."""
    t1 = datetime(2026, 1, 1, 13, 0, 0)
    t2 = datetime(2026, 1, 1, 13, 0, 1)
    t3 = datetime(2026, 1, 1, 13, 0, 2)
    t4 = datetime(2026, 1, 1, 13, 0, 3)
    
    s1 = db_client.create_session("full", "F1", start=t1)
    db_client.update_session(s1.session_name, status="completed")
    
    s2 = db_client.create_session("full", "F2", start=t2)
    db_client.update_session(s2.session_name, status="failed")
    
    s3 = db_client.create_session("incremental", "I1", start=t3)
    db_client.update_session(s3.session_name, status="completed")
    
    db_client.create_session("mailbox", "M1", start=t4)
    # M1 status is in_progress by default
    
    stats = db_client.get_statistics()
    assert stats["total"] == 4
    assert stats["by_type"]["full"] == 2
    assert stats["by_type"]["incremental"] == 1
    assert stats["by_type"]["mailbox"] == 1
    assert stats["by_status"]["completed"] == 2
    assert stats["by_status"]["failed"] == 1
    assert stats["by_status"]["in_progress"] == 1
