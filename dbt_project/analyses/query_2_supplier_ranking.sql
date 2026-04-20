SELECT
    supplier_id,
    SUM(profit) AS total_profit,
    RANK() OVER (ORDER BY SUM(profit) DESC) AS supplier_rank
FROM fact_inventory
GROUP BY supplier_id;
