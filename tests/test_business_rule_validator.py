from app.backend.business_rule_validator import validate_business_rules

UNIQUE_Q = "Her eyalette kaç farklı müşteri sipariş vermiş?"
REVENUE_Q = "En fazla gelir getiren 10 ürün kategorisi hangileri? Kargo ücretini dahil etme."


def test_unique_customer_wrong_key_rejected():
    sql = """SELECT c.customer_state, COUNT(DISTINCT o.customer_id)
    FROM orders o JOIN customers c ON o.customer_id = c.customer_id
    GROUP BY c.customer_state"""
    assert validate_business_rules(UNIQUE_Q, sql)


def test_unique_customer_correct_key_accepted():
    sql = """SELECT c.customer_state, COUNT(DISTINCT c.customer_unique_id)
    FROM orders o JOIN customers c ON o.customer_id = c.customer_id
    GROUP BY c.customer_state"""
    assert not validate_business_rules(UNIQUE_Q, sql)


def test_category_revenue_unrequested_delivered_rejected():
    sql = """SELECT p.product_category_name, SUM(oi.price)
    FROM order_items oi JOIN orders o ON oi.order_id = o.order_id
    JOIN products p ON oi.product_id = p.product_id
    WHERE o.order_status = 'delivered'
    GROUP BY p.product_category_name"""
    assert validate_business_rules(REVENUE_Q, sql)


def test_category_revenue_without_status_accepted():
    sql = """SELECT p.product_category_name, SUM(oi.price)
    FROM order_items oi JOIN products p ON oi.product_id = p.product_id
    GROUP BY p.product_category_name"""
    assert not validate_business_rules(REVENUE_Q, sql)


def test_explicit_delivered_filter_allowed():
    sql = """SELECT p.product_category_name, SUM(oi.price)
    FROM order_items oi JOIN orders o ON oi.order_id = o.order_id
    JOIN products p ON oi.product_id = p.product_id
    WHERE o.order_status = 'delivered'
    GROUP BY p.product_category_name"""
    question = "Teslim edilmiş siparişlerde en fazla gelir getiren ürün kategorisi?"
    assert not validate_business_rules(question, sql)


def test_unrelated_question_untouched():
    assert not validate_business_rules("Toplam kaç sipariş var?", "SELECT COUNT(*) FROM orders")
