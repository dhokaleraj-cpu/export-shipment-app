import os
import hashlib
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def fetch_all(query, params=()):
    query = query.replace("?", "%s")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()
    finally:
        conn.close()

def execute_query(query, params=()):
    query = query.replace("?", "%s")
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
        "SELECT * FROM users WHERE username=? AND password_hash=? AND is_active=1",
        (username, hash_password(password))
    )
    return rows[0] if rows else None

def init_db():
    pass