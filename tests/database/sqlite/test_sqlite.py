import datetime
import os
import uuid

import pytest

from src.database.sqlite.constants import SqlManipulationStrings
from src.database.sqlite.filters.session_filter import SessionFilter
from src.database.sqlite.models import Account, Session
from src.database.sqlite.sqlite import SQLiteManager


@pytest.fixture(autouse=True)
def setup_database():
    db_path = "test_sessions.db"
    manager = SQLiteManager(db_path)
    session_id = uuid.uuid4()
    starting_date = datetime.datetime.now()
    end_date = datetime.datetime.now() + datetime.timedelta(hours=1)
    accounts = [Account(email="test@example.com", size=100)]
    session = Session(
        session_id=session_id,
        starting_date=starting_date,
        end_date=end_date,
        accounts=accounts,
    )
    yield manager, session, session_id
    if os.path.exists(db_path):
        os.remove(db_path)


def test_create_session(setup_database):
    manager, session, session_id = setup_database
    manager.create_session(session)
    retrieved_session = manager.get_session(str(session_id))
    assert retrieved_session is not None
    assert retrieved_session.session_id == session.session_id
    assert retrieved_session.accounts[0].email == "test@example.com"


def test_get_session(setup_database):
    manager, session, session_id = setup_database
    manager.create_session(session)
    retrieved_session = manager.get_session(str(session_id))
    assert retrieved_session is not None
    assert retrieved_session.session_id == session.session_id

    non_existent_session = manager.get_session(str(uuid.uuid4()))
    assert non_existent_session is None


def test_update_session(setup_database):
    manager, session, session_id = setup_database
    manager.create_session(session)
    updated_accounts = [Account(email="updated@example.com", size=200)]
    session.accounts = updated_accounts
    manager.update_session(session)

    retrieved_session = manager.get_session(str(session_id))
    assert retrieved_session is not None
    assert retrieved_session.accounts[0].email == "updated@example.com"


def test_delete_session(setup_database):
    manager, session, session_id = setup_database
    manager.create_session(session)
    manager.delete_session(str(session_id))
    retrieved_session = manager.get_session(str(session_id))
    assert retrieved_session is None


@pytest.mark.parametrize(
    "email_filter, expected_count, expected_session_id_func",
    [
        ("test@example.com", 1, lambda s: s.session_id),
        ("another@example.com", 1, lambda s: s.session_id),
        ("nonexistent@example.com", 0, None),
    ],
)
def test_get_sessions_by_email(setup_database, email_filter, expected_count, expected_session_id_func):
    manager, session, session_id = setup_database
    session2_id = uuid.uuid4()
    session2 = Session(
        session_id=session2_id,
        starting_date=datetime.datetime.now(),
        end_date=datetime.datetime.now() + datetime.timedelta(hours=2),
        accounts=[Account(email="another@example.com", size=50)],
    )
    manager.create_session(session)
    manager.create_session(session2)

    filters = SessionFilter(account_email=email_filter)
    sessions = manager.get_sessions(filters)
    assert len(sessions) == expected_count
    if expected_session_id_func:
        if email_filter == "test@example.com":
            assert sessions[0].session_id == session_id
        elif email_filter == "another@example.com":
            assert sessions[0].session_id == session2_id


@pytest.mark.parametrize(
    "start_date_filter, end_date_filter, expected_count, expected_session_ids_func",
    [
        (datetime.datetime(2023, 1, 1), datetime.datetime(2023, 1, 2), 1, [lambda s: s.session_id]),
        (
            datetime.datetime(2022, 1, 1),
            datetime.datetime(2025, 1, 1),
            2,
            [lambda s: s.session_id, lambda s: s.session_id],
        ),
        (datetime.datetime(2025, 1, 1), datetime.datetime(2026, 1, 1), 0, []),
    ],
)
def test_get_sessions_by_date_range(
    setup_database, start_date_filter, end_date_filter, expected_count, expected_session_ids_func
):
    manager, session, session_id = setup_database
    old_session_id = uuid.uuid4()
    old_session = Session(
        session_id=old_session_id,
        starting_date=datetime.datetime(2023, 1, 1),
        end_date=datetime.datetime(2023, 1, 2),
        accounts=[],
    )
    new_session_id = uuid.uuid4()
    new_session = Session(
        session_id=new_session_id,
        starting_date=datetime.datetime(2024, 1, 1),
        end_date=datetime.datetime(2024, 1, 2),
        accounts=[],
    )
    manager.create_session(old_session)
    manager.create_session(new_session)

    filters = SessionFilter(
        starting_date=start_date_filter,
        end_date=end_date_filter,
    )
    sessions = manager.get_sessions(filters)
    assert len(sessions) == expected_count
    if expected_session_ids_func:
        actual_session_ids = sorted([s.session_id for s in sessions])
        expected_ids = sorted([old_session_id, new_session_id])
        if expected_count == 1:
            if start_date_filter == datetime.datetime(2023, 1, 1):
                assert sessions[0].session_id == old_session_id
        elif expected_count == 2:
            assert actual_session_ids == expected_ids
