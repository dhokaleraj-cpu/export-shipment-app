from common import *

page_setup()

require_page_view('reports')
show_edit_permission_status('reports')

show_header('Reports with Export')


def _reports_total_footer_df_fallback(rows_or_df):
    """Local fallback if common.py total footer helper is unavailable on deployment."""
    df = pd.DataFrame(rows_or_df)
    if df.empty:
        return df
    first_col = df.columns[0]
    df = df[df[first_col].astype(str).str.upper() != "TOTAL"].copy()
    total_row = {col: "" for col in df.columns}
    numeric_cols = []
    for col in df.columns:
        low = str(col).lower()
        if any(k in low for k in ["qty", "quantity", "amount", "sale", "sales", "balance", "pending", "paid", "received", "stock", "delivered", "invoice_amount", "total"]):
            vals = pd.to_numeric(df[col], errors="coerce")
            if vals.notna().any():
                total_row[col] = vals.sum()
                numeric_cols.append(col)
    if numeric_cols:
        total_row[first_col] = "TOTAL"
        df = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)
    return df

if "report_total_footer_df" not in globals():
    report_total_footer_df = _reports_total_footer_df_fallback


def _highlight_overdue_payment_due_date(row):
    styles = ['' for _ in row]
    try:
        due = pd.to_datetime(row.get("payment_due_date"), errors="coerce")
        if pd.notna(due) and due.date() < date.today():
            styles = ['background-color: #fee2e2; color: #b91c1c; font-weight: 900;' if col == "payment_due_date" else '' for col in row.index]
    except Exception:
        pass
    return styles

report_options = [
    'Delivery to Customer Product Wise Sale Report',
    'Product Wise and Delivery Invoice Wise Report for Original Invoice Number',
    'Product Wise Stock Report',
    'Product Wise Sale Report',
    'Original Invoice Wise Sale Report',
    'Warehouse Wise Sale Report',
    'Balance Quantity Report Product Wise',
    'Original Invoice Number Wise Payment Due',
    'Original Invoice Number Wise Balance Quantity Product Wise',
    'Pallet Wise Balance Quantity',
    'Original Invoice Wise Balance Quantity',
    'Original Invoice wise payment Balance',
    'Delivery Invoice Wise Summary Report',
    'Monthly Sales Report - Product and Customer',
    'Monthly Payment Receipt Report',
]

report = searchable_selectbox('Select Report', report_options, key='reports_select_report')

st.markdown('<div class="sap-grid-card"><div class="sap-grid-card-title">Report Filters</div>', unsafe_allow_html=True)
f1, f2, f3 = st.columns(3)
with f1:
    product_filter = st.text_input('Search Product Code / Name', key='reports_product_filter')
with f2:
    invoice_filter = st.text_input('Search Original Invoice Number', key='reports_invoice_filter')
with f3:
    customer_filter = st.text_input('Search Customer / Warehouse', key='reports_customer_filter')
st.markdown('</div>', unsafe_allow_html=True)

rows = []


if report == 'Delivery to Customer Product Wise Sale Report':
    rows = fetch_all("""
        SELECT
            d.delivery_invoice_no,
            d.delivery_date,
            s.invoice_no AS original_invoice_no,
            s.shipment_no,
            c.customer_name,
            p.product_code,
            p.product_name,
            d.currency,
            SUM(d.delivered_qty) AS delivered_qty,
            AVG(d.unit_price) AS average_price,
            SUM(d.sale_amount) AS sale_amount
        FROM customer_deliveries d
        JOIN shipments s ON d.shipment_id = s.id
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products p ON b.product_id = p.id
        JOIN customers c ON d.customer_id = c.id
        WHERE (? = '' OR LOWER(p.product_code || ' ' || p.product_name) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(s.invoice_no || ' ' || d.delivery_invoice_no) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(c.customer_name) LIKE LOWER(CONCAT('%', ?, '%')))
        GROUP BY d.delivery_invoice_no, d.delivery_date, s.invoice_no, s.shipment_no,
                 c.customer_name, p.product_code, p.product_name, d.currency
        ORDER BY d.delivery_date DESC, d.delivery_invoice_no, p.product_code
    """, (product_filter, product_filter, invoice_filter, invoice_filter, customer_filter, customer_filter))

elif report == 'Product Wise and Delivery Invoice Wise Report for Original Invoice Number':
    rows = fetch_all("""
        SELECT s.invoice_no AS original_invoice_no,
               d.delivery_invoice_no,
               p.product_code,
               p.product_name,
               c.customer_name,
               d.currency,
               SUM(d.delivered_qty) AS delivered_qty,
               SUM(d.sale_amount) AS sale_amount,
               MIN(d.delivery_date) AS first_delivery_date,
               MAX(d.delivery_date) AS last_delivery_date
        FROM customer_deliveries d
        JOIN shipments s ON d.shipment_id = s.id
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products p ON b.product_id = p.id
        JOIN customers c ON d.customer_id = c.id
        WHERE (? = '' OR LOWER(p.product_code || ' ' || p.product_name) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(s.invoice_no) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(c.customer_name) LIKE LOWER(CONCAT('%', ?, '%')))
        GROUP BY s.invoice_no, d.delivery_invoice_no, p.product_code, p.product_name, c.customer_name, d.currency
        ORDER BY s.invoice_no, d.delivery_invoice_no, p.product_code
    """, (product_filter, product_filter, invoice_filter, invoice_filter, customer_filter, customer_filter))

elif report == 'Product Wise Stock Report':
    rows = fetch_all("""
        SELECT p.product_code,
               p.product_name,
               COALESCE(SUM(b.original_qty),0) AS shipment_qty,
               COALESCE(SUM(d.delivered_qty),0) AS delivered_qty,
               COALESCE(SUM(b.original_qty),0) - COALESCE(SUM(d.delivered_qty),0) AS stock_balance_qty,
               b.currency,
               COALESCE(SUM((b.original_qty - COALESCE(d.delivered_qty,0)) * COALESCE(b.unit_price,0)),0) AS stock_balance_amount
        FROM shipment_boxes b
        JOIN products p ON b.product_id = p.id
        LEFT JOIN (
            SELECT box_id, SUM(delivered_qty) AS delivered_qty
            FROM customer_deliveries
            GROUP BY box_id
        ) d ON b.id = d.box_id
        WHERE (? = '' OR LOWER(p.product_code || ' ' || p.product_name) LIKE LOWER(CONCAT('%', ?, '%')))
        GROUP BY p.product_code, p.product_name, b.currency
        ORDER BY p.product_code
    """, (product_filter, product_filter))

elif report == 'Product Wise Sale Report':
    rows = fetch_all("""
        SELECT p.product_code,
               p.product_name,
               c.customer_name,
               d.currency,
               SUM(d.delivered_qty) AS sold_qty,
               SUM(d.sale_amount) AS sale_amount
        FROM customer_deliveries d
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products p ON b.product_id = p.id
        JOIN customers c ON d.customer_id = c.id
        WHERE (? = '' OR LOWER(p.product_code || ' ' || p.product_name) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(c.customer_name) LIKE LOWER(CONCAT('%', ?, '%')))
        GROUP BY p.product_code, p.product_name, c.customer_name, d.currency
        ORDER BY p.product_code, c.customer_name
    """, (product_filter, product_filter, customer_filter, customer_filter))

elif report == 'Original Invoice Wise Sale Report':
    rows = fetch_all("""
        SELECT s.invoice_no AS original_invoice_no,
               s.shipment_no,
               c.customer_name,
               d.currency,
               SUM(d.delivered_qty) AS sold_qty,
               SUM(d.sale_amount) AS sale_amount,
               COUNT(DISTINCT d.delivery_invoice_no) AS delivery_invoice_count
        FROM customer_deliveries d
        JOIN shipments s ON d.shipment_id = s.id
        JOIN customers c ON d.customer_id = c.id
        WHERE (? = '' OR LOWER(s.invoice_no) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(c.customer_name) LIKE LOWER(CONCAT('%', ?, '%')))
        GROUP BY s.invoice_no, s.shipment_no, c.customer_name, d.currency
        ORDER BY s.invoice_no
    """, (invoice_filter, invoice_filter, customer_filter, customer_filter))

elif report == 'Warehouse Wise Sale Report':
    rows = fetch_all("""
        SELECT w.warehouse_name,
               c.customer_name,
               d.currency,
               SUM(d.delivered_qty) AS sold_qty,
               SUM(d.sale_amount) AS sale_amount
        FROM customer_deliveries d
        JOIN shipments s ON d.shipment_id = s.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        JOIN customers c ON d.customer_id = c.id
        WHERE (? = '' OR LOWER(COALESCE(w.warehouse_name,'') || ' ' || c.customer_name) LIKE LOWER(CONCAT('%', ?, '%')))
        GROUP BY w.warehouse_name, c.customer_name, d.currency
        ORDER BY w.warehouse_name, c.customer_name
    """, (customer_filter, customer_filter))

elif report == 'Balance Quantity Report Product Wise':
    rows = fetch_all("""
        SELECT p.product_code,
               p.product_name,
               b.currency,
               COALESCE(SUM(b.original_qty),0) AS original_qty,
               COALESCE(SUM(d.delivered_qty),0) AS delivered_qty,
               COALESCE(SUM(b.original_qty),0) - COALESCE(SUM(d.delivered_qty),0) AS balance_qty
        FROM shipment_boxes b
        JOIN products p ON b.product_id = p.id
        LEFT JOIN (
            SELECT box_id, SUM(delivered_qty) AS delivered_qty
            FROM customer_deliveries
            GROUP BY box_id
        ) d ON b.id = d.box_id
        WHERE (? = '' OR LOWER(p.product_code || ' ' || p.product_name) LIKE LOWER(CONCAT('%', ?, '%')))
        GROUP BY p.product_code, p.product_name, b.currency
        ORDER BY p.product_code
    """, (product_filter, product_filter))

elif report == 'Original Invoice Number Wise Payment Due':
    rows = fetch_all("""
        SELECT s.invoice_no AS original_invoice_no,
               s.shipment_no,
               c.customer_name,
               d.currency,
               MIN(d.delivery_date) AS first_delivery_date,
               MAX(d.payment_due_date) AS payment_due_date,
               SUM(d.sale_amount) AS sale_amount,
               COALESCE(SUM(pay.payment_amount),0) AS paid_amount,
               SUM(d.sale_amount) - COALESCE(SUM(pay.payment_amount),0) AS pending_amount,
               CASE
                   WHEN SUM(d.sale_amount) - COALESCE(SUM(pay.payment_amount),0) <= 0 THEN 'Paid'
                   WHEN MAX(d.payment_due_date)::date < CURRENT_DATE THEN 'Overdue'
                   ELSE 'Pending'
               END AS payment_status
        FROM customer_deliveries d
        JOIN shipments s ON d.shipment_id = s.id
        JOIN customers c ON d.customer_id = c.id
        LEFT JOIN (
            SELECT delivery_id, SUM(payment_amount) AS payment_amount
            FROM payments
            GROUP BY delivery_id
        ) pay ON d.id = pay.delivery_id
        WHERE (? = '' OR LOWER(s.invoice_no) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(c.customer_name) LIKE LOWER(CONCAT('%', ?, '%')))
        GROUP BY s.invoice_no, s.shipment_no, c.customer_name, d.currency
        ORDER BY payment_due_date
    """, (invoice_filter, invoice_filter, customer_filter, customer_filter))

elif report == 'Original Invoice Number Wise Balance Quantity Product Wise':
    rows = fetch_all("""
        SELECT s.invoice_no AS original_invoice_no,
               s.shipment_no,
               p.product_code,
               p.product_name,
               b.currency,
               COALESCE(SUM(b.original_qty),0) AS original_qty,
               COALESCE(SUM(d.delivered_qty),0) AS delivered_qty,
               COALESCE(SUM(b.original_qty),0) - COALESCE(SUM(d.delivered_qty),0) AS balance_qty
        FROM shipment_boxes b
        JOIN shipments s ON b.shipment_id = s.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN (
            SELECT box_id, SUM(delivered_qty) AS delivered_qty
            FROM customer_deliveries
            GROUP BY box_id
        ) d ON b.id = d.box_id
        WHERE (? = '' OR LOWER(p.product_code || ' ' || p.product_name) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(s.invoice_no) LIKE LOWER(CONCAT('%', ?, '%')))
        GROUP BY s.invoice_no, s.shipment_no, p.product_code, p.product_name, b.currency
        ORDER BY s.invoice_no, p.product_code
    """, (product_filter, product_filter, invoice_filter, invoice_filter))

elif report == 'Pallet Wise Balance Quantity':
    rows = fetch_all("""
        SELECT s.shipment_no, s.invoice_no, b.fifo_row_id, b.pallet_no, b.box_no, p.product_code, p.product_name,
               b.original_qty, b.unit_price, b.currency, b.amount,
               COALESCE(d.delivered_qty,0) AS delivered_qty,
               b.original_qty - COALESCE(d.delivered_qty,0) AS balance_qty
        FROM shipment_boxes b
        JOIN shipments s ON b.shipment_id = s.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN (
            SELECT box_id, SUM(delivered_qty) AS delivered_qty
            FROM customer_deliveries
            GROUP BY box_id
        ) d ON b.id = d.box_id
        GROUP BY b.id, s.shipment_no, s.invoice_no, b.fifo_row_id, b.pallet_no, b.box_no, p.product_code,
                 p.product_name, b.original_qty, b.unit_price, b.currency, b.amount, d.delivered_qty
        ORDER BY COALESCE(b.fifo_row_id,b.id), s.shipment_no, b.pallet_no
    """)

elif report == 'Original Invoice Wise Balance Quantity':
    rows = fetch_all("""
        SELECT s.invoice_no, s.shipment_no, p.product_code, p.product_name,
               SUM(b.original_qty) AS original_qty, SUM(b.amount) AS amount,
               COALESCE(SUM(d.delivered_qty),0) AS delivered_qty,
               SUM(b.original_qty) - COALESCE(SUM(d.delivered_qty),0) AS balance_qty
        FROM shipment_boxes b
        JOIN shipments s ON b.shipment_id = s.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN (
            SELECT box_id, SUM(delivered_qty) AS delivered_qty
            FROM customer_deliveries
            GROUP BY box_id
        ) d ON b.id = d.box_id
        GROUP BY s.invoice_no, s.shipment_no, p.product_code, p.product_name
        ORDER BY s.invoice_no
    """)

elif report == 'Original Invoice wise payment Balance':
    rows = fetch_all("""
        SELECT s.invoice_no AS original_invoice_no,
               d.delivery_invoice_no,
               c.customer_name,
               MIN(d.delivery_date) AS delivery_date,
               MAX(d.payment_due_date) AS payment_due_date,
               pt.term_name,
               SUM(d.delivered_qty) AS delivered_qty,
               d.currency,
               SUM(d.sale_amount) AS sale_amount,
               COALESCE(SUM(pay.payment_amount),0) AS paid_amount,
               SUM(d.sale_amount) - COALESCE(SUM(pay.payment_amount),0) AS pending_amount,
               CASE WHEN SUM(d.sale_amount) - COALESCE(SUM(pay.payment_amount),0) <= 0 THEN 'Paid'
                    WHEN MAX(d.payment_due_date)::date < CURRENT_DATE THEN 'Overdue'
                    ELSE 'Pending' END AS payment_status
        FROM customer_deliveries d
        JOIN shipments s ON d.shipment_id = s.id
        JOIN customers c ON d.customer_id = c.id
        LEFT JOIN payment_terms pt ON d.payment_term_id = pt.id
        LEFT JOIN (
            SELECT delivery_id, SUM(payment_amount) AS payment_amount
            FROM payments
            GROUP BY delivery_id
        ) pay ON d.id = pay.delivery_id
        GROUP BY s.invoice_no, d.delivery_invoice_no, c.customer_name, pt.term_name, d.currency
        ORDER BY original_invoice_no, payment_due_date
    """)

elif report == 'Delivery Invoice Wise Summary Report':
    rows = fetch_all("""
        SELECT d.delivery_invoice_no, c.customer_name, s.invoice_no AS original_invoice_no,
               s.shipment_no, MIN(d.delivery_date) AS delivery_date, MAX(d.payment_due_date) AS payment_due_date,
               d.currency, SUM(d.delivered_qty) AS total_qty, SUM(d.sale_amount) AS total_amount,
               COUNT(d.id) AS product_rows
        FROM customer_deliveries d
        JOIN customers c ON d.customer_id = c.id
        JOIN shipments s ON d.shipment_id = s.id
        GROUP BY d.delivery_invoice_no, c.customer_name, s.invoice_no, s.shipment_no, d.currency
        ORDER BY MIN(d.id) DESC
    """)

elif report == 'Monthly Sales Report - Product and Customer':
    rows = fetch_all("""
        SELECT to_char(d.delivery_date::date, 'YYYY-MM') AS sales_month,
               c.customer_name, p.product_code, p.product_name, d.currency,
               SUM(d.delivered_qty) AS total_qty,
               SUM(d.sale_amount) AS total_sales
        FROM customer_deliveries d
        JOIN customers c ON d.customer_id = c.id
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products p ON b.product_id = p.id
        GROUP BY sales_month, c.customer_name, p.product_code, p.product_name, d.currency
        ORDER BY sales_month DESC, c.customer_name, p.product_code
    """)

else:
    rows = fetch_all("""
        SELECT to_char(p.payment_received_date::date, 'YYYY-MM') AS receipt_month,
               c.customer_name, d.delivery_invoice_no, s.invoice_no AS original_invoice_no,
               p.payment_reference, p.payment_received_date, p.payment_amount, p.remarks
        FROM payments p
        JOIN customer_deliveries d ON p.delivery_id = d.id
        JOIN shipments s ON d.shipment_id = s.id
        JOIN customers c ON d.customer_id = c.id
        ORDER BY p.payment_received_date DESC, p.id DESC
    """)

df = report_total_footer_df(rows)
df = show_filtered_df(df.to_dict('records'), f'reports_filter_{report}', total=False)
export_buttons(df, report.replace(' ', '_').replace('-', '').lower())

render_slogan_footer()
