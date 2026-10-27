"""Read-only, parameterized PostgreSQL analytics for the BI dashboard."""
from datetime import date, datetime, time, timedelta
import pandas as pd
from sqlalchemy import text
from app.backend.db import get_engine

def get_date_bounds():
    query = text("""
        SELECT MIN(order_purchase_timestamp)::date AS min_date,
               MAX(order_purchase_timestamp)::date AS max_date
        FROM public.orders
        WHERE order_purchase_timestamp IS NOT NULL
    """)
    with get_engine().connect() as connection:
        row = connection.execute(query).mappings().one()
    return row["min_date"], row["max_date"]

def date_parameters(start_date: date, end_date: date):
    """Use half-open timestamp bounds to include the entire selected end date."""
    return {
        "start_ts": datetime.combine(start_date, time.min),
        "end_ts": datetime.combine(end_date + timedelta(days=1), time.min),
    }

def get_core_kpis(start_date: date, end_date: date):
    query = text("""
        WITH selected_orders AS (
            SELECT order_id, order_status
            FROM public.orders
            WHERE order_purchase_timestamp >= :start_ts
              AND order_purchase_timestamp < :end_ts
        ), delivered_order_values AS (
            SELECT oi.order_id, SUM(oi.price) AS order_value
            FROM public.order_items AS oi
            JOIN selected_orders AS o ON o.order_id = oi.order_id
            WHERE o.order_status = 'delivered'
            GROUP BY oi.order_id
        )
        SELECT
            (SELECT COUNT(*) FROM selected_orders) AS total_orders,
            COUNT(*) AS delivered_orders,
            COALESCE(SUM(order_value), 0) AS total_revenue,
            COALESCE(AVG(order_value), 0) AS average_order_value
        FROM delivered_order_values
    """)
    with get_engine().connect() as connection:
        return dict(connection.execute(query, date_parameters(start_date, end_date)).mappings().one())

def get_monthly_revenue(start_date: date, end_date: date):
    query = text("""
        WITH delivered_order_values AS (
            SELECT o.order_id,
                   DATE_TRUNC('month', o.order_purchase_timestamp)::date AS purchase_month,
                   SUM(oi.price) AS order_value
            FROM public.orders AS o
            JOIN public.order_items AS oi ON oi.order_id = o.order_id
            WHERE o.order_status = 'delivered'
              AND o.order_purchase_timestamp >= :start_ts
              AND o.order_purchase_timestamp < :end_ts
            GROUP BY o.order_id, DATE_TRUNC('month', o.order_purchase_timestamp)::date
        )
        SELECT purchase_month, COUNT(*) AS delivered_orders,
               ROUND(SUM(order_value), 2) AS monthly_revenue,
               ROUND(AVG(order_value), 2) AS monthly_aov
        FROM delivered_order_values
        GROUP BY purchase_month
        ORDER BY purchase_month
    """)
    with get_engine().connect() as connection:
        df = pd.read_sql(query, connection, params=date_parameters(start_date, end_date))
    if not df.empty:
        df["purchase_month"] = pd.to_datetime(df["purchase_month"])
        df["monthly_revenue"] = df["monthly_revenue"].astype(float)
        df["monthly_aov"] = df["monthly_aov"].astype(float)
    return df

def get_order_status_distribution(start_date: date, end_date: date):
    query = text("""
        SELECT order_status, COUNT(*) AS order_count,
               ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_orders
        FROM public.orders
        WHERE order_purchase_timestamp >= :start_ts
          AND order_purchase_timestamp < :end_ts
        GROUP BY order_status
        ORDER BY order_count DESC, order_status
    """)
    with get_engine().connect() as connection:
        df = pd.read_sql(query, connection, params=date_parameters(start_date, end_date))
    if not df.empty:
        df["pct_of_orders"] = df["pct_of_orders"].astype(float)
    return df

def get_top_products(start_date: date, end_date: date):
    query = text("""
        SELECT oi.product_id, COUNT(*) AS items_sold,
               COUNT(DISTINCT oi.order_id) AS orders_count,
               ROUND(SUM(oi.price), 2) AS product_revenue
        FROM public.order_items AS oi
        JOIN public.orders AS o ON o.order_id = oi.order_id
        WHERE o.order_status = 'delivered'
          AND o.order_purchase_timestamp >= :start_ts
          AND o.order_purchase_timestamp < :end_ts
        GROUP BY oi.product_id
        ORDER BY product_revenue DESC, oi.product_id
        LIMIT 10
    """)
    with get_engine().connect() as connection:
        df = pd.read_sql(query, connection, params=date_parameters(start_date, end_date))
    if not df.empty:
        df["product_revenue"] = df["product_revenue"].astype(float)
    return df

def get_top_sellers(start_date: date, end_date: date):
    query = text("""
        SELECT oi.seller_id,
               COUNT(DISTINCT oi.order_id) AS delivered_orders,
               COUNT(*) AS items_sold,
               ROUND(SUM(oi.price), 2) AS seller_revenue,
               ROUND(AVG(oi.price), 2) AS avg_item_price
        FROM public.order_items AS oi
        JOIN public.orders AS o ON o.order_id = oi.order_id
        WHERE o.order_status = 'delivered'
          AND o.order_purchase_timestamp >= :start_ts
          AND o.order_purchase_timestamp < :end_ts
        GROUP BY oi.seller_id
        ORDER BY seller_revenue DESC, oi.seller_id
        LIMIT 10
    """)
    with get_engine().connect() as connection:
        df = pd.read_sql(query, connection, params=date_parameters(start_date, end_date))
    if not df.empty:
        df["seller_revenue"] = df["seller_revenue"].astype(float)
        df["avg_item_price"] = df["avg_item_price"].astype(float)
    return df

def get_delivery_performance(start_date: date, end_date: date):
    query = text("""
        WITH delivery_metrics AS (
            SELECT EXTRACT(EPOCH FROM (
                       order_delivered_customer_date - order_purchase_timestamp
                   )) / 86400.0 AS delivery_days,
                   CASE WHEN order_delivered_customer_date > order_estimated_delivery_date
                        THEN 1 ELSE 0 END AS is_late
            FROM public.orders
            WHERE order_status = 'delivered'
              AND order_purchase_timestamp >= :start_ts
              AND order_purchase_timestamp < :end_ts
              AND order_delivered_customer_date IS NOT NULL
              AND order_estimated_delivery_date IS NOT NULL
        )
        SELECT COUNT(*) AS evaluated_deliveries,
               ROUND(AVG(delivery_days)::numeric, 2) AS avg_delivery_days,
               COALESCE(SUM(is_late), 0) AS late_deliveries,
               COALESCE(ROUND(100.0 * SUM(is_late) / NULLIF(COUNT(*), 0), 2), 0)
                   AS late_delivery_rate
        FROM delivery_metrics
    """)
    with get_engine().connect() as connection:
        return dict(connection.execute(query, date_parameters(start_date, end_date)).mappings().one())

