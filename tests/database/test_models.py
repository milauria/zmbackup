import pytest
from datetime import datetime
from src.database.models import BackupSession, generate_session_uuid

@pytest.mark.parametrize("backup_type, timestamp, expected_len", [
    ("full", datetime(2026, 1, 1, 12, 0, 0), 36),
    ("incremental", datetime(2026, 1, 1, 12, 0, 0), 36),
    ("mailbox", datetime(2026, 1, 1, 12, 0, 0), 36),
])
def test_generate_session_uuid_parametrized(backup_type, timestamp, expected_len):
    """Test deterministic UUID generation with different backup types."""
    uuid1 = generate_session_uuid(backup_type, timestamp)
    uuid2 = generate_session_uuid(backup_type, timestamp)
    
    # Same inputs should produce same UUID
    assert uuid1 == uuid2
    # Check format
    assert len(uuid1) == expected_len
    assert "-" in uuid1

def test_generate_session_uuid_uniqueness():
    """Test that different inputs produce different UUIDs."""
    ts = datetime(2026, 1, 1, 12, 0, 0)
    uuid_full = generate_session_uuid("full", ts)
    uuid_incr = generate_session_uuid("incremental", ts)
    uuid_diff_time = generate_session_uuid("full", datetime(2026, 1, 1, 12, 0, 1))
    
    assert uuid_full != uuid_incr
    assert uuid_full != uuid_diff_time

def test_backup_session_creation():
    """Test BackupSession model creation and default values."""
    start_time = datetime.now()
    session = BackupSession(
        session_name="test-session",
        start=start_time,
        backup_type="full",
        description="Test description",
        status="in_progress"
    )
    
    assert session.session_name == "test-session"
    assert session.start == start_time
    assert session.backup_type == "full"
    assert session.description == "Test description"
    assert session.status == "in_progress"
    assert session.size is None
    assert session.accounts_count is None
    assert session.error_message is None

def test_backup_session_repr():
    """Test string representation of BackupSession."""
    session = BackupSession(
        session_name="test-session",
        backup_type="full",
        status="completed"
    )
    repr_str = repr(session)
    assert "test-session" in repr_str
    assert "full" in repr_str
    assert "completed" in repr_str

def test_backup_session_to_dict():
    """Test to_dict method serialization."""
    start_time = datetime(2026, 1, 1, 12, 0, 0)
    end_time = datetime(2026, 1, 1, 13, 0, 0)
    created_at = datetime(2026, 1, 1, 11, 0, 0)
    updated_at = datetime(2026, 1, 1, 11, 30, 0)
    
    session = BackupSession(
        session_name="test-session",
        start=start_time,
        ending=end_time,
        backup_type="full",
        description="Test description",
        size="1.2G",
        accounts_count=10,
        status="completed",
        error_message="None",
        created_at=created_at,
        updated_at=updated_at
    )
    
    data = session.to_dict()
    
    assert data["session_name"] == "test-session"
    assert data["start"] == start_time.isoformat()
    assert data["ending"] == end_time.isoformat()
    assert data["backup_type"] == "full"
    assert data["description"] == "Test description"
    assert data["size"] == "1.2G"
    assert data["accounts_count"] == 10
    assert data["status"] == "completed"
    assert data["error_message"] == "None"
    assert data["created_at"] == created_at.isoformat()
    assert data["updated_at"] == updated_at.isoformat()

def test_backup_session_to_dict_none_values():
    """Test to_dict with None values."""
    session = BackupSession(
        session_name="test",
        backup_type="full",
        description="desc"
    )
    # Ensure values are None
    session.start = None
    session.created_at = None
    session.updated_at = None
    
    data = session.to_dict()
    assert data["start"] is None
    assert data["ending"] is None
    assert data["created_at"] is None
    assert data["updated_at"] is None
