-- InsightPilot AI
-- Module 1: Data Foundation & Dashboard
-- Step 11: Business KPI SQL Queries
-- Dataset: Olist Brazilian E-Commerce
-- PostgreSQL 18
--
-- Definitions:
-- * Total orders include all statuses.
-- * Sales revenue is SUM(order_items.price) for delivered orders only,
--   excluding freight, refunds, and payment adjustments.
-- * AOV = delivered product sales revenue / number of delivered orders
--   with at least one order item.
-- * Monthly sales are grouped by purchase month.
-- * Run queries separately in pgAdmin for clear result sets.

-- KPI 1: Total orders (all statuses)
-- Expected: 99,441
SELECT COUNT(*) AS total_orders
FROM public.orders;

-- KPI 2: Delivered product sales revenue (excluding freight)
-- Expected: positive monetary amount; exact value to be validated.
SELECT ROUND(SUM(oi.price), 2) AS total_revenue
FROM public.order_items AS oi
JOIN public.orders AS o ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered';

-- KPI 3: Average order value (AOV), delivered product sales only
-- Expected: positive monetary amount; total_revenue / delivered_orders_with_items.
WITH delivered_order_values AS (
    SELECT oi.order_id, SUM(oi.price) AS order_value
    FROM public.order_items AS oi
    JOIN public.orders AS o ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY oi.order_id
)
SELECT
    COUNT(*) AS delivered_orders_with_items,
    ROUND(SUM(order_value), 2) AS total_revenue,
    ROUND(AVG(order_value), 2) AS average_order_value
FROM delivered_order_values;

-- KPI 4: Monthly delivered product sales revenue and order volume
-- Expected: one row per purchase month with delivered orders; ascending month.
WITH delivered_order_values AS (
    SELECT o.order_id,
           DATE_TRUNC('month', o.order_purchase_timestamp)::date AS purchase_month,
           SUM(oi.price) AS order_value
    FROM public.orders AS o
    JOIN public.order_items AS oi ON oi.order_id = o.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY o.order_id, DATE_TRUNC('month', o.order_purchase_timestamp)::date
)
SELECT purchase_month,
       COUNT(*) AS delivered_orders,
       ROUND(SUM(order_value), 2) AS monthly_revenue,
       ROUND(AVG(order_value), 2) AS monthly_aov
FROM delivered_order_values
GROUP BY purchase_month
ORDER BY purchase_month;

-- KPI 5: Order status distribution
-- Expected: 8 statuses for standard Olist dataset; total orders = 99,441.
SELECT order_status,
       COUNT(*) AS order_count,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_orders
FROM public.orders
GROUP BY order_status
ORDER BY order_count DESC, order_status;

-- KPI 6: Top 10 products by delivered sales revenue
-- Expected: at most 10 products; revenue descending; item counts >= order counts.
SELECT oi.product_id,
       COUNT(*) AS items_sold,
       COUNT(DISTINCT oi.order_id) AS orders_count,
       ROUND(SUM(oi.price), 2) AS product_revenue
FROM public.order_items AS oi
JOIN public.orders AS o ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
GROUP BY oi.product_id
ORDER BY product_revenue DESC, oi.product_id
LIMIT 10;

-- KPI 7: Top 10 sellers by delivered sales revenue
-- Expected: at most 10 sellers; revenue descending.
SELECT oi.seller_id,
       COUNT(DISTINCT oi.order_id) AS delivered_orders,
       COUNT(*) AS items_sold,
       ROUND(SUM(oi.price), 2) AS seller_revenue,
       ROUND(AVG(oi.price), 2) AS avg_item_price
FROM public.order_items AS oi
JOIN public.orders AS o ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
GROUP BY oi.seller_id
ORDER BY seller_revenue DESC, oi.seller_id
LIMIT 10;