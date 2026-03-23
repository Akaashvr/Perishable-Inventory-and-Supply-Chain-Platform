-- security
-- EAS 550 Team 9

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'perishable_analyst') THEN
        CREATE ROLE perishable_analyst NOLOGIN;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'perishable_app_user') THEN
        CREATE ROLE perishable_app_user NOLOGIN;
    END IF;
END
$$;

GRANT CONNECT ON DATABASE neondb TO perishable_analyst;
GRANT CONNECT ON DATABASE neondb TO perishable_app_user;

GRANT USAGE ON SCHEMA public TO perishable_analyst;
GRANT USAGE ON SCHEMA public TO perishable_app_user;

GRANT SELECT ON TABLE
    regions,
    categories,
    stores,
    suppliers,
    products,
    promotions,
    product_promotions,
    inventory_transactions
TO perishable_analyst;

GRANT SELECT, INSERT, UPDATE ON TABLE
    regions,
    categories,
    stores,
    suppliers,
    products,
    promotions,
    product_promotions,
    inventory_transactions
TO perishable_app_user;

GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO perishable_analyst;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO perishable_app_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO perishable_analyst;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE ON TABLES TO perishable_app_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO perishable_app_user;