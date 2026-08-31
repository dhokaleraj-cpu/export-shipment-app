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


def save_shipment_atomic(header, box_rows):
    """Atomically save a shipment header and every pallet/product row.

    SN 27.15 fixes the legacy pattern where INSERT INTO shipments committed
    before shipment_boxes were written. That could leave an orphan/partial
    shipment and make a retry fail on shipments.shipment_no UNIQUE.

    Recovery is deliberately conservative: an existing shipment number is
    reused only when it is clearly an incomplete retry of the same shipment.
    Otherwise a friendly ValueError is raised and no database row is changed.
    """
    from decimal import Decimal, InvalidOperation

    header = dict(header or {})
    box_rows = [dict(x or {}) for x in (box_rows or [])]
    shipment_no = str(header.get("shipment_no") or "").strip()
    invoice_no = str(header.get("invoice_no") or "").strip()
    if not shipment_no:
        raise ValueError("Shipment Number is mandatory.")
    if not invoice_no:
        raise ValueError("Original Invoice Number is mandatory.")
    if not box_rows:
        raise ValueError("At least one pallet/product row is required.")

    def _txt(value):
        return str(value or "").strip()

    def _id(value):
        try:
            return int(value) if value not in (None, "") else None
        except Exception:
            return value

    def _dec(value):
        try:
            return Decimal(str(value or 0)).quantize(Decimal("0.000001"))
        except (InvalidOperation, ValueError, TypeError):
            return Decimal("0")

    requested = {}
    for row in box_rows:
        pallet_no = _txt(row.get("pallet_no"))
        product_id = _id(row.get("product_id"))
        if not pallet_no or product_id is None:
            raise ValueError("Every shipment row requires Pallet Number and Product.")
        key = (pallet_no, product_id)
        if key in requested:
            raise ValueError(f"Duplicate pallet/product row in this shipment: {pallet_no}")
        requested[key] = row

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Serialize shipment saves briefly. This also prevents two users from
            # racing on Shipment No / FIFO allocation during the same second.
            cur.execute("SELECT pg_advisory_xact_lock(%s)", (2715001,))

            cur.execute(
                """
                SELECT id, shipment_no, invoice_no, supplier_id, warehouse_id,
                       customer_id, ship_to_master_id
                FROM shipments
                WHERE shipment_no=%s
                FOR UPDATE
                """,
                (shipment_no,),
            )
            existing_header = cur.fetchone()
            existing_header = dict(existing_header) if existing_header else None
            recovered = False
            skipped_existing = 0

            if existing_header:
                shipment_id = int(existing_header["id"])
                cur.execute(
                    """
                    SELECT id, shipment_id, fifo_row_id, pallet_no, box_no, product_id,
                           original_qty, unit_price, currency, amount, po_number, po_date
                    FROM shipment_boxes
                    WHERE shipment_id=%s
                    ORDER BY id
                    FOR UPDATE
                    """,
                    (shipment_id,),
                )
                existing_boxes = [dict(r) for r in cur.fetchall()]

                same_invoice = _txt(existing_header.get("invoice_no")) == invoice_no
                same_supplier = _id(existing_header.get("supplier_id")) == _id(header.get("supplier_id"))
                same_warehouse = _id(existing_header.get("warehouse_id")) == _id(header.get("warehouse_id"))
                same_customer = _id(existing_header.get("customer_id")) == _id(header.get("customer_id"))
                same_ship_to = _id(existing_header.get("ship_to_master_id")) == _id(header.get("ship_to_master_id"))

                # A header with no boxes is the exact orphan pattern created by the
                # old code. For a partial save, require the same header identity.
                if not same_invoice:
                    raise ValueError(
                        f"Shipment Number {shipment_no} already exists for Original Invoice "
                        f"{_txt(existing_header.get('invoice_no')) or '-'}; use a different Shipment Number "
                        "or edit the existing shipment."
                    )
                if existing_boxes and not (same_supplier and same_warehouse and same_customer and same_ship_to):
                    raise ValueError(
                        f"Shipment Number {shipment_no} already exists with saved pallet rows and a different header. "
                        "Use Edit Shipment or a different Shipment Number."
                    )

                # Every already-saved row must be part of this retry and must match.
                for old in existing_boxes:
                    key = (_txt(old.get("pallet_no")), _id(old.get("product_id")))
                    new = requested.get(key)
                    if not new:
                        raise ValueError(
                            f"Shipment Number {shipment_no} already contains pallet {key[0]} that is not in this retry. "
                            "Use Edit Shipment instead of creating a new shipment with the same number."
                        )
                    if (
                        _txt(old.get("box_no")) != _txt(new.get("box_no"))
                        or _dec(old.get("original_qty")) != _dec(new.get("quantity"))
                        or _dec(old.get("unit_price")) != _dec(new.get("unit_price"))
                        or _txt(old.get("currency")) != _txt(new.get("currency"))
                    ):
                        raise ValueError(
                            f"Shipment Number {shipment_no} already contains pallet {key[0]} with different saved values. "
                            "Use Edit Shipment to change the existing record."
                        )
                recovered = True

                # Refresh an orphan/partial header from the current form before
                # completing the missing rows.
                cur.execute(
                    """
                    UPDATE shipments SET
                        invoice_no=%s, po_number=%s, po_date=%s, shipment_date=%s,
                        supplier_id=%s, warehouse_id=%s, customer_id=%s, ship_to_master_id=%s,
                        shipment_time_days=%s, shipment_status=%s, warehouse_delivery_date=%s,
                        shipment_status_updated_at=CURRENT_TIMESTAMP,
                        invoice_amount=%s, currency=%s, attachment_path=%s, remarks=%s,
                        shipping_bill_no=%s, shipping_bill_date=%s, shipment_doc_date=%s,
                        forwarder_name=%s, incoterm=%s, forwarder_id=%s, incoterm_id=%s
                    WHERE id=%s
                    """,
                    (
                        invoice_no, header.get("po_number"), header.get("po_date"), header.get("shipment_date"),
                        header.get("supplier_id"), header.get("warehouse_id"), header.get("customer_id"),
                        header.get("ship_to_master_id"), header.get("shipment_time_days"), header.get("shipment_status"),
                        header.get("warehouse_delivery_date"), header.get("invoice_amount"), header.get("currency"),
                        header.get("attachment_path"), header.get("remarks"), header.get("shipping_bill_no"),
                        header.get("shipping_bill_date"), header.get("shipment_doc_date"), header.get("forwarder_name"),
                        header.get("incoterm"), header.get("forwarder_id"), header.get("incoterm_id"), shipment_id,
                    ),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO shipments
                    (shipment_no, invoice_no, po_number, po_date, shipment_date, supplier_id, warehouse_id,
                     customer_id, ship_to_master_id, shipment_time_days, shipment_status, warehouse_delivery_date,
                     shipment_status_updated_at, invoice_amount, currency, attachment_path, remarks,
                     shipping_bill_no, shipping_bill_date, shipment_doc_date, forwarder_name, incoterm,
                     forwarder_id, incoterm_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            CURRENT_TIMESTAMP, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        shipment_no, invoice_no, header.get("po_number"), header.get("po_date"), header.get("shipment_date"),
                        header.get("supplier_id"), header.get("warehouse_id"), header.get("customer_id"),
                        header.get("ship_to_master_id"), header.get("shipment_time_days"), header.get("shipment_status"),
                        header.get("warehouse_delivery_date"), header.get("invoice_amount"), header.get("currency"),
                        header.get("attachment_path"), header.get("remarks"), header.get("shipping_bill_no"),
                        header.get("shipping_bill_date"), header.get("shipment_doc_date"), header.get("forwarder_name"),
                        header.get("incoterm"), header.get("forwarder_id"), header.get("incoterm_id"),
                    ),
                )
                inserted = cur.fetchone()
                shipment_id = int(inserted["id"] if isinstance(inserted, dict) else inserted[0])
                existing_boxes = []

            existing_by_key = {
                (_txt(x.get("pallet_no")), _id(x.get("product_id"))): x
                for x in existing_boxes
            }

            # Allocate FIFO IDs inside the same transaction to avoid stale MAX()+1
            # values from the UI when multiple users save shipments concurrently.
            cur.execute("SELECT COALESCE(MAX(fifo_row_id), 0) AS max_id FROM shipment_boxes")
            max_row = cur.fetchone()
            if isinstance(max_row, dict):
                next_fifo = int(max_row.get("max_id") or 0) + 1
            else:
                next_fifo = int((max_row[0] if max_row else 0) or 0) + 1

            inserted_boxes = 0
            for row in box_rows:
                key = (_txt(row.get("pallet_no")), _id(row.get("product_id")))
                if key in existing_by_key:
                    skipped_existing += 1
                    continue

                # Prevent the same pallet/product from being attached to another
                # shipment. Lock the matching row when it exists.
                cur.execute(
                    """
                    SELECT id, shipment_id
                    FROM shipment_boxes
                    WHERE pallet_no=%s AND product_id=%s
                    FOR UPDATE
                    """,
                    key,
                )
                conflict = cur.fetchone()
                if conflict:
                    conflict = dict(conflict)
                    raise ValueError(
                        f"Pallet {key[0]} is already used for this Product in another shipment. "
                        "No part of this shipment was saved."
                    )

                cur.execute(
                    """
                    INSERT INTO shipment_boxes
                    (shipment_id, fifo_row_id, pallet_no, box_no, po_number, po_date, product_id,
                     original_qty, unit_price, currency, amount)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        shipment_id, next_fifo, key[0], _txt(row.get("box_no")), _txt(row.get("po_number")),
                        row.get("po_date"), key[1], row.get("quantity"), row.get("unit_price"),
                        _txt(row.get("currency")), row.get("amount"),
                    ),
                )
                next_fifo += 1
                inserted_boxes += 1

        conn.commit()
        return {
            "shipment_id": shipment_id,
            "recovered": recovered,
            "inserted_boxes": inserted_boxes,
            "existing_boxes_reused": skipped_existing,
        }
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass

MASTER_RELATIONSHIP_SCHEMA_VERSION = "SN 27.14"

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



def ensure_payment_allocation_schema():
    """Create the SN 27.17 line-allocation table without changing existing payment rows."""
    statements = [
        """
        CREATE TABLE IF NOT EXISTS payment_allocations (
            id SERIAL PRIMARY KEY,
            payment_id INTEGER NOT NULL REFERENCES payments(id) ON DELETE CASCADE,
            delivery_id INTEGER NOT NULL REFERENCES customer_deliveries(id) ON DELETE RESTRICT,
            allocated_amount NUMERIC(18,6) NOT NULL CHECK (allocated_amount >= 0),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(payment_id, delivery_id)
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_payment_allocations_payment_id ON payment_allocations(payment_id)",
        "CREATE INDEX IF NOT EXISTS idx_payment_allocations_delivery_id ON payment_allocations(delivery_id)",
    ]
    for sql in statements:
        execute_query(sql)
    return True


def _payment_line_balances_in_cursor(cur, invoice_no, exclude_payment_id=0):
    """Return payable Delivery-Invoice line groups while holding the caller transaction.

    Explicit SN 27.17 allocations are respected exactly. Older receipts that do not
    have allocation rows are preserved and distributed FIFO only across the remaining
    line capacity, so historical data is not rewritten or double-counted.
    """
    from decimal import Decimal

    cur.execute(
        """
        SELECT
            MIN(d.id) AS anchor_delivery_id,
            s.invoice_no AS original_invoice_no,
            b.product_id,
            p.product_code,
            p.product_name,
            COALESCE(d.unit_price,0) AS unit_price,
            MAX(d.currency) AS currency,
            SUM(COALESCE(d.delivered_qty,0)) AS delivered_qty,
            SUM(COALESCE(d.sale_amount,0)) AS invoice_amount
        FROM customer_deliveries d
        JOIN shipments s ON s.id=d.shipment_id
        JOIN shipment_boxes b ON b.id=d.box_id
        JOIN products p ON p.id=b.product_id
        WHERE d.delivery_invoice_no=%s
        GROUP BY s.invoice_no, b.product_id, p.product_code, p.product_name, COALESCE(d.unit_price,0)
        ORDER BY MIN(d.id), s.invoice_no, p.product_code
        """,
        (invoice_no,),
    )
    lines=[dict(r) for r in cur.fetchall()]
    if not lines:
        return []

    cur.execute(
        """
        SELECT
            s.invoice_no AS original_invoice_no,
            b.product_id,
            COALESCE(d.unit_price,0) AS unit_price,
            SUM(COALESCE(pa.allocated_amount,0)) AS explicit_paid
        FROM payment_allocations pa
        JOIN payments pay ON pay.id=pa.payment_id
        JOIN customer_deliveries d ON d.id=pa.delivery_id
        JOIN shipments s ON s.id=d.shipment_id
        JOIN shipment_boxes b ON b.id=d.box_id
        WHERE d.delivery_invoice_no=%s AND pay.id<>%s
        GROUP BY s.invoice_no, b.product_id, COALESCE(d.unit_price,0)
        """,
        (invoice_no, int(exclude_payment_id or 0)),
    )
    explicit={
        (str(r.get('original_invoice_no') or ''), int(r.get('product_id') or 0), str(r.get('unit_price') or 0)):
        Decimal(str(r.get('explicit_paid') or 0))
        for r in (dict(x) for x in cur.fetchall())
    }

    cur.execute(
        """
        SELECT COALESCE(SUM(pay.payment_amount),0) AS legacy_paid
        FROM payments pay
        JOIN customer_deliveries anchor ON anchor.id=pay.delivery_id
        WHERE anchor.delivery_invoice_no=%s
          AND pay.id<>%s
          AND NOT EXISTS (SELECT 1 FROM payment_allocations pa WHERE pa.payment_id=pay.id)
        """,
        (invoice_no, int(exclude_payment_id or 0)),
    )
    legacy_row=cur.fetchone()
    legacy_remaining=Decimal(str(dict(legacy_row).get('legacy_paid') or 0)) if legacy_row else Decimal('0')

    result=[]
    for line in lines:
        key=(str(line.get('original_invoice_no') or ''), int(line.get('product_id') or 0), str(line.get('unit_price') or 0))
        invoice_amount=Decimal(str(line.get('invoice_amount') or 0))
        explicit_paid=max(Decimal('0'), explicit.get(key, Decimal('0')))
        capacity=max(Decimal('0'), invoice_amount-explicit_paid)
        legacy_alloc=min(capacity, max(Decimal('0'), legacy_remaining))
        legacy_remaining-=legacy_alloc
        paid=min(invoice_amount, explicit_paid+legacy_alloc)
        pending=max(Decimal('0'), invoice_amount-paid)
        row=dict(line)
        row['paid_amount']=float(paid)
        row['pending_amount']=float(pending)
        row['explicit_paid_amount']=float(explicit_paid)
        row['legacy_paid_amount']=float(legacy_alloc)
        row['invoice_amount']=float(invoice_amount)
        result.append(row)
    return result


def save_invoice_payment_allocated_atomic(delivery_invoice_no, payment_received_date, allocations,
                                          payment_reference="", attachment_path=None, remarks=""):
    """Save one payment receipt with user-selected line allocations atomically."""
    from decimal import Decimal

    invoice_no=str(delivery_invoice_no or '').strip()
    if not invoice_no:
        raise ValueError('Delivery Invoice Number is mandatory.')
    normalized={}
    for item in allocations or []:
        delivery_id=int(item.get('delivery_id') or 0)
        amount=Decimal(str(item.get('amount') or 0))
        if delivery_id<=0 or amount<=0:
            continue
        normalized[delivery_id]=normalized.get(delivery_id, Decimal('0'))+amount
    if not normalized:
        raise ValueError('Select at least one line item and enter an allocation amount greater than zero.')

    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ('PAYMENT:'+invoice_no,))
            cur.execute(
                "SELECT id, COALESCE(sale_amount,0) AS sale_amount FROM customer_deliveries WHERE delivery_invoice_no=%s ORDER BY id FOR UPDATE",
                (invoice_no,),
            )
            delivery_rows=[dict(r) for r in cur.fetchall()]
            if not delivery_rows:
                raise ValueError(f'Delivery Invoice {invoice_no} was not found.')
            invoice_delivery_ids={int(r['id']) for r in delivery_rows}
            invoice_amount=sum(Decimal(str(r.get('sale_amount') or 0)) for r in delivery_rows)

            cur.execute(
                """
                SELECT pay.id, COALESCE(pay.payment_amount,0) AS payment_amount
                FROM payments pay
                JOIN customer_deliveries anchor ON anchor.id=pay.delivery_id
                WHERE anchor.delivery_invoice_no=%s
                FOR UPDATE OF pay
                """,
                (invoice_no,),
            )
            payment_rows=[dict(r) for r in cur.fetchall()]
            already_paid=sum(Decimal(str(r.get('payment_amount') or 0)) for r in payment_rows)
            invoice_pending=max(Decimal('0'), invoice_amount-already_paid)

            line_rows=_payment_line_balances_in_cursor(cur, invoice_no, 0)
            line_by_anchor={int(r['anchor_delivery_id']):r for r in line_rows}
            tolerance=Decimal('0.0005')
            total=Decimal('0')
            for delivery_id, amount in normalized.items():
                if delivery_id not in invoice_delivery_ids or delivery_id not in line_by_anchor:
                    raise ValueError('A selected payment line does not belong to the chosen Delivery Invoice.')
                pending=Decimal(str(line_by_anchor[delivery_id].get('pending_amount') or 0))
                if amount-pending>tolerance:
                    line=line_by_anchor[delivery_id]
                    raise ValueError(
                        f"Allocation {amount:,.3f} exceeds pending {pending:,.3f} for "
                        f"Original Invoice {line.get('original_invoice_no') or '-'} / Product {line.get('product_code') or '-'} ."
                    )
                total+=amount
            if total-invoice_pending>tolerance:
                raise ValueError(f'Allocated payment {total:,.3f} exceeds Delivery Invoice pending balance {invoice_pending:,.3f}.')

            anchor_id=next(iter(normalized.keys()))
            cur.execute(
                """
                INSERT INTO payments
                    (delivery_id, payment_received_date, payment_amount, payment_reference, attachment_path, remarks)
                VALUES (%s,%s,%s,%s,%s,%s)
                RETURNING id
                """,
                (anchor_id, str(payment_received_date), total, str(payment_reference or ''), attachment_path, str(remarks or '')),
            )
            payment_id=int(dict(cur.fetchone())['id'])
            for delivery_id, amount in normalized.items():
                cur.execute(
                    "INSERT INTO payment_allocations (payment_id, delivery_id, allocated_amount) VALUES (%s,%s,%s)",
                    (payment_id, delivery_id, amount),
                )
        conn.commit()
        return {
            'payment_id':payment_id,
            'delivery_invoice_no':invoice_no,
            'payment_amount':float(total),
            'allocation_count':len(normalized),
            'pending_after':float(max(Decimal('0'), invoice_pending-total)),
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def update_invoice_payment_allocated_atomic(payment_id, payment_received_date, allocations,
                                            payment_reference="", remarks=""):
    """Edit one receipt and its selected line allocations as one transaction."""
    from decimal import Decimal

    pid=int(payment_id)
    normalized={}
    for item in allocations or []:
        delivery_id=int(item.get('delivery_id') or 0)
        amount=Decimal(str(item.get('amount') or 0))
        if delivery_id<=0 or amount<=0:
            continue
        normalized[delivery_id]=normalized.get(delivery_id, Decimal('0'))+amount
    if not normalized:
        raise ValueError('Select at least one line item and enter an allocation amount greater than zero.')

    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT pay.id, anchor.delivery_invoice_no
                   FROM payments pay JOIN customer_deliveries anchor ON anchor.id=pay.delivery_id
                   WHERE pay.id=%s""", (pid,)
            )
            base=cur.fetchone()
            if not base:
                raise ValueError('Payment receipt was not found.')
            invoice_no=str(dict(base).get('delivery_invoice_no') or '')
            cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ('PAYMENT:'+invoice_no,))
            cur.execute(
                "SELECT id, COALESCE(sale_amount,0) AS sale_amount FROM customer_deliveries WHERE delivery_invoice_no=%s ORDER BY id FOR UPDATE",
                (invoice_no,),
            )
            delivery_rows=[dict(r) for r in cur.fetchall()]
            invoice_delivery_ids={int(r['id']) for r in delivery_rows}
            invoice_amount=sum(Decimal(str(r.get('sale_amount') or 0)) for r in delivery_rows)
            cur.execute(
                """
                SELECT pay.id, COALESCE(pay.payment_amount,0) AS payment_amount
                FROM payments pay JOIN customer_deliveries anchor ON anchor.id=pay.delivery_id
                WHERE anchor.delivery_invoice_no=%s AND pay.id<>%s
                FOR UPDATE OF pay
                """, (invoice_no,pid)
            )
            other_paid=sum(Decimal(str(dict(r).get('payment_amount') or 0)) for r in cur.fetchall())
            max_receipt=max(Decimal('0'), invoice_amount-other_paid)
            line_rows=_payment_line_balances_in_cursor(cur, invoice_no, pid)
            line_by_anchor={int(r['anchor_delivery_id']):r for r in line_rows}
            tolerance=Decimal('0.0005')
            total=Decimal('0')
            for delivery_id, amount in normalized.items():
                if delivery_id not in invoice_delivery_ids or delivery_id not in line_by_anchor:
                    raise ValueError('A selected payment line does not belong to this Delivery Invoice.')
                pending=Decimal(str(line_by_anchor[delivery_id].get('pending_amount') or 0))
                if amount-pending>tolerance:
                    line=line_by_anchor[delivery_id]
                    raise ValueError(
                        f"Allocation {amount:,.3f} exceeds available {pending:,.3f} for "
                        f"Original Invoice {line.get('original_invoice_no') or '-'} / Product {line.get('product_code') or '-'} ."
                    )
                total+=amount
            if total-max_receipt>tolerance:
                raise ValueError(f'Allocated payment {total:,.3f} exceeds the maximum editable receipt amount {max_receipt:,.3f}.')

            anchor_id=next(iter(normalized.keys()))
            cur.execute(
                """UPDATE payments SET delivery_id=%s, payment_received_date=%s, payment_amount=%s,
                   payment_reference=%s, remarks=%s WHERE id=%s""",
                (anchor_id, str(payment_received_date), total, str(payment_reference or ''), str(remarks or ''), pid),
            )
            cur.execute('DELETE FROM payment_allocations WHERE payment_id=%s', (pid,))
            for delivery_id, amount in normalized.items():
                cur.execute(
                    'INSERT INTO payment_allocations (payment_id, delivery_id, allocated_amount) VALUES (%s,%s,%s)',
                    (pid, delivery_id, amount),
                )
        conn.commit()
        return {'payment_id':pid, 'delivery_invoice_no':invoice_no, 'payment_amount':float(total)}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# Backward-compatible wrappers retained for any older page imports. They auto-
# distribute an invoice-level amount across available lines instead of anchoring
# the whole payment to one line.
def save_invoice_payment_atomic(delivery_invoice_no, payment_received_date, payment_amount,
                                payment_reference="", attachment_path=None, remarks=""):
    from decimal import Decimal
    amount=Decimal(str(payment_amount or 0))
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            rows=_payment_line_balances_in_cursor(cur, str(delivery_invoice_no or '').strip(), 0)
    finally:
        conn.close()
    remaining=amount
    allocations=[]
    for row in rows:
        if remaining<=Decimal('0.0005'):
            break
        pending=Decimal(str(row.get('pending_amount') or 0))
        alloc=min(pending,remaining)
        if alloc>Decimal('0.0005'):
            allocations.append({'delivery_id':int(row['anchor_delivery_id']),'amount':alloc})
            remaining-=alloc
    if remaining>Decimal('0.0005'):
        raise ValueError('Payment amount exceeds available Delivery Invoice line balances.')
    return save_invoice_payment_allocated_atomic(
        delivery_invoice_no, payment_received_date, allocations,
        payment_reference, attachment_path, remarks
    )


def update_invoice_payment_atomic(payment_id, payment_received_date, payment_amount,
                                  payment_reference="", remarks=""):
    from decimal import Decimal
    pid=int(payment_id)
    base=fetch_all("""SELECT anchor.delivery_invoice_no
                      FROM payments p JOIN customer_deliveries anchor ON anchor.id=p.delivery_id
                      WHERE p.id=?""", (pid,))
    if not base:
        raise ValueError('Payment receipt was not found.')
    invoice_no=str(base[0].get('delivery_invoice_no') or '')
    amount=Decimal(str(payment_amount or 0))
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            rows=_payment_line_balances_in_cursor(cur, invoice_no, pid)
    finally:
        conn.close()
    remaining=amount
    allocations=[]
    for row in rows:
        if remaining<=Decimal('0.0005'):
            break
        pending=Decimal(str(row.get('pending_amount') or 0))
        alloc=min(pending,remaining)
        if alloc>Decimal('0.0005'):
            allocations.append({'delivery_id':int(row['anchor_delivery_id']),'amount':alloc})
            remaining-=alloc
    if remaining>Decimal('0.0005'):
        raise ValueError('Payment amount exceeds available Delivery Invoice line balances.')
    return update_invoice_payment_allocated_atomic(
        pid, payment_received_date, allocations, payment_reference, remarks
    )

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
    # SN 27.14: do not run the old full relationship migration + information_schema
    # verification at startup. The normal additive list below already includes the
    # two simple Master links and transaction reference columns.
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
        CREATE TABLE IF NOT EXISTS payment_allocations (
            id SERIAL PRIMARY KEY,
            payment_id INTEGER NOT NULL REFERENCES payments(id) ON DELETE CASCADE,
            delivery_id INTEGER NOT NULL REFERENCES customer_deliveries(id) ON DELETE RESTRICT,
            allocated_amount NUMERIC(18,6) NOT NULL CHECK (allocated_amount >= 0),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(payment_id, delivery_id)
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_payment_allocations_payment_id ON payment_allocations(payment_id)",
        "CREATE INDEX IF NOT EXISTS idx_payment_allocations_delivery_id ON payment_allocations(delivery_id)",
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
        "ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS ship_via TEXT DEFAULT 'Road'",
        "CREATE INDEX IF NOT EXISTS idx_products_customer_id ON products(customer_id)",
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
