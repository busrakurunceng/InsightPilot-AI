-- InsightPilot AI
-- Step 10: Analytical Index Benchmarks

-- Experiment 2: Date range filtering
-- Baseline: before creating the date index

EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM public.orders
WHERE order_purchase_timestamp >= TIMESTAMP '2018-01-01'
  AND order_purchase_timestamp < TIMESTAMP '2018-02-01';

  -- Experiment 3: Product-based order item lookup
-- Baseline: before creating the product_id index

EXPLAIN (ANALYZE, BUFFERS)
SELECT
    order_id,
    product_id,
    price,
    freight_value
FROM public.order_items
WHERE product_id = 'aca2eb7d00ea1a7b8ebd4e68314663af';

-- Experiment 4: Seller-based order item lookup
-- Baseline: before creating the seller_id index

EXPLAIN (ANALYZE, BUFFERS)
SELECT
    order_id,
    seller_id,
    price,
    freight_value
FROM public.order_items
WHERE seller_id = '6560211a19b47992c3666cc44a7e94c0';

-- Experiment 5: Order review lookup
-- Identify the order ID before baseline measurement

SELECT
    order_id,
    COUNT(*) AS review_count
FROM public.order_reviews
GROUP BY order_id
ORDER BY review_count DESC, order_id
LIMIT 1;
-- Experiment 5: Order review lookup
-- Fixed-order baseline and post-index benchmark

EXPLAIN (ANALYZE, BUFFERS)
SELECT
    review_id,
    order_id,
    review_score,
    review_comment_message
FROM public.order_reviews
WHERE order_id = '03c939fd7fd3b38f8485a0f95798f1f6';
