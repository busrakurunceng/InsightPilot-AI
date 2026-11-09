
"""Tests for the Module 4 AnalyticsService adapter."""

from unittest.mock import Mock

import pytest

from app.backend.analytics_contract import AnalyticsResponse
from app.backend.analytics_service import (
    AnalyticsService,
    to_analytics_response,
)
from app.backend.text_to_sql_service import TextToSQLResult


def make_text_to_sql_result(**overrides):
    values = {
        "question": "Her eyalette kaç sipariş var?",
        "sql": (
            "SELECT customer_state, COUNT(*) AS total_orders "
            "FROM customers GROUP BY customer_state"
        ),
        "model": "qwen2.5-coder:7b-instruct",
        "columns": ["customer_state", "total_orders"],
        "rows": [
            {"customer_state": "SP", "total_orders": 100},
            {"customer_state": "RJ", "total_orders": 50},
        ],
        "row_count": 2,
        "truncated": False,
        "selected_chunk_ids": ["schema_customers"],
        "dependency_chunk_ids": ["schema_orders"],
    }

    values.update(overrides)
    return TextToSQLResult(**values)


def test_conversion_returns_analytics_response():
    result = make_text_to_sql_result()

    response = to_analytics_response(result)

    assert isinstance(response, AnalyticsResponse)
    assert response.question == result.question
    assert response.sql == result.sql


def test_conversion_preserves_rows_and_columns():
    result = make_text_to_sql_result()

    response = to_analytics_response(result)

    assert response.columns == result.columns
    assert response.rows == result.rows
    assert response.row_count == 2


def test_conversion_preserves_metadata():
    result = make_text_to_sql_result()

    response = to_analytics_response(result)

    assert response.model == result.model
    assert response.truncated is False
    assert response.selected_chunk_ids == [
        "schema_customers"
    ]
    assert response.dependency_chunk_ids == [
        "schema_orders"
    ]

def test_conversion_copies_mutable_data():
    result = make_text_to_sql_result()

    response = to_analytics_response(result)

    assert response.rows is not result.rows
    assert response.rows[0] is not result.rows[0]
    assert response.columns is not result.columns
    assert (
        response.selected_chunk_ids
        is not result.selected_chunk_ids
    )
    assert (
        response.dependency_chunk_ids
        is not result.dependency_chunk_ids
    )

    response.rows[0]["total_orders"] = 999

    assert result.rows[0]["total_orders"] == 100


def test_conversion_rejects_wrong_type():
    with pytest.raises(TypeError, match="TextToSQLResult"):
        to_analytics_response({"rows": []})


def test_conversion_supports_empty_results():
    result = make_text_to_sql_result(
        rows=[],
        row_count=0,
    )

    response = to_analytics_response(result)

    assert response.rows == []
    assert response.row_count == 0


def test_conversion_preserves_truncation():
    result = make_text_to_sql_result(
        truncated=True
    )

    response = to_analytics_response(result)

    assert response.truncated is True


def test_service_calls_text_to_sql_once():
    backend = Mock()
    backend.run.return_value = make_text_to_sql_result()

    service = AnalyticsService(
        text_to_sql_service=backend
    )

    response = service.run(
        "  Her eyalette kaç sipariş var?  "
    )

    backend.run.assert_called_once_with(
        "Her eyalette kaç sipariş var?"
    )

    assert isinstance(response, AnalyticsResponse)


def test_service_returns_expected_result():
    backend = Mock()
    backend.run.return_value = make_text_to_sql_result()

    service = AnalyticsService(
        text_to_sql_service=backend
    )

    response = service.run(
        "Her eyalette kaç sipariş var?"
    )

    assert response.row_count == 2
    assert response.rows[0]["customer_state"] == "SP"
    assert response.model == "qwen2.5-coder:7b-instruct"


@pytest.mark.parametrize(
    "question",
    ["", " ", "\n\t", None, 123],
)
def test_service_rejects_invalid_question(question):
    backend = Mock()

    service = AnalyticsService(
        text_to_sql_service=backend
    )

    with pytest.raises(ValueError, match="Question"):
        service.run(question)

    backend.run.assert_not_called()


def test_service_propagates_backend_error():
    backend = Mock()
    backend.run.side_effect = RuntimeError(
        "Database unavailable"
    )

    service = AnalyticsService(
        text_to_sql_service=backend
    )

    with pytest.raises(
        RuntimeError,
        match="Database unavailable",
    ):
        service.run("Toplam kaç sipariş var?")


def test_service_does_not_call_llm_directly():
    backend = Mock()
    backend.run.return_value = make_text_to_sql_result()

    service = AnalyticsService(
        text_to_sql_service=backend
    )

    service.run("Toplam kaç sipariş var?")

    backend.run.assert_called_once()


def test_conversion_initializes_analytics_fields():
    response = to_analytics_response(
        make_text_to_sql_result()
    )

    assert len(response.column_profiles) == 2

    assert response.column_profiles[0].name == "customer_state"
    assert response.column_profiles[0].data_type == "categorical"
    assert response.column_profiles[0].role == "dimension"

    assert response.column_profiles[1].name == "total_orders"
    assert response.column_profiles[1].data_type == "numeric"
    assert response.column_profiles[1].role == "measure"

    assert response.visualization is None
    assert response.insights == []


def test_service_populates_column_profiles():
    backend = Mock()
    backend.run.return_value = make_text_to_sql_result()

    service = AnalyticsService(
        text_to_sql_service=backend
    )

    response = service.run(
        "Her eyalette kaç sipariş var?"
    )

    assert len(response.column_profiles) == 2

    profiles = {
        profile.name: profile
        for profile in response.column_profiles
    }

    assert profiles["customer_state"].data_type == "categorical"
    assert profiles["customer_state"].role == "dimension"

    assert profiles["total_orders"].data_type == "numeric"
    assert profiles["total_orders"].role == "measure"


def test_service_detects_nullable_column():
    backend = Mock()
    backend.run.return_value = make_text_to_sql_result(
        rows=[
            {"customer_state": "SP", "total_orders": 100},
            {"customer_state": "RJ", "total_orders": None},
        ],
    )

    service = AnalyticsService(
        text_to_sql_service=backend
    )

    response = service.run(
        "Her eyalette kaç sipariş var?"
    )

    profiles = {
        profile.name: profile
        for profile in response.column_profiles
    }

    assert profiles["total_orders"].nullable is True
    assert profiles["total_orders"].data_type == "numeric"
    assert profiles["customer_state"].nullable is False


def test_service_profiles_empty_results():
    backend = Mock()
    backend.run.return_value = make_text_to_sql_result(
        rows=[],
        row_count=0,
    )

    service = AnalyticsService(
        text_to_sql_service=backend
    )

    response = service.run(
        "Her eyalette kaç sipariş var?"
    )

    assert response.row_count == 0
    assert len(response.column_profiles) == 2

    assert all(
        profile.data_type == "unknown"
        for profile in response.column_profiles
    )


def test_service_preserves_metadata_after_profiling():
    backend = Mock()
    backend.run.return_value = make_text_to_sql_result(
        truncated=True
    )

    service = AnalyticsService(
        text_to_sql_service=backend
    )

    response = service.run(
        "Her eyalette kaç sipariş var?"
    )

    assert response.truncated is True
    assert response.model == "qwen2.5-coder:7b-instruct"
    assert response.selected_chunk_ids == ["schema_customers"]
    assert response.dependency_chunk_ids == ["schema_orders"]

    assert len(response.column_profiles) == 2


def test_service_profiles_decimal_values():
    from decimal import Decimal

    backend = Mock()
    backend.run.return_value = make_text_to_sql_result(
        columns=["revenue"],
        rows=[
            {"revenue": Decimal("125.50")},
            {"revenue": Decimal("75.25")},
        ],
    )

    service = AnalyticsService(
        text_to_sql_service=backend
    )

    response = service.run("Toplam gelir nedir?")

    assert len(response.column_profiles) == 1
    assert response.column_profiles[0].data_type == "numeric"
    assert response.column_profiles[0].role == "measure"


def test_service_profiles_datetime_values():
    from datetime import datetime

    backend = Mock()
    backend.run.return_value = make_text_to_sql_result(
        columns=["order_month"],
        rows=[
            {"order_month": datetime(2026, 1, 1)},
            {"order_month": datetime(2026, 2, 1)},
        ],
    )

    service = AnalyticsService(
        text_to_sql_service=backend
    )

    response = service.run(
        "Aylara göre siparişleri göster."
    )

    assert response.column_profiles[0].data_type == "datetime"
    assert response.column_profiles[0].role == "dimension"


def test_conversion_rejects_invalid_result_structure():
    result = make_text_to_sql_result(
        columns=["customer_state", "total_orders"],
        rows=[
            {"customer_state": "SP"},
            {"customer_state": "RJ", "total_orders": 50},
        ],
    )

    with pytest.raises(
        ValueError,
        match="declared columns",
    ):
        to_analytics_response(result)


def test_service_does_not_mutate_backend_rows():
    result = make_text_to_sql_result()

    backend = Mock()
    backend.run.return_value = result

    service = AnalyticsService(
        text_to_sql_service=backend
    )

    response = service.run(
        "Her eyalette kaç sipariş var?"
    )

    response.rows[0]["total_orders"] = 999

    assert result.rows[0]["total_orders"] == 100
