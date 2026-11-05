# app/backend/question_table_relevance.py

from app.backend.schema_relevance import normalize_text


def infer_question_tables(question: str) -> list[str]:
    """
    Infer required Olist tables from explicit Turkish question terms.

    This is a conservative supplement to semantic retrieval,
    not a replacement for vector search.
    """
    if not isinstance(question, str):
        raise TypeError("Question must be a string.")

    normalized = normalize_text(question)

    if not normalized:
        return []

    tokens = set(normalized.split())
    tables = []

    customer_terms = {
        "musteri",
        "musteriler",
        "musterilerin",
        "musterilerinin",
        "musterinin",
        "musterilerin",
    }

    order_terms = {
        "siparis",
        "siparisler",
        "siparislerin",
        "siparislerinın",
        "siparisi",
        "siparisini",
        "siparislerinin",
        "siparislerinin",
    }

    payment_terms = {
        "odeme",
        "odemeler",
        "odemelerin",
        "odemenin",
    }

    has_customers = bool(tokens & customer_terms)
    has_orders = bool(tokens & order_terms)
    has_payments = bool(tokens & payment_terms)

    if has_customers:
        tables.append("customers")

    if has_orders:
        tables.append("orders")

    if has_payments:
        tables.append("order_payments")

    return tables