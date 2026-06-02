import sqlite3
import hashlib

DB_NAME = "shipment_app.db"

def get_connection():
    # SQLite lock protection for Streamlit reruns.
    # timeout waits if another query is writing; WAL allows readers while writing.
    conn = sqlite3.connect(DB_NAME, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
    except sqlite3.OperationalError:
        # If DB is momentarily locked during startup, continue;
        # the timeout/busy_timeout will handle normal operations.
        pass
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def column_exists(cur, table, column):
    cur.execute(f"PRAGMA table_info({table})")
    return column in [r[1] for r in cur.fetchall()]

def add_column_if_missing(cur, table, column, definition):
    if not column_exists(cur, table, column):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('user', 'admin', 'super_admin')),
        is_active INTEGER DEFAULT 1
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT UNIQUE NOT NULL,
        contact_person TEXT,
        email TEXT,
        phone TEXT,
        whatsapp_no TEXT,
        address TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_name TEXT UNIQUE NOT NULL,
        contact_person TEXT,
        email TEXT,
        phone TEXT,
        address TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS warehouses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        warehouse_name TEXT UNIQUE NOT NULL,
        location TEXT,
        contact_person TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_code TEXT UNIQUE NOT NULL,
        product_name TEXT NOT NULL,
        unit TEXT DEFAULT 'Nos',
        unit_price REAL DEFAULT 0,
        currency TEXT DEFAULT 'INR'
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS payment_terms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        term_name TEXT UNIQUE NOT NULL,
        days INTEGER NOT NULL DEFAULT 0,
        remarks TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS shipments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shipment_no TEXT UNIQUE NOT NULL,
        invoice_no TEXT NOT NULL,
        shipment_date TEXT,
        supplier_id INTEGER,
        warehouse_id INTEGER,
        invoice_amount REAL DEFAULT 0,
        currency TEXT DEFAULT 'INR',
        attachment_path TEXT,
        remarks TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS shipment_boxes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shipment_id INTEGER NOT NULL,
        pallet_no TEXT NOT NULL,
        box_no TEXT,
        product_id INTEGER NOT NULL,
        original_qty REAL NOT NULL,
        unit_price REAL DEFAULT 0,
        currency TEXT DEFAULT 'INR',
        amount REAL DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_pallet_row
    ON shipment_boxes (shipment_id, pallet_no, IFNULL(box_no, ''), product_id)
    """)

    # Pallet number cannot be reused again for the same product in any future shipment.
    # If old duplicate records already exist, the index creation may fail, so the app also checks before saving.
    try:
        cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_pallet_product_global
        ON shipment_boxes (pallet_no, product_id)
        """)
    except sqlite3.IntegrityError:
        pass
    except sqlite3.OperationalError:
        pass

    cur.execute("""
    CREATE TABLE IF NOT EXISTS customer_deliveries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shipment_id INTEGER NOT NULL,
        box_id INTEGER NOT NULL,
        customer_id INTEGER NOT NULL,
        delivery_date TEXT NOT NULL,
        delivered_qty REAL NOT NULL,
        delivery_invoice_no TEXT,
        payment_term_id INTEGER,
        payment_terms_days INTEGER DEFAULT 0,
        payment_due_date TEXT,
        unit_price REAL DEFAULT 0,
        currency TEXT DEFAULT 'INR',
        sale_amount REAL DEFAULT 0,
        attachment_path TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        delivery_id INTEGER NOT NULL,
        payment_received_date TEXT,
        payment_amount REAL NOT NULL,
        payment_reference TEXT,
        attachment_path TEXT,
        remarks TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notification_settings (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        sender_email TEXT,
        app_password TEXT,
        smtp_server TEXT DEFAULT 'smtp.gmail.com',
        smtp_port INTEGER DEFAULT 587,
        enable_email INTEGER DEFAULT 0,
        enable_whatsapp INTEGER DEFAULT 1
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notification_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        delivery_id INTEGER,
        sent_date TEXT,
        channel TEXT,
        status TEXT,
        message TEXT
    )
    """)

    # Safe migration for existing database. This keeps all previous entries.
    add_column_if_missing(cur, "customers", "whatsapp_no", "TEXT")
    add_column_if_missing(cur, "customers", "payment_term_id", "INTEGER")
    add_column_if_missing(cur, "products", "unit_price", "REAL DEFAULT 0")
    add_column_if_missing(cur, "products", "currency", "TEXT DEFAULT 'INR'")
    add_column_if_missing(cur, "shipments", "invoice_amount", "REAL DEFAULT 0")
    add_column_if_missing(cur, "shipments", "currency", "TEXT DEFAULT 'INR'")
    add_column_if_missing(cur, "shipments", "attachment_path", "TEXT")
    add_column_if_missing(cur, "shipment_boxes", "unit_price", "REAL DEFAULT 0")
    add_column_if_missing(cur, "shipment_boxes", "currency", "TEXT DEFAULT 'INR'")
    add_column_if_missing(cur, "shipment_boxes", "amount", "REAL DEFAULT 0")
    add_column_if_missing(cur, "customer_deliveries", "payment_term_id", "INTEGER")
    add_column_if_missing(cur, "customer_deliveries", "unit_price", "REAL DEFAULT 0")
    add_column_if_missing(cur, "customer_deliveries", "currency", "TEXT DEFAULT 'INR'")
    add_column_if_missing(cur, "customer_deliveries", "sale_amount", "REAL DEFAULT 0")
    add_column_if_missing(cur, "customer_deliveries", "attachment_path", "TEXT")
    add_column_if_missing(cur, "payments", "attachment_path", "TEXT")

    cur.execute("""
    ON CONFLICT DO NOTHING INTO notification_settings (id, smtp_server, smtp_port, enable_email, enable_whatsapp)
    VALUES (1, 'smtp.gmail.com', 587, 0, 1)
    """)

    users = [("superadmin", "super123", "super_admin"), ("admin", "admin123", "admin"), ("user", "user123", "user")]
    for username, password, role in users:
        cur.execute("ON CONFLICT DO NOTHING INTO users (username, password_hash, role, is_active) VALUES (?, ?, ?, 1)",
                    (username, hash_password(password), role))

    terms = [("Immediate", 0, "Payment due on delivery date"), ("Net 30", 30, "Payment due after 30 days"),
             ("Net 45", 45, "Payment due after 45 days"), ("Net 60", 60, "Payment due after 60 days")]
    for term_name, days, remarks in terms:
        cur.execute("ON CONFLICT DO NOTHING INTO payment_terms (term_name, days, remarks) VALUES (?, ?, ?)", (term_name, days, remarks))


    cur.execute("""
    CREATE TABLE IF NOT EXISTS notification_recipients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        recipient_email TEXT NOT NULL,
        is_active INTEGER DEFAULT 1
    )
    """)

    default_recipients = [
        ("shipment", "admin@example.com"),
        ("delivery", "finance@example.com"),
        ("payment", "finance@example.com"),
    ]
    for event_type, email in default_recipients:
        cur.execute("""
            ON CONFLICT DO NOTHING INTO notification_recipients (event_type, recipient_email, is_active)
            VALUES (?, ?, 1)
        """, (event_type, email))


    # V18: Coverage Plan with editable customer forecast and delivery linkage
    add_column_if_missing(cur, "products", "program", "TEXT")
    add_column_if_missing(cur, "products", "assy_plant", "TEXT")
    add_column_if_missing(cur, "products", "weight", "REAL DEFAULT 0")
    add_column_if_missing(cur, "products", "lcr_weekly", "REAL DEFAULT 0")
    add_column_if_missing(cur, "products", "mcr_weekly", "REAL DEFAULT 0")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS coverage_plan_meta (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        title TEXT,
        shipment_time_days INTEGER DEFAULT 0,
        shipment_time_label TEXT,
        shipment_time_value TEXT,
        part_size TEXT,
        product_label TEXT,
        last_shipment_no TEXT,
        last_shipment_qty REAL DEFAULT 0,
        next_shipment_plan TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS coverage_plan_lines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        week_no INTEGER,
        plan_date TEXT,
        customer_forecast REAL DEFAULT 0,
        stock_at_wh REAL DEFAULT 0,
        delivered_to_customer REAL DEFAULT 0,
        wh_bank REAL DEFAULT 0,
        two_months_inventory REAL DEFAULT 0,
        bank_status REAL DEFAULT 0,
        suggested_shipment_qty REAL DEFAULT 0,
        next_shipment_date TEXT
    )
    """)

    add_column_if_missing(cur, "coverage_plan_meta", "shipment_time_days", "INTEGER DEFAULT 0")
    add_column_if_missing(cur, "coverage_plan_lines", "customer_forecast", "REAL DEFAULT 0")
    add_column_if_missing(cur, "coverage_plan_lines", "delivered_to_customer", "REAL DEFAULT 0")
    add_column_if_missing(cur, "coverage_plan_lines", "suggested_shipment_qty", "REAL DEFAULT 0")
    add_column_if_missing(cur, "coverage_plan_lines", "next_shipment_date", "TEXT")

    product_seed_rows = [{'program': 'T1XX SUV', 'assy_plant': 'GMC-5', 'part_no': '40257237', 'price': 2.71, 'weight': 0.55, 'lcr_weekly': 6809.0, 'mcr_weekly': 7831.0}, {'program': 'T1XX HD', 'assy_plant': 'TRMF', 'part_no': '40256626', 'price': 2.54, 'weight': 0.5, 'lcr_weekly': 8316.0, 'mcr_weekly': 9564.0}, {'program': 'D2U C/G/H RDM', 'assy_plant': 'GMC-1', 'part_no': '40229265', 'price': 0.89, 'weight': 0.081, 'lcr_weekly': 4160.0, 'mcr_weekly': 4784.0}, {'program': 'CUSW', 'assy_plant': 'GMC-1', 'part_no': '40282130', 'price': 1.51, 'weight': 0.165, 'lcr_weekly': 392.0, 'mcr_weekly': 451.0}]
    for p in product_seed_rows:
        cur.execute("""
            ON CONFLICT DO NOTHING INTO products
            (product_code, product_name, unit, unit_price, currency, program, assy_plant, weight, lcr_weekly, mcr_weekly)
            VALUES (?, ?, 'Nos', ?, 'USD', ?, ?, ?, ?, ?)
        """, (p["part_no"], p["program"], p["price"], p["program"], p["assy_plant"], p["weight"], p["lcr_weekly"], p["mcr_weekly"]))
        cur.execute("""
            UPDATE products
            SET program=?, assy_plant=?, unit_price=?, currency='USD', weight=?, lcr_weekly=?, mcr_weekly=?
            WHERE product_code=?
        """, (p["program"], p["assy_plant"], p["price"], p["weight"], p["lcr_weekly"], p["mcr_weekly"], p["part_no"]))

    cur.execute("""
        ON CONFLICT DO NOTHING INTO coverage_plan_meta
        (id, title, shipment_time_days, shipment_time_label, shipment_time_value, part_size, product_label, last_shipment_no, last_shipment_qty, next_shipment_plan)
        VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ('Coverage', 0, 'Shipment Time', '12-14 weeks', '', '', '', 0, ''))

    existing_coverage_count = cur.execute("SELECT COUNT(*) FROM coverage_plan_lines").fetchone()[0]
    if existing_coverage_count == 0:
        coverage_seed_rows = [{'week_no': 1, 'plan_date': '1899-12-31', 'customer_forecast': 0.0, 'stock_at_wh': 75400.0, 'wh_bank': 4.0, 'two_months_inventory': 46188.0, 'bank_status': 16000.0}, {'week_no': 2, 'plan_date': '1900-01-01', 'customer_forecast': 0.0, 'stock_at_wh': 86720.0, 'wh_bank': 5.0, 'two_months_inventory': 46195.0, 'bank_status': 0.0}, {'week_no': 3, 'plan_date': '1900-01-02', 'customer_forecast': 0.0, 'stock_at_wh': 81680.0, 'wh_bank': 6.0, 'two_months_inventory': 46202.0, 'bank_status': 16000.0}, {'week_no': 4, 'plan_date': '1900-01-03', 'customer_forecast': 0.0, 'stock_at_wh': 94080.0, 'wh_bank': 7.0, 'two_months_inventory': 46209.0, 'bank_status': 0.0}, {'week_no': 5, 'plan_date': '1900-01-04', 'customer_forecast': 0.0, 'stock_at_wh': 87960.0, 'wh_bank': 8.0, 'two_months_inventory': 46216.0, 'bank_status': 0.0}, {'week_no': 6, 'plan_date': '1900-01-05', 'customer_forecast': 0.0, 'stock_at_wh': 82560.0, 'wh_bank': 9.0, 'two_months_inventory': 46223.0, 'bank_status': 0.0}, {'week_no': 7, 'plan_date': '1900-01-06', 'customer_forecast': 0.0, 'stock_at_wh': 76800.0, 'wh_bank': 10.0, 'two_months_inventory': 46230.0, 'bank_status': 0.0}, {'week_no': 8, 'plan_date': '1900-01-07', 'customer_forecast': 0.0, 'stock_at_wh': 71400.0, 'wh_bank': 11.0, 'two_months_inventory': 46237.0, 'bank_status': 12000.0}, {'week_no': 9, 'plan_date': '1900-01-08', 'customer_forecast': 0.0, 'stock_at_wh': 77640.0, 'wh_bank': 12.0, 'two_months_inventory': 46244.0, 'bank_status': 0.0}, {'week_no': 10, 'plan_date': '1900-01-09', 'customer_forecast': 0.0, 'stock_at_wh': 72240.0, 'wh_bank': 13.0, 'two_months_inventory': 46251.0, 'bank_status': 0.0}, {'week_no': 11, 'plan_date': '1900-01-10', 'customer_forecast': 0.0, 'stock_at_wh': 66840.0, 'wh_bank': 14.0, 'two_months_inventory': 46258.0, 'bank_status': 0.0}, {'week_no': 12, 'plan_date': '1900-01-11', 'customer_forecast': 0.0, 'stock_at_wh': 61440.0, 'wh_bank': 15.0, 'two_months_inventory': 46265.0, 'bank_status': 0.0}, {'week_no': 13, 'plan_date': '1900-01-12', 'customer_forecast': 0.0, 'stock_at_wh': 56760.0, 'wh_bank': 16.0, 'two_months_inventory': 46272.0, 'bank_status': 34000.0}, {'week_no': 14, 'plan_date': '1900-01-13', 'customer_forecast': 0.0, 'stock_at_wh': 85000.0, 'wh_bank': 0.0, 'two_months_inventory': 46279.0, 'bank_status': 0.0}, {'week_no': 15, 'plan_date': '1900-01-14', 'customer_forecast': 0.0, 'stock_at_wh': 80320.0, 'wh_bank': 0.0, 'two_months_inventory': 46286.0, 'bank_status': 0.0}, {'week_no': 16, 'plan_date': '1900-01-15', 'customer_forecast': 0.0, 'stock_at_wh': 74560.0, 'wh_bank': 0.0, 'two_months_inventory': 46293.0, 'bank_status': 0.0}]
        for r in coverage_seed_rows:
            cur.execute("""
                INSERT INTO coverage_plan_lines
                (week_no, plan_date, customer_forecast, stock_at_wh, wh_bank, two_months_inventory, bank_status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (r["week_no"], r["plan_date"], r["customer_forecast"], r["stock_at_wh"], r["wh_bank"], r["two_months_inventory"], r["bank_status"]))


    # V20: Warehouse shipment time and product-wise coverage plan
    add_column_if_missing(cur, "warehouses", "shipment_time_days", "INTEGER DEFAULT 0")
    add_column_if_missing(cur, "coverage_plan_lines", "product_id", "INTEGER")
    add_column_if_missing(cur, "coverage_plan_lines", "suggested_shipment_qty", "REAL DEFAULT 0")
    add_column_if_missing(cur, "coverage_plan_lines", "next_shipment_date", "TEXT")


    # V21: Product master two months inventory for coverage plan
    add_column_if_missing(cur, "products", "two_months_inventory", "REAL DEFAULT 0")


    # V23: Product Master two months inventory = MCR Weekly * 8
    add_column_if_missing(cur, "products", "two_months_inventory", "REAL DEFAULT 0")


    # V24: Shipment delivery date/week/quantity for Coverage Plan
    add_column_if_missing(cur, "coverage_plan_lines", "shipment_delivery_date", "TEXT")
    add_column_if_missing(cur, "coverage_plan_lines", "shipment_delivery_weekday", "TEXT")
    add_column_if_missing(cur, "coverage_plan_lines", "shipment_delivery_qty", "REAL DEFAULT 0")


    # V25: Coverage plan shipment qty and weekly delivery correction
    add_column_if_missing(cur, "coverage_plan_lines", "shipment_delivery_qty", "REAL DEFAULT 0")
    add_column_if_missing(cur, "coverage_plan_lines", "shipment_delivery_date", "TEXT")


    # V26: Coverage plan separate import modules and weekly formula support
    add_column_if_missing(cur, "coverage_plan_lines", "shipment_delivery_qty", "REAL DEFAULT 0")
    add_column_if_missing(cur, "coverage_plan_lines", "shipment_delivery_date", "TEXT")


    # V27: two_months_inventory = LCR Weekly * 8 and clear Stock_at_WH once
    add_column_if_missing(cur, "products", "two_months_inventory", "REAL DEFAULT 0")
    cur.execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS delete_audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_name TEXT,
        record_id INTEGER,
        deleted_by TEXT,
        deleted_at TEXT DEFAULT CURRENT_TIMESTAMP,
        details TEXT
    )
    """)
    cur.execute("UPDATE products SET two_months_inventory = IFNULL(lcr_weekly, 0) * 8")
    clear_marker = cur.execute("SELECT value FROM app_settings WHERE key='stock_at_wh_cleared_v27'").fetchone()
    if clear_marker is None:
        cur.execute("UPDATE coverage_plan_lines SET stock_at_wh = 0")
        cur.execute("INSERT INTO app_settings (key, value) VALUES ('stock_at_wh_cleared_v27', 'done')")


    # V32: Product PO fields and company/admin settings
    add_column_if_missing(cur, "products", "po_number", "TEXT")
    add_column_if_missing(cur, "products", "po_date", "TEXT")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS company_settings (
        id INTEGER PRIMARY KEY CHECK (id=1),
        company_name TEXT DEFAULT 'FOUR STAR INDUSTRIES PVT. LTD.',
        address TEXT,
        phone TEXT,
        email TEXT,
        website TEXT,
        tax_id TEXT,
        logo_path TEXT DEFAULT 'FSI_LOGO_new.png'
    )
    """)
    cur.execute("""
        ON CONFLICT DO NOTHING INTO company_settings
        (id, company_name, logo_path)
        VALUES (1, 'FOUR STAR INDUSTRIES PVT. LTD.', 'FSI_LOGO_new.png')
    """)


    # V34: Shipment header additional dates / shipping bill fields
    add_column_if_missing(cur, "shipments", "shipment_doc_date", "TEXT")
    add_column_if_missing(cur, "shipments", "original_invoice_date", "TEXT")
    add_column_if_missing(cur, "shipments", "shipping_bill_no", "TEXT")
    add_column_if_missing(cur, "shipments", "shipping_bill_date", "TEXT")


    # V38: Shipment Entry header fields
    add_column_if_missing(cur, "shipments", "shipping_bill_no", "TEXT")
    add_column_if_missing(cur, "shipments", "shipping_bill_date", "TEXT")
    add_column_if_missing(cur, "shipments", "shipment_doc_date", "TEXT")
    add_column_if_missing(cur, "shipments", "forwarder_name", "TEXT")
    add_column_if_missing(cur, "shipments", "incoterm", "TEXT")


    # V39: Incoterm and Forwarder masters
    cur.execute("""
    CREATE TABLE IF NOT EXISTS incoterms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        incoterm_name TEXT UNIQUE NOT NULL,
        remarks TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS forwarders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        forwarder_name TEXT UNIQUE NOT NULL,
        contact_person TEXT,
        email TEXT,
        phone TEXT,
        remarks TEXT
    )
    """)
    add_column_if_missing(cur, "shipments", "forwarder_id", "INTEGER")
    add_column_if_missing(cur, "shipments", "incoterm_id", "INTEGER")
    default_incoterms = ["EXW", "FCA", "FOB", "CFR", "CIF", "DAP", "DDP"]
    for inc in default_incoterms:
        cur.execute("ON CONFLICT DO NOTHING INTO incoterms (incoterm_name, remarks) VALUES (?, '')", (inc,))

    conn.commit()
    conn.close()

def verify_user(username: str, password: str):
    conn = get_connection()
    row = conn.execute("""
        SELECT id, username, role FROM users
        WHERE username = ? AND password_hash = ? AND is_active = 1
    """, (username, hash_password(password))).fetchone()
    conn.close()
    return dict(row) if row else None
