/*
  # Awab Reselling Dashboard - Database Schema

  Complete schema for personal reselling business tracking across multiple platforms.
  Replaces the Vinted notifications schema with proper reselling operations tables.

  ## Tables Created:
  1. inventory - Product catalog with purchase, listing, and sale tracking
  2. sales - Completed sales with profit calculations
  3. shipments - Shipping and dispatch tracking
  4. returns - Return cases and disputes
  5. tasks - Workflow and todo management
  6. settings - Application configuration

  ## Security:
  - RLS enabled on all tables
  - Single-user application (no auth.uid() checks needed)
*/

-- Drop old tables
DROP TABLE IF EXISTS items CASCADE;
DROP TABLE IF EXISTS queries CASCADE;
DROP TABLE IF EXISTS allowlist CASCADE;
DROP TABLE IF EXISTS parameters CASCADE;

-- ============================
-- INVENTORY TABLE
-- ============================
CREATE TABLE IF NOT EXISTS inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku TEXT UNIQUE NOT NULL,
    item_name TEXT NOT NULL,
    category TEXT,
    size TEXT,
    condition TEXT CHECK (condition IN ('New', 'Like New', 'Good', 'Fair', 'Poor')),
    brand TEXT,
    platforms TEXT[], -- ['Vinted', 'eBay', 'Depop']
    listing_status TEXT DEFAULT 'Draft' CHECK (listing_status IN ('Draft', 'Listed', 'Sold', 'Returned', 'Archived')),
    purchase_price NUMERIC(10, 2) DEFAULT 0,
    fees_estimate NUMERIC(10, 2) DEFAULT 0,
    shipping_paid_by TEXT DEFAULT 'Buyer' CHECK (shipping_paid_by IN ('Buyer', 'Seller')),
    shipping_cost NUMERIC(10, 2) DEFAULT 0,
    sale_price NUMERIC(10, 2),
    profit NUMERIC(10, 2),
    roi_percent NUMERIC(5, 2),
    date_purchased DATE,
    date_listed DATE,
    date_sold DATE,
    storage_location TEXT,
    notes TEXT,
    photos TEXT[], -- Array of photo URLs
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================
-- SALES TABLE
-- ============================
CREATE TABLE IF NOT EXISTS sales (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id TEXT UNIQUE NOT NULL,
    inventory_id UUID REFERENCES inventory(id) ON DELETE SET NULL,
    platform TEXT NOT NULL,
    item_name TEXT NOT NULL,
    sale_price NUMERIC(10, 2) NOT NULL,
    platform_fees NUMERIC(10, 2) DEFAULT 0,
    payment_processing_fees NUMERIC(10, 2) DEFAULT 0,
    shipping_cost NUMERIC(10, 2) DEFAULT 0,
    buyer_paid_shipping BOOLEAN DEFAULT true,
    net_profit NUMERIC(10, 2),
    date_sold DATE NOT NULL,
    date_shipped DATE,
    tracking_number TEXT,
    payout_status TEXT DEFAULT 'Pending' CHECK (payout_status IN ('Pending', 'Processing', 'Paid', 'On Hold')),
    payout_date DATE,
    buyer_name TEXT,
    buyer_address TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================
-- SHIPMENTS TABLE
-- ============================
CREATE TABLE IF NOT EXISTS shipments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sale_id UUID REFERENCES sales(id) ON DELETE CASCADE,
    carrier TEXT,
    tracking_number TEXT,
    label_cost NUMERIC(10, 2) DEFAULT 0,
    dispatch_deadline DATE,
    status TEXT DEFAULT 'Pending Label' CHECK (status IN ('Pending Label', 'Label Created', 'Shipped', 'In Transit', 'Delivered', 'Problem')),
    shipped_date DATE,
    delivered_date DATE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================
-- RETURNS TABLE
-- ============================
CREATE TABLE IF NOT EXISTS returns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sale_id UUID REFERENCES sales(id) ON DELETE SET NULL,
    order_id TEXT,
    reason TEXT,
    status TEXT DEFAULT 'Opened' CHECK (status IN ('Opened', 'In Progress', 'Resolved', 'Rejected')),
    date_opened DATE NOT NULL,
    date_closed DATE,
    expected_loss NUMERIC(10, 2),
    actual_loss NUMERIC(10, 2),
    resolution TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================
-- TASKS TABLE
-- ============================
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    category TEXT CHECK (category IN ('Photography', 'Listing', 'Packing', 'Shipping', 'Customer Service', 'Sourcing', 'Other')),
    priority TEXT DEFAULT 'Medium' CHECK (priority IN ('Low', 'Medium', 'High', 'Urgent')),
    status TEXT DEFAULT 'Todo' CHECK (status IN ('Todo', 'In Progress', 'Done', 'Cancelled')),
    due_date DATE,
    completed_date DATE,
    related_inventory_id UUID REFERENCES inventory(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================
-- SETTINGS TABLE
-- ============================
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================
-- INDEXES
-- ============================
CREATE INDEX IF NOT EXISTS idx_inventory_status ON inventory(listing_status);
CREATE INDEX IF NOT EXISTS idx_inventory_brand ON inventory(brand);
CREATE INDEX IF NOT EXISTS idx_inventory_date_purchased ON inventory(date_purchased);
CREATE INDEX IF NOT EXISTS idx_inventory_date_sold ON inventory(date_sold);

CREATE INDEX IF NOT EXISTS idx_sales_platform ON sales(platform);
CREATE INDEX IF NOT EXISTS idx_sales_date_sold ON sales(date_sold);
CREATE INDEX IF NOT EXISTS idx_sales_payout_status ON sales(payout_status);

CREATE INDEX IF NOT EXISTS idx_shipments_status ON shipments(status);
CREATE INDEX IF NOT EXISTS idx_shipments_dispatch_deadline ON shipments(dispatch_deadline);

CREATE INDEX IF NOT EXISTS idx_returns_status ON returns(status);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);

-- ============================
-- ROW LEVEL SECURITY
-- ============================
ALTER TABLE inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE sales ENABLE ROW LEVEL SECURITY;
ALTER TABLE shipments ENABLE ROW LEVEL SECURITY;
ALTER TABLE returns ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;

-- Since this is a single-user personal dashboard, allow all operations
-- In production, you'd restrict these to authenticated users

CREATE POLICY "Allow all operations on inventory"
    ON inventory FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow all operations on sales"
    ON sales FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow all operations on shipments"
    ON shipments FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow all operations on returns"
    ON returns FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow all operations on tasks"
    ON tasks FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow all operations on settings"
    ON settings FOR ALL
    USING (true)
    WITH CHECK (true);

-- ============================
-- DEFAULT SETTINGS
-- ============================
INSERT INTO settings (key, value) VALUES
    ('currency', 'GBP'),
    ('vinted_fee_percent', '5.0'),
    ('ebay_fee_percent', '12.8'),
    ('depop_fee_percent', '10.0'),
    ('paypal_fee_percent', '3.4'),
    ('default_shipping_buyer', 'true'),
    ('app_version', '2.0.0'),
    ('app_name', 'Awab Reselling Dashboard')
ON CONFLICT (key) DO NOTHING;
