
# Olist Data Validation Results

## Dataset Overview

- Dataset: Brazilian E-Commerce Public Dataset by Olist
- Database: PostgreSQL
- Database name: insightpilot_db
- Tables: 9
- Total records: 1,550,922

## Validation Results

| Check | Result | Status |
|---|---:|---|
| Orphan Orders (Customers) | 0 | PASS |
| Orphan Order Items (Orders) | 0 | PASS |
| Orphan Order Items (Products) | 0 | PASS |
| Orphan Order Items (Sellers) | 0 | PASS |
| Duplicate Order IDs | 0 | PASS |
| Duplicate Customer IDs | 0 | PASS |
| Duplicate Order Item Keys | 0 | PASS |
| Invalid Item Prices | 0 | PASS |
| Negative Freight Values | 0 | PASS |
| Invalid Review Scores | 0 | PASS |
| Missing Purchase Dates | 0 | PASS |
| Delivery Before Purchase | 0 | PASS |
| Negative Payment Values | 0 | PASS |

## Summary

All 13 validation checks passed.

The imported Olist dataset satisfies the tested
referential integrity, uniqueness, and data quality
conditions.

These checks do not establish that every possible
data quality issue has been eliminated.
