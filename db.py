import os
import hashlib
import time
import psycopg2
import psycopg2.pool
import streamlit as st
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    try:
        DATABASE_URL = st.secrets["DATABASE_URL"]
    except Exception:
        DATABASE_URL = None

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not configured")

_POOL = None

def convert_sqlite_to_postgres(query: str) -> str:
    query = query.replace("?", "%s")
    query = query.replace("date('now')", "CURRENT_DATE")
    query = query.replace('date("now")', "CURRENT_DATE")
    query = query.replace("strftime('%Y-%m', d.delivery_date)", "to_char(d.delivery_date::date, 'YYYY-MM')")
    query = query.replace("strftime('%Y-%m', p.payment_received_date)", "to_char(p.payment_received_date::date, 'YYYY-MM')")
    query = query.replace("IFNULL", "COALESCE")
    return query


def _escape_percent_literals_for_psycopg(query: str, params=()):
    """psycopg2 uses % for placeholders.

    Queries like LIKE '%' || %s || '%' cause 'tuple index out of range'
    because the literal % is parsed as a placeholder marker.
    Escape all percent literals, then restore %s placeholders.
    """
    if params and isinstance(query, str) and "%" in query:
        query = query.replace("%", "%%").replace("%%s", "%s")
    return query

def reset_pool():
    """Close and recreate PostgreSQL pool after stale SSL timeout errors."""
    global _POOL
    if _POOL is not None:
        try:
            _POOL.closeall()
        except Exception:
            pass
    _POOL = None

def get_pool():
    """Create/reuse PostgreSQL pool.

    maxconn increased because Streamlit can rerun pages quickly and multiple
    cached/dashboard queries may overlap. Pool exhaustion is also handled below
    by reset-and-retry.
    """
    global _POOL
    if _POOL is None:
        _POOL = SimpleConnectionPool(
            minconn=1,
            maxconn=15,
            dsn=DATABASE_URL,
            cursor_factory=RealDictCursor,
            sslmode="require",
            connect_timeout=15,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5,
        )
    return _POOL

def get_connection():
    """Get a healthy PostgreSQL connection.

    Fixes stale pool / closed cursor / closed connection issues that can happen
    after Streamlit reruns or network timeout.
    """
    last_error = None

    for attempt in range(3):
        conn = None
        try:
            conn = get_pool().getconn()

            # If pool returned a closed connection, discard it.
            if conn is None or getattr(conn, "closed", 1):
                try:
                    get_pool().putconn(conn, close=True)
                except Exception:
                    pass
                reset_pool()
                time.sleep(0.2)
                continue

            # Validate connection with a very small query. Do not use the
            # connection if cursor/session setup fails.
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.execute("SET statement_timeout = '45s'")
                    cur.execute("SET idle_in_transaction_session_timeout = '30s'")
            except Exception as setup_error:
                last_error = setup_error
                try:
                    get_pool().putconn(conn, close=True)
                except Exception:
                    pass
                conn = None
                reset_pool()
                time.sleep(0.3)
                continue

            return conn

        except Exception as e:
            last_error = e
            try:
                if conn is not None:
                    get_pool().putconn(conn, close=True)
            except Exception:
                pass
            reset_pool()
            time.sleep(0.3)

    raise last_error


def release_connection(conn, close=False):
    if conn is not None:
        try:
            get_pool().putconn(conn, close=close)
        except Exception:
            reset_pool()

def _is_connection_error(exc):
    text = str(exc).lower()
    return (
        isinstance(exc, (psycopg2.OperationalError, psycopg2.InterfaceError, psycopg2.pool.PoolError))
        or "connection pool exhausted" in text
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
    query = _escape_percent_literals_for_psycopg(query, params)
    last_error = None

    for attempt in range(4):
        conn = None
        released = False
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
                return [dict(row) for row in rows]

        except Exception as e:
            last_error = e
            try:
                if conn:
                    conn.rollback()
            except Exception:
                pass

            # Always discard bad connections on cursor/connection errors.
            if _is_connection_error(e) and attempt < 3:
                release_connection(conn, close=True)
                released = True
                reset_pool()
                time.sleep(0.4)
                continue

            raise

        finally:
            if conn is not None and not released:
                release_connection(conn)

    raise last_error


def execute_query(query, params=()):
    query = convert_sqlite_to_postgres(query)
    query = _escape_percent_literals_for_psycopg(query, params)
    last_error = None

    for attempt in range(4):
        conn = None
        released = False
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()
            return

        except Exception as e:
            last_error = e
            try:
                if conn:
                    conn.rollback()
            except Exception:
                pass

            if _is_connection_error(e) and attempt < 3:
                release_connection(conn, close=True)
                released = True
                reset_pool()
                time.sleep(0.4)
                continue

            raise

        finally:
            if conn is not None and not released:
                release_connection(conn)

    raise last_error


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_user(username, password):
    rows = fetch_all(
        "SELECT * FROM users WHERE username=? AND password_hash=? AND is_active=TRUE",
        (username, hash_password(password))
    )
    return rows[0] if rows else None

def init_db():
    """Lightweight migrations for existing Supabase/PostgreSQL database."""
    migrations = [
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
    ]
    for q in migrations:
        try:
            execute_query(q)
        except Exception:
            pass

    try:
        execute_query("""
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
        """)
    except Exception:
        pass
