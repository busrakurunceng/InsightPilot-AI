"""InsightPilot AI — Streamlit business intelligence dashboard.

All date filters use orders.order_purchase_timestamp, with an inclusive end date.
Revenue is delivered-order item price only, excluding freight and adjustments.
"""

import os
from datetime import date, datetime, time, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

load_dotenv()

st.set_page_config(page_title="InsightPilot AI", page_icon="📊", layout="wide")
st.title("InsightPilot AI")
st.caption("Business Intelligence Dashboard | Olist E-Commerce")


@st.cache_resource
def get_engine():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return create_engine(database_url, pool_pre_ping=True)
    url = URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "insightpilot_db"),
    )
    return create_engine(url, pool_pre_ping=True)


@st.cache_data(ttl=300)
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


@st.cache_data(ttl=300)
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


@st.cache_data(ttl=300)
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


@st.cache_data(ttl=300)
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


@st.cache_data(ttl=300)
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


@st.cache_data(ttl=300)
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


@st.cache_data(ttl=300)
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


# Load the available date range once, then use the same selection everywhere.
try:
    min_date, max_date = get_date_bounds()
except Exception as exc:
    st.error("Could not connect to PostgreSQL or retrieve order dates.")
    st.exception(exc)
    st.stop()

if min_date is None or max_date is None:
    st.warning("No dated orders are available in the database.")
    st.stop()

st.subheader("Dashboard Filters")
selected_dates = st.date_input(
    "Purchase date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
    format="DD/MM/YYYY",
)
if not isinstance(selected_dates, (tuple, list)) or len(selected_dates) != 2:
    st.info("Select both a start date and an end date to load the dashboard.")
    st.stop()
start_date, end_date = selected_dates
if start_date > end_date:
    st.warning("The start date must not be after the end date.")
    st.stop()

st.caption(f"Purchase dates: {start_date:%d/%m/%Y} – {end_date:%d/%m/%Y} (inclusive)")

try:
    kpis = get_core_kpis(start_date, end_date)
    monthly_df = get_monthly_revenue(start_date, end_date)
    status_df = get_order_status_distribution(start_date, end_date)
    products_df = get_top_products(start_date, end_date)
    sellers_df = get_top_sellers(start_date, end_date)
    delivery = get_delivery_performance(start_date, end_date)
except Exception as exc:
    st.error("Failed to load dashboard data from PostgreSQL.")
    st.exception(exc)
    st.stop()

st.divider()
st.subheader("Business Overview")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Orders", f"{kpis['total_orders']:,}")
with col2:
    st.metric("Total Revenue (BRL)", f"R$ {float(kpis['total_revenue']) / 1_000_000:,.2f}M")
    st.caption(f"Exact value: R$ {float(kpis['total_revenue']):,.2f}")
with col3:
    st.metric("Average Order Value (BRL)", f"R$ {float(kpis['average_order_value']):,.2f}")
st.caption("Revenue and AOV use delivered orders only; item prices exclude freight, refunds and adjustments.")

st.divider()
st.subheader("Monthly Revenue Trend")
if monthly_df.empty:
    st.info("No delivered-order revenue in this date range.")
else:
    fig = px.line(
        monthly_df, x="purchase_month", y="monthly_revenue", markers=True,
        title="Monthly Product Sales Revenue",
        labels={"purchase_month": "Purchase Month", "monthly_revenue": "Revenue (BRL)"},
        hover_data={"delivered_orders": True, "monthly_aov": ":.2f"},
    )
    fig.update_layout(hovermode="x unified", margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, width="stretch")
    with st.expander("View Monthly Revenue Data"):
        st.dataframe(monthly_df, width="stretch", hide_index=True)

st.divider()
st.subheader("Business Analytics")
st.markdown("#### Order Status Distribution")
if status_df.empty:
    st.info("No orders in this date range.")
else:
    fig_status = px.pie(
        status_df, names="order_status", values="order_count", hole=0.48,
        title="Orders by Status",
    )
    fig_status.update_traces(
        textinfo="none",
        hovertemplate="%{label}<br>Orders: %{value:,}<br>Share: %{percent}<extra></extra>",
    )
    fig_status.update_layout(showlegend=True, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig_status, width="stretch")
    with st.expander("View Order Status Data"):
        st.dataframe(status_df, width="stretch", hide_index=True)


def show_top_entities(df, id_column, revenue_column, heading, title, hover_columns):
    st.markdown(f"#### {heading}")
    if df.empty:
        st.info("No delivered-order sales in this date range.")
        return
    chart_df = df.copy()
    chart_df["short_id"] = chart_df[id_column].str[:10] + "…"
    chart_df = chart_df.sort_values(revenue_column)
    fig = px.bar(
        chart_df, x=revenue_column, y="short_id", orientation="h",
        title=title,
        labels={revenue_column: "Revenue (BRL)", "short_id": "ID (shortened)"},
        custom_data=[id_column] + hover_columns,
    )
    details = "".join(
        f"<br>{column}: %{{customdata[{i}]}}"
        for i, column in enumerate(hover_columns, start=1)
    )
    fig.update_traces(
        hovertemplate=(
            "Full ID: %{customdata[0]}<br>Revenue: R$ %{x:,.2f}"
            + details + "<extra></extra>"
        )
    )
    fig.update_layout(height=490, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, width="stretch")
    with st.expander(f"View {heading} Data"):
        st.dataframe(df, width="stretch", hide_index=True)


show_top_entities(
    products_df, "product_id", "product_revenue", "Top 10 Products by Revenue",
    "Top Products by Delivered Sales Revenue", ["items_sold", "orders_count"],
)
show_top_entities(
    sellers_df, "seller_id", "seller_revenue", "Top 10 Sellers by Revenue",
    "Top Sellers by Delivered Sales Revenue", ["delivered_orders", "items_sold", "avg_item_price"],
)

st.divider()
st.subheader("Delivery Performance")
col1, col2, col3 = st.columns(3)
with col1:
    days = delivery["avg_delivery_days"]
    st.metric("Average Delivery Time", f"{float(days):.2f} days" if days is not None else "N/A")
with col2:
    st.metric("Late Deliveries", f"{int(delivery['late_deliveries']):,}")
with col3:
    st.metric("Late Delivery Rate", f"{float(delivery['late_delivery_rate']):.2f}%")
st.caption(
    f"Based on {int(delivery['evaluated_deliveries']):,} delivered orders "
    "with complete delivery dates in the selected purchase-date range."
)
