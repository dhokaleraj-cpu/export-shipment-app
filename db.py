DATA_RETENTION_NOTE = "This application uses non-destructive migrations; replacing db.py does not delete existing database rows."

import os
import hashlib
import time
from dotenv import load_dotenv

try:
    import streamlit as st
except Exception:
    st = None

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL") or os.getenv("POSTGRES_URL")
if not DATABASE_URL and st is not None:
    try:
        DATABASE_URL = st.secrets["DATABASE_URL"]
    except Exception:
        DATABASE_URL = None

_DRIVER = None
try:
    import psycopg
    from psycopg.rows import dict_row
    _DRIVER = "psycopg3"
except Exception:
    psycopg = None
    dict_row = None

if _DRIVER is None:
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        _DRIVER = "psycopg2"
    except Exception:
        psycopg2 = None
        RealDictCursor = None


def convert_sqlite_to_postgres(query: str) -> str:
    query = str(query)
    if "%s" not in query:
        query = query.replace("?", "%s")
    query = query.replace("date('now')", "CURRENT_DATE")
    query = query.replace('date("now")', "CURRENT_DATE")
    query = query.replace("strftime('%Y-%m', d.delivery_date)", "to_char(d.delivery_date::date, 'YYYY-MM')")
    query = query.replace("strftime('%Y-%m', p.payment_received_date)", "to_char(p.payment_received_date::date, 'YYYY-MM')")
    query = query.replace("IFNULL", "COALESCE")
    return query


def get_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured in Streamlit secrets/environment.")
    if _DRIVER == "psycopg3":
        return psycopg.connect(
            DATABASE_URL,
            row_factory=dict_row,
            connect_timeout=15,
            sslmode="require",
        )
    if _DRIVER == "psycopg2":
        return psycopg2.connect(
            DATABASE_URL,
            cursor_factory=RealDictCursor,
            sslmode="require",
            connect_timeout=15,
        )
    raise RuntimeError("No PostgreSQL driver available. requirements.txt must include psycopg[binary].")


def _is_connection_error(exc):
    text = str(exc).lower()
    return (
        "connection pool exhausted" in text
        or "ssl syscall" in text
        or "operation timed out" in text
        or "server closed the connection" in text
        or "connection already closed" in text
        or "cursor already closed" in text
        or "closed cursor" in text
        or "could not receive data from server" in text
        or "could not send data to server" in text
    )


def fetch_all(query, params=()):
    query = convert_sqlite_to_postgres(query)
    last_error = None
    for attempt in range(3):
        conn = None
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                try:
                    cur.execute("SET statement_timeout = '45s'")
                    cur.execute("SET idle_in_transaction_session_timeout = '30s'")
                except Exception:
                    pass
                cur.execute(query, tuple(params or ()))
                rows = cur.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            last_error = e
            try:
                if conn:
                    conn.rollback()
            except Exception:
                pass
            if _is_connection_error(e) and attempt < 2:
                time.sleep(0.4)
                continue
            raise
        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                pass
    raise last_error


def fetch_one(query, params=()):
    rows = fetch_all(query, params)
    return rows[0] if rows else None


def execute_query(query, params=()):
    query = convert_sqlite_to_postgres(query)
    last_error = None
    for attempt in range(3):
        conn = None
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                try:
                    cur.execute("SET statement_timeout = '45s'")
                    cur.execute("SET idle_in_transaction_session_timeout = '30s'")
                except Exception:
                    pass
                cur.execute(query, tuple(params or ()))
            conn.commit()
            return
        except Exception as e:
            last_error = e
            try:
                if conn:
                    conn.rollback()
            except Exception:
                pass
            if _is_connection_error(e) and attempt < 2:
                time.sleep(0.4)
                continue
            raise
        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                pass
    raise last_error


def execute_many(query, param_list):
    query = convert_sqlite_to_postgres(query)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for params in (param_list or []):
                cur.execute(query, tuple(params or ()))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def hash_password(password):
    return hashlib.sha256(str(password or "").encode()).hexdigest()


def verify_user(username, password):
    rows = fetch_all(
        "SELECT * FROM users WHERE username=? AND password_hash=? AND is_active=TRUE",
        (username, hash_password(password)),
    )
    return rows[0] if rows else None


def init_db():
    """Lightweight non-destructive migrations for existing Supabase/PostgreSQL database."""
    migrations = [
        "ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS packaging_remark TEXT",
        "CREATE INDEX IF NOT EXISTS idx_shipments_invoice_no ON shipments(invoice_no)",
        "CREATE INDEX IF NOT EXISTS idx_shipments_warehouse_id ON shipments(warehouse_id)",
        "CREATE INDEX IF NOT EXISTS idx_shipment_boxes_shipment_id ON shipment_boxes(shipment_id)",
        "CREATE INDEX IF NOT EXISTS idx_shipment_boxes_product_id ON shipment_boxes(product_id)",
        "CREATE INDEX IF NOT EXISTS idx_customer_deliveries_delivery_date ON customer_deliveries(delivery_date)",
        "CREATE INDEX IF NOT EXISTS idx_customer_deliveries_shipment_id ON customer_deliveries(shipment_id)",
        "CREATE INDEX IF NOT EXISTS idx_customer_deliveries_box_id ON customer_deliveries(box_id)",
        "CREATE INDEX IF NOT EXISTS idx_customer_deliveries_invoice_no ON customer_deliveries(delivery_invoice_no)",
        "CREATE INDEX IF NOT EXISTS idx_payments_delivery_id ON payments(delivery_id)",
        "CREATE TABLE IF NOT EXISTS user_product_access (id SERIAL PRIMARY KEY, username TEXT NOT NULL, product_id INTEGER NOT NULL, can_access BOOLEAN DEFAULT TRUE, UNIQUE(username, product_id))",
        "CREATE TABLE IF NOT EXISTS user_warehouse_access (id SERIAL PRIMARY KEY, username TEXT NOT NULL, warehouse_id INTEGER NOT NULL, can_access BOOLEAN DEFAULT TRUE, UNIQUE(username, warehouse_id))",
        "ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS warehouse_id INTEGER",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS warehouse_id INTEGER",
        "ALTER TABLE page_permissions ADD COLUMN IF NOT EXISTS can_modify BOOLEAN DEFAULT FALSE",
        "ALTER TABLE user_page_access ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE customers ADD COLUMN IF NOT EXISTS company_code TEXT",
        "ALTER TABLE user_page_access ADD COLUMN IF NOT EXISTS can_modify BOOLEAN DEFAULT FALSE",
        "ALTER TABLE shipment_boxes ADD COLUMN IF NOT EXISTS po_number TEXT",
        "ALTER TABLE shipment_boxes ADD COLUMN IF NOT EXISTS po_date DATE",
        "ALTER TABLE shipment_boxes ADD COLUMN IF NOT EXISTS fifo_row_id INTEGER",
        "CREATE INDEX IF NOT EXISTS idx_shipment_boxes_fifo_row_id ON shipment_boxes(fifo_row_id)",
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS customer_id INTEGER",
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS ship_to_master_id INTEGER",
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS shipment_time_days INTEGER DEFAULT 0",
        "ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS ship_to_master_id INTEGER",
        "ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS po_number TEXT",
        "ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS po_date DATE",
        "ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS vehicle_number TEXT",
        "ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS asn_number TEXT",
        "ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS asn_date DATE",
        "ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS packaging_details TEXT",
        """
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
        )
        """,
    ]
    for q in migrations:
        try:
            execute_query(q)
        except Exception:
            pass
    return True
