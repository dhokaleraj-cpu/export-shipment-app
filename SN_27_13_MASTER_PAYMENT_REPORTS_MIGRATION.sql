-- SN 27.13 additive relationship migration
CREATE TABLE IF NOT EXISTS ship_to_masters (
    id SERIAL PRIMARY KEY,
    ship_to_name TEXT NOT NULL,
    ship_to_id TEXT,
    addressline1 TEXT,
    addressline2 TEXT,
    addressline3 TEXT,
    vendor_gstin TEXT,
    vendor_phone TEXT,
    vendor_email TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE customers ADD COLUMN IF NOT EXISTS company_code TEXT;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS ship_to_master_id INTEGER;
ALTER TABLE products ADD COLUMN IF NOT EXISTS customer_id INTEGER;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS customer_id INTEGER;
ALTER TABLE shipments ADD COLUMN IF NOT EXISTS ship_to_master_id INTEGER;
ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS customer_id INTEGER;
ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS ship_to_master_id INTEGER;
CREATE INDEX IF NOT EXISTS idx_customers_ship_to_master_id ON customers(ship_to_master_id);
CREATE INDEX IF NOT EXISTS idx_products_customer_id ON products(customer_id);
CREATE INDEX IF NOT EXISTS idx_shipments_customer_id ON shipments(customer_id);
CREATE INDEX IF NOT EXISTS idx_shipments_ship_to_master_id ON shipments(ship_to_master_id);
CREATE INDEX IF NOT EXISTS idx_customer_deliveries_customer_id ON customer_deliveries(customer_id);
CREATE INDEX IF NOT EXISTS idx_customer_deliveries_ship_to_master_id ON customer_deliveries(ship_to_master_id);
