import os
import hashlib
import time
import psycopg2
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
    global _POOL
    if _POOL is None:
        _POOL = SimpleConnectionPool(
            minconn=1,
            maxconn=5,
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
    conn = get_pool().getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = '45s'")
            cur.execute("SET idle_in_transaction_session_timeout = '30s'")
    except Exception:
        try:
            get_pool().putconn(conn, close=True)
        except Exception:
            pass
        reset_pool()
        raise
    return conn

def release_connection(conn, close=False):
    if conn is not None:
        try:
            get_pool().putconn(conn, close=close)
        except Exception:
            reset_pool()

def _is_connection_error(exc):
    text = str(exc).lower()
    return (
        isinstance(exc, (psycopg2.OperationalError, psycopg2.InterfaceError))
        or "ssl syscall" in text
        or "operation timed out" in text
        or "server closed the connection" in text
        or "connection already closed" in text
        or "could not receive data from server" in text
        or "could not send data to server" in text
    )

def fetch_all(query, params=()):
    query = convert_sqlite_to_postgres(query)
    last_error = None

    for attempt in range(2):
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

            if _is_connection_error(e) and attempt == 0:
                release_connection(conn, close=True)
                released = True
                reset_pool()
                time.sleep(0.5)
                continue

            raise
        finally:
            if conn is not None and not released:
                release_connection(conn)

    raise last_error

def execute_query(query, params=()):
    query = convert_sqlite_to_postgres(query)
    last_error = None

    for attempt in range(2):
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

            if _is_connection_error(e) and attempt == 0:
                release_connection(conn, close=True)
                released = True
                reset_pool()
                time.sleep(0.5)
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
    # Tables are already created in Supabase.
    pass
