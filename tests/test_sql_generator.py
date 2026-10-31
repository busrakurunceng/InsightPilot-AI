
from unittest.mock import Mock, patch

import pytest

from app.backend.llm_client import LLMResponse
from app.backend.sql_generator import SQLGenerator


def make_chunk(chunk_id, chunk_type, content):
    return {
        "chunk_id": chunk_id,
        "chunk_type": chunk_type,
        "content": content,
        "metadata": {},
    }


@pytest.fixture
def mock_client():
    client = Mock()
    client.chat.return_value = LLMResponse(
        content="SELECT COUNT(*) FROM orders",
        model="qwen2.5-coder:7b-instruct",
    )
    return client


@patch("app.backend.sql_generator.search_schema")
def test_generate_success(mock_search, mock_client):
    mock_search.return_value = (
        [make_chunk("metric:total_orders", "metric", "Count orders")],
        [make_chunk("table:orders", "table", "Orders table")],
    )

    generator = SQLGenerator(llm_client=mock_client)

    result = generator.generate("Toplam kaç sipariş var?")

    assert result.sql == "SELECT COUNT(*) FROM orders"
    assert result.model == "qwen2.5-coder:7b-instruct"
    assert result.selected_chunk_ids == ["metric:total_orders"]
    assert result.dependency_chunk_ids == ["table:orders"]

    mock_search.assert_called_once_with(
        "Toplam kaç sipariş var?",
        top_k=5,
    )
    mock_client.chat.assert_called_once()


@patch("app.backend.sql_generator.search_schema")
def test_custom_top_k(mock_search, mock_client):
    mock_search.return_value = (
        [make_chunk("table:orders", "table", "Orders")],
        [],
    )

    generator = SQLGenerator(
        llm_client=mock_client,
        top_k=8,
    )

    generator.generate("Kaç sipariş var?")

    mock_search.assert_called_once_with(
        "Kaç sipariş var?",
        top_k=8,
    )


def test_empty_question(mock_client):
    generator = SQLGenerator(llm_client=mock_client)

    with pytest.raises(ValueError):
        generator.generate("   ")

    mock_client.chat.assert_not_called()


def test_invalid_top_k(mock_client):
    with pytest.raises(ValueError):
        SQLGenerator(llm_client=mock_client, top_k=0)


@patch("app.backend.sql_generator.search_schema")
def test_empty_context(mock_search, mock_client):
    mock_search.return_value = ([], [])

    generator = SQLGenerator(llm_client=mock_client)

    with pytest.raises(ValueError):
        generator.generate("Kaç sipariş var?")

    mock_client.chat.assert_not_called()


@patch("app.backend.sql_generator.search_schema")
def test_empty_llm_response(mock_search, mock_client):
    mock_search.return_value = (
        [make_chunk("table:orders", "table", "Orders")],
        [],
    )

    mock_client.chat.return_value = LLMResponse(
        content="   ",
        model="qwen2.5-coder:7b-instruct",
    )

    generator = SQLGenerator(llm_client=mock_client)

    with pytest.raises(ValueError):
        generator.generate("Kaç sipariş var?")
