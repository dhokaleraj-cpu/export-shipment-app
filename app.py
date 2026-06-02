import io
import base64
import html
import sqlite3
import smtplib
import urllib.parse
from datetime import date, timedelta, datetime, datetime, datetime, datetime, datetime, datetime, datetime
from email.message import EmailMessage
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from db import get_connection, init_db, verify_user, hash_password

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
LOGO_PATH = Path("FSI_LOGO_new.png")

CURRENCIES = ["INR", "USD", "EUR", "GBP", "AED", "JPY", "CNY"]
MAX_LIST_ROWS = 300  # Limits large on-screen tables for better web performance

st.set_page_config(page_title="Export Shipment Management", layout="wide", initial_sidebar_state="collapsed")
init_db()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Aptos:wght@400;600;700;800&display=swap');
html, body, [class*="css"], .stApp, div, span, p, label, input, button, textarea, select {
    font-family: Aptos, Arial, sans-serif !important;
}
.stApp {background:#f4f6f8;}
.block-container {padding-top: 3.2rem; max-width: 100%;}
h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {font-weight: 800 !important;}
.top-strip {
    display:flex; justify-content:space-between; align-items:center;
    background:#ffffff; border:1px solid #c9eef5; border-radius:10px;
    padding:10px 16px; margin-bottom:10px; box-shadow:0 1px 6px rgba(0,0,0,.08);
}
.logo-box {display:flex; align-items:center; gap:12px; font-weight:800; font-size:18px; color:#003b73;}
.logo-circle {
    width:52px; height:52px; border-radius:10px; background:#0b5cab; color:white;
    display:flex; align-items:center; justify-content:center; font-weight:900; font-size:22px;
}
.user-clock {text-align:right; font-weight:700; color:#003b73;}
.topbar {background:#f8fafc;color:#003b73;padding:22px 26px;border-radius:12px;margin-top:24px;margin-bottom:20px;border:1px solid #d9e2ec;box-shadow:0 1px 6px rgba(0,0,0,.06);}
.topbar h1 {font-size:28px;margin:0;font-weight:800;}
.subtext {font-size:13px;opacity:.9;margin-top:4px;}
.card {background:white;padding:18px;border-radius:10px;box-shadow:0 1px 8px rgba(0,0,0,.10);border:1px solid #c9eef5;}
.kpi-head {color:white;padding:10px;text-align:center;font-weight:800;border-radius:4px 4px 0 0;}
.kpi-value {border:1px solid #d0d7e2;border-top:0;padding:18px;text-align:center;font-size:25px;font-weight:800;background:white;}
.green {background:#008a00;}.teal {background:#42b883;}.orange {background:#ff8c00;}.red {background:#b00020;}.blue {background:#0b5cab;}.yellow {background:#fff3b0;color:#111;}
.total-box {background:#fff3b0;border:1px solid #d9c35c;padding:12px;border-radius:8px;font-size:18px;font-weight:800;}
.footer {text-align:center;color:#687386;font-size:12px;margin-top:30px;font-weight:700;}
div[data-baseweb="tab-list"] {
    gap: 14px !important;
    background:#ffffff;
    padding:10px 14px;
    border-radius:12px;
    border:1px solid #dde3ea;
    box-shadow:0 1px 6px rgba(0,0,0,.06);
}
button[data-baseweb="tab"] {
    background:#eef3f7;
    border-radius:10px;
    color:#003b73;
    font-weight:800;
    padding-left:18px !important;
    padding-right:18px !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    background:#0b5cab;
    color:white;
}

h1 {font-size: 38px !important; font-weight: 900 !important;}
h2 {font-size: 30px !important; font-weight: 900 !important;}
h3 {font-size: 24px !important; font-weight: 850 !important;}
label, .stTextInput label, .stSelectbox label, .stNumberInput label, .stDateInput label {font-size:15px !important;font-weight:750 !important;color:#1f2937 !important;}


.main-title-center {
    text-align:center;
    font-family:Aptos, Arial, sans-serif !important;
    font-size:38px;
    line-height:1.1;
    font-weight:900;
    color:#003B73;
    letter-spacing:.8px;
    padding-top:16px;
}
h1, h2, h3, h4, h5, h6,
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
div[data-testid="stMarkdownContainer"] h1,
div[data-testid="stMarkdownContainer"] h2,
div[data-testid="stMarkdownContainer"] h3 {
    font-family:Aptos, Arial, sans-serif !important;
    font-weight:900 !important;
}
.subtext, .topbar h1, .kpi-head, .total-box {
    font-family:Aptos, Arial, sans-serif !important;
    font-weight:900 !important;
}


/* V30 bold headings and titles */
h1, h2, h3, h4, h5, h6,
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
div[data-testid="stMarkdownContainer"] h1,
div[data-testid="stMarkdownContainer"] h2,
div[data-testid="stMarkdownContainer"] h3,
label, .stTextInput label, .stTextArea label, .stNumberInput label,
.stDateInput label, .stSelectbox label, .stFileUploader label {
    font-family: Aptos, Arial, sans-serif !important;
    font-weight: 900 !important;
    color: #003B73 !important;
}
.coverage-dashboard-title {
    font-size: 26px;
    font-weight: 900;
    color:#003B73;
    padding: 12px 0;
}


/* V39 light/dark friendly UI improvements */
:root {
    --fsi-bg: #f8fafc;
    --fsi-card: #ffffff;
    --fsi-text: #111827;
    --fsi-muted: #475569;
    --fsi-primary: #003B73;
    --fsi-border: #cbd5e1;
    --fsi-input-bg: #ffffff;
}
@media (prefers-color-scheme: dark) {
    :root {
        --fsi-bg: #0f172a;
        --fsi-card: #111827;
        --fsi-text: #f8fafc;
        --fsi-muted: #cbd5e1;
        --fsi-primary: #93c5fd;
        --fsi-border: #64748b;
        --fsi-input-bg: #1f2937;
    }
}
.stApp {
    background: var(--fsi-bg) !important;
    color: var(--fsi-text) !important;
}
.card, .total-box {
    background: var(--fsi-card) !important;
    color: var(--fsi-text) !important;
    border: 1px solid var(--fsi-border) !important;
}
div[data-testid="stMarkdownContainer"], p, span, div {
    color: inherit;
}
label, .stTextInput label, .stTextArea label, .stNumberInput label,
.stDateInput label, .stSelectbox label, .stFileUploader label {
    font-family: Aptos, Arial, sans-serif !important;
    font-weight: 900 !important;
    font-size: 15px !important;
    color: var(--fsi-primary) !important;
    letter-spacing: .01em !important;
}
div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div,
div[data-baseweb="textarea"] textarea,
.stTextInput input,
.stNumberInput input,
.stDateInput input,
.stTextArea textarea {
    background: var(--fsi-input-bg) !important;
    color: var(--fsi-text) !important;
    border: 1px solid var(--fsi-border) !important;
    border-radius: 10px !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06) !important;
}
div[data-baseweb="select"] span,
div[data-baseweb="input"] input {
    color: var(--fsi-text) !important;
}
div[data-testid="stFileUploader"] section {
    background: var(--fsi-input-bg) !important;
    border: 1px dashed var(--fsi-border) !important;
    border-radius: 12px !important;
}
div[data-testid="stFileUploader"] small {
    display: none !important;
}
div[data-testid="stFileUploader"] [data-testid="stMarkdownContainer"] p {
    color: var(--fsi-muted) !important;
    font-weight: 700 !important;
}
.input-section-title {
    font-size: 18px;
    font-weight: 900;
    color: var(--fsi-primary);
    margin: 12px 0 8px 0;
}


/* V40 equal KPI/card sizing and consistent field sizing */
.kpi-head {
    min-height: 64px !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    text-align:center !important;
    font-size:18px !important;
    line-height:1.25 !important;
}
.kpi-value {
    min-height: 86px !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    text-align:center !important;
}
div[data-testid="column"] {
    min-width: 0 !important;
}
.stTextInput input, .stNumberInput input, .stDateInput input,
div[data-baseweb="select"] > div {
    min-height: 44px !important;
}


/* V41 file uploader overlap fix */
div[data-testid="stFileUploader"] {
    max-width: 100% !important;
}
div[data-testid="stFileUploader"] section {
    min-height: 86px !important;
    padding: 14px 18px !important;
    display: flex !important;
    align-items: center !important;
    gap: 14px !important;
    overflow: hidden !important;
}
div[data-testid="stFileUploader"] section button {
    min-width: 118px !important;
    height: 44px !important;
    font-size: 0 !important;
    position: relative !important;
}
div[data-testid="stFileUploader"] section button::after {
    content: "Upload" !important;
    font-size: 16px !important;
    font-weight: 900 !important;
    color: var(--fsi-primary) !important;
    position: absolute !important;
    left: 50% !important;
    top: 50% !important;
    transform: translate(-50%, -50%) !important;
}
div[data-testid="stFileUploader"] section [data-testid="stFileUploaderDropzoneInstructions"] {
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}
div[data-testid="stFileUploader"] section [data-testid="stFileUploaderDropzoneInstructions"] span {
    font-size: 16px !important;
    color: var(--fsi-muted) !important;
    font-weight: 700 !important;
}
div[data-testid="stFileUploader"] section [data-testid="stFileUploaderDropzoneInstructions"] div:first-child {
    display: none !important;
}


/* V43 coverage product filter and login cleanup */
.coverage-product-filter-title {
    font-family: Aptos, Arial, sans-serif;
    font-size: 20px;
    font-weight: 900;
    color: var(--fsi-primary);
    background: rgba(147, 197, 253, 0.18);
    border: 1px solid var(--fsi-border);
    border-radius: 10px;
    padding: 10px 14px;
    text-align: center;
    margin-bottom: 8px;
}
.coverage-kpi-product-card .kpi-head,
.coverage-kpi-product-card .kpi-value {
    text-align: center !important;
}
.login-logo-gap-fix {
    height: 0px !important;
    margin: 0 !important;
    padding: 0 !important;
}

</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300, show_spinner=False)
def _cached_fetch_all(query, params=()):
    """Cache repeated SELECT results for 5 minutes to improve Streamlit speed."""
    from db import fetch_all as db_fetch_all
    return db_fetch_all(query, params)

def fetch_all(query, params=()):
    """Cached database reads. Cache is cleared automatically after writes."""
    safe_params = tuple(params) if params else ()
    return _cached_fetch_all(query, safe_params)

def execute_query(query, params=()):
    from db import execute_query as db_execute_query
    result = db_execute_query(query, params)
    try:
        _cached_fetch_all.clear()
    except Exception:
        pass
    return result


def ensure_runtime_columns():
    """Keep Supabase/PostgreSQL schema aligned with the latest app fields."""
    schema_updates = [
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS po_number TEXT",
        "ALTER TABLE shipments ADD COLUMN IF NOT EXISTS po_date DATE",
        "ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS po_number TEXT",
        "ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS po_date DATE",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS po_number TEXT",
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS po_date DATE",
        "ALTER TABLE coverage_plan_lines ADD COLUMN IF NOT EXISTS delivered_to_customer NUMERIC DEFAULT 0",
        "ALTER TABLE coverage_plan_lines ADD COLUMN IF NOT EXISTS wh_bank NUMERIC DEFAULT 0",
        "ALTER TABLE coverage_plan_lines ADD COLUMN IF NOT EXISTS bank_status NUMERIC DEFAULT 0",
        "ALTER TABLE coverage_plan_lines ADD COLUMN IF NOT EXISTS suggested_shipment_qty NUMERIC DEFAULT 0",
        "ALTER TABLE coverage_plan_lines ADD COLUMN IF NOT EXISTS next_shipment_date DATE",
        "ALTER TABLE coverage_plan_lines ADD COLUMN IF NOT EXISTS shipment_delivery_date DATE",
        "ALTER TABLE coverage_plan_lines ADD COLUMN IF NOT EXISTS shipment_delivery_qty NUMERIC DEFAULT 0",
        "ALTER TABLE coverage_plan_lines ADD COLUMN IF NOT EXISTS two_months_inventory NUMERIC DEFAULT 0",
    ]
    for sql in schema_updates:
        try:
            execute_query(sql)
        except Exception:
            pass

try:
    ensure_runtime_columns()
except Exception:
    pass


def check_delete_password(password):
    user = st.session_state.get("user", {})
    username = user.get("username", "")
    return bool(verify_user(username, password))

def delete_record_with_password(table_name, record_id, password, details=""):
    if not check_delete_password(password):
        st.error("Wrong password. Delete cancelled.")
        return False
    try:
        execute_query("INSERT INTO delete_audit_log (table_name, record_id, deleted_by, details) VALUES (?, ?, ?, ?)",
                      (table_name, record_id, st.session_state.user.get("username", ""), details))
    except Exception:
        pass
    execute_query(f"DELETE FROM {table_name} WHERE id=?", (record_id,))
    st.success("Record deleted successfully.")
    return True



def format_date_ddmmyyyy(value):
    """Display any YYYY-MM-DD/date/datetime value as DD-MM-YYYY."""
    if value in (None, ""):
        return ""
    try:
        if hasattr(value, "strftime"):
            return value.strftime("%d-%m-%Y")
        text = str(value)[:10]
        return datetime.strptime(text, "%Y-%m-%d").strftime("%d-%m-%Y")
    except Exception:
        return str(value)

def format_date_columns(rows):
    """Format all date-like columns for display only."""
    date_keys = ["date", "due", "plan_date", "shipment_date", "delivery_date", "payment_received_date", "payment_due_date", "next_shipment_date"]
    output = []
    for row in rows:
        new_row = dict(row)
        for k, v in list(new_row.items()):
            kl = str(k).lower()
            if any(x in kl for x in date_keys):
                new_row[k] = format_date_ddmmyyyy(v)
        output.append(new_row)
    return output


def cleanup_orphan_transactions():
    """Remove transaction rows linked to deleted primary records so edit modules stay refreshed."""
    try:
        execute_query("""
            DELETE FROM payments
            WHERE delivery_id NOT IN (SELECT id FROM customer_deliveries)
        """)
    except Exception:
        pass
    try:
        execute_query("""
            DELETE FROM customer_deliveries
            WHERE shipment_id NOT IN (SELECT id FROM shipments)
               OR box_id NOT IN (SELECT id FROM shipment_boxes)
               OR customer_id NOT IN (SELECT id FROM customers)
        """)
    except Exception:
        pass
    try:
        execute_query("""
            DELETE FROM shipment_boxes
            WHERE shipment_id NOT IN (SELECT id FROM shipments)
               OR product_id NOT IN (SELECT id FROM products)
        """)
    except Exception:
        pass


def save_upload(file, prefix):
    if not file:
        return None
    safe_name = file.name.replace("/", "_").replace("\\", "_")
    path = UPLOAD_DIR / f"{prefix}_{safe_name}"
    with open(path, "wb") as f:
        f.write(file.getbuffer())
    return str(path)

def top_layout():
    user = st.session_state.get("user", {"username": "-", "role": "-"})
    c1, c2, c3 = st.columns([1.6, 3.2, 1.4])
    with c1:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), use_container_width=False, width=420)
        else:
            st.markdown('<div class="logo-circle">FSI</div>', unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="main-title-center">
            EXPORT SHIPMENT<br>MONITORING SYSTEM
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="user-clock">
            User: {user["username"]}<br>
            Role: {user["role"]}<br>
            Module: Export Shipment<br>
            <span id="liveClock"></span>
        </div>
        <script>
        function updateClock(){{
            const now = new Date();
            const els = window.parent.document.querySelectorAll('#liveClock');
            els.forEach(el => el.innerHTML = now.toLocaleString());
        }}
        setInterval(updateClock, 1000); updateClock();
        </script>
        """, unsafe_allow_html=True)
    st.divider()

def show_header(title, subtitle="EXPORT SHIPMENT MONITORING SYSTEM"):
    st.markdown(f'<div class="topbar"><h1>{title}</h1><div class="subtext">{subtitle}</div></div>', unsafe_allow_html=True)

def add_total_row(df):
    if df.empty:
        return df
    total_row = {}
    numeric_cols = df.select_dtypes(include="number").columns
    no_total_cols = {"unit_price", "price", "sale_unit_price"}
    for col in df.columns:
        col_key = str(col).lower().strip()
        if col in numeric_cols and col_key not in no_total_cols and "price" not in col_key:
            total_row[col] = df[col].sum()
        elif col == df.columns[0]:
            total_row[col] = "TOTAL"
        else:
            total_row[col] = ""
    return pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)

def style_total_row(df):
    def row_style(row):
        if str(row.iloc[0]).upper() == "TOTAL":
            return ["font-weight: 800; background-color: #fff3b0;" for _ in row]
        return ["" for _ in row]
    return df.style.apply(row_style, axis=1)

def style_fifo_balance(df):
    def style_cell(value, column_name):
        if str(column_name).lower() == "balance_qty":
            return "background-color: #d1fae5; color: #065f46; font-weight: 900;"
        return ""
    return df.style.apply(lambda row: [style_cell(row[col], col) for col in df.columns], axis=1)

def show_df(rows, key=None, total=False):
    rows = format_date_columns(rows)
    if key:
        df = filter_rows(rows, key)
    else:
        df = pd.DataFrame(rows)
    if total:
        df = add_total_row(df)
    if df.empty:
        st.info("No data available.")
    else:
        st.dataframe(style_total_row(df), use_container_width=True, hide_index=True)
    return df


def filter_rows(rows, key):
    rows = format_date_columns(rows)
    df = pd.DataFrame(rows)
    if df.empty:
        st.info("No data available.")
        return df

    if "filter_key_counter" not in st.session_state:
        st.session_state.filter_key_counter = {}
    base_key = str(key)
    st.session_state.filter_key_counter[base_key] = st.session_state.filter_key_counter.get(base_key, 0) + 1
    unique_key = f"{base_key}_{st.session_state.filter_key_counter[base_key]}"

    with st.expander("Search / Multiple Field Filters", expanded=True):
        search = st.text_input("Global Search", key=f"global_search_{unique_key}")
        if search:
            mask = df.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
            df = df[mask]

        f1, f2 = st.columns([1, 2])
        with f1:
            filter_cols = st.multiselect("Fields", list(df.columns), key=f"field_filter_cols_{unique_key}")
        with f2:
            for col in filter_cols:
                values = sorted([str(x) for x in df[col].dropna().unique().tolist()])
                selected_values = st.multiselect(f"Filter {col}", values, key=f"field_filter_{unique_key}_{col}")
                if selected_values:
                    df = df[df[col].astype(str).isin(selected_values)]

    if df.empty:
        st.info("No data available after filter.")
    return df

def show_filtered_df(rows, key, total=False):
    df = filter_rows(rows, key)
    if total:
        df = add_total_row(df)
    if not df.empty:
        st.dataframe(style_total_row(df), use_container_width=True, hide_index=True)
    return df

def show_fifo_df(rows, key):
    df = filter_rows(rows, key)
    if not df.empty:
        st.dataframe(style_fifo_balance(df), use_container_width=True, hide_index=True)
    return df

def get_notification_settings():
    rows = fetch_all("SELECT * FROM notification_settings WHERE id=1")
    return rows[0] if rows else {}

def send_email_message(to_email, subject, body):
    settings = get_notification_settings()
    if not settings or not settings.get("enable_email"):
        return False, "Email disabled"
    if not settings.get("sender_email") or not settings.get("app_password"):
        return False, "Sender email/app password not configured"
    msg = EmailMessage()
    msg["From"] = settings["sender_email"]
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(settings.get("smtp_server") or "smtp.gmail.com", int(settings.get("smtp_port") or 587)) as smtp:
        smtp.starttls()
        smtp.login(settings["sender_email"], settings["app_password"])
        smtp.send_message(msg)
    return True, "Sent"

def notify_event(event_type, subject, body):
    recipients = fetch_all("""
        SELECT recipient_email FROM notification_recipients
        WHERE event_type=? AND is_active=true
    """, (event_type,))
    results = []
    for r in recipients:
        ok, msg = send_email_message(r["recipient_email"], subject, body)
        results.append(f'{r["recipient_email"]}: {msg}')
    return results

def quick_add_supplier():
    with st.expander("+ Add Supplier"):
        name = st.text_input("Supplier Name", key="quick_supplier_name")
        if st.button("Save Supplier", key="quick_supplier_save"):
            if name.strip():
                execute_query("INSERT INTO suppliers (supplier_name) VALUES (?) ON CONFLICT DO NOTHING", (name.strip(),))
                st.success("Supplier added. Refresh/reopen this module if not visible immediately.")

def quick_add_warehouse():
    with st.expander("+ Add Warehouse"):
        name = st.text_input("Warehouse Name", key="quick_warehouse_name")
        if st.button("Save Warehouse", key="quick_warehouse_save"):
            if name.strip():
                execute_query("INSERT INTO warehouses (warehouse_name) VALUES (?) ON CONFLICT DO NOTHING", (name.strip(),))
                st.success("Warehouse added. Refresh/reopen this module if not visible immediately.")

def quick_add_product():
    with st.expander("+ Add Product"):
        c1, c2, c3 = st.columns(3)
        with c1:
            code = st.text_input("Product Code", key="quick_product_code")
            name = st.text_input("Product Name", key="quick_product_name")
        with c2:
            unit = st.text_input("Unit", value="Nos", key="quick_product_unit")
            price = st.number_input("Price", min_value=0.0, key="quick_product_price")
        with c3:
            currency = st.selectbox("Currency", CURRENCIES, key="quick_product_currency")
        if st.button("Save Product", key="quick_product_save"):
            if code.strip() and name.strip():
                execute_query("""
                    INSERT INTO products (product_code, product_name, unit, unit_price, currency)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT DO NOTHING
                """, (code.strip(), name.strip(), unit, price, currency))
                st.success("Product added. Refresh/reopen this module if not visible immediately.")

def quick_add_customer():
    with st.expander("+ Add Customer"):
        name = st.text_input("Customer Name", key="quick_customer_name")
        email = st.text_input("Email", key="quick_customer_email")
        whatsapp = st.text_input("WhatsApp No", key="quick_customer_whatsapp")
        terms = fetch_all("SELECT * FROM payment_terms ORDER BY days LIMIT 200")
        term_options = {"No Payment Term": None}
        for t in terms:
            term_options[f'{t["term_name"]} - {t["days"]} days'] = t["id"]
        selected_term = st.selectbox("Default Payment Term", list(term_options.keys()), key="quick_customer_payment_term")
        if st.button("Save Customer", key="quick_customer_save"):
            if name.strip():
                execute_query("""
                    INSERT INTO customers (customer_name, email, whatsapp_no, payment_term_id)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT DO NOTHING
                """, (name.strip(), email.strip(), whatsapp.strip(), term_options[selected_term]))
                st.success("Customer added. Refresh/reopen this module if not visible immediately.")

def quick_add_payment_term():
    with st.expander("+ Add Payment Term"):
        term = st.text_input("Term Name", key="quick_term_name")
        days = st.number_input("Days", min_value=0, step=1, key="quick_term_days")
        if st.button("Save Payment Term", key="quick_term_save"):
            if term.strip():
                execute_query("INSERT INTO payment_terms (term_name, days) VALUES (?, ?) ON CONFLICT DO NOTHING", (term.strip(), int(days)))
                st.success("Payment term added. Refresh/reopen this module if not visible immediately.")

def edit_button_column(rows, prefix):
    # The visual table shows Edit as last column; actual edit controls appear below for selected row.
    return [dict(r, Edit="Use edit selector below") for r in rows]

def to_excel_bytes(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Report")
    return output.getvalue()

def to_pdf_bytes(df, title):
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    data = [list(df.columns)] + df.astype(str).values.tolist()
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0b5cab")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 7),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
    ]))
    doc.build([Paragraph(title, styles["Title"]), Spacer(1,10), table])
    return output.getvalue()

def to_image_bytes(df, title):
    fig, ax = plt.subplots(figsize=(12, max(3, len(df) * 0.35 + 1.5)))
    ax.axis("off")
    ax.set_title(title, fontsize=16, fontweight="bold", pad=12)
    table = ax.table(cellText=df.astype(str).values, colLabels=df.columns, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.35)
    output = io.BytesIO()
    plt.savefig(output, format="png", bbox_inches="tight", dpi=180)
    plt.close(fig)
    return output.getvalue()

def export_buttons(df, report_name):
    if df.empty:
        return
    c1, c2, c3 = st.columns(3)
    c1.download_button("Export Excel", to_excel_bytes(df), f"{report_name}.xlsx")
    c2.download_button("Export PDF", to_pdf_bytes(df, report_name), f"{report_name}.pdf")
    c3.download_button("Export Image", to_image_bytes(df, report_name), f"{report_name}.png")


def logo_data_uri():
    try:
        if LOGO_PATH.exists():
            data = base64.b64encode(LOGO_PATH.read_bytes()).decode("utf-8")
            return f"data:image/png;base64,{data}"
    except Exception:
        pass
    return ""

def parse_date_for_input(value):
    try:
        if value:
            return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except Exception:
        pass
    return date.today()

def delivery_note_html(data):
    delivery_date = format_date_ddmmyyyy(data.get("delivery_date", ""))
    due_date = format_date_ddmmyyyy(data.get("payment_due_date", ""))
    po_date = format_date_ddmmyyyy(data.get("po_date", ""))
    items = data.get("items") or []
    if not items:
        qty = float(data.get("qty") or 0)
        unit_price = float(data.get("unit_price") or 0)
        amount = float(data.get("sale_amount") or (qty * unit_price))
        items = [{
            "product_code": data.get("product_code", ""),
            "product_name": data.get("product_name", ""),
            "pallet_no": data.get("pallet_no", ""),
            "box_no": data.get("box_no", ""),
            "qty": qty,
            "unit_price": unit_price,
            "currency": data.get("currency", ""),
            "amount": amount,
            "original_invoice_no": data.get("original_invoice_no", ""),
            "po_number": data.get("po_number", ""),
            "po_date": data.get("po_date", ""),
        }]

    total_qty = sum(float(i.get("qty") or 0) for i in items)
    total_amount = sum(float(i.get("amount") or 0) for i in items)
    currency = data.get("currency", "") or (items[0].get("currency", "") if items else "")
    original_invoice_no = data.get("original_invoice_no", "") or (items[0].get("original_invoice_no", "") if items else "")
    po_number = data.get("po_number", "") or (items[0].get("po_number", "") if items else "")
    po_date = format_date_ddmmyyyy(data.get("po_date", "") or (items[0].get("po_date", "") if items else ""))

    item_rows = ""
    for idx, item in enumerate(items, start=1):
        qty = float(item.get("qty") or 0)
        unit_price = float(item.get("unit_price") or 0)
        amount = float(item.get("amount") or 0)
        item_rows += f"""
        <tr>
          <td>{idx}</td>
          <td>{item.get("original_invoice_no", original_invoice_no)}</td>
          <td>{item.get("po_number", po_number)}</td>
          <td>{format_date_ddmmyyyy(item.get("po_date", po_date))}</td>
          <td>{item.get("product_code", "")}</td>
          <td>{item.get("product_name", "")}</td>
          <td>{item.get("pallet_no", "")}</td>
          <td>{item.get("box_no", "")}</td>
          <td class="right">{qty:,.2f}</td>
          <td class="right">{unit_price:,.4f}</td>
          <td>{item.get("currency", currency)}</td>
          <td class="right">{amount:,.2f}</td>
        </tr>
        """

    logo_src = logo_data_uri()
    logo_html = f'<img src="{logo_src}" style="max-width:180px;max-height:70px;">' if logo_src else ''
    return f"""
    <html>
    <head>
    <style>
    @page {{ size: A4 portrait; margin: 12mm; }}
    body {{ font-family: Aptos, Arial, sans-serif; color:#111827; padding: 0; }}
    .invoice-title {{ font-size:28px; font-weight:900; color:#003B73; text-align:right; }}
    .company {{ font-size:22px; font-weight:900; color:#003B73; }}
    .small {{ font-size:12px; color:#374151; }}
    .box {{ border:1px solid #111827; padding:9px; margin-top:9px; }}
    .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; }}
    .detail-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:5px 12px; }}
    .detail-cell {{ border-bottom:1px dotted #9ca3af; padding:2px 0; }}
    table {{ width:100%; border-collapse:collapse; margin-top:14px; font-size:10.5px; }}
    th {{ background:#e5e7eb; color:#111827; font-weight:900; border:1px solid #111827; padding:5px; }}
    td {{ border:1px solid #111827; padding:5px; }}
    .right {{ text-align:right; }}
    .total-row td {{ font-weight:900; background:#fef3c7; }}
    .footer {{ margin-top:35px; display:grid; grid-template-columns:1fr 1fr; gap:25px; }}
    .sign {{ border-top:1px solid #111827; padding-top:8px; text-align:center; font-weight:900; }}
    </style>
    </head>
    <body>
      <div class="grid">
        <div>
          {logo_html}
          <div class="company">FOUR STAR INDUSTRIES PVT. LTD.</div>
          <div class="small">Export Shipment Monitoring System</div>
        </div>
        <div class="invoice-title">COMMERCIAL INVOICE</div>
      </div>

      <div class="grid">
        <div class="box">
          <b>BILL TO / CUSTOMER</b><br>
          {data.get("customer_name", "")}<br>
          <span class="small">Ship To / Customer delivery location as per purchase order</span>
        </div>
        <div class="box">
          <b>INVOICE DETAILS</b><br>
          <div class="detail-grid">
            <div class="detail-cell">Delivery Invoice No: <b>{data.get("delivery_invoice_no", "")}</b></div>
            <div class="detail-cell">Delivery Date: <b>{delivery_date}</b></div>
            <div class="detail-cell">Original Invoice No: <b>{original_invoice_no}</b></div>
            <div class="detail-cell">Shipment No: <b>{data.get("shipment_no", "")}</b></div>
            <div class="detail-cell">PO Number: <b>{po_number}</b></div>
            <div class="detail-cell">PO Date: <b>{po_date}</b></div>
            <div class="detail-cell">Payment Term: <b>{data.get("payment_term", "")}</b></div>
            <div class="detail-cell">Due Date: <b>{due_date}</b></div>
          </div>
        </div>
      </div>

      <table>
        <tr>
          <th>Item</th><th>Original Invoice No</th><th>PO No</th><th>PO Date</th><th>Product Code</th><th>Description</th>
          <th>Pallet No</th><th>Box No</th><th class="right">Qty</th>
          <th class="right">Unit Price</th><th>Currency</th><th class="right">Amount</th>
        </tr>
        {item_rows}
        <tr class="total-row">
          <td colspan="8" class="right">TOTAL</td>
          <td class="right">{total_qty:,.2f}</td>
          <td></td><td>{currency}</td>
          <td class="right">{total_amount:,.2f}</td>
        </tr>
      </table>

      <div class="box">
        <b>References:</b><br>
        Original Invoice Number: <b>{original_invoice_no}</b><br>
        Shipment Number: <b>{data.get("shipment_no", "")}</b><br>
        PO Number / Date: <b>{po_number}</b> / <b>{po_date}</b>
      </div>

      <div class="footer">
        <div class="sign">Prepared By</div>
        <div class="sign">Authorized Signatory</div>
      </div>
    </body>
    </html>
    """

def build_delivery_invoice_print_data(delivery_invoice_no):
    rows = fetch_all("""
        SELECT d.*, c.customer_name, s.shipment_no, s.invoice_no AS original_invoice_no,
               p.product_code, p.product_name,
               COALESCE(d.po_number, s.po_number, p.po_number) AS po_number,
               COALESCE(d.po_date, s.po_date, p.po_date) AS po_date,
               b.pallet_no, b.box_no
        FROM customer_deliveries d
        JOIN customers c ON d.customer_id = c.id
        JOIN shipments s ON d.shipment_id = s.id
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products p ON b.product_id = p.id
        WHERE d.delivery_invoice_no=?
        ORDER BY d.id
    """, (delivery_invoice_no,))
    if not rows:
        return None

    first = rows[0]
    items = []
    total_qty = 0
    total_amount = 0
    for r in rows:
        qty = float(r.get("delivered_qty") or 0)
        amount = float(r.get("sale_amount") or 0)
        total_qty += qty
        total_amount += amount
        items.append({
            "original_invoice_no": r.get("original_invoice_no", ""),
            "product_code": r.get("product_code", ""),
            "product_name": r.get("product_name", ""),
            "po_number": r.get("po_number", ""),
            "po_date": r.get("po_date", ""),
            "pallet_no": r.get("pallet_no", ""),
            "box_no": r.get("box_no", "") or "-",
            "qty": qty,
            "unit_price": float(r.get("unit_price") or 0),
            "currency": r.get("currency", ""),
            "amount": amount,
        })

    return {
        "customer_name": first.get("customer_name", ""),
        "shipment_no": first.get("shipment_no", ""),
        "original_invoice_no": first.get("original_invoice_no", ""),
        "delivery_invoice_no": delivery_invoice_no,
        "delivery_date": first.get("delivery_date", ""),
        "payment_term": f'{first.get("payment_terms_days", 0)} Days',
        "payment_due_date": first.get("payment_due_date", ""),
        "currency": first.get("currency", ""),
        "qty": total_qty,
        "sale_amount": total_amount,
        "po_number": first.get("po_number", ""),
        "po_date": first.get("po_date", ""),
        "items": items,
    }

def print_popup(html):
    components.html(f"""
    <script>
      const w = window.open('', '_blank', 'width=900,height=700');
      w.document.write(`{html}`);
      w.document.close();
      w.focus();
      setTimeout(() => w.print(), 500);
    </script>
    """, height=0)


def require_roles(allowed):
    if st.session_state.user["role"] not in allowed:
        st.error("You do not have permission to access this module.")
        st.stop()

def login_page():
    st.markdown("<br>", unsafe_allow_html=True)
    c_logo1, c_logo2, c_logo3 = st.columns([1, 2, 1])
    with c_logo2:
        if LOGO_PATH.exists():
            st.image(str(LOGO_PATH), use_container_width=True)
        st.markdown("""
        <div style="text-align:center; color:#003b73; font-size:34px; font-weight:900; margin-top:0px; margin-bottom:8px;">
            EXPORT SHIPMENT<br>MONITORING SYSTEM
        </div>
        """, unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        username = st.text_input("User Name", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login", type="primary", use_container_width=True, key="login_button"):
            user = verify_user(username, password)
            if user:
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Invalid user name or password.")
        st.info("Default login: superadmin/super123, admin/admin123, user/user123")
        st.markdown('</div>', unsafe_allow_html=True)

def overdue_rows():
    return fetch_all("""
        SELECT
            d.id AS delivery_id,
            d.delivery_invoice_no,
            c.customer_name,
            c.email,
            c.whatsapp_no,
            d.delivery_date,
            d.payment_due_date,
            d.sale_amount,
            COALESCE(SUM(p.payment_amount), 0) AS paid_amount,
            d.sale_amount - COALESCE(SUM(p.payment_amount), 0) AS pending_amount
        FROM customer_deliveries d
        JOIN customers c ON d.customer_id = c.id
        LEFT JOIN payments p ON d.id = p.delivery_id
        GROUP BY
            d.id,
            d.delivery_invoice_no,
            c.customer_name,
            c.email,
            c.whatsapp_no,
            d.delivery_date,
            d.payment_due_date,
            d.sale_amount
        HAVING
            d.sale_amount - COALESCE(SUM(p.payment_amount), 0) > 0
            AND d.payment_due_date < CURRENT_DATE
        ORDER BY d.payment_due_date
    """)
    return fetch_all("""
        SELECT d.id delivery_id, d.delivery_invoice_no, c.customer_name, c.email, c.whatsapp_no,
               d.delivery_date, d.payment_due_date, d.sale_amount,
               IFNULL(SUM(p.payment_amount),0) paid_amount,
               d.sale_amount - IFNULL(SUM(p.payment_amount),0) pending_amount
        FROM customer_deliveries d
        JOIN customers c ON d.customer_id = c.id
        LEFT JOIN payments p ON d.id = p.delivery_id
        GROUP BY d.id
        HAVING pending_amount > 0 AND date(d.payment_due_date) < date('now')
        ORDER BY d.payment_due_date
    """)

def whatsapp_link(phone, message):
    phone = str(phone or "").replace("+", "").replace(" ", "").replace("-", "")
    return f"https://wa.me/{phone}?text={urllib.parse.quote(message)}"

if "user" not in st.session_state:
    login_page()
    st.stop()

top_layout()
st.session_state.filter_key_counter = {}

role = st.session_state.user["role"]
cleanup_orphan_transactions()

all_items = ["Dashboard", "Masters", "Shipment Entry", "Delivery to Customer", "Payment Entry", "Coverage Plan", "Admin", "Reports", "Overdue Notification"]
if role == "user":
    all_items = ["Dashboard", "Delivery to Customer", "Coverage Plan", "Reports"]

selected_tabs = st.tabs(all_items)


def customer_form():
    require_roles(("admin", "super_admin"))
    st.subheader("Customer Master")
    terms = fetch_all("SELECT * FROM payment_terms ORDER BY days LIMIT 200")
    term_options = {"No Payment Term": None}
    for t in terms:
        term_options[f'{t["term_name"]} - {t["days"]} days'] = t["id"]

    c1, c2 = st.columns(2)
    with c1:
        customer_name = st.text_input("Customer Name", key="customer_name")
        contact_person = st.text_input("Contact Person", key="customer_contact_person")
        email = st.text_input("Email", key="customer_email")
    with c2:
        phone = st.text_input("Phone", key="customer_phone")
        whatsapp_no = st.text_input("WhatsApp No", key="customer_whatsapp_no")
        address = st.text_area("Address", key="customer_address")
        selected_term = st.selectbox("Default Payment Term", list(term_options.keys()), key="customer_payment_term")

    if st.button("Save Customer Master", type="primary", key="save_customer_master"):
        try:
            execute_query("""
                INSERT INTO customers
                (customer_name, contact_person, email, phone, whatsapp_no, address, payment_term_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (customer_name, contact_person, email, phone, whatsapp_no, address, term_options[selected_term]))
            st.success("Customer saved successfully.")
        except sqlite3.IntegrityError:
            st.error("Duplicate customer found.")

    rows = fetch_all("""
        SELECT c.id, c.customer_name, c.contact_person, c.email, c.phone, c.whatsapp_no,
               pt.term_name AS payment_term, c.address
        FROM customers c
        LEFT JOIN payment_terms pt ON c.payment_term_id = pt.id
        ORDER BY c.id DESC
        LIMIT 300
    """)
    show_filtered_df(edit_button_column(rows, "customers"), "master_customers", total=True)

    if st.session_state.user["role"] == "super_admin":
        st.divider()
        st.subheader("Edit Customer Master")
        old_rows = fetch_all("SELECT * FROM customers ORDER BY id DESC LIMIT 300")
        if old_rows:
            row_map = {f'{r["id"]} | {r["customer_name"]}': r for r in old_rows}
            selected = row_map[st.selectbox("Select Customer to Edit", list(row_map.keys()), key="edit_customer_select")]
            current_term_id = selected.get("payment_term_id")
            selected_term_label = "No Payment Term"
            for label, tid in term_options.items():
                if tid == current_term_id:
                    selected_term_label = label
                    break

            e1, e2 = st.columns(2)
            with e1:
                e_customer_name = st.text_input("Edit Customer Name", selected.get("customer_name") or "", key="edit_customer_name")
                e_contact_person = st.text_input("Edit Contact Person", selected.get("contact_person") or "", key="edit_customer_contact")
                e_email = st.text_input("Edit Email", selected.get("email") or "", key="edit_customer_email")
            with e2:
                e_phone = st.text_input("Edit Phone", selected.get("phone") or "", key="edit_customer_phone")
                e_whatsapp = st.text_input("Edit WhatsApp No", selected.get("whatsapp_no") or "", key="edit_customer_whatsapp")
                e_address = st.text_area("Edit Address", selected.get("address") or "", key="edit_customer_address")
                e_term = st.selectbox("Edit Default Payment Term", list(term_options.keys()), index=list(term_options.keys()).index(selected_term_label), key="edit_customer_term")

            if st.button("Update Customer", type="primary", key="update_customer_master"):
                execute_query("""
                    UPDATE customers
                    SET customer_name=?, contact_person=?, email=?, phone=?, whatsapp_no=?, address=?, payment_term_id=?
                    WHERE id=?
                """, (e_customer_name, e_contact_person, e_email, e_phone, e_whatsapp, e_address, term_options[e_term], selected["id"]))
                st.success("Customer updated successfully.")
                st.rerun()



def product_form():
    require_roles(("admin", "super_admin"))
    st.subheader("Product Master")

    c1, c2 = st.columns(2)
    with c1:
        product_code = st.text_input("Product Code", key="product_code")
        product_name = st.text_input("Product Name", key="product_name")
        program = st.text_input("Program", key="product_program")
        assy_plant = st.text_input("Assy Plant", key="product_assy_plant")
        unit = st.text_input("Unit", value="Nos", key="product_unit")
        po_number = st.text_input("PO Number", key="product_po_number")
    with c2:
        unit_price = st.number_input("Price", min_value=0.0, step=1.0, key="product_unit_price")
        currency = st.selectbox("Currency", CURRENCIES, key="product_currency")
        weight = st.number_input("Weight", min_value=0.0, step=1.0, key="product_weight")
        lcr_weekly = st.number_input("LCR Weekly", min_value=0.0, step=1.0, key="product_lcr_weekly")
        mcr_weekly = st.number_input("MCR Weekly", min_value=0.0, step=1.0, key="product_mcr_weekly")
        po_date = st.date_input("PO Date", value=date.today(), key="product_po_date")
        two_months_inventory = lcr_weekly * 8
        st.markdown(f'<div class="total-box">Two Months Inventory = LCR Weekly × 8 = {two_months_inventory:,.2f}</div>', unsafe_allow_html=True)

    if st.button("Save Product Master", type="primary", key="save_product_master"):
        try:
            execute_query("""
                INSERT INTO products
                (product_code, product_name, program, assy_plant, unit, unit_price, currency, weight,
                 lcr_weekly, mcr_weekly, two_months_inventory, po_number, po_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (product_code, product_name, program, assy_plant, unit, unit_price, currency, weight,
                  lcr_weekly, mcr_weekly, two_months_inventory, po_number, str(po_date)))
            st.success("Product saved successfully.")
        except sqlite3.IntegrityError:
            st.error("Duplicate product code found.")

    rows = fetch_all("""
        SELECT id, product_code, product_name, program, assy_plant, unit, unit_price, currency,
               weight, lcr_weekly, mcr_weekly, two_months_inventory, po_number, po_date
        FROM products
        ORDER BY id DESC
        LIMIT 300
    """)
    show_filtered_df(edit_button_column(rows, "products"), "master_products", total=True)

    if st.session_state.user["role"] == "super_admin":
        st.divider()
        st.subheader("Edit Product Master")
        old_rows = fetch_all("SELECT * FROM products ORDER BY id DESC LIMIT 300")
        if old_rows:
            row_map = {f'{r["id"]} | {r["product_code"]} | {r["product_name"]}': r for r in old_rows}
            selected_key = st.selectbox("Select Product Master Entry to Edit", list(row_map.keys()), key="edit_product_select")
            selected = row_map[selected_key]
            sid = selected["id"]

            e1, e2 = st.columns(2)
            with e1:
                e_product_code = st.text_input("Edit Product Code", selected.get("product_code") or "", key=f"edit_product_code_{sid}")
                e_product_name = st.text_input("Edit Product Name", selected.get("product_name") or "", key=f"edit_product_name_{sid}")
                e_program = st.text_input("Edit Program", selected.get("program") or "", key=f"edit_product_program_{sid}")
                e_assy_plant = st.text_input("Edit Assy Plant", selected.get("assy_plant") or "", key=f"edit_product_assy_plant_{sid}")
                e_unit = st.text_input("Edit Unit", selected.get("unit") or "Nos", key=f"edit_product_unit_{sid}")
                e_po_number = st.text_input("Edit PO Number", selected.get("po_number") or "", key=f"edit_product_po_number_{sid}")
            with e2:
                e_unit_price = st.number_input("Edit Price", min_value=0.0, value=float(selected.get("unit_price") or 0), step=1.0, key=f"edit_product_unit_price_{sid}")
                current_currency = selected.get("currency") or "INR"
                e_currency = st.selectbox("Edit Currency", CURRENCIES, index=CURRENCIES.index(current_currency) if current_currency in CURRENCIES else 0, key=f"edit_product_currency_{sid}")
                e_weight = st.number_input("Edit Weight", min_value=0.0, value=float(selected.get("weight") or 0), step=1.0, key=f"edit_product_weight_{sid}")
                e_lcr_weekly = st.number_input("Edit LCR Weekly", min_value=0.0, value=float(selected.get("lcr_weekly") or 0), step=1.0, key=f"edit_product_lcr_weekly_{sid}")
                e_mcr_weekly = st.number_input("Edit MCR Weekly", min_value=0.0, value=float(selected.get("mcr_weekly") or 0), step=1.0, key=f"edit_product_mcr_weekly_{sid}")
                e_po_date = st.date_input("Edit PO Date", value=parse_date_for_input(selected.get("po_date")), key=f"edit_product_po_date_{sid}")
                e_two_months_inventory = e_lcr_weekly * 8
                st.markdown(f'<div class="total-box">Two Months Inventory = LCR Weekly × 8 = {e_two_months_inventory:,.2f}</div>', unsafe_allow_html=True)

            if st.button("Update Product Master", type="primary", key=f"update_product_master_{sid}"):
                try:
                    execute_query("""
                        UPDATE products
                        SET product_code=?, product_name=?, program=?, assy_plant=?, unit=?,
                            unit_price=?, currency=?, weight=?, lcr_weekly=?, mcr_weekly=?,
                            two_months_inventory=?, po_number=?, po_date=?
                        WHERE id=?
                    """, (e_product_code, e_product_name, e_program, e_assy_plant, e_unit,
                          e_unit_price, e_currency, e_weight, e_lcr_weekly, e_mcr_weekly,
                          e_two_months_inventory, e_po_number, str(e_po_date), sid))
                    st.success("Product updated successfully.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Duplicate product code found.")

            st.divider()
            st.subheader("Delete Product Master")
            st.warning("Delete requires your login password.")
            delete_password = st.text_input("Password to Delete Product", type="password", key=f"delete_product_password_{sid}")
            if st.button("Delete Product", key=f"delete_product_btn_{sid}"):
                if delete_record_with_password("products", sid, delete_password, f"Product {selected.get('product_code')}"):
                    st.rerun()


def master_form(title, table, fields, allowed_roles=("admin", "super_admin")):
    require_roles(allowed_roles)
    st.subheader(title)
    values = {}
    cols = st.columns(2)
    for i, field in enumerate(fields):
        with cols[i % 2]:
            if field in ("days", "unit_price", "weight", "lcr_weekly", "mcr_weekly", "two_months_inventory", "shipment_time_days"):
                values[field] = st.number_input(field.replace("_", " ").title(), min_value=0.0 if field in ("unit_price", "weight", "lcr_weekly", "mcr_weekly", "two_months_inventory") else 0, step=1.0 if field in ("unit_price", "weight", "lcr_weekly", "mcr_weekly", "two_months_inventory") else 1, key=f"{table}_{field}")
            elif field == "currency":
                values[field] = st.selectbox("Currency", CURRENCIES, key=f"{table}_{field}")
            else:
                values[field] = st.text_input(field.replace("_", " ").title(), key=f"{table}_{field}")
    if st.button(f"Save {title}", type="primary", key=f"save_{table}"):
        try:
            execute_query(f"INSERT INTO {table} ({', '.join(fields)}) VALUES ({', '.join(['?'] * len(fields))})", tuple(values.values()))
            st.success(f"{title} saved successfully.")
        except sqlite3.IntegrityError:
            st.error("Duplicate value found. Please check unique fields.")
    show_filtered_df(edit_button_column(fetch_all(f"SELECT * FROM {table} ORDER BY id DESC LIMIT 300"), table), f"master_{table}", total=True)

    if st.session_state.user["role"] == "super_admin":
        st.divider()
        st.subheader(f"Edit {title}")
        rows = fetch_all(f"SELECT * FROM {table} ORDER BY id DESC LIMIT 300")
        if rows:
            row_map = {f'{r["id"]} | ' + str(r.get(fields[0], "")): r for r in rows}
            selected = row_map[st.selectbox(f"Select {title} Entry to Edit", list(row_map.keys()), key=f"edit_select_{table}")]
            edit_values = {}
            ecols = st.columns(2)
            for i, field in enumerate(fields):
                with ecols[i % 2]:
                    if field in ("days", "shipment_time_days"):
                        edit_values[field] = st.number_input(field.replace("_", " ").title(), min_value=0, value=int(selected.get(field) or 0), step=1, key=f"edit_{table}_{field}")
                    elif field in ("unit_price", "weight", "lcr_weekly", "mcr_weekly", "two_months_inventory"):
                        edit_values[field] = st.number_input(field.replace("_", " ").title(), min_value=0.0, value=float(selected.get(field) or 0), step=1.0, key=f"edit_{table}_{field}")
                    elif field == "currency":
                        current = selected.get(field) or "INR"
                        edit_values[field] = st.selectbox("Currency", CURRENCIES, index=CURRENCIES.index(current) if current in CURRENCIES else 0, key=f"edit_{table}_{field}")
                    else:
                        edit_values[field] = st.text_input(field.replace("_", " ").title(), value=str(selected.get(field) or ""), key=f"edit_{table}_{field}")
            if st.button(f"Update {title}", type="primary", key=f"update_{table}"):
                set_clause = ", ".join([f"{f}=?" for f in fields])
                execute_query(f"UPDATE {table} SET {set_clause} WHERE id=?", tuple(edit_values.values()) + (selected["id"],))
                st.success(f"{title} updated successfully.")
                st.rerun()

            st.divider()
            st.subheader("Delete Master Entry")
            st.warning("Delete requires your login password.")
            delete_password = st.text_input("Password to Delete", type="password", key=f"delete_{table}_{selected['id']}")
            if st.button("Delete Selected Entry", key=f"delete_btn_{table}_{selected['id']}"):
                if delete_record_with_password(table, selected["id"], delete_password, f"{title}"):
                    st.rerun()



with selected_tabs[0]:
    show_header("Dashboard")
    total_shipments = fetch_all("SELECT COUNT(*) c FROM shipments")[0]["c"]
    total_boxes = fetch_all("SELECT COUNT(*) c FROM shipment_boxes")[0]["c"]
    total_customers = fetch_all("SELECT COUNT(*) c FROM customers")[0]["c"]
    qty = fetch_all("""
        SELECT IFNULL((SELECT SUM(original_qty) FROM shipment_boxes),0) original_qty,
               IFNULL((SELECT SUM(delivered_qty) FROM customer_deliveries),0) delivered_qty,
               IFNULL((SELECT SUM(sale_amount) FROM customer_deliveries),0) total_sale
    """)[0]
    balance_qty = qty["original_qty"] - qty["delivered_qty"]
    try:
        overdue_count = len(overdue_rows())
        overdue_amount = sum(float(r.get("pending_amount") or 0) for r in overdue_rows())
    except Exception:
        overdue_count = 0
        overdue_amount = 0

    labels = [
        ("TOTAL SHIPMENTS", total_shipments, "green"),
        ("TOTAL BOXES", total_boxes, "teal"),
        ("DELIVERED QTY", qty["delivered_qty"], "orange"),
        ("BALANCE QTY", balance_qty, "blue"),
        ("TOTAL SALE", round(qty["total_sale"], 2), "yellow"),
        ("OVERDUE PAYMENTS", overdue_count, "red"),
        ("OVERDUE PAYMENT AMOUNT", f"{overdue_amount:,.2f}", "red"),
    ]
    cols = st.columns(7)
    for col, (lab, val, cls) in zip(cols, labels):
        col.markdown(f'<div class="kpi-head {cls}">{lab}</div><div class="kpi-value">{val}</div>', unsafe_allow_html=True)

    st.divider()
    st.markdown('<div class="coverage-dashboard-title">Coverage Plan Dashboard</div>', unsafe_allow_html=True)
    try:
        dashboard_products = fetch_all("""
            SELECT id, product_code, product_name
            FROM products
            ORDER BY product_code
        """)
        if dashboard_products:
            product_options = [p["product_code"] for p in dashboard_products]
            default_index = product_options.index("40257237") if "40257237" in product_options else 0

            cov_cols = st.columns([1.05, 1, 1, 1, 1])
            with cov_cols[0]:
                st.markdown('<div class="coverage-product-filter-title">Coverage Dashboard Product Filter</div>', unsafe_allow_html=True)
                dashboard_product_code = st.selectbox(
                    "Coverage Dashboard Product Filter",
                    product_options,
                    index=default_index,
                    key="dashboard_coverage_product_filter",
                    label_visibility="collapsed"
                )

            dashboard_product = next(p for p in dashboard_products if p["product_code"] == dashboard_product_code)
            coverage_kpi = fetch_all("""
                SELECT next_shipment_date, suggested_shipment_qty
                FROM coverage_plan_lines
                WHERE product_id = ?
                  AND suggested_shipment_qty > 0
                  AND (COALESCE(customer_forecast,0) > 0 OR COALESCE(delivered_to_customer,0) > 0)
                ORDER BY date(next_shipment_date), date(plan_date), week_no
                LIMIT 1
            """, (dashboard_product["id"],))

            shipment_time_row = fetch_all("""
                SELECT IFNULL(MAX(shipment_time_days),0) AS shipment_time_days
                FROM warehouses
            """)[0]

            next_date = coverage_kpi[0]["next_shipment_date"] if coverage_kpi else ""
            next_qty = float(coverage_kpi[0]["suggested_shipment_qty"] or 0) if coverage_kpi else 0
            shipment_time_days = int(shipment_time_row["shipment_time_days"] or 0)
            next_date_display = format_date_ddmmyyyy(next_date) if next_date else "-"

            with cov_cols[1]:
                st.markdown(f'<div class="kpi-head yellow">NEXT SHIPMENT DATE</div><div class="kpi-value" style="background:#fde047;color:#b91c1c;font-weight:900;">{next_date_display}</div>', unsafe_allow_html=True)
            with cov_cols[2]:
                st.markdown(f'<div class="kpi-head orange">NEXT SHIPMENT QTY</div><div class="kpi-value">{next_qty:,.0f}</div>', unsafe_allow_html=True)
            with cov_cols[3]:
                st.markdown(f'<div class="kpi-head teal">PRODUCT</div><div class="kpi-value">{dashboard_product_code}</div>', unsafe_allow_html=True)
            with cov_cols[4]:
                st.markdown(f'<div class="kpi-head green">SHIPMENT TIME</div><div class="kpi-value">{shipment_time_days} Days</div>', unsafe_allow_html=True)
        else:
            st.info("Coverage dashboard will appear after product master is available.")
    except Exception:
        st.info("Coverage Plan dashboard will appear after coverage data is available.")

    st.divider()
    st.subheader("Recent Shipments")
    show_filtered_df(fetch_all("""
        SELECT s.shipment_no, s.invoice_no, s.shipment_date, sup.supplier_name, w.warehouse_name, s.currency, s.invoice_amount
        FROM shipments s
        LEFT JOIN suppliers sup ON s.supplier_id = sup.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        ORDER BY s.id DESC LIMIT 10
    """), "dashboard_recent_shipments", total=True)



def transaction_selector(rows, key, label_field):
    data = []
    for r in rows:
        item = dict(r)
        item["Select"] = False
        data.append(item)
    if not data:
        st.info("No records available.")
        return None, pd.DataFrame()
    cols = ["Select"] + [c for c in data[0].keys() if c != "Select"]
    df = pd.DataFrame(format_date_columns(data))[cols]
    edited = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        key=key,
        column_config={"Select": st.column_config.CheckboxColumn("Select", default=False)},
        disabled=[c for c in cols if c != "Select"]
    )
    selected = None
    if "Select" in edited.columns:
        selected_rows = edited[edited["Select"] == True]
        if not selected_rows.empty:
            selected_id = int(selected_rows.iloc[0]["id"]) if "id" in selected_rows.columns else None
            if selected_id:
                selected = next((r for r in rows if int(r["id"]) == selected_id), None)
    return selected, edited

def reopen_record_message(record_type, record_id):
    st.info(f"Reopen in new window requested for {record_type} ID {record_id}. Streamlit opens secure edit forms inside the current app page; use the edit panel below for modification.")

if "Masters" in all_items:
    with selected_tabs[all_items.index("Masters")]:
        show_header("Masters")
        mtab = st.tabs(["Customer", "Supplier", "Warehouse", "Product", "Payment Terms", "Incoterm", "Forwarder"])
        with mtab[0]:
            customer_form()
        with mtab[1]:
            master_form("Supplier Master", "suppliers", ["supplier_name", "contact_person", "email", "phone", "address"])
        with mtab[2]:
            master_form("Warehouse Master", "warehouses", ["warehouse_name", "location", "contact_person", "shipment_time_days"])
        with mtab[3]:
            product_form()
        with mtab[4]:
            master_form("Payment Term Master", "payment_terms", ["term_name", "days", "remarks"])
        with mtab[5]:
            master_form("Incoterm Master", "incoterms", ["incoterm_name", "remarks"])
        with mtab[6]:
            master_form("Forwarder Master", "forwarders", ["forwarder_name", "contact_person", "email", "phone", "remarks"])

if "Shipment Entry" in all_items:
    with selected_tabs[all_items.index("Shipment Entry")]:
        require_roles(("admin", "super_admin"))
        show_header("Shipment Entry with Pallet / Product Rows")
        suppliers = fetch_all("SELECT * FROM suppliers ORDER BY supplier_name LIMIT 500")
        warehouses = fetch_all("SELECT * FROM warehouses ORDER BY warehouse_name LIMIT 500")
        products = fetch_all("SELECT * FROM products ORDER BY product_code LIMIT 500")
        forwarders = fetch_all("SELECT * FROM forwarders ORDER BY forwarder_name LIMIT 500")
        incoterms = fetch_all("SELECT * FROM incoterms ORDER BY incoterm_name LIMIT 500")
        if not suppliers or not warehouses or not products:
            st.warning("Create Supplier, Warehouse, and Product masters first.")
        else:
            supplier_map = {x["supplier_name"]: x["id"] for x in suppliers}
            warehouse_map = {x["warehouse_name"]: x["id"] for x in warehouses}
            forwarder_map = {x["forwarder_name"]: x["id"] for x in forwarders}
            incoterm_map = {x["incoterm_name"]: x["id"] for x in incoterms}
            product_options = [f'{x["product_code"]} | {x["product_name"]}' for x in products]
            product_info = {f'{x["product_code"]} | {x["product_name"]}': x for x in products}

            st.markdown('<div style="height:14px;"></div>', unsafe_allow_html=True)
            h1, h2 = st.columns(2)
            with h1:
                shipment_no = st.text_input("Shipment Number / BL No / Seaway Bill No", key="shipment_no_bl_seaway")
                shipping_bill_no = st.text_input("Shipping Bill No.", key="shipment_shipping_bill_no")
                if forwarder_map:
                    forwarder_name = st.selectbox("Forwarder Name", list(forwarder_map.keys()), key="shipment_forwarder_name")
                else:
                    forwarder_name = st.text_input("Forwarder Name", key="shipment_forwarder_name")
                    forwarder_map = {forwarder_name: None}
                invoice_no = st.text_input("Original Invoice Number")
                po_number = st.text_input("PO Number", key="shipment_po_number")
                supplier = st.selectbox("Supplier", list(supplier_map.keys()), key="shipment_supplier")
                attachment = st.file_uploader("Attach Shipment File", key="auto_file_uploader_1")
            with h2:
                shipment_doc_date = st.date_input("Shipment / BL / Seaway Bill Date", value=date.today(), key="shipment_doc_date")
                shipping_bill_date = st.date_input("Shipping Bill Date", value=date.today(), key="shipment_shipping_bill_date")
                if incoterm_map:
                    incoterm = st.selectbox("Incoterm", list(incoterm_map.keys()), key="shipment_incoterm")
                else:
                    incoterm = st.text_input("Incoterm", key="shipment_incoterm")
                    incoterm_map = {incoterm: None}
                shipment_date = st.date_input("Shipment Date", value=date.today())
                po_date = st.date_input("PO Date", value=date.today(), key="shipment_po_date")
                warehouse = st.selectbox("Warehouse", list(warehouse_map.keys()), key="shipment_warehouse")
                remarks = st.text_area("Remarks", key="auto_textarea_1")

            st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)
            st.subheader("Add Pallet/Product Row")
            if "shipment_temp_rows" not in st.session_state:
                st.session_state.shipment_temp_rows = []

            st.markdown("""
            <style>
            .shipment-grid-label {
                font-family: Aptos, Arial, sans-serif;
                font-size: 15px;
                font-weight: 900;
                color: #003B73;
                margin-bottom: 6px;
                min-height: 22px;
            }
            .amount-input-look {
                height: 52px;
                border-radius: 10px;
                background: #f3f6fa;
                display: flex;
                align-items: center;
                justify-content: center;
                font-family: Aptos, Arial, sans-serif;
                font-size: 16px;
                font-weight: 700;
                color: #1f2937;
                border: 1px solid transparent;
                margin-top: 0px;
            }
            div[data-testid="stHorizontalBlock"] div[data-testid="column"] {
                padding-top: 2px;
            }
            </style>
            """, unsafe_allow_html=True)

            r1, r2, r3, r4, r5, r6, r7 = st.columns([1.15, 1.15, 2.45, 0.95, 0.95, 0.9, 1.15])
            with r1:
                st.markdown('<div class="shipment-grid-label">Pallet Number</div>', unsafe_allow_html=True)
                pallet_no = st.text_input("Pallet Number", key="shipment_grid_pallet_no", label_visibility="collapsed")
            with r2:
                st.markdown('<div class="shipment-grid-label">Box Number (Optional)</div>', unsafe_allow_html=True)
                box_no = st.text_input("Box Number (Optional)", key="shipment_grid_box_no", label_visibility="collapsed")
            with r3:
                st.markdown('<div class="shipment-grid-label">Product Code</div>', unsafe_allow_html=True)
                selected_product = st.selectbox("Product Code", product_options, key="shipment_product_select", label_visibility="collapsed")
            selected_product_data = product_info[selected_product]
            auto_price = float(selected_product_data.get("unit_price") or 0)
            auto_currency = selected_product_data.get("currency") or "USD"
            product_id_for_key = str(selected_product_data.get("id") or selected_product).replace(" ", "_").replace("|", "_").replace("/", "_")

            with r4:
                st.markdown('<div class="shipment-grid-label">Quantity</div>', unsafe_allow_html=True)
                quantity = st.number_input(
                    "Quantity",
                    min_value=0.0,
                    step=1.0,
                    key="shipment_grid_qty",
                    label_visibility="collapsed"
                )

            with r5:
                st.markdown('<div class="shipment-grid-label">Price</div>', unsafe_allow_html=True)
                unit_price = st.number_input(
                    "Price",
                    min_value=0.0,
                    value=auto_price,
                    step=1.0,
                    key=f"shipment_grid_price_{product_id_for_key}",
                    label_visibility="collapsed"
                )

            with r6:
                st.markdown('<div class="shipment-grid-label">Currency</div>', unsafe_allow_html=True)
                currency = st.selectbox(
                    "Currency",
                    CURRENCIES,
                    index=CURRENCIES.index(auto_currency) if auto_currency in CURRENCIES else 0,
                    key=f"shipment_grid_currency_{product_id_for_key}",
                    label_visibility="collapsed"
                )

            with r7:
                st.markdown('<div class="shipment-grid-label">Amount</div>', unsafe_allow_html=True)
                amount = quantity * unit_price
                st.markdown(
                    f'<div class="amount-input-look">{amount:,.2f} {currency}</div>',
                    unsafe_allow_html=True
                )

            st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)

            if st.button("Add Row to Table", type="primary", key="shipment_grid_add_row"):
                if not pallet_no.strip():
                    st.error("Pallet Number is mandatory.")
                elif quantity <= 0:
                    st.error("Quantity must be greater than zero.")
                else:
                    new_key = (pallet_no.strip(), selected_product_data["id"])
                    existing_keys = [(r["pallet_no"], r["product_id"]) for r in st.session_state.shipment_temp_rows]
                    old_match = fetch_all("""
                        SELECT b.id, s.shipment_no
                        FROM shipment_boxes b
                        JOIN shipments s ON b.shipment_id = s.id
                        WHERE b.pallet_no = ? AND b.product_id = ?
                    """, (pallet_no.strip(), selected_product_data["id"]))
                    if new_key in existing_keys:
                        st.error("Duplicate pallet/product row already added in this shipment.")
                    elif old_match:
                        st.error(f"This pallet number is already used for the same product in shipment {old_match[0]['shipment_no']}. It cannot be used again.")
                    else:
                        st.session_state.shipment_temp_rows.append({
                            "pallet_no": pallet_no.strip(),
                            "box_no": (box_no or "").strip(),
                            "product_id": selected_product_data["id"],
                            "product_code": selected_product_data["product_code"],
                            "product_name": selected_product_data["product_name"],
                            "quantity": quantity,
                            "unit_price": unit_price,
                            "currency": currency,
                            "amount": amount,
                        })
                        st.success("Row added.")

            st.subheader("Current Shipment Rows")
            temp_df = pd.DataFrame(st.session_state.shipment_temp_rows)

            if not temp_df.empty:
                display_df = add_total_row(
                    temp_df[["pallet_no", "box_no", "product_code", "product_name", "quantity", "unit_price", "currency", "amount"]]
                )
                st.dataframe(style_total_row(display_df), use_container_width=True, hide_index=True)

                total_qty = temp_df["quantity"].sum()
                total_amount = temp_df["amount"].sum()
                st.markdown(
                    f'<div class="total-box">Total Quantity: {total_qty} &nbsp;&nbsp; | &nbsp;&nbsp; Total Amount: {total_amount:,.2f}</div>',
                    unsafe_allow_html=True
                )

                if st.button("Clear Unsaved Rows", key="clear_unsaved_shipment_rows"):
                    st.session_state.shipment_temp_rows = []
                    st.rerun()
            else:
                st.info("No rows added yet.")

            if st.button("Save Shipment with All Rows", type="primary", key="save_shipment_all_rows"):
                if not shipment_no.strip():
                    st.error("Shipment Number is mandatory.")
                elif not invoice_no.strip():
                    st.error("Original Invoice Number is mandatory.")
                elif not st.session_state.shipment_temp_rows:
                    st.error("Add at least one pallet/product row before saving shipment.")
                else:
                    try:
                        total_amount = sum(r["amount"] for r in st.session_state.shipment_temp_rows)
                        first_currency = st.session_state.shipment_temp_rows[0]["currency"]
                        path = save_upload(attachment, f"shipment_{shipment_no}")
                        execute_query("""
                            INSERT INTO shipments (shipment_no, invoice_no, po_number, po_date, shipment_date, supplier_id, warehouse_id, invoice_amount, currency, attachment_path, remarks, shipping_bill_no, shipping_bill_date, shipment_doc_date, forwarder_name, incoterm, forwarder_id, incoterm_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (shipment_no, invoice_no, po_number, str(po_date), str(shipment_date), supplier_map[supplier], warehouse_map[warehouse], total_amount, first_currency, path, remarks, shipping_bill_no, str(shipping_bill_date), str(shipment_doc_date), forwarder_name, incoterm, forwarder_map.get(forwarder_name), incoterm_map.get(incoterm)))
                        shipment_id = fetch_all("SELECT id FROM shipments WHERE shipment_no=?", (shipment_no,))[0]["id"]
                        for row in st.session_state.shipment_temp_rows:
                            old_match = fetch_all("""
                                SELECT b.id FROM shipment_boxes b
                                WHERE b.pallet_no = ? AND b.product_id = ?
                            """, (row["pallet_no"], row["product_id"]))
                            if old_match:
                                raise sqlite3.IntegrityError(f"Pallet {row['pallet_no']} already used for product {row['product_code']}")
                            execute_query("""
                                INSERT INTO shipment_boxes (shipment_id, pallet_no, box_no, product_id, original_qty, unit_price, currency, amount)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (shipment_id, row["pallet_no"], row["box_no"], row["product_id"], row["quantity"], row["unit_price"], row["currency"], row["amount"]))
                        st.session_state.shipment_temp_rows = []
                        notify_event("shipment", "New Shipment Created", f"Shipment No: {shipment_no}\nOriginal Invoice: {invoice_no}\nPO Number: {po_number}\nPO Date: {po_date}\nAmount: {total_amount}\nCurrency: {first_currency}")
                        st.success("Shipment and pallet/product rows saved successfully. Email notification attempted if enabled.")
                    except Exception as e:
                        st.error(f"Duplicate shipment or duplicate pallet row found. Existing database entries were not changed. {e}")

            st.divider()
            st.subheader("Last Shipment Entries")
            shipment_rows_for_actions = fetch_all("""
                SELECT s.id, s.shipment_no, s.invoice_no, s.po_number, s.po_date, s.shipment_date, s.shipping_bill_no, s.shipping_bill_date,
                       s.shipment_doc_date, s.forwarder_name, s.incoterm,
                       sup.supplier_name, w.warehouse_name, s.currency, s.invoice_amount
                FROM shipments s
                LEFT JOIN suppliers sup ON s.supplier_id = sup.id
                LEFT JOIN warehouses w ON s.warehouse_id = w.id
                ORDER BY s.id DESC
                LIMIT 50
            """)
            selected_shipment_action, _ = transaction_selector(shipment_rows_for_actions, "shipment_transaction_selector", "shipment_no")
            ship_action_col1, ship_action_col2 = st.columns(2)
            with ship_action_col1:
                if st.button("Reopen Selected Shipment for Modify", key="reopen_selected_shipment"):
                    if selected_shipment_action:
                        st.session_state.edit_shipment_id = selected_shipment_action["id"]
                        reopen_record_message("Shipment", selected_shipment_action["id"])
                    else:
                        st.warning("Select a shipment first.")
            with ship_action_col2:
                delete_password_ship = st.text_input("Password to Delete Selected Shipment", type="password", key="delete_selected_shipment_password")
                if st.button("Delete Selected Shipment", key="delete_selected_shipment"):
                    if not selected_shipment_action:
                        st.warning("Select a shipment first.")
                    elif check_delete_password(delete_password_ship):
                        execute_query("DELETE FROM shipment_boxes WHERE shipment_id=?", (selected_shipment_action["id"],))
                        delete_record_with_password("shipments", selected_shipment_action["id"], delete_password_ship, f"Shipment {selected_shipment_action['shipment_no']}")
                        st.rerun()
                    else:
                        st.error("Wrong password. Delete cancelled.")

            st.subheader("Saved Shipment / Pallet Stock")
            show_filtered_df(fetch_all("""
                SELECT s.shipment_no, s.invoice_no, b.pallet_no, b.box_no, p.product_code, p.product_name,
                       b.original_qty, b.unit_price, b.currency, b.amount
                FROM shipment_boxes b
                JOIN shipments s ON b.shipment_id = s.id
                JOIN products p ON b.product_id = p.id
                ORDER BY b.id DESC
            """), "auto_filter_key_1", total=True)

            if st.session_state.user["role"] == "super_admin":
                st.divider()
                st.subheader("Super Admin: Edit Old Shipment Header")
                old_shipments = fetch_all("""
                    SELECT s.*, sup.supplier_name, w.warehouse_name
                    FROM shipments s
                    LEFT JOIN suppliers sup ON s.supplier_id = sup.id
                    LEFT JOIN warehouses w ON s.warehouse_id = w.id
                    ORDER BY s.id DESC
                """)
                if old_shipments:
                    ship_map = {f'{s["id"]} | {s["shipment_no"]} | Invoice {s["invoice_no"]}': s for s in old_shipments}
                    default_ship_key = None
                    if st.session_state.get("edit_shipment_id"):
                        default_ship_key = next((k for k, v in ship_map.items() if v["id"] == st.session_state.edit_shipment_id), None)
                    ship_keys = list(ship_map.keys())
                    default_ship_index = ship_keys.index(default_ship_key) if default_ship_key in ship_keys else 0
                    edit_ship = ship_map[st.selectbox("Select Shipment to Edit", ship_keys, index=default_ship_index, key="edit_shipment_header_select")]
                    suppliers2 = fetch_all("SELECT * FROM suppliers ORDER BY supplier_name LIMIT 500")
                    warehouses2 = fetch_all("SELECT * FROM warehouses ORDER BY warehouse_name LIMIT 500")
                    supplier_names = [x["supplier_name"] for x in suppliers2]
                    warehouse_names = [x["warehouse_name"] for x in warehouses2]
                    supplier_id_map = {x["supplier_name"]: x["id"] for x in suppliers2}
                    warehouse_id_map = {x["warehouse_name"]: x["id"] for x in warehouses2}
                    sh1, sh2 = st.columns(2)
                    with sh1:
                        edit_shipment_no = st.text_input("Edit Shipment Number", edit_ship["shipment_no"], key="edit_header_shipment_no")
                        edit_invoice_no = st.text_input("Edit Original Invoice Number", edit_ship["invoice_no"], key="edit_header_invoice_no")
                        edit_shipment_date = st.text_input("Edit Shipment Date YYYY-MM-DD", edit_ship["shipment_date"] or "", key="edit_header_date")
                    with sh2:
                        current_supplier = edit_ship.get("supplier_name") if edit_ship.get("supplier_name") in supplier_names else (supplier_names[0] if supplier_names else "")
                        current_warehouse = edit_ship.get("warehouse_name") if edit_ship.get("warehouse_name") in warehouse_names else (warehouse_names[0] if warehouse_names else "")
                        edit_supplier = st.selectbox("Edit Supplier", supplier_names, index=supplier_names.index(current_supplier) if current_supplier in supplier_names else 0, key="edit_header_supplier")
                        edit_warehouse = st.selectbox("Edit Warehouse", warehouse_names, index=warehouse_names.index(current_warehouse) if current_warehouse in warehouse_names else 0, key="edit_header_warehouse")
                        edit_remarks = st.text_area("Edit Remarks", edit_ship["remarks"] or "", key="edit_header_remarks")
                    if st.button("Update Shipment Header", type="primary", key="update_shipment_header"):
                        if not edit_shipment_no.strip() or not edit_invoice_no.strip():
                            st.error("Shipment Number and Original Invoice Number are mandatory.")
                        else:
                            try:
                                execute_query("""
                                    UPDATE shipments
                                    SET shipment_no=?, invoice_no=?, shipment_date=?, supplier_id=?, warehouse_id=?, remarks=?
                                    WHERE id=?
                                """, (edit_shipment_no.strip(), edit_invoice_no.strip(), edit_shipment_date.strip(),
                                      supplier_id_map[edit_supplier], warehouse_id_map[edit_warehouse], edit_remarks, edit_ship["id"]))
                                st.success("Shipment header updated successfully.")
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.error("Duplicate shipment number found.")


            if st.session_state.user["role"] == "super_admin":
                st.divider()
                st.subheader("Super Admin: Edit Old Pallet / Product Entry")
                old_rows = fetch_all("""
                    SELECT b.id, s.shipment_no, s.invoice_no, b.pallet_no, b.box_no,
                           p.product_code, p.product_name, b.original_qty, b.unit_price, b.currency, b.amount
                    FROM shipment_boxes b
                    JOIN shipments s ON b.shipment_id = s.id
                    JOIN products p ON b.product_id = p.id
                    ORDER BY b.id DESC
                """)
                if old_rows:
                    row_map = {
                        f'{r["id"]} | {r["shipment_no"]} | Pallet {r["pallet_no"]} | {r["product_code"]} | Qty {r["original_qty"]}': r
                        for r in old_rows
                    }
                    selected_old = row_map[st.selectbox("Select Old Row to Edit", list(row_map.keys()), key="super_edit_old_row")]
                    e1, e2, e3, e4 = st.columns(4)
                    with e1:
                        edit_pallet = st.text_input("Edit Pallet No", selected_old["pallet_no"])
                    with e2:
                        edit_box = st.text_input("Edit Box No Optional", selected_old["box_no"] or "")
                    with e3:
                        edit_qty = st.number_input("Edit Quantity", min_value=0.0, value=float(selected_old["original_qty"] or 0), step=1.0)
                    with e4:
                        edit_price = st.number_input("Edit Price", min_value=0.0, value=float(selected_old["unit_price"] or 0), step=1.0)
                    edit_currency = st.selectbox("Edit Currency", CURRENCIES, index=CURRENCIES.index(selected_old["currency"]) if selected_old["currency"] in CURRENCIES else 0, key="super_edit_currency")
                    edit_amount = edit_qty * edit_price
                    st.markdown(f'<div class="total-box">New Amount: {edit_amount:,.2f} {edit_currency}</div>', unsafe_allow_html=True)
                    if st.button("Update Old Row", type="primary"):
                        try:
                            execute_query("""
                                UPDATE shipment_boxes
                                SET pallet_no=?, box_no=?, original_qty=?, unit_price=?, currency=?, amount=?
                                WHERE id=?
                            """, (edit_pallet.strip(), edit_box.strip(), edit_qty, edit_price, edit_currency, edit_amount, selected_old["id"]))
                            st.success("Old row updated successfully.")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Cannot update. This pallet number is already used for same product.")
                else:
                    st.info("No old rows available for editing.")

if "Delivery to Customer" in all_items:
    with selected_tabs[all_items.index("Delivery to Customer")]:
        show_header("Delivery Entry", "Invoice-style FIFO delivery form with multi-pallet selection")
        st.markdown("""
        <div class="card" style="margin-bottom:14px;">
            <b>DELIVERY / COMMERCIAL INVOICE ENTRY</b><br>
            Select Original Invoice + Shipment, then choose one or more pallets. Pallets are shown FIFO by shipment date and pallet number.
        </div>
        """, unsafe_allow_html=True)


        customers = fetch_all("SELECT * FROM customers ORDER BY customer_name LIMIT 500")
        terms = fetch_all("SELECT * FROM payment_terms ORDER BY days LIMIT 200")

        invoice_shipments = fetch_all("""
            SELECT id, shipment_no, invoice_no, po_number, po_date, shipment_date
            FROM shipments
            ORDER BY shipment_date ASC, id ASC
        """)
        if not customers or not invoice_shipments:
            st.warning("Create Customer Master and Shipment Entry first.")
        else:
            customer_map = {x["customer_name"]: x["id"] for x in customers}
            term_map = {f'{x["term_name"]} - {x["days"]} days': x for x in terms}
            inv_map = {f'{s["invoice_no"]} | Shipment {s["shipment_no"]} | PO {s.get("po_number") or "-"} | Date {s["shipment_date"]}': s for s in invoice_shipments}

            ctop1, ctop2 = st.columns(2)
            with ctop1:
                st.markdown('<div class="input-section-title">Original Invoice Number with Shipment Number</div>', unsafe_allow_html=True)
                selected_invoice = st.selectbox("Original Invoice Number with Shipment Number", list(inv_map.keys()), key="delivery_original_invoice_ship", label_visibility="collapsed")
            selected_ship = inv_map[selected_invoice]
            po_info_cols = st.columns(2)
            with po_info_cols[0]:
                st.text_input("PO Number", value=selected_ship.get("po_number") or "", disabled=True, key="delivery_selected_po_number")
            with po_info_cols[1]:
                st.text_input("PO Date", value=format_date_ddmmyyyy(selected_ship.get("po_date")), disabled=True, key="delivery_selected_po_date")

            available_rows = fetch_all("""
                SELECT
                    b.*,
                    s.shipment_no,
                    s.invoice_no,
                    s.shipment_date,
                    COALESCE(s.po_number, p.po_number) AS po_number,
                    COALESCE(s.po_date, p.po_date) AS po_date,
                    p.product_code,
                    p.product_name,
                    COALESCE(del.delivered_qty, 0) AS delivered_qty,
                    b.original_qty - COALESCE(del.delivered_qty, 0) AS balance_qty
                FROM shipment_boxes b
                JOIN shipments s ON b.shipment_id = s.id
                JOIN products p ON b.product_id = p.id
                LEFT JOIN (
                    SELECT box_id, SUM(delivered_qty) AS delivered_qty
                    FROM customer_deliveries
                    GROUP BY box_id
                ) del ON b.id = del.box_id
                WHERE s.id = ?
                  AND b.original_qty - COALESCE(del.delivered_qty, 0) > 0
                ORDER BY s.shipment_date ASC, b.pallet_no ASC, b.id ASC
            """, (selected_ship["id"],))

            if not available_rows:
                st.warning("No pending pallet quantity available for this original invoice/shipment.")
            else:
                pallet_map = {
                    f'FIFO | Pallet {r["pallet_no"]} | Box {r["box_no"] or "-"} | {r["product_code"]} | Balance {r["balance_qty"]} | Price {r["unit_price"]} {r["currency"]}': r
                    for r in available_rows
                }
                selected_pallet_labels = st.multiselect("Select Pallet Numbers / Product Rows", list(pallet_map.keys()), key="delivery_multi_pallets")
                selected_pallets = [pallet_map[x] for x in selected_pallet_labels]

                c1, c2 = st.columns(2)
                with c1:
                    customer = st.selectbox("Customer", list(customer_map.keys()), key="delivery_customer_v10")
                    selected_customer_row = next((x for x in customers if x["customer_name"] == customer), None)
                    default_term_id = selected_customer_row.get("payment_term_id") if selected_customer_row else None
                    delivery_date = st.date_input("Delivery Date", value=date.today(), key="delivery_date_v10")
                    delivery_invoice_no = st.text_input("Delivery Invoice Number", key="delivery_invoice_v10")
                with c2:
                    term_keys = list(term_map.keys())
                    default_term_key = term_keys[0]
                    if default_term_id:
                        for k, v in term_map.items():
                            if v["id"] == default_term_id:
                                default_term_key = k
                                break
                    selected_term = st.selectbox("Payment Term", term_keys, index=term_keys.index(default_term_key), key="delivery_payment_term_v10")
                    term = term_map[selected_term]
                    payment_due_date = delivery_date + timedelta(days=int(term["days"]))
                    attachment = st.file_uploader("Attach Delivery File", key="delivery_attachment_v10")
                    st.info(f"Payment Due Date: {payment_due_date}")

                st.subheader("Enter Delivery Quantity for Selected Pallets")
                delivery_inputs = []
                total_qty = 0
                total_amount = 0
                for i, row in enumerate(selected_pallets):
                    dc1, dc2, dc3, dc4 = st.columns([2,1,1,1])
                    with dc1:
                        st.write(f'{row["pallet_no"]} | {row["product_code"]} | Balance {row["balance_qty"]}')
                    with dc2:
                        qty = st.number_input("Qty", min_value=0.0, max_value=float(row["balance_qty"]), value=0.0, step=1.0, key=f"delivery_qty_{row['id']}_{i}")
                    with dc3:
                        price = st.number_input("Price", min_value=0.0, value=float(row["unit_price"] or 0), step=1.0, key=f"delivery_price_{row['id']}_{i}")
                    with dc4:
                        amount = qty * price
                        st.write(f'{amount:,.2f} {row["currency"]}')
                    if qty > 0:
                        total_qty += qty
                        total_amount += amount
                        delivery_inputs.append((row, qty, price, amount))

                st.markdown(f'<div class="total-box">Total Delivery Qty: {total_qty} &nbsp;&nbsp; | &nbsp;&nbsp; Total Amount: {total_amount:,.2f}</div>', unsafe_allow_html=True)

                st.subheader("FIFO Available Pallets")
                fifo_display_rows = []
                for r in available_rows:
                    if float(r.get("balance_qty") or 0) > 0:
                        fifo_display_rows.append({
                            "shipment_no": r["shipment_no"],
                            "original_invoice_no": r["invoice_no"],
                            "po_number": r.get("po_number", ""),
                            "po_date": r.get("po_date", ""),
                            "shipment_date": r["shipment_date"],
                            "pallet_no": r["pallet_no"],
                            "box_no": r["box_no"] or "-",
                            "product_code": r["product_code"],
                            "product_name": r["product_name"],
                            "original_qty": r["original_qty"],
                            "delivered_qty": r["delivered_qty"],
                            "balance_qty": r["balance_qty"],
                            "unit_price": r["unit_price"],
                            "currency": r["currency"],
                        })
                show_fifo_df(fifo_display_rows, "delivery_fifo_available")

                if st.button("Save Delivery & Print", type="primary", key="save_delivery_fifo"):
                    if not delivery_invoice_no.strip():
                        st.error("Delivery Invoice Number is mandatory.")
                    elif not delivery_inputs:
                        st.error("Select pallets and enter delivery quantity.")
                    else:
                        path = save_upload(attachment, f"delivery_{delivery_invoice_no}")
                        first_print = None
                        for row, qty, price, amount in delivery_inputs:
                            execute_query("""
                                INSERT INTO customer_deliveries
                                (shipment_id, box_id, customer_id, delivery_date, delivered_qty, delivery_invoice_no,
                                 payment_term_id, payment_terms_days, payment_due_date, unit_price, currency, sale_amount, attachment_path, po_number, po_date)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (row["shipment_id"], row["id"], customer_map[customer], str(delivery_date),
                                  qty, delivery_invoice_no.strip(), term["id"], term["days"], str(payment_due_date),
                                  price, row["currency"], amount, path, row.get("po_number", ""), row.get("po_date", None)))
                            if first_print is None:
                                first_print = {
                                    "customer_name": customer,
                                    "shipment_no": row["shipment_no"],
                                    "original_invoice_no": row["invoice_no"],
                                    "delivery_invoice_no": delivery_invoice_no,
                                    "delivery_date": str(delivery_date),
                                    "payment_term": selected_term,
                                    "payment_due_date": str(payment_due_date),
                                    "product_code": row["product_code"],
                                    "product_name": row["product_name"],
                                    "po_number": row.get("po_number", ""),
                                    "po_date": row.get("po_date", ""),
                                    "pallet_no": row["pallet_no"],
                                    "box_no": row["box_no"] or "-",
                                    "qty": total_qty,
                                    "unit_price": price,
                                    "currency": row["currency"],
                                    "sale_amount": total_amount,
                                }
                        notify_event("delivery", "Delivery Created", f"Delivery Invoice: {delivery_invoice_no}\\nOriginal Invoice: {selected_ship['invoice_no']}\\nCustomer: {customer}\\nQty: {total_qty}\\nAmount: {total_amount}\\nDue Date: {payment_due_date}")
                        if first_print:
                            st.session_state.last_delivery_print = first_print
                        st.success("Delivery saved successfully. Email notification attempted if enabled. Print popup opened.")

        if "last_delivery_print" in st.session_state:
            html_doc = delivery_note_html(st.session_state.last_delivery_print)
            print_popup(html_doc)
            st.download_button("Download / Print Delivery Note HTML", html_doc, "delivery_note.html", mime="text/html", key="download_delivery_note_html")
            del st.session_state.last_delivery_print

        st.divider()
        st.subheader("Last Delivery Entries - Delivery Invoice Wise")

        delivery_invoice_rows = fetch_all("""
            SELECT d.delivery_invoice_no,
                   MIN(d.id) AS first_id,
                   MAX(d.delivery_date) AS delivery_date,
                   MAX(d.payment_due_date) AS payment_due_date,
                   c.customer_name,
                   s.invoice_no AS original_invoice_no,
                   s.shipment_no,
                   d.currency,
                   SUM(d.delivered_qty) AS total_qty,
                   SUM(d.sale_amount) AS total_amount,
                   COUNT(*) AS product_rows
            FROM customer_deliveries d
            JOIN customers c ON d.customer_id = c.id
            JOIN shipments s ON d.shipment_id = s.id
            GROUP BY d.delivery_invoice_no, c.customer_name, s.invoice_no, s.shipment_no, d.currency
            ORDER BY first_id DESC
            LIMIT 30
        """)

        if not delivery_invoice_rows:
            st.info("No delivery invoice entries available.")
        else:
            invoice_options = [
                f'{r["delivery_invoice_no"]} | Qty {r["total_qty"]:,.2f} | Amount {r["total_amount"]:,.2f} {r["currency"]} | Due {format_date_ddmmyyyy(r["payment_due_date"])}'
                for r in delivery_invoice_rows
            ]
            option_to_invoice = {opt: r["delivery_invoice_no"] for opt, r in zip(invoice_options, delivery_invoice_rows)}
            selected_delivery_invoice_label = st.selectbox(
                "Select Delivery Invoice No",
                invoice_options,
                key="selected_delivery_invoice_for_details"
            )
            selected_delivery_invoice_no = option_to_invoice[selected_delivery_invoice_label]

            summary_rows = []
            for r in delivery_invoice_rows:
                if r["delivery_invoice_no"] == selected_delivery_invoice_no:
                    summary_rows.append({
                        "Select": True,
                        "delivery_invoice_no": r["delivery_invoice_no"],
                        "customer_name": r["customer_name"],
                        "original_invoice_no": r["original_invoice_no"],
                        "shipment_no": r["shipment_no"],
                        "total_qty": r["total_qty"],
                        "total_amount": r["total_amount"],
                        "currency": r["currency"],
                        "payment_due_date": r["payment_due_date"],
                        "product_rows": r["product_rows"],
                    })
                    break

            st.dataframe(pd.DataFrame(format_date_columns(summary_rows)), use_container_width=True, hide_index=True)

            action_col1, action_col2, action_col3, action_col4 = st.columns(4)
            with action_col1:
                if st.button("Reprint Delivery Invoice", key="reprint_selected_delivery_invoice"):
                    data = build_delivery_invoice_print_data(selected_delivery_invoice_no)
                    if data:
                        html_doc = delivery_note_html(data)
                        st.session_state.last_delivery_reprint = html_doc
                        st.success("Reprint opened for selected delivery invoice.")
            with action_col2:
                if st.button("Send Email Delivery Invoice", key="email_selected_delivery_invoice"):
                    data = build_delivery_invoice_print_data(selected_delivery_invoice_no)
                    if data:
                        notify_event(
                            "delivery",
                            f"Delivery Invoice {selected_delivery_invoice_no}",
                            f"Delivery Invoice: {selected_delivery_invoice_no}\\nCustomer: {data.get('customer_name','')}\\nOriginal Invoice: {data.get('original_invoice_no','')}\\nTotal Qty: {data.get('qty',0)}\\nTotal Amount: {data.get('sale_amount',0)} {data.get('currency','')}\\nPayment Due Date: {data.get('payment_due_date','')}"
                        )
                        st.success("Email notification attempted for selected delivery invoice.")
            with action_col3:
                if st.button("Reopen Delivery Invoice for Modify", key=f"reopen_delivery_invoice_{selected_delivery_invoice_no}"):
                    st.session_state.edit_delivery_invoice_no = selected_delivery_invoice_no
                    reopen_record_message("Delivery Invoice", selected_delivery_invoice_no)
            with action_col4:
                if st.session_state.user["role"] == "super_admin":
                    delete_password = st.text_input("Password to Delete Delivery Invoice", type="password", key=f"delete_delivery_invoice_password_{selected_delivery_invoice_no}")
                    if st.button("Delete Delivery Invoice", key=f"delete_delivery_invoice_btn_{selected_delivery_invoice_no}"):
                        if check_delete_password(delete_password):
                            ids = fetch_all("SELECT id FROM customer_deliveries WHERE delivery_invoice_no=?", (selected_delivery_invoice_no,))
                            for row in ids:
                                try:
                                    execute_query("INSERT INTO delete_audit_log (table_name, record_id, deleted_by, details) VALUES (?, ?, ?, ?)",
                                                  ("customer_deliveries", row["id"], st.session_state.user.get("username", ""), f"Delivery Invoice {selected_delivery_invoice_no}"))
                                except Exception:
                                    pass
                                execute_query("DELETE FROM payments WHERE delivery_id=?", (row["id"],))
                            execute_query("DELETE FROM customer_deliveries WHERE delivery_invoice_no=?", (selected_delivery_invoice_no,))
                            cleanup_orphan_transactions()
                            st.success("Delivery invoice, linked payment references, and edit records deleted successfully.")
                            st.rerun()
                        else:
                            st.error("Wrong password. Delete cancelled.")
                else:
                    st.info("Delete allowed for Super Admin only.")

            if "last_delivery_reprint" in st.session_state:
                print_popup(st.session_state.last_delivery_reprint)
                st.download_button(
                    "Download Reprint Delivery Invoice HTML",
                    st.session_state.last_delivery_reprint,
                    "delivery_invoice_reprint.html",
                    mime="text/html",
                    key="download_reprint_delivery_invoice_html"
                )
                del st.session_state.last_delivery_reprint

            st.markdown("### Delivery Invoice Product Details")
            detail_rows = fetch_all("""
                SELECT d.id, d.delivery_invoice_no, d.delivery_date, s.invoice_no AS original_invoice_no,
                       s.shipment_no, p.product_code, p.product_name, b.pallet_no, b.box_no,
                       d.delivered_qty, d.unit_price, d.currency, d.sale_amount, d.payment_due_date
                FROM customer_deliveries d
                JOIN shipments s ON d.shipment_id = s.id
                JOIN shipment_boxes b ON d.box_id = b.id
                JOIN products p ON b.product_id = p.id
                WHERE d.delivery_invoice_no=?
                ORDER BY d.id
            """, (selected_delivery_invoice_no,))
            show_filtered_df(
                edit_button_column(detail_rows, "delivery"),
                f"delivery_invoice_detail_{selected_delivery_invoice_no}",
                total=True
            )

        if st.session_state.user["role"] == "super_admin":
            st.divider()
            st.subheader("Edit Delivery Entry")
            cleanup_orphan_transactions()
            old_deliveries = fetch_all("""
                SELECT d.*, c.customer_name, s.invoice_no AS original_invoice_no, s.shipment_no
                FROM customer_deliveries d
                JOIN customers c ON d.customer_id = c.id
                JOIN shipments s ON d.shipment_id = s.id
                JOIN shipment_boxes b ON d.box_id = b.id
                ORDER BY d.id DESC
            """)
            if old_deliveries:
                dmap = {f'{d["id"]} | {d["delivery_invoice_no"]} | {d["customer_name"]}': d for d in old_deliveries}
                ed = dmap[st.selectbox("Select Delivery to Edit", list(dmap.keys()), key="edit_delivery_select")]
                dc1, dc2 = st.columns(2)
                with dc1:
                    ed_inv = st.text_input("Edit Delivery Invoice No", ed["delivery_invoice_no"] or "", key="edit_delivery_inv")
                    ed_date = st.text_input("Edit Delivery Date YYYY-MM-DD", ed["delivery_date"] or "", key="edit_delivery_date")
                    ed_qty = st.number_input("Edit Delivered Qty", min_value=0.0, value=float(ed["delivered_qty"] or 0), step=1.0, key="edit_delivery_qty")
                with dc2:
                    ed_price = st.number_input("Edit Unit Price", min_value=0.0, value=float(ed["unit_price"] or 0), step=1.0, key="edit_delivery_price")
                    ed_currency = st.selectbox("Edit Currency", CURRENCIES, index=CURRENCIES.index(ed["currency"]) if ed["currency"] in CURRENCIES else 0, key="edit_delivery_currency")
                    ed_due = st.text_input("Edit Payment Due Date YYYY-MM-DD", ed["payment_due_date"] or "", key="edit_delivery_due")
                ed_amount = ed_qty * ed_price
                st.markdown(f'<div class="total-box">New Sale Amount: {ed_amount:,.2f} {ed_currency}</div>', unsafe_allow_html=True)
                if st.button("Update Delivery", type="primary", key="update_delivery"):
                    execute_query("""
                        UPDATE customer_deliveries
                        SET delivery_invoice_no=?, delivery_date=?, delivered_qty=?, unit_price=?, currency=?, sale_amount=?, payment_due_date=?
                        WHERE id=?
                    """, (ed_inv, ed_date, ed_qty, ed_price, ed_currency, ed_amount, ed_due, ed["id"]))
                    st.success("Delivery updated successfully.")
                    st.rerun()

if "Payment Entry" in all_items:
    with selected_tabs[all_items.index("Payment Entry")]:
        require_roles(("admin", "super_admin"))
        show_header("Payment Entry")

        deliveries = fetch_all("""
            SELECT
                MIN(d.id) AS id,
                d.delivery_invoice_no,
                s.invoice_no AS original_invoice_no,
                s.shipment_no,
                c.customer_name,
                d.currency,
                MAX(d.payment_due_date) AS payment_due_date,
                SUM(d.sale_amount) AS total_invoice_amount,
                COALESCE((
                    SELECT SUM(p.payment_amount)
                    FROM payments p
                    JOIN customer_deliveries d2 ON p.delivery_id = d2.id
                    WHERE d2.delivery_invoice_no = d.delivery_invoice_no
                ), 0) AS paid_amount,
                SUM(d.sale_amount) - COALESCE((
                    SELECT SUM(p.payment_amount)
                    FROM payments p
                    JOIN customer_deliveries d2 ON p.delivery_id = d2.id
                    WHERE d2.delivery_invoice_no = d.delivery_invoice_no
                ), 0) AS pending_amount
            FROM customer_deliveries d
            JOIN customers c ON d.customer_id = c.id
            JOIN shipments s ON d.shipment_id = s.id
            GROUP BY d.delivery_invoice_no, s.invoice_no, s.shipment_no, c.customer_name, d.currency
            HAVING
    SUM(d.sale_amount) - COALESCE((
        SELECT SUM(p.payment_amount)
        FROM payments p
        JOIN customer_deliveries d2 ON p.delivery_id = d2.id
        WHERE d2.delivery_invoice_no = d.delivery_invoice_no
    ), 0) > 0
            ORDER BY payment_due_date
        """)

        if not deliveries:
            st.warning("No pending delivery invoices available.")
        else:
            delivery_map = {
                f'Original Inv {d["original_invoice_no"]} | Delivery Inv {d["delivery_invoice_no"]} | {d["customer_name"]} | Pending {d["pending_amount"]} {d["currency"]}': d
                for d in deliveries
            }
            selected_delivery = delivery_map[
                st.selectbox("Select Pending Delivery Invoice", list(delivery_map.keys()), key="payment_delivery_select")
            ]

            st.markdown(f"""
            <div class="card" style="margin-bottom:16px;">
                <h3 style="margin:0;color:#003B73;">Payment Summary</h3>
                <table style="width:100%;font-family:Aptos,Arial,sans-serif;font-weight:700;margin-top:10px;">
                    <tr>
                        <td><b>Original Invoice</b></td><td>{selected_delivery["original_invoice_no"]}</td>
                        <td><b>Delivery Invoice</b></td><td>{selected_delivery["delivery_invoice_no"]}</td>
                    </tr>
                    <tr>
                        <td><b>Customer</b></td><td>{selected_delivery["customer_name"]}</td>
                        <td><b>Due Date</b></td><td>{selected_delivery["payment_due_date"]}</td>
                    </tr>
                    <tr>
                        <td><b>Invoice Amount</b></td><td>{selected_delivery["total_invoice_amount"]:,.2f} {selected_delivery["currency"]}</td>
                        <td><b style="color:#047857;">Received Amount</b></td><td style="color:#047857;font-weight:900;">{selected_delivery["paid_amount"]:,.2f}</td>
                    </tr>
                    <tr>
                        <td><b style="color:#b91c1c;">Pending Amount</b></td><td style="color:#b91c1c;font-weight:900;">{selected_delivery["pending_amount"]:,.2f}</td>
                        <td><b>Shipment No</b></td><td>{selected_delivery["shipment_no"]}</td>
                    </tr>
                </table>
            </div>
            """, unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                payment_received_date = st.date_input("Payment Received Date", value=date.today(), key="payment_received_date")
                payment_amount = st.number_input(
                    "Payment Amount",
                    min_value=0.0,
                    max_value=float(selected_delivery["pending_amount"]) if selected_delivery["pending_amount"] else None,
                    key="payment_amount"
                )
            with c2:
                payment_reference = st.text_input("Payment Reference", key="payment_reference")
                attachment = st.file_uploader("Attach Payment File", key="auto_file_uploader_3")
                remarks = st.text_area("Remarks", key="auto_textarea_2")

            if st.button("Save Payment", type="primary", key="save_payment"):
                path = save_upload(attachment, f"payment_{selected_delivery['delivery_invoice_no']}")
                execute_query("""
                    INSERT INTO payments (delivery_id, payment_received_date, payment_amount, payment_reference, attachment_path, remarks)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (selected_delivery["id"], str(payment_received_date), payment_amount, payment_reference, path, remarks))
                notify_event("payment", "Payment Received", f"Delivery Invoice: {selected_delivery['delivery_invoice_no']}\nCustomer: {selected_delivery['customer_name']}\nAmount Received: {payment_amount}\nReference: {payment_reference}")
                st.success("Payment saved successfully. Email notification attempted if enabled.")

        st.divider()
        st.subheader("Last Payment Entries")
        payment_action_rows = fetch_all("""
            SELECT p.id, p.payment_received_date, d.delivery_invoice_no, s.invoice_no AS original_invoice_no,
                   c.customer_name, p.payment_amount, p.payment_reference, p.remarks
            FROM payments p
            JOIN customer_deliveries d ON p.delivery_id = d.id
            JOIN shipments s ON d.shipment_id = s.id
            JOIN customers c ON d.customer_id = c.id
            ORDER BY p.id DESC
            LIMIT 50
        """)
        selected_payment_action, _ = transaction_selector(payment_action_rows, "payment_transaction_selector", "payment_reference")
        pay_action_col1, pay_action_col2 = st.columns(2)
        with pay_action_col1:
            if st.button("Reopen Selected Payment for Modify", key="reopen_selected_payment"):
                if selected_payment_action:
                    st.session_state.edit_payment_id = selected_payment_action["id"]
                    reopen_record_message("Payment", selected_payment_action["id"])
                else:
                    st.warning("Select a payment first.")
        with pay_action_col2:
            delete_password_pay = st.text_input("Password to Delete Selected Payment", type="password", key="delete_selected_payment_password")
            if st.button("Delete Selected Payment", key="delete_selected_payment"):
                if not selected_payment_action:
                    st.warning("Select a payment first.")
                elif delete_record_with_password("payments", selected_payment_action["id"], delete_password_pay, f"Payment {selected_payment_action.get('payment_reference','')}"):
                    st.rerun()

        if st.session_state.user["role"] == "super_admin":
            st.divider()
            st.subheader("Super Admin: Edit Old Payment Entries")
            cleanup_orphan_transactions()
            old_payments = fetch_all("""
                SELECT p.*, d.delivery_invoice_no, c.customer_name, s.invoice_no AS original_invoice_no
                FROM payments p
                JOIN customer_deliveries d ON p.delivery_id = d.id
                JOIN customers c ON d.customer_id = c.id
                JOIN shipments s ON d.shipment_id = s.id
                ORDER BY p.id DESC
            """)
            if old_payments:
                pmap = {f'{p["id"]} | {p["delivery_invoice_no"]} | Amount {p["payment_amount"]}': p for p in old_payments}
                ep = pmap[st.selectbox("Select Payment to Edit", list(pmap.keys()), key="edit_payment_select")]
                pc1, pc2 = st.columns(2)
                with pc1:
                    ep_date = st.text_input("Edit Payment Date YYYY-MM-DD", ep["payment_received_date"] or "", key="edit_payment_date")
                    ep_amount = st.number_input("Edit Payment Amount", min_value=0.0, value=float(ep["payment_amount"] or 0), step=1.0, key="edit_payment_amount")
                with pc2:
                    ep_ref = st.text_input("Edit Payment Reference", ep["payment_reference"] or "", key="edit_payment_ref")
                    ep_remarks = st.text_area("Edit Remarks", ep["remarks"] or "", key="edit_payment_remarks")
                if st.button("Update Payment", type="primary", key="update_payment"):
                    execute_query("""
                        UPDATE payments
                        SET payment_received_date=?, payment_amount=?, payment_reference=?, remarks=?
                        WHERE id=?
                    """, (ep_date, ep_amount, ep_ref, ep_remarks, ep["id"]))
                    st.success("Payment updated successfully.")
                    st.rerun()







def monday_of_date(value):
    if not value:
        return ""
    try:
        if isinstance(value, str):
            dt = datetime.strptime(value[:10], "%Y-%m-%d").date()
        else:
            dt = value
        return (dt - timedelta(days=dt.weekday())).isoformat()
    except Exception:
        return str(value)


def parse_db_date(value):
    """Return a Python date for YYYY-MM-DD/date/datetime values, otherwise None."""
    if value in (None, ""):
        return None
    try:
        if hasattr(value, "date") and not isinstance(value, date):
            return value.date()
        if hasattr(value, "strftime") and not isinstance(value, str):
            return value
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except Exception:
        return None

def normalize_coverage_plan_mondays(product_id):
    rows = fetch_all("""
        SELECT id, week_no, plan_date
        FROM coverage_plan_lines
        WHERE product_id=?
        ORDER BY date(plan_date), week_no, id
    """, (product_id,))
    if not rows:
        return
    first_date = rows[0].get("plan_date") or date.today().isoformat()
    first_monday = datetime.strptime(monday_of_date(first_date), "%Y-%m-%d").date()
    for i, row in enumerate(rows):
        monday_date = first_monday + timedelta(days=7*i)
        execute_query("""
            UPDATE coverage_plan_lines
            SET week_no=?, plan_date=?
            WHERE id=?
        """, (i + 1, monday_date.isoformat(), row["id"]))

if "Coverage Plan" in all_items:
    with selected_tabs[all_items.index("Coverage Plan")]:
        show_header("Coverage Plan", "Product-wise Customer Forecast, Shipment Delivery and Weekly Customer Delivery")

        products = fetch_all("""
            SELECT id, product_code, product_name, lcr_weekly, mcr_weekly, two_months_inventory
            FROM products
            ORDER BY product_code
        """)
        warehouses = fetch_all("""
            SELECT id, warehouse_name, shipment_time_days
            FROM warehouses
            ORDER BY warehouse_name
        """)

        if not products:
            st.warning("Please create Product Master first.")
        else:
            product_map = {f'{p["product_code"]} | {p["product_name"]}': p for p in products}
            filter_col1, filter_col2 = st.columns(2)
            with filter_col1:
                st.markdown("<b>Select Product Code</b>", unsafe_allow_html=True)
                selected_product_label = st.selectbox("Select Product Code", list(product_map.keys()), key="coverage_product_select", label_visibility="collapsed")
            selected_product = product_map[selected_product_label]

            shipment_time_days = 0
            with filter_col2:
                st.markdown("<b>Select Warehouse for Shipment Time</b>", unsafe_allow_html=True)
                if warehouses:
                    warehouse_map = {w["warehouse_name"]: w for w in warehouses}
                    selected_warehouse_name = st.selectbox("Select Warehouse for Shipment Time", list(warehouse_map.keys()), key="coverage_warehouse_select", label_visibility="collapsed")
                    shipment_time_days = int(warehouse_map[selected_warehouse_name].get("shipment_time_days") or 0)
                else:
                    st.info("Create Warehouse Master and enter Shipment Time Days.")
                    shipment_time_days = st.number_input("Shipment Time Days", min_value=0, value=0, step=1, key="coverage_shipment_days_manual")

            c0, c1, c2, c3 = st.columns(4)
            with c0:
                st.metric("Shipment Time Days", shipment_time_days)
            with c1:
                safety_stock_days = st.number_input("Safety Stock Days", min_value=0, value=60, step=1, key="coverage_safety_days")
            with c2:
                lcr_weekly = float(selected_product.get("lcr_weekly") or 0)
                st.metric("LCR Weekly", f"{lcr_weekly:,.0f}")
            with c3:
                mcr_weekly = float(selected_product.get("mcr_weekly") or 0)
                st.metric("MCR Weekly", f"{mcr_weekly:,.0f}")

            # Create product-specific coverage rows from template if missing
            existing_product_rows = fetch_all("""
                SELECT COUNT(*) AS c FROM coverage_plan_lines WHERE product_id=?
            """, (selected_product["id"],))[0]["c"]

            if existing_product_rows == 0:
                template_rows = fetch_all("""
                    SELECT week_no, plan_date, customer_forecast, stock_at_wh, two_months_inventory
                    FROM coverage_plan_lines
                    WHERE product_id IS NULL
                    ORDER BY week_no
                """)
                if not template_rows:
                    template_rows = fetch_all("""
                        SELECT week_no, plan_date, customer_forecast, stock_at_wh, two_months_inventory
                        FROM coverage_plan_lines
                        ORDER BY week_no
                        LIMIT 52
                    """)
                for r in template_rows:
                    execute_query("""
                        INSERT INTO coverage_plan_lines
                        (product_id, week_no, plan_date, customer_forecast, stock_at_wh, two_months_inventory)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (selected_product["id"], r["week_no"], r["plan_date"], r["customer_forecast"], r["stock_at_wh"], r["two_months_inventory"]))

            st.divider()
            st.subheader("Coverage Plan Table")

            current_week_start = datetime.strptime(monday_of_date(date.today()), "%Y-%m-%d").date()
            product_two_months_inventory = float(selected_product.get("two_months_inventory") or 0)

            # Keep existing data, but make sure current week and future weeks exist for this product.
            existing_future_count = fetch_all("""
                SELECT COUNT(*) AS c
                FROM coverage_plan_lines
                WHERE product_id=? AND date(plan_date) >= date(?)
            """, (selected_product["id"], current_week_start.isoformat()))[0]["c"] or 0
            if existing_future_count == 0:
                max_week_seed = int(fetch_all("""
                    SELECT IFNULL(MAX(week_no),0) AS max_week
                    FROM coverage_plan_lines
                    WHERE product_id=?
                """, (selected_product["id"],))[0]["max_week"] or 0)
                for i in range(52):
                    new_date = current_week_start + timedelta(days=7*i)
                    exists = fetch_all("""
                        SELECT id FROM coverage_plan_lines
                        WHERE product_id=? AND plan_date=?
                    """, (selected_product["id"], new_date.isoformat()))
                    if not exists:
                        execute_query("""
                            INSERT INTO coverage_plan_lines
                            (product_id, week_no, plan_date, customer_forecast, stock_at_wh,
                             shipment_delivery_qty, delivered_to_customer, wh_bank, two_months_inventory,
                             bank_status, suggested_shipment_qty, next_shipment_date, shipment_delivery_date)
                            VALUES (?, ?, ?, 0, 0, 0, 0, 0, ?, 0, 0, NULL, NULL)
                        """, (selected_product["id"], max_week_seed+i+1, new_date.isoformat(), product_two_months_inventory))

            # Always link two months inventory to Product Master without changing other existing data.
            execute_query("""
                UPDATE coverage_plan_lines
                SET two_months_inventory=?
                WHERE product_id=?
            """, (product_two_months_inventory, selected_product["id"]))

            st.subheader("Add Calendar Weeks")
            ac1, ac2, ac3 = st.columns(3)
            with ac1:
                add_start_date_input = st.date_input("Start Date for New Weeks", value=current_week_start, key="coverage_add_start_date")
                add_start_date = datetime.strptime(monday_of_date(add_start_date_input), "%Y-%m-%d").date()
                st.caption(f"Weeks will start from Monday: {add_start_date}")
            with ac2:
                add_weeks = st.number_input("Number of Weeks to Add", min_value=1, max_value=260, value=12, step=1, key="coverage_add_weeks")
            with ac3:
                if st.button("Add Weeks", type="primary", key="coverage_add_weeks_btn"):
                    max_week = int(fetch_all("""
                        SELECT IFNULL(MAX(week_no),0) AS max_week
                        FROM coverage_plan_lines
                        WHERE product_id=?
                    """, (selected_product["id"],))[0]["max_week"] or 0)
                    inserted = 0
                    for i in range(int(add_weeks)):
                        new_date = add_start_date + timedelta(days=7*i)
                        exists = fetch_all("""
                            SELECT id FROM coverage_plan_lines
                            WHERE product_id=? AND plan_date=?
                        """, (selected_product["id"], new_date.isoformat()))
                        if not exists:
                            execute_query("""
                                INSERT INTO coverage_plan_lines
                                (product_id, week_no, plan_date, customer_forecast, stock_at_wh,
                                 shipment_delivery_qty, delivered_to_customer, wh_bank, two_months_inventory,
                                 bank_status, suggested_shipment_qty, next_shipment_date, shipment_delivery_date)
                                VALUES (?, ?, ?, 0, 0, 0, 0, 0, ?, 0, 0, NULL, NULL)
                            """, (selected_product["id"], max_week+i+1, new_date.isoformat(), product_two_months_inventory))
                            inserted += 1
                    st.success(f"Weeks added successfully. New rows inserted: {inserted}")
                    st.rerun()

            raw_rows = fetch_all("""
                SELECT id, week_no, plan_date, customer_forecast, stock_at_wh, two_months_inventory
                FROM coverage_plan_lines
                WHERE product_id=? AND date(plan_date) >= date(?)
                ORDER BY date(plan_date), week_no, id
            """, (selected_product["id"], current_week_start.isoformat()))

            # Shipment delivery qty comes directly from Shipment Entry by product.
            # ETA week = shipment_date + selected warehouse shipment_time_days.
            shipment_rows = fetch_all("""
                SELECT s.shipment_date, b.original_qty
                FROM shipment_boxes b
                JOIN shipments s ON b.shipment_id = s.id
                WHERE b.product_id = ?
                  AND s.shipment_date IS NOT NULL
            """, (selected_product["id"],))

            shipment_delivery_events = []
            for sr in shipment_rows:
                ship_dt = parse_db_date(sr.get("shipment_date"))
                if ship_dt:
                    delivery_dt = ship_dt + timedelta(days=int(shipment_time_days))
                    shipment_delivery_events.append((delivery_dt, float(sr.get("original_qty") or 0)))

            display_rows = []
            next_shipment_date = ""
            next_shipment_qty = 0.0
            coverage_activity_started = False

            for idx, r in enumerate(raw_rows):
                plan_date = r.get("plan_date") or ""
                week_start = parse_db_date(plan_date)
                if week_start:
                    week_end = week_start + timedelta(days=6)
                else:
                    week_end = None

                delivered_to_customer = 0.0
                if week_start and week_end:
                    delivered_to_customer = float(fetch_all("""
                        SELECT IFNULL(SUM(d.delivered_qty),0) AS delivered_qty
                        FROM customer_deliveries d
                        JOIN shipment_boxes b ON d.box_id = b.id
                        WHERE b.product_id=?
                          AND d.delivery_date IS NOT NULL
                          AND date(d.delivery_date) >= date(?)
                          AND date(d.delivery_date) <= date(?)
                    """, (selected_product["id"], week_start.isoformat(), week_end.isoformat()))[0]["delivered_qty"] or 0)

                shipment_delivery_qty = 0.0
                shipment_delivery_date_value = None
                if week_start and week_end:
                    matched_dates = []
                    for delivery_dt, qty in shipment_delivery_events:
                        if week_start <= delivery_dt <= week_end:
                            shipment_delivery_qty += qty
                            matched_dates.append(delivery_dt)
                    if matched_dates:
                        shipment_delivery_date_value = sorted(matched_dates)[0].isoformat()

                customer_forecast = float(r.get("customer_forecast") or 0)
                stock_at_wh = float(r.get("stock_at_wh") or 0)

                if customer_forecast > 0 or delivered_to_customer > 0:
                    coverage_activity_started = True

                # Required formula:
                # wh_bank = stock_at_wh + shipment_delivery_qty - customer_forecast - delivered_to_customer
                wh_bank = stock_at_wh + shipment_delivery_qty - customer_forecast - delivered_to_customer
                two_months_inventory = product_two_months_inventory
                bank_status = wh_bank - two_months_inventory

                suggested_qty = 0.0
                suggested_date = None
                if coverage_activity_started:
                    suggested_qty = max(0.0, -bank_status)
                    if suggested_qty > 0 and week_start:
                        suggested_date = (week_start - timedelta(days=int(shipment_time_days))).isoformat()

                if suggested_qty > 0 and not next_shipment_date:
                    next_shipment_date = suggested_date or ""
                    next_shipment_qty = suggested_qty

                execute_query("""
                    UPDATE coverage_plan_lines
                    SET delivered_to_customer=?, wh_bank=?, bank_status=?,
                        suggested_shipment_qty=?, next_shipment_date=?,
                        shipment_delivery_date=?, shipment_delivery_qty=?, two_months_inventory=?
                    WHERE id=?
                """, (
                    delivered_to_customer, wh_bank, bank_status, suggested_qty, suggested_date,
                    shipment_delivery_date_value, shipment_delivery_qty, two_months_inventory, r["id"]
                ))

                display_rows.append({
                    "id": r["id"],
                    "week_no": r["week_no"],
                    "plan_date": plan_date,
                    "stock_at_wh": stock_at_wh,
                    "shipment_delivery_date": shipment_delivery_date_value or "",
                    "shipment_delivery_qty": round(shipment_delivery_qty, 2),
                    "customer_forecast": customer_forecast,
                    "delivered_to_customer": delivered_to_customer,
                    "wh_bank": round(wh_bank, 2),
                    "two_months_inventory": two_months_inventory,
                    "bank_status": round(bank_status, 2),
                    "suggested_shipment_qty": round(suggested_qty, 2),
                    "next_shipment_date": suggested_date or "",
                })

            k1, k2, k3, k4 = st.columns(4)
            k1.markdown(f'<div class="kpi-head yellow">NEXT SHIPMENT DATE</div><div class="kpi-value" style="background:#fde047;color:#b91c1c;font-weight:900;">{next_shipment_date or "-"}</div>', unsafe_allow_html=True)
            k2.markdown(f'<div class="kpi-head orange">NEXT SHIPMENT QTY</div><div class="kpi-value">{next_shipment_qty:,.0f}</div>', unsafe_allow_html=True)
            k3.markdown(f'<div class="kpi-head teal">PRODUCT</div><div class="kpi-value">{selected_product["product_code"]}</div>', unsafe_allow_html=True)
            k4.markdown(f'<div class="kpi-head green">SHIPMENT TIME</div><div class="kpi-value">{shipment_time_days} Days</div>', unsafe_allow_html=True)

            df = pd.DataFrame(format_date_columns(display_rows))
            search = st.text_input("Search / Filter Coverage Plan", key="coverage_plan_search")
            if search and not df.empty:
                mask = df.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
                df = df[mask]

            def style_coverage(row):
                styles = []
                for col in df.columns:
                    if col == "bank_status":
                        try:
                            styles.append("background-color:#fee2e2;color:#991b1b;font-weight:900;" if float(row[col]) < 0 else "background-color:#d1fae5;color:#065f46;font-weight:900;")
                        except Exception:
                            styles.append("")
                    elif col == "delivered_to_customer":
                        styles.append("background-color:#dbeafe;color:#1e3a8a;font-weight:900;")
                    elif col == "customer_forecast":
                        styles.append("background-color:#fef3c7;color:#92400e;font-weight:900;")
                    elif col == "suggested_shipment_qty":
                        styles.append("background-color:#ffedd5;color:#9a3412;font-weight:900;")
                    elif col == "next_shipment_date":
                        styles.append("background-color:#fde047;color:#b91c1c;font-weight:900;" if str(row[col]).strip() else "")
                    elif col == "stock_at_wh":
                        styles.append("background-color:#ecfeff;color:#155e75;font-weight:900;")
                    elif col == "shipment_delivery_qty":
                        styles.append("background-color:#dcfce7;color:#166534;font-weight:900;")
                    elif col == "shipment_delivery_date":
                        styles.append("background-color:#dcfce7;color:#166534;font-weight:900;" if str(row[col]).strip() else "")
                    else:
                        styles.append("")
                return styles

            if df.empty:
                st.info("No coverage plan data available.")
            else:
                st.dataframe(df.style.apply(style_coverage, axis=1), use_container_width=True, hide_index=True)
                export_buttons(df, "coverage_plan")
            st.divider()
            st.subheader("Customer Forecast & Stock at WH - Horizontal Grid")
            st.info("Columns show Week Number, Week Day, Year and Date. Edit Customer Forecast and Stock at WH directly in the grid and save.")

            edit_rows = fetch_all("""
                SELECT id, week_no, plan_date, customer_forecast, stock_at_wh
                FROM coverage_plan_lines
                WHERE product_id=? AND date(plan_date) >= date(?)
                ORDER BY date(plan_date), week_no
            """, (selected_product["id"], current_week_start.isoformat()))

            if edit_rows:
                header_labels = []
                forecast_values = {}
                stock_values = {}
                id_by_label = {}

                for r in edit_rows:
                    plan_date_text = r["plan_date"] or ""
                    try:
                        dt = datetime.strptime(plan_date_text, "%Y-%m-%d")
                        label = f'W{r["week_no"]} | {dt.strftime("%a")} | {dt.year} | {plan_date_text}'
                    except Exception:
                        label = f'W{r["week_no"]} | {plan_date_text}'
                    header_labels.append(label)
                    forecast_values[label] = float(r["customer_forecast"] or 0)
                    stock_values[label] = float(r["stock_at_wh"] or 0)
                    id_by_label[label] = r["id"]

                forecast_grid = pd.DataFrame([forecast_values, stock_values], index=["Customer Forecast", "Stock at WH"])
                edited_forecast_grid = st.data_editor(
                    forecast_grid,
                    use_container_width=True,
                    key="coverage_forecast_stock_horizontal_grid",
                    num_rows="fixed"
                )

                if st.button("Save Forecast / Stock Grid", type="primary", key="coverage_save_forecast_stock_grid"):
                    for label in header_labels:
                        new_forecast = float(edited_forecast_grid.loc["Customer Forecast", label] or 0)
                        new_stock = float(edited_forecast_grid.loc["Stock at WH", label] or 0)
                        execute_query(
                            "UPDATE coverage_plan_lines SET customer_forecast=?, stock_at_wh=? WHERE id=?",
                            (new_forecast, new_stock, id_by_label[label])
                        )
                    st.success("Customer Forecast and Stock at WH updated successfully.")
                    st.rerun()

            st.divider()
            st.subheader("Import Customer Forecast")
            forecast_template_df = pd.DataFrame({
                "product_code": [selected_product["product_code"]],
                "plan_date": [date.today().isoformat()],
                "customer_forecast": [0],
            })
            st.download_button(
                "Download Customer Forecast Template",
                to_excel_bytes(forecast_template_df),
                "customer_forecast_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_customer_forecast_template"
            )
            forecast_file = st.file_uploader("Import Customer Forecast Excel", type=["xlsx"], key="coverage_import_forecast_excel")
            if forecast_file is not None:
                try:
                    forecast_df = pd.read_excel(forecast_file)
                    forecast_df.columns = [str(c).strip().lower().replace(" ", "_") for c in forecast_df.columns]
                    required_cols = {"product_code", "plan_date", "customer_forecast"}
                    if not required_cols.issubset(set(forecast_df.columns)):
                        st.error("Excel must have columns: product_code, plan_date, customer_forecast")
                    else:
                        st.dataframe(forecast_df, use_container_width=True, hide_index=True)
                        if st.button("Update Customer Forecast from Excel", type="primary", key="coverage_import_forecast_btn"):
                            updated = 0
                            inserted = 0
                            for _, row in forecast_df.iterrows():
                                product_code = str(row.get("product_code") or "").strip()
                                try:
                                    plan_date_text = monday_of_date(pd.to_datetime(row.get("plan_date")).date())
                                except Exception:
                                    plan_date_text = str(row.get("plan_date"))
                                product_rows = fetch_all("SELECT id FROM products WHERE product_code=?", (product_code,))
                                if not product_rows:
                                    continue
                                pid = product_rows[0]["id"]
                                forecast = float(row.get("customer_forecast") or 0)
                                existing = fetch_all("SELECT id FROM coverage_plan_lines WHERE product_id=? AND plan_date=?", (pid, plan_date_text))
                                if existing:
                                    execute_query("UPDATE coverage_plan_lines SET customer_forecast=? WHERE id=?", (forecast, existing[0]["id"]))
                                    updated += 1
                                else:
                                    max_week = fetch_all("SELECT IFNULL(MAX(week_no),0) AS max_week FROM coverage_plan_lines WHERE product_id=?", (pid,))[0]["max_week"] or 0
                                    execute_query("""
                                        INSERT INTO coverage_plan_lines
                                        (product_id, week_no, plan_date, customer_forecast, stock_at_wh,
                                         shipment_delivery_qty, delivered_to_customer, wh_bank, two_months_inventory,
                                         bank_status, suggested_shipment_qty, next_shipment_date, shipment_delivery_date)
                                        VALUES (?, ?, ?, ?, 0, 0, 0, 0, ?, 0, 0, NULL, NULL)
                                    """, (pid, int(max_week)+1, plan_date_text, forecast, product_two_months_inventory))
                                    inserted += 1
                            st.success(f"Customer Forecast Import Complete. Updated: {updated}, Inserted: {inserted}")
                            st.rerun()
                except Exception as e:
                    st.error(f"Forecast import failed: {e}")

            st.divider()
            st.subheader("Import Stock at WH")
            st.warning("Stock at WH has been cleared by V27 migration. Import fresh stock using this module.")
            if st.button("Clear Stock at WH for Selected Product", key="clear_stock_selected_product"):
                execute_query("UPDATE coverage_plan_lines SET stock_at_wh=0 WHERE product_id=?", (selected_product["id"],))
                st.success("Stock at WH cleared for selected product.")
                st.rerun()
            stock_template_df = pd.DataFrame({
                "product_code": [selected_product["product_code"]],
                "plan_date": [date.today().isoformat()],
                "stock_at_wh": [0],
            })
            st.download_button(
                "Download Stock at WH Template",
                to_excel_bytes(stock_template_df),
                "stock_at_wh_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_stock_at_wh_template"
            )
            stock_file = st.file_uploader("Import Stock at WH Excel", type=["xlsx"], key="coverage_import_stock_excel")
            if stock_file is not None:
                try:
                    stock_df = pd.read_excel(stock_file)
                    stock_df.columns = [str(c).strip().lower().replace(" ", "_") for c in stock_df.columns]
                    required_cols = {"product_code", "plan_date", "stock_at_wh"}
                    if not required_cols.issubset(set(stock_df.columns)):
                        st.error("Excel must have columns: product_code, plan_date, stock_at_wh")
                    else:
                        st.dataframe(stock_df, use_container_width=True, hide_index=True)
                        if st.button("Update Stock at WH from Excel", type="primary", key="coverage_import_stock_btn"):
                            updated = 0
                            inserted = 0
                            for _, row in stock_df.iterrows():
                                product_code = str(row.get("product_code") or "").strip()
                                try:
                                    plan_date_text = monday_of_date(pd.to_datetime(row.get("plan_date")).date())
                                except Exception:
                                    plan_date_text = str(row.get("plan_date"))
                                product_rows = fetch_all("SELECT id FROM products WHERE product_code=?", (product_code,))
                                if not product_rows:
                                    continue
                                pid = product_rows[0]["id"]
                                stock = float(row.get("stock_at_wh") or 0)
                                existing = fetch_all("SELECT id FROM coverage_plan_lines WHERE product_id=? AND plan_date=?", (pid, plan_date_text))
                                if existing:
                                    execute_query("UPDATE coverage_plan_lines SET stock_at_wh=? WHERE id=?", (stock, existing[0]["id"]))
                                    updated += 1
                                else:
                                    max_week = fetch_all("SELECT IFNULL(MAX(week_no),0) AS max_week FROM coverage_plan_lines WHERE product_id=?", (pid,))[0]["max_week"] or 0
                                    execute_query("""
                                        INSERT INTO coverage_plan_lines
                                        (product_id, week_no, plan_date, customer_forecast, stock_at_wh,
                                         shipment_delivery_qty, delivered_to_customer, wh_bank, two_months_inventory,
                                         bank_status, suggested_shipment_qty, next_shipment_date, shipment_delivery_date)
                                        VALUES (?, ?, ?, 0, ?, 0, 0, 0, ?, 0, 0, NULL, NULL)
                                    """, (pid, int(max_week)+1, plan_date_text, stock, product_two_months_inventory))
                                    inserted += 1
                            st.success(f"Stock at WH Import Complete. Updated: {updated}, Inserted: {inserted}")
                            st.rerun()
                except Exception as e:
                    st.error(f"Stock import failed: {e}")



if "Admin" in all_items:
    with selected_tabs[all_items.index("Admin")]:
        require_roles(("admin", "super_admin"))
        show_header("Admin Control Panel", "Settings, User Management, Profile and Company Management")

        admin_tabs = st.tabs(["Profile", "User Management", "Company Management", "System Settings"])

        with admin_tabs[0]:
            st.subheader("Profile")
            current_user = st.session_state.user
            st.write(f"User: **{current_user['username']}**")
            st.write(f"Role: **{current_user['role']}**")
            old_password = st.text_input("Current Password", type="password", key="profile_old_password")
            new_password = st.text_input("New Password", type="password", key="profile_new_password")
            if st.button("Change My Password", key="profile_change_password"):
                if verify_user(current_user["username"], old_password):
                    execute_query("UPDATE users SET password_hash=? WHERE username=?", (hash_password(new_password), current_user["username"]))
                    st.success("Password changed successfully.")
                else:
                    st.error("Current password is incorrect.")

        with admin_tabs[1]:
            require_roles(("super_admin",))
            st.subheader("User Management")
            uc1, uc2, uc3, uc4 = st.columns(4)
            with uc1:
                new_username = st.text_input("New User Name", key="admin_new_username")
            with uc2:
                new_user_password = st.text_input("New User Password", type="password", key="admin_new_user_password")
            with uc3:
                new_user_role = st.selectbox("Role", ["user", "admin", "super_admin"], key="admin_new_user_role")
            with uc4:
                new_user_active = st.checkbox("Active", value=True, key="admin_new_user_active")
            if st.button("Create / Update User", key="admin_create_user"):
                if new_username and new_user_password:
                    existing = fetch_all("SELECT id FROM users WHERE username=?", (new_username,))
                    if existing:
                        execute_query("UPDATE users SET password_hash=?, role=?, is_active=? WHERE username=?",
                                      (hash_password(new_user_password), new_user_role, int(new_user_active), new_username))
                        st.success("User updated.")
                    else:
                        execute_query("INSERT INTO users (username, password_hash, role, is_active) VALUES (?, ?, ?, ?)",
                                      (new_username, hash_password(new_user_password), new_user_role, int(new_user_active)))
                        st.success("User created.")
                else:
                    st.error("User name and password are required.")
            show_filtered_df(fetch_all("SELECT id, username, role, is_active FROM users ORDER BY id"), "admin_users", total=False)

        with admin_tabs[2]:
            st.subheader("Company Management")
            company_rows = fetch_all("SELECT * FROM company_settings WHERE id=1")
            company = company_rows[0] if company_rows else {}
            cc1, cc2 = st.columns(2)
            with cc1:
                company_name = st.text_input("Company Name", company.get("company_name", "FOUR STAR INDUSTRIES PVT. LTD."), key="company_name")
                company_phone = st.text_input("Company Phone", company.get("phone", "") or "", key="company_phone")
                company_email = st.text_input("Company Email", company.get("email", "") or "", key="company_email")
                company_website = st.text_input("Website", company.get("website", "") or "", key="company_website")
            with cc2:
                company_address = st.text_area("Company Address", company.get("address", "") or "", key="company_address")
                company_tax = st.text_input("Tax ID", company.get("tax_id", "") or "", key="company_tax")
                company_logo = st.text_input("Logo Path", company.get("logo_path", "FSI_LOGO_new.png") or "FSI_LOGO_new.png", key="company_logo")
            if st.button("Save Company Settings", key="save_company_settings"):
                execute_query("""
  INSERT INTO company_settings
(id, company_name, address, phone, email, website, tax_id, logo_path)
VALUES (1, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (id)
DO UPDATE SET
    company_name = EXCLUDED.company_name,
    address = EXCLUDED.address,
    phone = EXCLUDED.phone,
    email = EXCLUDED.email,
    website = EXCLUDED.website,
    tax_id = EXCLUDED.tax_id,
    logo_path = EXCLUDED.logo_path
                """, (company_name, company_address, company_phone, company_email, company_website, company_tax, company_logo))
                st.success("Company settings saved.")

        with admin_tabs[3]:
            st.subheader("System Settings")
            st.info("Use this page for user, profile, and company settings. Email/WhatsApp notification settings remain under the Overdue Notification module.")
            st.write("Database: shipment_app.db")
            st.write("Uploads Folder: uploads/")
            if st.button("Run Database Unlock / Optimize", key="admin_optimize_db"):
                conn = get_connection()
                try:
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                    conn.execute("PRAGMA optimize")
                    conn.commit()
                    st.success("Database optimized.")
                finally:
                    conn.close()


if "Reports" in all_items:
    with selected_tabs[all_items.index("Reports")]:
        show_header("Reports with Export")
        report = st.selectbox("Select Report", [
            "Pallet Wise Balance Quantity",
            "Original Invoice Wise Balance Quantity",
            "Payment Due Summary Invoice Wise",
            "Delivery Invoice Wise Summary Report",
            "Monthly Sales Report - Product and Customer",
            "Monthly Payment Receipt Report"
        ])

        if report == "Pallet Wise Balance Quantity":
            rows = fetch_all("""
                SELECT s.shipment_no, s.invoice_no, b.pallet_no, b.box_no, p.product_code, p.product_name,
                       b.original_qty, b.unit_price, b.currency, b.amount,
                       IFNULL(SUM(d.delivered_qty),0) delivered_qty,
                       b.original_qty - IFNULL(SUM(d.delivered_qty),0) balance_qty
                FROM shipment_boxes b
                JOIN shipments s ON b.shipment_id = s.id
                JOIN products p ON b.product_id = p.id
                LEFT JOIN customer_deliveries d ON b.id = d.box_id
               GROUP BY
    b.id,
    s.shipment_no,
    s.invoice_no,
    b.pallet_no,
    b.box_no,
    p.product_code,
    p.product_name,
    b.original_qty,
    b.unit_price,
    b.currency,
    b.amount
                ORDER BY s.shipment_no, b.pallet_no, b.box_no
            """)
        elif report == "Original Invoice Wise Balance Quantity":
            rows = fetch_all("""
                SELECT s.invoice_no, s.shipment_no, p.product_code, p.product_name,
                       SUM(b.original_qty) original_qty, SUM(b.amount) amount,
                       IFNULL(SUM(d.delivered_qty),0) delivered_qty,
                       SUM(b.original_qty) - IFNULL(SUM(d.delivered_qty),0) balance_qty
                FROM shipment_boxes b
                JOIN shipments s ON b.shipment_id = s.id
                JOIN products p ON b.product_id = p.id
                LEFT JOIN customer_deliveries d ON b.id = d.box_id
                GROUP BY s.invoice_no, s.shipment_no, p.product_code, p.product_name
                ORDER BY s.invoice_no
            """)
        elif report == "Payment Due Summary Invoice Wise":
            rows = fetch_all("""
                SELECT d.delivery_invoice_no, c.customer_name, d.delivery_date, d.payment_due_date,
                       pt.term_name, SUM(d.delivered_qty) delivered_qty, d.currency, SUM(d.sale_amount) sale_amount,
                       IFNULL(SUM(p.payment_amount),0) paid_amount,
                       SUM(d.sale_amount) - IFNULL(SUM(p.payment_amount),0) pending_amount,
                       CASE WHEN SUM(d.sale_amount) - IFNULL(SUM(p.payment_amount),0) <= 0 THEN 'Paid'
                            WHEN date(MAX(d.payment_due_date)) < date('now') THEN 'Overdue'
                            ELSE 'Pending' END payment_status
                FROM customer_deliveries d
                JOIN customers c ON d.customer_id = c.id
                LEFT JOIN payment_terms pt ON d.payment_term_id = pt.id
                LEFT JOIN payments p ON d.id = p.delivery_id
                GROUP BY d.delivery_invoice_no, c.customer_name, d.currency
                ORDER BY d.payment_due_date
            """)
        elif report == "Delivery Invoice Wise Summary Report":
            rows = fetch_all("""
                SELECT d.delivery_invoice_no, c.customer_name, s.invoice_no AS original_invoice_no,
                       s.shipment_no, MIN(d.delivery_date) delivery_date, MAX(d.payment_due_date) payment_due_date,
                       d.currency, SUM(d.delivered_qty) total_qty, SUM(d.sale_amount) total_amount,
                       COUNT(d.id) product_rows
                FROM customer_deliveries d
                JOIN customers c ON d.customer_id = c.id
                JOIN shipments s ON d.shipment_id = s.id
                GROUP BY d.delivery_invoice_no, c.customer_name, s.invoice_no, s.shipment_no, d.currency
                ORDER BY MIN(d.id) DESC
            """)
        elif report == "Monthly Sales Report - Product and Customer":
            rows = fetch_all("""
                SELECT strftime('%Y-%m', d.delivery_date) sales_month,
                       c.customer_name, p.product_code, p.product_name, d.currency,
                       SUM(d.delivered_qty) total_qty,
                       SUM(d.sale_amount) total_sales
                FROM customer_deliveries d
                JOIN customers c ON d.customer_id = c.id
                JOIN shipment_boxes b ON d.box_id = b.id
                JOIN products p ON b.product_id = p.id
                GROUP BY sales_month, c.customer_name, p.product_code, p.product_name, d.currency
                ORDER BY sales_month DESC, c.customer_name, p.product_code
            """)
        else:
            rows = fetch_all("""
                SELECT strftime('%Y-%m', p.payment_received_date) receipt_month,
                       c.customer_name, d.delivery_invoice_no, s.invoice_no AS original_invoice_no,
                       p.payment_reference, p.payment_received_date, p.payment_amount, p.remarks
                FROM payments p
                JOIN customer_deliveries d ON p.delivery_id = d.id
                JOIN shipments s ON d.shipment_id = s.id
                JOIN customers c ON d.customer_id = c.id
                ORDER BY p.payment_received_date DESC, p.id DESC
            """)
        df = show_filtered_df(rows, f"reports_filter_{report}", total=True)
        export_buttons(df, report.replace(" ", "_").replace("-", "").lower())

if "Overdue Notification" in all_items:
    with selected_tabs[all_items.index("Overdue Notification")]:
        require_roles(("admin", "super_admin"))
        show_header("Email Notification Settings")
        st.info("Use Gmail App Password, not your normal Gmail password. Google Account → Security → 2-Step Verification → App Passwords.")
        settings = get_notification_settings()
        ns1, ns2 = st.columns(2)
        with ns1:
            sender_email = st.text_input("Sender Email", settings.get("sender_email") or "", key="notif_sender_email")
            app_password = st.text_input("Gmail App Password", settings.get("app_password") or "", type="password", key="notif_app_password")
        with ns2:
            smtp_server = st.text_input("SMTP Server", settings.get("smtp_server") or "smtp.gmail.com", key="notif_smtp_server")
            smtp_port = st.number_input("SMTP Port", value=int(settings.get("smtp_port") or 587), step=1, key="notif_smtp_port")
            enable_email = st.checkbox("Enable Email Notifications", value=bool(settings.get("enable_email")), key="notif_enable_email")
        if st.button("Save Email Settings", key="save_email_settings"):
            execute_query("""
                UPDATE notification_settings
                SET sender_email=?, app_password=?, smtp_server=?, smtp_port=?, enable_email=?
                WHERE id=1
            """, (sender_email, app_password, smtp_server, int(smtp_port), int(enable_email)))
            st.success("Email settings saved.")

        st.subheader("Notification Recipients")
        rec_event = st.selectbox("Event Type", ["shipment", "delivery", "payment"], key="recipient_event")
        rec_email = st.text_input("Recipient Email", key="recipient_email")
        if st.button("Add Recipient", key="add_recipient"):
            if rec_email.strip():
                execute_query("INSERT INTO notification_recipients (event_type, recipient_email, is_active) VALUES (?, ?, 1)", (rec_event, rec_email.strip()))
                st.success("Recipient added.")
        show_filtered_df(fetch_all("SELECT * FROM notification_recipients ORDER BY event_type, id DESC LIMIT 300"), "notification_recipients", total=False)

        st.divider()
        show_header("Overdue Payment Notification")
        rows = overdue_rows()
        df = show_filtered_df(rows, "reports_filter", total=True)
        export_buttons(df, "overdue_payment_list")
        st.warning("For WhatsApp, click the button to open WhatsApp message. Full auto-send needs WhatsApp Business API.")
        for r in rows:
            message = f"Dear {r['customer_name']}, payment is overdue for invoice {r['delivery_invoice_no']}. Due date: {r['payment_due_date']}. Pending amount: {r['pending_amount']}."
            with st.expander(f"{r['delivery_invoice_no']} - {r['customer_name']} - Pending {r['pending_amount']}"):
                if r.get("whatsapp_no"):
                    st.link_button("Open WhatsApp", whatsapp_link(r["whatsapp_no"], message))

st.markdown('<div class="footer">COPYRIGHT BY FOUR STAR INDUSTRIES PVT. LTD.</div>', unsafe_allow_html=True)
