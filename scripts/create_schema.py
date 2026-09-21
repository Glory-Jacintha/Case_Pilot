import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}


def create_schema():
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:

            # ============================================================
            # REFERENCE / BUSINESS DATA
            # ============================================================

            cur.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    customer_id VARCHAR(50) PRIMARY KEY,
                    customer_name TEXT,
                    city TEXT,
                    state TEXT,
                    country TEXT
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    product_id VARCHAR(50) PRIMARY KEY,
                    product_name TEXT,
                    category TEXT,
                    brand TEXT,
                    return_window_days INTEGER,
                    return_eligible BOOLEAN,
                    returnless_refund_eligible BOOLEAN,
                    non_returnable_reason TEXT
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id VARCHAR(50) PRIMARY KEY,
                    order_date TIMESTAMP,
                    customer_id VARCHAR(50),
                    customer_name TEXT,
                    product_id VARCHAR(50),
                    product_name TEXT,
                    category TEXT,
                    brand TEXT,
                    quantity INTEGER,
                    unit_price NUMERIC(12,2),
                    discount NUMERIC(12,2),
                    tax NUMERIC(12,2),
                    shipping_cost NUMERIC(12,2),
                    total_amount NUMERIC(12,2),
                    payment_method TEXT,
                    order_status TEXT,
                    city TEXT,
                    state TEXT,
                    country TEXT,
                    seller_id VARCHAR(50),

                    CONSTRAINT fk_orders_customer
                        FOREIGN KEY (customer_id)
                        REFERENCES customers(customer_id),

                    CONSTRAINT fk_orders_product
                        FOREIGN KEY (product_id)
                        REFERENCES products(product_id)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    transaction_id VARCHAR(50) PRIMARY KEY,
                    order_id VARCHAR(50),
                    customer_id VARCHAR(50),
                    amount NUMERIC(12,2),
                    payment_method TEXT,
                    payment_status TEXT,
                    transaction_date TIMESTAMP,
                    gateway_reference TEXT,

                    CONSTRAINT fk_payments_order
                        FOREIGN KEY (order_id)
                        REFERENCES orders(order_id),

                    CONSTRAINT fk_payments_customer
                        FOREIGN KEY (customer_id)
                        REFERENCES customers(customer_id)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS deliveries (
                    delivery_id VARCHAR(50) PRIMARY KEY,
                    order_id VARCHAR(50),
                    tracking_id TEXT,
                    delivery_status TEXT,
                    expected_date DATE,
                    actual_delivery_date DATE,
                    courier TEXT,
                    delivery_attempts INTEGER,
                    delivery_proof TEXT,

                    CONSTRAINT fk_deliveries_order
                        FOREIGN KEY (order_id)
                        REFERENCES orders(order_id)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS returns (
                    return_id VARCHAR(50) PRIMARY KEY,
                    order_id VARCHAR(50),
                    customer_id VARCHAR(50),
                    return_status TEXT,
                    return_reason TEXT,
                    requested_date DATE,
                    approved_date DATE,

                    CONSTRAINT fk_returns_order
                        FOREIGN KEY (order_id)
                        REFERENCES orders(order_id),

                    CONSTRAINT fk_returns_customer
                        FOREIGN KEY (customer_id)
                        REFERENCES customers(customer_id)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS refunds (
                    refund_id VARCHAR(50) PRIMARY KEY,
                    order_id VARCHAR(50),
                    customer_id VARCHAR(50),
                    transaction_id VARCHAR(50),
                    refund_amount NUMERIC(12,2),
                    refund_status TEXT,
                    refund_reason TEXT,
                    requested_date DATE,
                    processed_date DATE,
                    gateway_reference TEXT,

                    CONSTRAINT fk_refunds_order
                        FOREIGN KEY (order_id)
                        REFERENCES orders(order_id),

                    CONSTRAINT fk_refunds_customer
                        FOREIGN KEY (customer_id)
                        REFERENCES customers(customer_id),

                    CONSTRAINT fk_refunds_transaction
                        FOREIGN KEY (transaction_id)
                        REFERENCES payments(transaction_id)
                );
            """)

            # ============================================================
            # SUPPORT / KNOWLEDGE DATA
            # ============================================================

            cur.execute("""
                CREATE TABLE IF NOT EXISTS support_cases (
                    case_id VARCHAR(100) PRIMARY KEY,
                    customer_id VARCHAR(50),
                    order_id VARCHAR(50),
                    customer_message TEXT,
                    domain TEXT,
                    issue_type TEXT,
                    support_category TEXT,
                    product_name TEXT,
                    product_category TEXT,
                    transaction_amount NUMERIC(12,2),
                    order_status TEXT,
                    reported_at TIMESTAMP,
                    channel TEXT,
                    historical_csat NUMERIC(5,2),
                    amount_band TEXT,

                    status TEXT DEFAULT 'OPEN',
                    requires_human BOOLEAN DEFAULT FALSE,
                    resolution_success BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    CONSTRAINT fk_support_customer
                        FOREIGN KEY (customer_id)
                        REFERENCES customers(customer_id),

                    CONSTRAINT fk_support_order
                        FOREIGN KEY (order_id)
                        REFERENCES orders(order_id)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS resolution_strategies (
                    domain TEXT,
                    strategy_id VARCHAR(100),
                    description TEXT,
                    tool_sequence TEXT,
                    action_type TEXT,

                    PRIMARY KEY (domain, strategy_id)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS case_history_examples (
                    id BIGSERIAL PRIMARY KEY,
                    case_id VARCHAR(...) NOT NULL,
                    scenario TEXT,
                    domain TEXT,
                    case_description TEXT,
                    attempt TEXT,
                    result TEXT,
                    reason_or_next_step TEXT
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS data_dictionary (
                    file TEXT PRIMARY KEY,
                    purpose TEXT,
                    important_fields TEXT
                );
            """)

            # ============================================================
            # APPLICATION USERS
            # ============================================================

            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id UUID PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # ============================================================
            # CONVERSATIONS
            # ============================================================

            cur.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id UUID PRIMARY KEY,
                    user_id UUID NOT NULL,
                    title TEXT DEFAULT 'New Chat',
                    status TEXT DEFAULT 'ACTIVE',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    CONSTRAINT fk_conversations_user
                        FOREIGN KEY (user_id)
                        REFERENCES users(user_id)
                        ON DELETE CASCADE
                );
            """)

            # ============================================================
            # CHAT MESSAGES
            # ============================================================

            cur.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id UUID PRIMARY KEY,
                    conversation_id UUID NOT NULL,
                    role VARCHAR(30) NOT NULL,
                    content TEXT NOT NULL,
                    metadata JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    CONSTRAINT fk_messages_conversation
                        FOREIGN KEY (conversation_id)
                        REFERENCES conversations(conversation_id)
                        ON DELETE CASCADE
                );
            """)

            # ============================================================
            # RESOLUTION ATTEMPTS
            # ============================================================

            cur.execute("""
                CREATE TABLE IF NOT EXISTS resolution_attempts (
                    attempt_id UUID PRIMARY KEY,
                    case_id VARCHAR(100),
                    attempt_number INTEGER NOT NULL,
                    strategy VARCHAR(100) NOT NULL,
                    action TEXT,
                    success BOOLEAN DEFAULT FALSE,
                    error_code TEXT,
                    reason TEXT,
                    result JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    CONSTRAINT fk_attempt_case
                        FOREIGN KEY (case_id)
                        REFERENCES support_cases(case_id)
                        ON DELETE CASCADE
                );
            """)

            # ============================================================
            # INDEXES
            # ============================================================

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_orders_customer
                ON orders(customer_id);
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_payments_order
                ON payments(order_id);
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_deliveries_order
                ON deliveries(order_id);
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_returns_order
                ON returns(order_id);
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_refunds_order
                ON refunds(order_id);
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_support_cases_customer
                ON support_cases(customer_id);
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_support_cases_order
                ON support_cases(order_id);
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_user
                ON conversations(user_id);
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_conversation
                ON messages(conversation_id);
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_created
                ON messages(created_at);
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_resolution_attempts_case
                ON resolution_attempts(case_id);
            """)

            conn.commit()

    print("Database schema created successfully!")


if __name__ == "__main__":
    create_schema()