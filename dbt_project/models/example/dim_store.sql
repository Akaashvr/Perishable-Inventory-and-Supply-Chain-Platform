SELECT
    s.store_id,
    s.store_code,
    r.region_name
FROM stores AS s
LEFT JOIN regions AS r
    ON s.region_id = r.region_id
