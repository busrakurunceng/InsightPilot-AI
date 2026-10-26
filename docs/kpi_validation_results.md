# InsightPilot AI — Business KPI Validation Results

## Project and Scope

- **Module:** 1 — Data Foundation & Dashboard
- **Step:** 11 — Business KPI SQL Queries and Validation
- **Dataset:** Olist Brazilian E-Commerce Public Dataset
- **Database:** PostgreSQL 18 (`insightpilot_db`)
- **Query file:** `app/database/kpi_queries.sql`
- **Status:** SQL queries executed and reported; three reconciliation checks passed

## Metric Definitions

- **Total orders:** all rows in `public.orders`, regardless of order status.
- **Sales revenue:** `SUM(order_items.price)` for orders with `order_status = 'delivered'`; excludes freight, refunds, and payment adjustments. This is not net accounting revenue.
- **AOV:** delivered product sales revenue divided by delivered orders with at least one order item.
- **Monthly revenue:** delivered product sales grouped by `orders.order_purchase_timestamp` month.
- **Delivery duration:** actual customer delivery timestamp minus purchase timestamp; late if actual delivery is after estimated delivery date. Only delivered orders with all required dates are included.
- **Product and seller rankings:** delivered product sales revenue, excluding freight.

## KPI Results

| KPI | Metric | Observed result |
|---|---|---:|
| 1 | Total orders | 99,441 |
| 2 | Delivered product sales revenue | 13,221,498.11 |
| 3 | Delivered orders with items | 96,478 |
| 3 | Average order value | 137.04 |
| 4 | Monthly revenue periods | 23 |
| 5 | Order status categories | 8 |
| 6 | Top products returned | 10 |
| 7 | Top sellers returned | 10 |
| 8 | Deliveries evaluated | 96,470 |
| 8 | Average delivery duration | 12.56 days |
| 8 | Late deliveries | 7,826 |
| 8 | Late delivery rate | 8.11% |

### KPI 4: Monthly Revenue

| Purchase month | Delivered orders | Product revenue | Monthly AOV |
|---|---:|---:|---:|
| 2016-09 | 1 | 134.97 | 134.97 |
| 2016-10 | 265 | 40,325.11 | 152.17 |
| 2016-12 | 1 | 10.90 | 10.90 |
| 2017-01 | 750 | 111,798.36 | 149.06 |
| 2017-02 | 1,653 | 234,223.40 | 141.70 |
| 2017-03 | 2,546 | 359,198.85 | 141.08 |
| 2017-04 | 2,303 | 340,669.68 | 147.92 |
| 2017-05 | 3,546 | 489,338.25 | 138.00 |
| 2017-06 | 3,135 | 421,923.37 | 134.58 |
| 2017-07 | 3,872 | 481,604.52 | 124.38 |
| 2017-08 | 4,193 | 554,699.70 | 132.29 |
| 2017-09 | 4,150 | 607,399.67 | 146.36 |
| 2017-10 | 4,478 | 648,247.65 | 144.76 |
| 2017-11 | 7,289 | 987,765.37 | 135.51 |
| 2017-12 | 5,513 | 726,033.19 | 131.69 |
| 2018-01 | 7,069 | 924,645.00 | 130.80 |
| 2018-02 | 6,555 | 826,437.13 | 126.08 |
| 2018-03 | 7,003 | 953,356.25 | 136.14 |
| 2018-04 | 6,798 | 973,534.09 | 143.21 |
| 2018-05 | 6,749 | 977,544.69 | 144.84 |
| 2018-06 | 6,099 | 856,077.86 | 140.36 |
| 2018-07 | 6,159 | 867,953.46 | 140.92 |
| 2018-08 | 6,351 | 838,576.64 | 132.04 |

### KPI 5: Order Status Distribution

| Order status | Orders | Share (%) |
|---|---:|---:|
| delivered | 96,478 | 97.02 |
| shipped | 1,107 | 1.11 |
| canceled | 625 | 0.63 |
| unavailable | 609 | 0.61 |
| invoiced | 314 | 0.32 |
| processing | 301 | 0.30 |
| created | 5 | 0.01 |
| approved | 2 | 0.00 |

### KPI 6: Top 10 Products by Delivered Product Revenue

| Product ID | Items sold | Orders | Revenue |
|---|---:|---:|---:|
| bb50f2e236e5eea0100680137654686c | 194 | 186 | 63,560.00 |
| 6cdd53843498f92890544667809f1595 | 153 | 148 | 53,652.30 |
| d6160fb7873f184099d9bc95e30376af | 33 | 33 | 45,949.35 |
| d1c427060a0f73f6b889a5c7c61f2ac4 | 332 | 313 | 45,620.56 |
| 99a4788cb24856965c36a24e339b6058 | 477 | 456 | 42,049.66 |
| 3dd2a17168ec895c781a9191c1e95ad7 | 272 | 253 | 40,782.80 |
| 25c38557cf793876c5abdd5931f922db | 38 | 38 | 38,907.32 |
| 5f504b3a1c75b73d6151be81eb05bdc9 | 63 | 63 | 37,733.90 |
| 53b36df67ebb7c41585e8d54d6772e08 | 321 | 304 | 37,454.63 |
| aca2eb7d00ea1a7b8ebd4e68314663af | 520 | 425 | 37,104.30 |

### KPI 7: Top 10 Sellers by Delivered Product Revenue

| Seller ID | Delivered orders | Items sold | Revenue | Avg item price |
|---|---:|---:|---:|---:|
| 4869f7a5dfa277a7dca6462dcf3b52b2 | 1,124 | 1,148 | 226,987.93 | 197.72 |
| 53243585a1d6dc2643021fd1853d8905 | 348 | 400 | 217,940.44 | 544.85 |
| 4a3ca9315b744ce9f8e9374361493884 | 1,772 | 1,949 | 196,882.12 | 101.02 |
| fa1c13f2614d7b5c4749cbc52fecda94 | 578 | 579 | 190,917.14 | 329.74 |
| 7c67e1448b00f6e969d365cea6b010ab | 973 | 1,355 | 186,570.05 | 137.69 |
| 7e93a43ef30c4f03f38b393420bc753a | 319 | 322 | 165,981.49 | 515.47 |
| da8622b14eb17ae2831f4ac5b9dab84a | 1,311 | 1,548 | 159,816.87 | 103.24 |
| 7a67c85e85bb2ce8582c35f2203ad736 | 1,145 | 1,155 | 139,658.69 | 120.92 |
| 1025f0e2d44d7041d6cf58b6550e0bfa | 910 | 1,420 | 138,208.56 | 97.33 |
| 955fee9216a65b617aa5c0531780ce60 | 1,261 | 1,472 | 131,836.71 | 89.56 |

## Validation Checks

| Check | Observed output | Result |
|---|---|---|
| A — Revenue reconciliation | `revenue_difference = 0.00` | Passed |
| B — Order status count | `status_order_total = 99441`; `matches_total_orders = true` | Passed |
| C — Monthly revenue reconciliation | `monthly_revenue_difference = 0.00` | Passed |

## Interpretation and Limitations

- The delivered-order count is 96,478; delivery-performance metrics use 96,470 records with complete required dates, a difference of eight.
- The 8.11% late-delivery rate applies to the evaluated delivered orders, not all orders.
- The 23 monthly periods reflect months with delivered orders in the dataset; missing calendar months are not automatically represented as zero-valued rows.
- Revenue and AOV exclude freight and do not account for refunds, payment adjustments, or costs.
- All values are observations reported from the local SQL executions; the dashboard should be validated against these figures.

## Next Step

Implement the Streamlit dashboard and reconcile displayed metrics with the SQL reference values in this report.
