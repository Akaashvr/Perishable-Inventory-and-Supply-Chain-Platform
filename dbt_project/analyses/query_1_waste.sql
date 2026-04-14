WITH waste_cte AS (
    SELECT 
        product_id,
        SUM(waste_amount) AS total_waste
    FROM fact_inventory
    GROUP BY product_id
)

SELECT 
    p.product_name,
    w.total_waste
FROM waste_cte w
JOIN dim_product p
    ON w.product_id = p.product_id
ORDER BY w.total_waste DESC;