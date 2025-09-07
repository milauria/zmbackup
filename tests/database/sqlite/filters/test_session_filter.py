import datetime
import uuid

import pytest

from src.database.sqlite.constants import SqlManipulationStrings
from src.database.sqlite.filters.session_filter import SessionFilter


@pytest.mark.parametrize(
    "filters, expected_query, expected_params",
    [
        (
            SessionFilter(),
            "SELECT data FROM sessions",
            [],
        ),
        (
            SessionFilter(session_id="123"),
            "SELECT data FROM sessions WHERE session_id = ?",
            ["123"],
        ),
        (
            SessionFilter(starting_date=datetime.datetime(2023, 1, 1)),
            "SELECT data FROM sessions WHERE json_extract(data, '$.starting_date') >= ?",
            [datetime.datetime(2023, 1, 1).isoformat()],
        ),
        (
            SessionFilter(end_date=datetime.datetime(2023, 1, 31)),
            "SELECT data FROM sessions WHERE json_extract(data, '$.end_date') <= ?",
            [datetime.datetime(2023, 1, 31).isoformat()],
        ),
        (
            SessionFilter(account_email="test@example.com"),
            "SELECT data FROM sessions WHERE EXISTS (SELECT 1 FROM json_each(data, '$.accounts') WHERE json_extract(value, '$.email') = ?)",
            ["test@example.com"],
        ),
        (
            SessionFilter(
                session_id="456",
                starting_date=datetime.datetime(2023, 2, 1),
                end_date=datetime.datetime(2023, 2, 28),
                account_email="multi@example.com",
            ),
            "SELECT data FROM sessions WHERE session_id = ? AND "
            "json_extract(data, '$.starting_date') >= ? AND "
            "json_extract(data, '$.end_date') <= ? AND "
            "EXISTS (SELECT 1 FROM json_each(data, '$.accounts') WHERE json_extract(value, '$.email') = ?)",
            [
                "456",
                datetime.datetime(2023, 2, 1).isoformat(),
                datetime.datetime(2023, 2, 28).isoformat(),
                "multi@example.com",
            ],
        ),
    ],
)
def test_build_select_query(filters, expected_query, expected_params):
    query, params = filters.build_select_query()
    assert query == expected_query
    assert params == expected_params
