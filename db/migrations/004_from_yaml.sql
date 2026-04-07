-- Auto-generated database migration from schema/database.yaml
-- Tables: product, orders, complex

-- Product catalog
CREATE TABLE IF NOT EXISTS product (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    price DECIMAL NOT NULL
);

-- Customer orders
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    total DECIMAL NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    status VARCHAR(50) DEFAULT 'pending',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);

-- Complex properties
CREATE TABLE IF NOT EXISTS complex (
    name VARCHAR(255) NOT NULL,
    id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid()
);
