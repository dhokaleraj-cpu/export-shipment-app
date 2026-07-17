import os
import hashlib
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL") or os.getenv("POSTGRES_URL")

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


def _normalize_query(query):
    query = str(query)
    # Most app SQL uses sqlite-style ?. PostgreSQL drivers need %s.
    # Do not modify queries already using %s.
    if "%s" not in query:
        query = query.replace("?", "%s")
    return query


def get_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured in Streamlit secrets/environment.")
    if _DRIVER == "psycopg3":
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    if _DRIVER == "psycopg2":
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    raise RuntimeError("No PostgreSQL driver available. Install psycopg[binary].")


def fetch_all(query, params=()):
    query = _normalize_query(query)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, tuple(params or ()))
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    finally:
        conn.close()


def fetch_one(query, params=()):
    rows = fetch_all(query, params)
    return rows[0] if rows else None


def execute_query(query, params=()):
    query = _normalize_query(query)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, tuple(params or ()))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute_many(query, param_list):
    query = _normalize_query(query)
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
        "SELECT * FROM users WHERE username=? AND password_hash=? AND is_active=1",
        (username, hash_password(password)),
    )
    return rows[0] if rows else None


def init_db():
    # Database tables already exist in Supabase/PostgreSQL for this app.
    # Kept as no-op for compatibility with common.py.
    return True
