
import pytest

from app.backend.sql_generator import (
    normalize_sql_response,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "```sql\nSELECT COUNT(*) FROM orders;\n```",
            "SELECT COUNT(*) FROM orders;",
        ),
        (
            "```postgresql\nSELECT 1;\n```",
            "SELECT 1;",
        ),
        (
            "```\nSELECT 1;\n```",
            "SELECT 1;",
        ),
        (
            "SELECT COUNT(*) FROM orders;",
            "SELECT COUNT(*) FROM orders;",
        ),
        (
            "INSUFFICIENT_CONTEXT",
            "INSUFFICIENT_CONTEXT",
        ),
        (
            "Here is SQL:\n```sql\nSELECT 1;\n```",
            "Here is SQL:\n```sql\nSELECT 1;\n```",
        ),
        (
            "```sql\nSELECT 1;\n```\n"
            "```sql\nSELECT 2;\n```",
            "```sql\nSELECT 1;\n```\n"
            "```sql\nSELECT 2;\n```",
        ),
        (
            "```sql\nSELECT 1;\n```\nExplanation",
            "```sql\nSELECT 1;\n```\nExplanation",
        ),
        (
            "```sql\nSELECT 1;\n",
            "```sql\nSELECT 1;",
        ),
        (
            "```sql\nSELECT 1;\n```\n```",
            "```sql\nSELECT 1;\n```\n```",
        ),
        (
            "  ```sql\nSELECT 1;\n```  ",
            "SELECT 1;",
        ),
    ],
)
def test_normalize_sql_response(raw, expected):
    assert normalize_sql_response(raw) == expected


@pytest.mark.parametrize(
    "invalid_response",
    [None, 123, [], {}],
)
def test_normalize_sql_response_invalid_type(
    invalid_response,
):
    with pytest.raises(TypeError):
        normalize_sql_response(invalid_response)
