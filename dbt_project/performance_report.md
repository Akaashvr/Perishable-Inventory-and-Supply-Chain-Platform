# Performance Optimization Report

## Objective

The objective of this task was to analyze performance of analytical SQL query and improve its execution time using indexing techniques.

---

## Query Description

We analyzed a time-series query that calculates a **moving average of product demand** using a window function:

```sql
SELECT
    product_id,
    transaction_date,
    quantity,
    AVG(quantity) OVER (
        PARTITION BY product_id
        ORDER BY transaction_date
        ROWS BETWEEN 7 PRECEDING AND CURRENT ROW
    ) AS moving_avg_quantity
FROM inventory_transactions;
```

This query is computationally expensive because it involves:

* Partitioning by product
* Ordering by date
* Processing multiple rows per window

---

## Before Optimization

* **Execution Time:** ~851 ms
* **Query Plan:** Sequential Scan
* **Issue:**
  The database performed a full table scan on `inventory_transactions` which leads to slower performance, especially for analytical workloads.

---

## Optimization Applied

To improve performance, we created a **composite index** on the columns used in filtering and ordering:

```sql
CREATE INDEX idx_fact_product_date
ON inventory_transactions(product_id, transaction_date);
```

### Reason:

* `product_id` → used in PARTITION BY
* `transaction_date` → used in ORDER BY
* Helps database quickly locate relevant rows

---

## After Optimization

* **Execution Time:** ~142 ms
* **Query Plan:** Index Scan
* **Improvement:**
  The database used the index instead of scanning the full table, significantly reducing execution time.

---

## Performance Comparison

| Metric         | Before Optimization | After Optimization |
| -------------- | ------------------- | ------------------ |
| Execution Time | ~851 ms             | ~142 ms            |
| Query Plan     | Sequential Scan     | Index Scan         |
| Performance    | Slow                | ~6x Faster         |

---

## Conclusion

Use of a composite index significantly improved query performance by reducing execution time from ~851 ms to ~142 ms.

This demonstrates:

* The importance of indexing in analytical queries
* How EXPLAIN ANALYZE helps identify bottlenecks
* The effectiveness of optimizing queries based on access patterns

---
