import os
import hashlib
import psycopg2
import streamlit as st
from psycopg2.extras import RealDictCursor
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


def convert_sqlite_to_postgres(query: str) -> str:
    query = query.replace("?", "%s")
    query = query.replace("date('now')", "CURRENT_DATE")
    query = query.replace("date(\"now\")", "CURRENT_DATE")
    query = query.replace("strftime('%Y-%m', d.delivery_date)", "to_char(d.delivery_date::date, 'YYYY-MM')")
    query = query.replace("strftime('%Y-%m', p.payment_received_date)", "to_char(p.payment_received_date::date, 'YYYY-MM')")
    query = query.replace("IFNULL", "COALESCE")
    return query


def get_connection():
    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor,
        sslmode="require"
    )


def fetch_all(query, params=()):
    query = convert_sqlite_to_postgres(query)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    finally:
        conn.close()


def execute_query(query, params=()):
    query = convert_sqlite_to_postgres(query)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


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
    # Keep this function because app.py calls init_db().
    pass