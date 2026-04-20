SELECT
    transaction_id,
    product_id,
    store_id,
    supplier_id,
    transaction_date,
    expiration_date,
    quantity,
    unit_price,
    waste_amount,
    profit,
    is_promotion,
    demand_level
FROM inventory_transactions
