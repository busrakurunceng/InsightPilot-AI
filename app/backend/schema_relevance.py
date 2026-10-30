
import re
import unicodedata


METRIC_INTENTS = {
    "total_orders": {
        "positive": [
            "toplam siparis",
            "kac siparis",
            "siparis sayisi",
        ],
        "negative": [
            "ortalama",
            "gelir",
            "teslimat suresi",
        ],
    },
    "delivered_product_revenue": {
        "positive": [
            "toplam gelir",
            "satis geliri",
            "ne kadar gelir",
            "ciro",
        ],
        "negative": [
            "ortalama gelir",
            "siparis basina",
        ],
    },
    "delivered_order_aov": {
        "positive": [
            "ortalama siparis",
            "siparis basina",
            "ortalama gelir",
            "sepet ortalamasi",
        ],
        "negative": [],
    },
    "average_delivery_days": {
        "positive": [
            "ortalama teslimat",
            "teslimat suresi",
            "kac gunde",
        ],
        "negative": [
            "gec teslim",
        ],
    },
    "late_delivery_rate": {
        "positive": [
            "gec teslim",
            "geciken siparis",
            "teslimat gecikme",
        ],
        "negative": [],
    },
}


RULE_DEPENDENCIES = {
    "rule:join_caveat": [
        "table:orders",
        "table:order_items",
        "table:order_payments",
    ],
    "rule:revenue_caveat": [
        "table:orders",
        "table:order_items",
        "table:order_payments",
    ],
    "rule:date_filter": [
        "table:orders",
    ],
    "rule:geolocation_caveat": [
        "table:geolocation",
    ],
}


def normalize_text(value: str) -> str:
    value = value.casefold()
    value = unicodedata.normalize("NFKD", value)

    value = "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )

    translations = str.maketrans({
        "ı": "i",
        "ğ": "g",
        "ü": "u",
        "ş": "s",
        "ö": "o",
        "ç": "c",
    })

    value = value.translate(translations)
    value = re.sub(r"[^a-z0-9\s]", " ", value)

    return re.sub(r"\s+", " ", value).strip()


def intent_score(question: str, metric_name: str) -> int:
    normalized = normalize_text(question)
    rules = METRIC_INTENTS.get(metric_name)

    if not rules:
        return 0

    score = 0

    for phrase in rules["positive"]:
        if phrase in normalized:
            score += 2

    for phrase in rules["negative"]:
        if phrase in normalized:
            score -= 2

    return score


def select_primary_metric(question: str, semantic_results):
    candidates = []

    for result in semantic_results:
        if result["chunk_type"] != "metric":
            continue

        metric_name = result["chunk_id"].removeprefix(
            "metric:"
        )

        score = intent_score(question, metric_name)

        if score > 0:
            candidates.append((
                score,
                float(result["similarity"]),
                result["chunk_id"],
            ))

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (-item[0], -item[1], item[2])
    )

    return candidates[0][2]


def select_relevant_rule(question: str, semantic_results):
    """
    İlişki/join sorularında uygun iş kuralını seçer.

    Kuralın semantic sonuçlarda bulunması gerekir.
    """
    normalized = normalize_text(question)

    relationship_terms = (
        "join",
        "birlestir",
        "iliski",
        "eslestir",
        "baglanti",
    )

    is_relationship_question = any(
        term in normalized
        for term in relationship_terms
    )

    if not is_relationship_question:
        return None

    available_ids = {
        row["chunk_id"]
        for row in semantic_results
    }

    if "rule:join_caveat" in available_ids:
        return "rule:join_caveat"

    return None


def rule_dependencies(rule_id: str):
    """
    Seçilen iş kuralının ihtiyaç duyduğu tablo chunk'ları.
    """
    return list(RULE_DEPENDENCIES.get(rule_id, []))
