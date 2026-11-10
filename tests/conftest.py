"""Shared mocks for Text-to-SQL pipeline unit tests."""

from unittest.mock import patch

import pytest


@pytest.fixture
def mock_schema_validation():
    """Isolate PostgreSQL EXPLAIN from pipeline unit tests.

    The real schema validator is tested separately in
    tests/test_sql_schema_validator.py and with live PostgreSQL.
    """
    with patch(
        "app.backend.text_to_sql_service.validate_sql_schema"
    ) as mocked:
        yield mocked
