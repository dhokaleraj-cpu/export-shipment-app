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

MASTER_RELATIONSHIP_SCHEMA_VERSION = "SN 27.13"

MASTER_RELATIONSHIP_MIGRATIONS = [
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
    "ALTER TABLE ship_to_masters ADD COLUMN IF NOT EXISTS ship_to_name TEXT",
    "ALTER TABLE ship_to_masters ADD COLUMN IF NOT EXISTS ship_to_id TEXT",
    "ALTER TABLE ship_to_masters ADD COLUMN IF NOT EXISTS addressline1 TEXT",
    "ALTER TABLE ship_to_masters ADD COLUMN IF NOT EXISTS addressline2 TEXT",
    "ALTER TABLE ship_to_masters ADD COLUMN IF NOT EXISTS addressline3 TEXT",
    "ALTER TABLE ship_to_masters ADD COLUMN IF NOT EXISTS vendor_gstin TEXT",
    "ALTER TABLE ship_to_masters ADD COLUMN IF NOT EXISTS vendor_phone TEXT",
    "ALTER TABLE ship_to_masters ADD COLUMN IF NOT EXISTS vendor_email TEXT",
    "ALTER TABLE ship_to_masters ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
    "ALTER TABLE ship_to_masters ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "ALTER TABLE customers ADD COLUMN IF NOT EXISTS company_code TEXT",
    "ALTER TABLE customers ADD COLUMN IF NOT EXISTS ship_to_master_id INTEGER",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS customer_id INTEGER",
    # Retained for backward compatibility only. The canonical SN 27.13 chain is
    # Product.customer_id -> Customer.ship_to_master_id.
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS ship_to_master_id INTEGER",
    "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS customer_id INTEGER",
    "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS ship_to_master_id INTEGER",
    "ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS customer_id INTEGER",
    "ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS ship_to_master_id INTEGER",
    "ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS ship_via TEXT DEFAULT 'Road'",
    "ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS packaging_remark TEXT",
    "ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS vehicle_number TEXT",
    "ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS asn_number TEXT",
    "ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS asn_date DATE",
    "ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS packaging_details TEXT",
    "CREATE INDEX IF NOT EXISTS idx_products_customer_id ON products(customer_id)",
    "CREATE INDEX IF NOT EXISTS idx_products_ship_to_master_id ON products(ship_to_master_id)",
    "CREATE INDEX IF NOT EXISTS idx_customers_ship_to_master_id ON customers(ship_to_master_id)",
    "CREATE INDEX IF NOT EXISTS idx_shipments_customer_id ON shipments(customer_id)",
    "CREATE INDEX IF NOT EXISTS idx_shipments_ship_to_master_id ON shipments(ship_to_master_id)",
    "CREATE INDEX IF NOT EXISTS idx_customer_deliveries_customer_id ON customer_deliveries(customer_id)",
    "CREATE INDEX IF NOT EXISTS idx_customer_deliveries_ship_to_master_id ON customer_deliveries(ship_to_master_id)",
]

MASTER_RELATIONSHIP_REQUIRED_COLUMNS = {
    ("ship_to_masters", "id"),
    ("ship_to_masters", "ship_to_name"),
    ("ship_to_masters", "ship_to_id"),
    ("ship_to_masters", "addressline1"),
    ("ship_to_masters", "addressline2"),
    ("ship_to_masters", "addressline3"),
    ("ship_to_masters", "is_active"),
    ("ship_to_masters", "created_at"),
    ("customers", "id"),
    ("customers", "customer_name"),
    ("customers", "address"),
    ("customers", "payment_term_id"),
    ("customers", "ship_to_master_id"),
    ("products", "id"),
    ("products", "product_code"),
    ("products", "customer_id"),
    ("shipments", "customer_id"),
    ("shipments", "ship_to_master_id"),
    ("customer_deliveries", "customer_id"),
    ("customer_deliveries", "ship_to_master_id"),
    ("customer_deliveries", "ship_via"),
}


def ensure_master_relationship_schema():
    """Create and verify Product -> Customer -> Ship To fields.

    Every migration is additive. No existing master or transaction row is
    deleted, reset, truncated, or overwritten.
    """
    errors = []
    for sql in MASTER_RELATIONSHIP_MIGRATIONS:
        try:
            execute_query(sql)
        except Exception as exc:
            errors.append({
                "sql": " ".join(str(sql).split())[:240],
                "error": str(exc),
            })

    found = set()
    verification_error = ""
    try:
        rows = fetch_all("""
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
              AND table_name IN ('ship_to_masters','customers','products','shipments','customer_deliveries')
        """)
        found = {
            (str(row.get("table_name") or ""), str(row.get("column_name") or ""))
            for row in rows
        }
    except Exception as exc:
        verification_error = str(exc)

    missing = sorted(MASTER_RELATIONSHIP_REQUIRED_COLUMNS - found)
    return {
        "ok": not errors and not verification_error and not missing,
        "version": MASTER_RELATIONSHIP_SCHEMA_VERSION,
        "missing": [f"{table}.{column}" for table, column in missing],
        "errors": errors,
        "verification_error": verification_error,
    }


def apply_master_relationship_migrations(raise_on_error=False):
    """Compatibility wrapper used by init_db and the deployment migrator."""
    status = ensure_master_relationship_schema()
    if raise_on_error and not status.get("ok"):
        details = [item.get("error", "") for item in status.get("errors", [])]
        details.extend(status.get("missing", []))
        if status.get("verification_error"):
            details.append(status["verification_error"])
        raise RuntimeError("; ".join(x for x in details if x) or "Master relationship migration failed")
    return bool(status.get("ok")), status


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
    apply_master_relationship_migrations(raise_on_error=False)
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
        """
        CREATE TABLE IF NOT EXISTS product_price_history (
            id SERIAL PRIMARY KEY,
            product_id INTEGER NOT NULL,
            currency TEXT,
            price NUMERIC(18,6) NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE,
            remarks TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_product_price_history_product_dates ON product_price_history(product_id, start_date, end_date)",
        "ALTER TABLE product_price_history ADD COLUMN IF NOT EXISTS po_number TEXT",
        "ALTER TABLE product_price_history ADD COLUMN IF NOT EXISTS po_date DATE",
        "ALTER TABLE product_price_history ADD COLUMN IF NOT EXISTS po_copy_path TEXT",
        "CREATE TABLE IF NOT EXISTS user_product_access (id SERIAL PRIMARY KEY, username TEXT NOT NULL, product_id INTEGER NOT NULL, can_access BOOLEAN DEFAULT TRUE, UNIQUE(username, product_id))",
        "CREATE TABLE IF NOT EXISTS user_warehouse_access (id SERIAL PRIMARY KEY, username TEXT NOT NULL, warehouse_id INTEGER NOT NULL, can_access BOOLEAN DEFAULT TRUE, UNIQUE(username, warehouse_id))",
        "ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS warehouse_id INTEGER",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS warehouse_id INTEGER",
        "ALTER TABLE page_permissions ADD COLUMN IF NOT EXISTS can_modify BOOLEAN DEFAULT FALSE",
        "ALTER TABLE user_page_access ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE customers ADD COLUMN IF NOT EXISTS company_code TEXT",
        "ALTER TABLE customers ADD COLUMN IF NOT EXISTS ship_to_master_id INTEGER",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS customer_id INTEGER",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS ship_to_master_id INTEGER",
        "ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS ship_via TEXT DEFAULT 'Road'",
        "CREATE INDEX IF NOT EXISTS idx_products_customer_id ON products(customer_id)",
        "CREATE INDEX IF NOT EXISTS idx_products_ship_to_master_id ON products(ship_to_master_id)",
        "CREATE INDEX IF NOT EXISTS idx_customers_ship_to_master_id ON customers(ship_to_master_id)",
        "ALTER TABLE user_page_access ADD COLUMN IF NOT EXISTS can_modify BOOLEAN DEFAULT FALSE",
        "ALTER TABLE shipment_boxes ADD COLUMN IF NOT EXISTS po_number TEXT",
        "ALTER TABLE shipment_boxes ADD COLUMN IF NOT EXISTS po_date DATE",
        "ALTER TABLE shipment_boxes ADD COLUMN IF NOT EXISTS fifo_row_id INTEGER",
        "CREATE INDEX IF NOT EXISTS idx_shipment_boxes_fifo_row_id ON shipment_boxes(fifo_row_id)",
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS customer_id INTEGER",
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS ship_to_master_id INTEGER",
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS shipment_time_days INTEGER DEFAULT 0",
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS shipment_status TEXT DEFAULT 'In Transit'",
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS warehouse_delivery_date DATE",
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS shipment_status_updated_at TIMESTAMP",
        "CREATE INDEX IF NOT EXISTS idx_shipments_status_wh_date ON shipments(shipment_status, warehouse_delivery_date)",
        "ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS ship_to_master_id INTEGER",
        "CREATE INDEX IF NOT EXISTS idx_customer_deliveries_customer_id ON customer_deliveries(customer_id)",
        "CREATE INDEX IF NOT EXISTS idx_customer_deliveries_ship_to_master_id ON customer_deliveries(ship_to_master_id)",
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
