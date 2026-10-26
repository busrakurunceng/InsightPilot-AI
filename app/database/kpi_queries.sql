-- InsightPilot AI
-- Module 1: Business KPI Queries
-- Step 11: Core Business Metrics

-- KPI 1: Total Orders
-- Count all orders, regardless of order status.

SELECT
    COUNT(*) AS total_orders
FROM public.orders;