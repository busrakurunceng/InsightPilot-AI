
from app.backend.sql_prompt_builder import SYSTEM_PROMPT


def test_prompt_requires_measure_and_dimensions():
    assert "MEASURE:" in SYSTEM_PROMPT
    assert "DIMENSIONS:" in SYSTEM_PROMPT


def test_prompt_requires_join_planning():
    assert "JOINS:" in SYSTEM_PROMPT
    assert "supplied relationship" in SYSTEM_PROMPT


def test_prompt_preserves_grouping_dimensions():
    assert "Never discard a grouping dimension" in SYSTEM_PROMPT
    assert "SELECT and GROUP BY" in SYSTEM_PROMPT


def test_prompt_preserves_overall_aggregations():
    assert "do not add GROUP BY" in SYSTEM_PROMPT


def test_prompt_preserves_sql_only_output():
    assert "Output SQL only" in SYSTEM_PROMPT
    assert "INSUFFICIENT_CONTEXT" in SYSTEM_PROMPT
