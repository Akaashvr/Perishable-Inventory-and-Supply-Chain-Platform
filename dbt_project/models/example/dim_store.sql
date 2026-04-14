SELECT
    s.store_id,
    s.store_code,
    r.region_name
FROM stores s
LEFT JOIN regions r
    ON s.region_id = r.region_id