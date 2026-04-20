SELECT
    product_id,
    transaction_date,
    quantity,
    AVG(quantity) OVER (
        PARTITION BY product_id
        ORDER BY transaction_date
        ROWS BETWEEN 7 PRECEDING AND CURRENT ROW
    ) AS moving_avg_quantity
FROM fact_inventory;
