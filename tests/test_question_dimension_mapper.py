import pytest

from app.backend.question_dimension_mapper import infer_question_dimension


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Her eyaletteki müşterilerin verdiği sipariş sayısını göster.", "customers.customer_state"),
        ("Müşterileri şehirlere göre grupla.", "customers.customer_city"),
        ("Sipariş durumlarına göre dağılım nedir?", "orders.order_status"),
        ("Satıcıları eyaletlere göre listele.", "sellers.seller_state"),
        ("Toplam kaç sipariş var?", None),
        ("Eyaletlere göre dağılım nedir?", None),
        ("Müşterilerin toplam sayısı nedir?", None),
        ("Müşterilerin eyaletlere göre dağılımı nedir?", "customers.customer_state"),
        ("Müşterilerin eyalet ve şehir bazında dağılımı nedir?", None),
        ("Müşterilerin eyaletinde kaç sipariş var?", None),
        ("Satıcıların şehirlerine göre dağılımı nedir?", "sellers.seller_city"),
    ],
)
def test_infer_question_dimension(question, expected):
    assert infer_question_dimension(question) == expected


def test_reject_non_string():
    with pytest.raises(TypeError):
        infer_question_dimension(None)


def test_empty_question():
    assert infer_question_dimension("   ") is None


def test_ambiguous_owners_abstain():
    assert infer_question_dimension("Müşteriler ve satıcılar eyaletlere göre kaç kişi?") is None


def test_custom_semantics():
    semantics = {
        "dimensions": {
            "orders.order_status": {
                "grouping_phrases": ["durumlara gore"],
                "owner_terms": [],
            }
        }
    }
    assert infer_question_dimension("Durumlara göre dağılım", semantics) == "orders.order_status"


@pytest.mark.parametrize(
    "question",
    [
        "Müşterilerin eyalet ve şehir bazında dağılımı nedir?",
        "Müşterilerin şehir ve eyalet bazında dağılımı nedir?",
        "Satıcıların eyalet ve şehir bazında dağılımı nedir?",
        "Satıcıların şehir ve eyalet bazında dağılımı nedir?",
    ],
)
def test_multiple_grouping_dimensions_abstain(question):
    assert infer_question_dimension(question) is None
