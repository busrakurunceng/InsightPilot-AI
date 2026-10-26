# PostgreSQL Index Performance Analysis

## Project
InsightPilot AI — Agentic Conversational Business Intelligence Platform

## Methodology
Each experiment compares the same fixed SQL query before and after creating a B-tree index. Measurements use `EXPLAIN (ANALYZE, BUFFERS)` on the local PostgreSQL database. Execution times are individual observations, not controlled multi-run benchmarks. Planning time is reported separately.

## Experiment 1: Customer Order Lookup

### Objective
Evaluate the effect of indexing `orders.customer_id` when retrieving orders for one customer.

### Query
```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM public.orders
WHERE customer_id = '9ef432eb6251297304e76186b10a928d';
```

### Index
```sql
CREATE INDEX IF NOT EXISTS idx_orders_customer_id
ON public.orders (customer_id);
```

### Results
| Metric | Before Index | After Index |
|---|---|---|
| Scan Type | Sequential Scan | Index Scan |
| Index Used | None | `idx_orders_customer_id` |
| Rows Returned | 1 | 1 |
| Rows Removed by Filter | 99,440 | Not reported |
| Execution Time | 9.301 ms | 0.067 ms |
| Planning Time | 0.078 ms | 0.126 ms |
| Shared Buffer Hits | 1,809 | 4 |

**Observed execution-time speedup:** approximately **138.82x** (99.28% reduction).

**Interpretation:** PostgreSQL used `idx_orders_customer_id` to locate the matching customer order without a sequential scan of the full orders table.

## Experiment 2: Order Purchase Date Filtering

### Objective
Evaluate the effect of indexing `orders.order_purchase_timestamp` when retrieving January 2018 orders.

### Query
```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM public.orders
WHERE order_purchase_timestamp >= TIMESTAMP '2018-01-01'
  AND order_purchase_timestamp < TIMESTAMP '2018-02-01';
```

### Index
```sql
CREATE INDEX IF NOT EXISTS idx_orders_purchase_timestamp
ON public.orders (order_purchase_timestamp);
```

### Results
| Metric | Before Index | After Index |
|---|---|---|
| Scan Type | Sequential Scan | Bitmap Heap Scan |
| Index Operation | None | Bitmap Index Scan (`idx_orders_purchase_timestamp`) |
| Rows Returned | 7,269 | 7,269 |
| Rows Removed by Filter | 92,172 | Not reported |
| Execution Time | 10.053 ms | 3.886 ms |
| Planning Time | 0.374 ms | 1.993 ms |
| Shared Buffer Hits | 1,809 | 1,784 |
| Shared Buffer Reads | 0 reported | 21 |
| Heap Blocks (exact) | Not reported | 1,784 |

**Observed execution-time speedup:** approximately **2.59x** (61.35% reduction).

**Interpretation:** PostgreSQL used a Bitmap Index Scan to identify matching rows and a Bitmap Heap Scan to retrieve them. The indexed query was faster in the observed run.

## Experiment 3: Product-Based Order Item Lookup

### Objective
Evaluate the effect of indexing `order_items.product_id` when retrieving order items for a fixed product.

### Query
```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT order_id, product_id, price, freight_value
FROM public.order_items
WHERE product_id = 'aca2eb7d00ea1a7b8ebd4e68314663af';
```

### Index
```sql
CREATE INDEX IF NOT EXISTS idx_order_items_product_id
ON public.order_items (product_id);
```

### Results
| Metric | Before Index | After Index |
|---|---|---|
| Scan Type | Sequential Scan | Bitmap Heap Scan |
| Index Operation | None | Bitmap Index Scan (`idx_order_items_product_id`) |
| Rows Returned | 527 | 527 |
| Rows Removed by Filter | 112,123 | Not reported |
| Execution Time | 10.960 ms | 0.631 ms |
| Planning Time | 0.087 ms | 2.091 ms |
| Shared Buffer Hits | 2,299 | 396 |
| Shared Buffer Reads | 0 reported | 3 |
| Heap Blocks (exact) | Not reported | 396 |

**Observed execution-time speedup:** approximately **17.37x** (94.24% reduction).

**Interpretation:** PostgreSQL used `idx_order_items_product_id` via a Bitmap Index Scan and fetched the matching rows using a Bitmap Heap Scan. The earlier query that dynamically calculated the most frequent product was excluded from this comparison because it included a costly aggregation step.

## Experiment 4: Seller-Based Order Item Lookup

### Objective
Evaluate the effect of indexing `order_items.seller_id` when retrieving order items for a fixed seller.

### Query
```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT order_id, seller_id, price, freight_value
FROM public.order_items
WHERE seller_id = '6560211a19b47992c3666cc44a7e94c0';
```

### Index
```sql
CREATE INDEX IF NOT EXISTS idx_order_items_seller_id
ON public.order_items (seller_id);
```

### Results
| Metric | Before Index | After Index |
|---|---|---|
| Scan Type | Sequential Scan | Bitmap Heap Scan |
| Index Operation | None | Bitmap Index Scan (`idx_order_items_seller_id`) |
| Rows Returned | 2,033 | 2,033 |
| Rows Removed by Filter | 110,617 | Not reported |
| Execution Time | 11.707 ms | 1.566 ms |
| Planning Time | 0.091 ms | 1.533 ms |
| Shared Buffer Hits | 2,299 | 1,293 |
| Shared Buffer Reads | 0 reported | 4 |
| Heap Blocks (exact) | Not reported | 1,293 |

**Observed execution-time speedup:** approximately **7.48x** (86.62% reduction).

**Interpretation:** PostgreSQL used a Bitmap Index Scan on the seller index and a Bitmap Heap Scan to fetch 2,033 matching order items.

## Experiment 5: Order Review Lookup

### Objective
Evaluate the effect of indexing `order_reviews.order_id` when retrieving reviews for a fixed order.

### Query
```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT review_id, order_id, review_score, review_comment_message
FROM public.order_reviews
WHERE order_id = '03c939fd7fd3b38f8485a0f95798f1f6';
```

### Index
```sql
CREATE INDEX IF NOT EXISTS idx_order_reviews_order_id
ON public.order_reviews (order_id);
```

### Results
| Metric | Before Index | After Index |
|---|---|---|
| Scan Type | Sequential Scan | Index Scan |
| Index Used | None | `idx_order_reviews_order_id` |
| Rows Returned | 3 | 3 |
| Rows Removed by Filter | 99,221 | Not reported |
| Execution Time | 8.533 ms | 0.153 ms |
| Planning Time | 0.261 ms | 1.972 ms |
| Shared Buffer Hits | 1,819 | 3 |
| Shared Buffer Reads | 0 reported | 3 |

**Observed execution-time speedup:** approximately **55.77x** (98.21% reduction).

**Interpretation:** PostgreSQL used an Index Scan to retrieve the three reviews for the selected order instead of scanning the entire reviews table.

## Overall Findings and Limitations

| Experiment | Before | After | Observed Speedup |
|---|---:|---:|---:|
| Customer lookup | 9.301 ms | 0.067 ms | 138.82x |
| January 2018 date filter | 10.053 ms | 3.886 ms | 2.59x |
| Product lookup | 10.960 ms | 0.631 ms | 17.37x |
| Seller lookup | 11.707 ms | 1.566 ms | 7.48x |
| Review lookup | 8.533 ms | 0.153 ms | 55.77x |

All five indexes were selected by PostgreSQL in their observed post-index execution plans. Indexes consume storage and add maintenance overhead during inserts and updates. Results are based on single executions with potentially different cache states; repeated runs and representative workloads are needed before making general performance claims. Planning time is not included in the execution-time speedup ratios.

## Next Experiments

- Develop and validate analytical SQL queries for business KPIs.
- Benchmark representative joins and aggregate queries where appropriate.
- Evaluate additional indexes only when justified by measured query workloads.
