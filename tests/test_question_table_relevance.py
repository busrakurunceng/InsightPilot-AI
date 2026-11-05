import pytest

from app.backend.question_table_relevance import (
    infer_question_tables,
)


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        (
            "Toplam kaç sipariş var?",
            ["orders"],
        ),
        (
            "Teslim edilmiş kaç sipariş var?",
            ["orders"],
        ),
        (
            "Müşterilerin eyaletlere göre dağılımı nedir?",
            ["customers"],
        ),
        (
            "São Paulo eyaletindeki müşterilerin verdiği toplam sipariş sayısı kaçtır?",
            ["customers", "orders"],
        ),
        (
            "Her eyaletteki müşterilerin verdiği sipariş sayısını göster.",
            ["customers", "orders"],
        ),
        (
            "Ödeme kayıtlarındaki toplam ödeme tutarı nedir?",
            ["order_payments"],
        ),
        (
            "Ödeme kayıtlarının ortalama tutarı nedir?",
            ["order_payments"],
        ),
        (
            "İptal edilmiş kaç sipariş var?",
            ["orders"],
        ),
        (
            "Müşteri kayıtlarını listele.",
            ["customers"],
        ),
        (
            "Merhaba",
            [],
        ),
        (
            "",
            [],
        ),
    ],
)
def test_infer_question_tables(question, expected):
    assert infer_question_tables(question) == expected


def test_infer_question_tables_invalid_type():
    with pytest.raises(TypeError):
        infer_question_tables(None)