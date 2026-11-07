
"""Conservative, semantics-driven dimension extraction for Turkish BI questions."""
from __future__ import annotations

from typing import Any, Mapping

from app.backend.schema_dependencies import load_semantics
from app.backend.schema_relevance import normalize_text


def _contains_phrase(normalized_question: str, phrase: str) -> bool:
    """Match whole normalized tokens rather than substrings."""
    normalized_phrase = normalize_text(phrase)
    if not normalized_phrase:
        return False
    return f" {normalized_phrase} " in f" {normalized_question} "


def _grouping_matches(
    question: str,
    phrases: list[str],
    all_phrases: list[str],
) -> bool:
    """Recognize direct and coordinated grouping expressions."""
    if any(_contains_phrase(question, phrase) for phrase in phrases):
        return True

    # Handle shared suffixes such as:
    # "eyalet ve sehir bazinda"
    # "sehir ve eyalet bazinda"
    #
    # The possible dimension terms come from semantic metadata,
    # not from a hardcoded list of database columns.
    suffix = " bazinda"

    all_terms = {
        normalized[: -len(suffix)]
        for phrase in all_phrases
        if (normalized := normalize_text(phrase)).endswith(suffix)
    }

    own_terms = {
        normalized[: -len(suffix)]
        for phrase in phrases
        if (normalized := normalize_text(phrase)).endswith(suffix)
    }

    for own_term in own_terms:
        for other_term in all_terms:
            if other_term == own_term:
                continue

            for coordinated_phrase in (
                f"{own_term} ve {other_term} bazinda",
                f"{other_term} ve {own_term} bazinda",
            ):
                if _contains_phrase(question, coordinated_phrase):
                    return True

    return False


def infer_question_dimension(
    question: str,
    semantics: Mapping[str, Any] | None = None,
) -> str | None:
    """Return one unambiguous grouping dimension, otherwise None.

    Multiple requested dimensions and ambiguous dimension owners
    are intentionally not resolved in this version.
    """
    if not isinstance(question, str):
        raise TypeError("Question must be a string.")

    normalized = normalize_text(question)
    if not normalized:
        return None

    data = semantics if semantics is not None else load_semantics()
    definitions = data.get("dimensions", {})

    if not isinstance(definitions, dict):
        raise ValueError("Semantic dimensions must be a mapping.")

    all_phrases: list[str] = []

    for column, definition in definitions.items():
        if not isinstance(definition, dict):
            raise ValueError(f"Invalid dimension definition: {column}")

        phrases = definition.get("grouping_phrases", [])
        owners = definition.get("owner_terms", [])

        if not isinstance(phrases, list) or not isinstance(owners, list):
            raise ValueError(f"Invalid dimension phrases: {column}")

        all_phrases.extend(phrases)

    candidates: list[str] = []

    for column, definition in definitions.items():
        grouping_phrases = definition.get("grouping_phrases", [])
        owners = definition.get("owner_terms", [])

        if not _grouping_matches(
            normalized,
            grouping_phrases,
            all_phrases,
        ):
            continue

        if owners and not any(
            _contains_phrase(normalized, owner)
            for owner in owners
        ):
            continue

        candidates.append(column)

    return candidates[0] if len(candidates) == 1 else None
