-- =========================================================
-- Healthyma Database Schema (MySQL)
-- Run this once in MySQL Workbench / CLI before starting the backend
-- =========================================================

CREATE DATABASE IF NOT EXISTS healthyma;
USE healthyma;

-- ---------- USERS (phone number login) ----------
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    phone VARCHAR(15) UNIQUE NOT NULL,
    otp VARCHAR(6),
    otp_expiry DATETIME,
    is_verified TINYINT(1) DEFAULT 0,
    is_blocked TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ---------- PRODUCTS ----------
CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category_id INT NULL,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NULL,
    category VARCHAR(100) NOT NULL,
    short_description TEXT,
    price DECIMAL(10,2) NOT NULL,
    original_price DECIMAL(10,2) NULL,
    discount_percentage DECIMAL(5,2) DEFAULT 0,
    weight VARCHAR(50) NULL,
    unit VARCHAR(30) NULL,
    sku VARCHAR(120),
    image_url VARCHAR(500) DEFAULT '/images/default-product.jpg',
    description TEXT,
    ingredients TEXT,
    benefits TEXT,
    usage_instructions TEXT,
    storage_instructions TEXT,
    stock INT DEFAULT 100,
    low_stock_limit INT DEFAULT 10,
    is_premium BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    is_best_seller BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- If your existing products table was created before these columns, run these safely one by one.
-- ALTER TABLE products ADD COLUMN original_price DECIMAL(10,2) NULL;
-- ALTER TABLE products ADD COLUMN discount_percentage DECIMAL(5,2) DEFAULT 0;
-- ALTER TABLE products ADD COLUMN weight VARCHAR(50) NULL;
-- ALTER TABLE products ADD COLUMN unit VARCHAR(30) NULL;
-- ALTER TABLE products ADD COLUMN low_stock_limit INT DEFAULT 10;
-- ALTER TABLE products ADD COLUMN is_featured BOOLEAN DEFAULT FALSE;
-- ALTER TABLE products ADD COLUMN is_best_seller BOOLEAN DEFAULT FALSE;
-- ALTER TABLE products ADD COLUMN is_premium BOOLEAN DEFAULT TRUE;
-- ALTER TABLE products ADD COLUMN is_active BOOLEAN DEFAULT TRUE;

-- ---------- CART ----------
CREATE TABLE IF NOT EXISTS cart (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT DEFAULT 1,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- ---------- DELIVERY ADDRESSES ----------
CREATE TABLE IF NOT EXISTS addresses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    label VARCHAR(80) DEFAULT 'Home',
    full_name VARCHAR(120) NOT NULL,
    mobile VARCHAR(10) NOT NULL,
    alternate_mobile VARCHAR(10),
    house VARCHAR(180) NOT NULL,
    street VARCHAR(220) NOT NULL,
    area VARCHAR(160) NOT NULL,
    landmark VARCHAR(180),
    city VARCHAR(120) NOT NULL,
    state VARCHAR(120) NOT NULL,
    pincode VARCHAR(6) NOT NULL,
    delivery_instructions TEXT,
    latitude VARCHAR(40),
    longitude VARCHAR(40),
    is_default TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_addresses_user (user_id),
    INDEX idx_addresses_pincode (pincode),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ---------- ORDERS ----------
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_number VARCHAR(32) UNIQUE NOT NULL,
    user_id INT NOT NULL,
    address_id INT NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    product_discount DECIMAL(10,2) DEFAULT 0,
    coupon_discount DECIMAL(10,2) DEFAULT 0,
    delivery_fee DECIMAL(10,2) DEFAULT 0,
    cod_fee DECIMAL(10,2) DEFAULT 0,
    tax_amount DECIMAL(10,2) DEFAULT 0,
    grand_total DECIMAL(10,2) NOT NULL,
    payment_method ENUM('COD','ONLINE') NOT NULL,
    payment_status VARCHAR(40) DEFAULT 'PENDING',
    order_status VARCHAR(40) DEFAULT 'PLACED',
    customer_note TEXT,
    cancellation_reason TEXT,
    idempotency_key VARCHAR(80),
    razorpay_order_id VARCHAR(120),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP NULL,
    paid_at TIMESTAMP NULL,
    delivered_at TIMESTAMP NULL,
    INDEX idx_orders_user (user_id),
    INDEX idx_orders_payment (payment_status),
    UNIQUE KEY uniq_user_idempotency (user_id, idempotency_key),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (address_id) REFERENCES addresses(id)
);

CREATE TABLE IF NOT EXISTS order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    quantity INT NOT NULL,
    line_total DECIMAL(10,2) NOT NULL,
    INDEX idx_order_items_order (order_id),
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    provider VARCHAR(40) NOT NULL,
    provider_order_id VARCHAR(120),
    provider_payment_id VARCHAR(120),
    provider_signature VARCHAR(255),
    status VARCHAR(40) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'INR',
    failure_code VARCHAR(120),
    failure_reason TEXT,
    raw_payload JSON,
    paid_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_payments_order (order_id),
    INDEX idx_payments_provider_order (provider_order_id),
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL UNIQUE,
    slug VARCHAR(140) NOT NULL UNIQUE,
    image_url VARCHAR(500),
    is_active TINYINT(1) DEFAULT 1,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS coupons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(60) UNIQUE NOT NULL,
    discount_type VARCHAR(30) NOT NULL,
    discount_value DECIMAL(10,2) NOT NULL,
    minimum_order DECIMAL(10,2) DEFAULT 0,
    maximum_discount DECIMAL(10,2),
    start_date DATETIME,
    end_date DATETIME,
    usage_limit INT,
    used_count INT DEFAULT 0,
    is_active TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_status_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    old_status VARCHAR(40),
    new_status VARCHAR(40) NOT NULL,
    note TEXT,
    changed_by VARCHAR(80),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS payment_webhook_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    provider VARCHAR(40) NOT NULL,
    event_id VARCHAR(160) UNIQUE,
    event_type VARCHAR(120),
    raw_payload JSON NOT NULL,
    processed TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------- SAMPLE PRODUCTS (edit / add your own anytime) ----------
INSERT INTO products (
    name, category, price, original_price, discount_percentage, weight, unit,
    image_url, description, stock, is_premium, is_active
) VALUES
('Moringa Mix Powder', 'Health Mix', 180.00, 220.00, 18.18, '250', 'g', '/images/moringa-mix-powder.jpeg', 'Premium moringa leaf podi made for everyday nutrition.', 100, TRUE, TRUE),
('Curry Leaf Mix', 'Health Mix', 160.00, 199.00, 19.60, '250', 'g', '/images/curry-leaf-mix.jpeg', 'Traditional karuveppilai podi with natural curry leaves and spices.', 100, TRUE, TRUE),
('Millet Atta', 'Millet Flour', 220.00, 260.00, 15.38, '1', 'kg', '/images/millet-atta.jpeg', 'Multigrain millet flour with ragi, kambu, thinai, samai and kuthiravali.', 150, TRUE, TRUE),
('Kambu Ragi Mix', 'Millet Flour', 210.00, 250.00, 16.00, '1', 'kg', '/images/kambu-ragi-mix.jpeg', 'Nutritious kambu, ragi and millet flour mix for daily cooking.', 150, TRUE, TRUE),
('Corn Flour', 'Flour', 120.00, 150.00, 20.00, '500', 'g', '/images/corn-flour.jpeg', 'Pure corn flour for cooking, baking and everyday kitchen use.', 120, TRUE, TRUE);
