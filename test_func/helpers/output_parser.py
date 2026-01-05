from typing import Dict, List, Optional


class ParsedTable:
    """
    Parsed representation of PrettyTable output.

    This class provides structured access to the data extracted from a
    PrettyTable string, allowing for easy verification of headers and rows.

    :param headers: List of column headers
    :param rows: List of row data (each row is a dict mapping header to value)
    """

    def __init__(self, headers: List[str], rows: List[Dict[str, str]]):
        """
        Initialize parsed table.

        :param headers: Column headers
        :param rows: Table rows as dictionaries
        """
        self.headers = headers
        self.rows = rows

    def get_row(self, index: int) -> Optional[Dict[str, str]]:
        """
        Get row by index (0-based).

        :param index: Row index
        :return: Row data as dictionary or None if out of bounds
        """
        if 0 <= index < len(self.rows):
            return self.rows[index]
        return None

    def get_row_count(self) -> int:
        """
        Get number of data rows.

        :return: Row count
        """
        return len(self.rows)

    def has_column(self, column: str) -> bool:
        """
        Check if table has a specific column.

        :param column: Column name
        :return: True if column exists
        """
        return column in self.headers


def parse_prettytable_output(output: str) -> Optional[ParsedTable]:
    """
    Parse PrettyTable output string into structured data.

    Expected format:
    +---------------+-------------+-------------+------+-------------+
    | Session Name  | Start       | Ending      | Size | Description |
    +---------------+-------------+-------------+------+-------------+
    | full-20260105 | 2026-01-05  | 2026-01-05  | 2 GB | Full backup |
    +---------------+-------------+-------------+------+-------------+

    :param output: String output from PrettyTable
    :return: ParsedTable instance or None if not a table
    """
    lines = output.strip().split("\n")

    # Find table boundaries (lines with +---)
    separator_indices = [
        i for i, line in enumerate(lines) if line.strip().startswith("+")
    ]

    if len(separator_indices) < 3:
        # Not a valid table (need at least top, header separator, bottom)
        return None

    # Extract header (between first two separators)
    header_line = lines[separator_indices[0] + 1]
    headers = [h.strip() for h in header_line.split("|")[1:-1]]

    # Extract data rows (between header separator and last separator)
    data_rows = []
    for i in range(separator_indices[1] + 1, separator_indices[-1]):
        if lines[i].strip().startswith("+"):
            continue  # Skip internal separators if any

        values = [v.strip() for v in lines[i].split("|")[1:-1]]
        row_dict = dict(zip(headers, values))
        data_rows.append(row_dict)

    return ParsedTable(headers, data_rows)


def assert_table_has_columns(
    parsed_table: ParsedTable, expected_columns: List[str]
) -> None:
    """
    Assert that table has expected columns.

    :param parsed_table: Parsed table instance
    :param expected_columns: List of expected column names
    :raises AssertionError: If columns don't match
    """
    for col in expected_columns:
        assert parsed_table.has_column(col), f"Table missing column: {col}"


def assert_row_contains(
    parsed_table: ParsedTable, row_index: int, expected_values: Dict[str, str]
) -> None:
    """
    Assert that a specific row contains expected values.

    :param parsed_table: Parsed table instance
    :param row_index: Row index (0-based)
    :param expected_values: Dictionary of column->value to verify
    :raises AssertionError: If values don't match
    """
    row = parsed_table.get_row(row_index)
    assert row is not None, f"Row {row_index} does not exist"

    for column, expected_value in expected_values.items():
        actual_value = row.get(column)
        assert actual_value == expected_value, (
            f"Row {row_index}, column '{column}': "
            f"expected '{expected_value}', got '{actual_value}'"
        )


__all__ = [
    "ParsedTable",
    "parse_prettytable_output",
    "assert_table_has_columns",
    "assert_row_contains",
]
