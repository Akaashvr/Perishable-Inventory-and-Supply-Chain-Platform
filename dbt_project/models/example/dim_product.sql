SELECT
    p.product_id,
    p.product_code,
    p.product_name,
    c.category_name,
    p.shelf_life_days,
    p.storage_temp_celsius,
    p.spoilage_sensitivity
FROM products p
LEFT JOIN categories c
    ON p.category_id = c.category_id