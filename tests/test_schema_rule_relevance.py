
import pytest

from app.backend.schema_relevance import (
    rule_dependencies,
    select_relevant_rule,
)


def make_result(chunk_id, similarity=0.5):
    return {
        "chunk_id": chunk_id,
        "chunk_type": chunk_id.split(":")[0],
        "similarity": similarity,
    }


@pytest.mark.parametrize(
    "question",
    [
        "Sipariş ve ödeme tablolarını birleştirirken nelere dikkat etmeliyiz?",
        "Orders ve payments arasında JOIN yaparken riskler nelerdir?",
        "Sipariş ve ödeme tabloları arasındaki ilişki nedir?",
    ],
)
def test_select_join_rule(question):
    results = [
        make_result("rule:revenue_caveat", 0.43),
        make_result("rule:join_caveat", 0.41),
        make_result("table:order_payments", 0.29),
    ]

    assert select_relevant_rule(
        question, results
    ) == "rule:join_caveat"


def test_metric_question_does_not_select_join_rule():
    results = [
        make_result("rule:join_caveat", 0.41),
        make_result("metric:total_orders", 0.40),
    ]

    assert select_relevant_rule(
        "Toplam kaç sipariş var?", results
    ) is None


def test_rule_must_be_in_semantic_results():
    results = [
        make_result("table:orders", 0.50),
    ]

    assert select_relevant_rule(
        "Sipariş tablolarını birleştirirken nelere dikkat etmeliyiz?",
        results,
    ) is None


def test_join_rule_dependencies():
    dependencies = rule_dependencies(
        "rule:join_caveat"
    )

    assert dependencies == [
        "table:orders",
        "table:order_items",
        "table:order_payments",
    ]


def test_unknown_rule_has_no_dependencies():
    assert rule_dependencies(
        "rule:unknown"
    ) == []
