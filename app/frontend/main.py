"""InsightPilot AI Streamlit dashboard."""
import sys
from pathlib import Path

# Allow `python -m streamlit run app/frontend/main.py` from the repository root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import plotly.express as px
from app.backend.analytics import (
    get_date_bounds, get_core_kpis, get_monthly_revenue,
    get_order_status_distribution, get_top_products,
    get_top_sellers, get_delivery_performance,
)

st.set_page_config(page_title="InsightPilot AI", page_icon="📊", layout="wide")
st.title("InsightPilot AI")
st.caption("Business Intelligence Dashboard | Olist E-Commerce")

@st.cache_data(ttl=300)
def cached_get_date_bounds(*args):
    return get_date_bounds(*args)

@st.cache_data(ttl=300)
def cached_date_parameters(*args):
    return date_parameters(*args)

@st.cache_data(ttl=300)
def cached_get_core_kpis(*args):
    return get_core_kpis(*args)

@st.cache_data(ttl=300)
def cached_get_monthly_revenue(*args):
    return get_monthly_revenue(*args)

@st.cache_data(ttl=300)
def cached_get_order_status_distribution(*args):
    return get_order_status_distribution(*args)

@st.cache_data(ttl=300)
def cached_get_top_products(*args):
    return get_top_products(*args)

@st.cache_data(ttl=300)
def cached_get_top_sellers(*args):
    return get_top_sellers(*args)

@st.cache_data(ttl=300)
def cached_get_delivery_performance(*args):
    return get_delivery_performance(*args)

# Load the available date range once, then use the same selection everywhere.
try:
    min_date, max_date = cached_get_date_bounds()
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
    kpis = cached_get_core_kpis(start_date, end_date)
    monthly_df = cached_get_monthly_revenue(start_date, end_date)
    status_df = cached_get_order_status_distribution(start_date, end_date)
    products_df = cached_get_top_products(start_date, end_date)
    sellers_df = cached_get_top_sellers(start_date, end_date)
    delivery = cached_get_delivery_performance(start_date, end_date)
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
