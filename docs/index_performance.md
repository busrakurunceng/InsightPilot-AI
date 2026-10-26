
# PostgreSQL Index Performance Analysis

## Project
InsightPilot AI — Agentic Conversational Business Intelligence Platform

## Experiment 1: Customer Order Lookup

### Objective
Evaluate the impact of a B-tree index on customer-based
order lookup performance.

### Query

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM orders
WHERE customer_id = '9ef432eb6251297304e76186b10a928d';
```

### Before Index

| Metric | Value |
|---|---|
| Scan Type | Sequential Scan |
| Execution Time | 9.301 ms |
| Planning Time | 0.078 ms |
| Rows Returned | 1 |
| Rows Removed by Filter | 99,440 |
| Shared Buffer Hits | 1,809 |

### Observations

- PostgreSQL performed a sequential scan on the orders table.
- The query examined 99,441 rows to return one matching record.
- No index currently exists on orders.customer_id.
- This measurement will serve as the baseline.



### After Index

| Metric | Value |
|---|---|
| Scan Type | Index Scan |
| Index Used | idx_orders_customer_id |
| Execution Time | 0.067 ms |
| Planning Time | 0.126 ms |
| Rows Returned | 1 |
| Shared Buffer Hits | 4 |
| Index Searches | 1 |

### Performance Comparison

| Metric | Before | After |
|---|---|---|
| Scan Type | Sequential Scan | Index Scan |
| Execution Time | 9.301 ms | 0.067 ms |
| Shared Buffer Hits | 1,809 | 4 |

### Conclusion

A B-tree index was created on orders.customer_id.

PostgreSQL successfully selected an Index Scan for the
customer lookup query.

The measured execution time decreased from 9.301 ms
to 0.067 ms, approximately a 138.8x speedup.

These results represent individual query executions.
Repeated benchmarks under controlled conditions
would be required for a robust performance assessment.
