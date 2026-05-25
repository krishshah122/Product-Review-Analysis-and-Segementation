DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS reviews;

CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    signup_date TEXT,
    region TEXT,
    age_group TEXT,
    acquisition_channel TEXT
);

CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT,
    order_date TEXT,
    product_id TEXT,
    product_name TEXT,
    category TEXT,
    order_value REAL,
    discount_pct REAL,
    is_returned INTEGER,
    ab_group TEXT,
    converted INTEGER,
    retained_30d INTEGER,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE reviews (
    review_id TEXT PRIMARY KEY,
    order_id TEXT,
    customer_id TEXT,
    review_date TEXT,
    rating INTEGER,
    review_title TEXT,
    review_text TEXT,
    review_topic TEXT,
    verified_purchase INTEGER,
    helpful_votes INTEGER,
    source_product_id TEXT,
    sentiment_label TEXT,
    sentiment_score REAL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);
