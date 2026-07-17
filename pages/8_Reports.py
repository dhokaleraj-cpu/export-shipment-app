from common import *

page_setup()

require_page_view('reports')
show_edit_permission_status('reports')

show_header('Reports - Fast Filter Table Grid', 'Filter first, then click Generate Report')
access_notice()
st.success("REPORT MODULE UPDATED: reports are filter-first. Select Report + filters, then click Generate Report. No heavy auto-loading.")

def _reports_total_footer_df_fallback(rows_or_df):
    df = rows_or_df.copy() if isinstance(rows_or_df, pd.DataFrame) else pd.DataFrame(rows_or_df)
    if df.empty:
        return df
    total_row = {col: "" for col in df.columns}
    total_row[df.columns[0]] = "TOTAL"
    has_numeric_total = False
    for col in df.columns:
        col_name = str(col).lower()
        if any(word in col_name for word in ["qty", "amount", "sale", "paid", "pending", "balance", "stock", "total"]):
            try:
                total_row[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).sum()
                has_numeric_total = True
            except Exception:
                pass
    if has_numeric_total:
        df = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)
    return df

if "report_total_footer_df" not in globals():
    report_total_footer_df = _reports_total_footer_df_fallback

def _in_clause(column_name, values):
    values = [int(v) for v in (values or []) if v not in (None, "")]
    if not values:
        return "", []
    return f" AND {column_name} IN ({','.join(['?'] * len(values))}) ", values

def _access_clause(product_column="b.product_id", warehouse_column="s.warehouse_id"):
    clauses = []
    params = []

    product_ids = current_user_allowed_product_ids()
    warehouse_ids = current_user_allowed_warehouse_ids()

    if product_column and product_ids:
        c, p = _in_clause(product_column, product_ids)
        clauses.append(c)
        params.extend(p)

    if warehouse_column and warehouse_ids:
        c, p = _in_clause(warehouse_column, warehouse_ids)
        clauses.append(c)
        params.extend(p)

    return "".join(clauses), params

def _txt_filter(text):
    return str(text or "").strip()


def _safe_sql_literal(value):
    """Small report helper for optional LIKE filters; keeps report filters out of psycopg2 placeholder mismatch paths."""
    return str(value or "").replace("'", "''").strip().lower()

def _literal_like_filter(column_expr, value):
    value = _safe_sql_literal(value)
    if not value:
        return ""
    return f" AND LOWER(COALESCE({column_expr}, '')) LIKE '%{value}%' "

def _fetch_report(sql, base_params=(), product_column="b.product_id", warehouse_column="s.warehouse_id"):
    access_sql, access_params = _access_clause(product_column, warehouse_column)
    sql = sql.replace("/*ACCESS_FILTER*/", access_sql)
    if " limit " not in sql.lower():
        sql = sql.rstrip().rstrip(";") + f"\n LIMIT {int(row_limit)}"
    final_params = tuple(base_params) + tuple(access_params)
    expected_params = sql.count("?")
    if expected_params != len(final_params):
        st.error(f"Report filter parameter mismatch: SQL expects {expected_params}, received {len(final_params)}. Please share this report name with Admin.")
        st.stop()
    return fetch_all(sql, final_params)

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

st.markdown('<div class="sap-grid-card"><div class="sap-grid-card-title">UPDATED REPORT FILTERS - FILTER FIRST / NO AUTO LOAD</div>', unsafe_allow_html=True)
st.caption("Use these filters before generating any report. This avoids heavy loading and makes payment reports searchable.")
f1, f2, f3, f4 = st.columns(4)
with f1:
    product_filter = _txt_filter(st.text_input('Part Number / Product Code', key='reports_product_filter', placeholder='Example: 40256626'))
with f2:
    customer_filter = _txt_filter(st.text_input('Customer / Warehouse', key='reports_customer_filter', placeholder='Customer or warehouse'))
with f3:
    invoice_filter = _txt_filter(st.text_input('Original Invoice Number', key='reports_invoice_filter', placeholder='Original invoice'))
with f4:
    delivery_invoice_filter = _txt_filter(st.text_input('Delivery Invoice Number', key='reports_delivery_invoice_filter', placeholder='Delivery invoice'))

f5, f6, f7 = st.columns([1, 1, 1])
with f5:
    report_from_date = st.date_input('From Date', value=date(date.today().year, 1, 1), key='reports_from_date')
with f6:
    report_to_date = st.date_input('To Date', value=date.today(), key='reports_to_date')
with f7:
    row_limit = st.selectbox('Max Rows', [100, 250, 500, 1000, 2000], index=1, key='reports_row_limit')

generate_report = st.button('GENERATE REPORT', type='primary', key='reports_generate_button', width='stretch')
st.markdown('</div>', unsafe_allow_html=True)

if report in ['Original Invoice Number Wise Payment Due', 'Original Invoice wise payment Balance', 'Monthly Payment Receipt Report']:
    st.info("Payment report filters active: Part Number, Customer, Original Invoice Number, Delivery Invoice Number, Date Range, Max Rows.")

if not generate_report:
    st.info('Select filters and click Generate Report. Reports are not loaded automatically to keep this page fast.')
    render_slogan_footer()
    st.stop()

rows = []

# Every report query below is product/warehouse access filtered by /*ACCESS_FILTER*/.
# Blank Product Access = all products. Blank Warehouse Access = all warehouses.

if report == 'Delivery to Customer Product Wise Sale Report':
    rows = _fetch_report("""
        SELECT
            d.delivery_invoice_no,
            d.delivery_date,
            s.invoice_no AS original_invoice_no,
            s.shipment_no,
            w.warehouse_name,
            c.customer_name,
            b.product_id,
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
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        JOIN customers c ON d.customer_id = c.id
        WHERE (? = '' OR LOWER(p.product_code || ' ' || p.product_name) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(s.invoice_no || ' ' || d.delivery_invoice_no) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(c.customer_name || ' ' || COALESCE(w.warehouse_name,'')) LIKE LOWER(CONCAT('%', ?, '%')))
          /*ACCESS_FILTER*/
        GROUP BY d.delivery_invoice_no, d.delivery_date, s.invoice_no, s.shipment_no,
                 w.warehouse_name, c.customer_name, b.product_id, p.product_code, p.product_name, d.currency
        ORDER BY d.delivery_date DESC, d.delivery_invoice_no, p.product_code
    """, (product_filter, product_filter, invoice_filter, invoice_filter, customer_filter, customer_filter))

elif report == 'Product Wise and Delivery Invoice Wise Report for Original Invoice Number':
    rows = _fetch_report("""
        SELECT s.invoice_no AS original_invoice_no,
               d.delivery_invoice_no,
               w.warehouse_name,
               b.product_id,
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
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        JOIN customers c ON d.customer_id = c.id
        WHERE (? = '' OR LOWER(p.product_code || ' ' || p.product_name) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(s.invoice_no) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(c.customer_name || ' ' || COALESCE(w.warehouse_name,'')) LIKE LOWER(CONCAT('%', ?, '%')))
          /*ACCESS_FILTER*/
        GROUP BY s.invoice_no, d.delivery_invoice_no, w.warehouse_name, b.product_id, p.product_code, p.product_name, c.customer_name, d.currency
        ORDER BY s.invoice_no, d.delivery_invoice_no, p.product_code
    """, (product_filter, product_filter, invoice_filter, invoice_filter, customer_filter, customer_filter))

elif report == 'Product Wise Stock Report':
    rows = _fetch_report("""
        SELECT p.product_code,
               p.product_name,
               b.product_id,
               w.warehouse_name,
               COALESCE(SUM(b.original_qty),0) AS shipment_qty,
               COALESCE(SUM(d.delivered_qty),0) AS delivered_qty,
               COALESCE(SUM(b.original_qty),0) - COALESCE(SUM(d.delivered_qty),0) AS stock_balance_qty,
               b.currency,
               COALESCE(SUM((b.original_qty - COALESCE(d.delivered_qty,0)) * COALESCE(b.unit_price,0)),0) AS stock_balance_amount
        FROM shipment_boxes b
        JOIN shipments s ON b.shipment_id = s.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        LEFT JOIN (
            SELECT box_id, SUM(delivered_qty) AS delivered_qty
            FROM customer_deliveries
            GROUP BY box_id
        ) d ON b.id = d.box_id
        WHERE (? = '' OR LOWER(p.product_code || ' ' || p.product_name) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(COALESCE(w.warehouse_name,'')) LIKE LOWER(CONCAT('%', ?, '%')))
          /*ACCESS_FILTER*/
        GROUP BY p.product_code, p.product_name, b.product_id, w.warehouse_name, b.currency
        ORDER BY p.product_code, w.warehouse_name
    """, (product_filter, product_filter, customer_filter, customer_filter))

elif report == 'Product Wise Sale Report':
    rows = _fetch_report("""
        SELECT p.product_code,
               p.product_name,
               b.product_id,
               w.warehouse_name,
               c.customer_name,
               d.currency,
               SUM(d.delivered_qty) AS sold_qty,
               SUM(d.sale_amount) AS sale_amount
        FROM customer_deliveries d
        JOIN shipments s ON d.shipment_id = s.id
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        JOIN customers c ON d.customer_id = c.id
        WHERE (? = '' OR LOWER(p.product_code || ' ' || p.product_name) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(c.customer_name || ' ' || COALESCE(w.warehouse_name,'')) LIKE LOWER(CONCAT('%', ?, '%')))
          /*ACCESS_FILTER*/
        GROUP BY p.product_code, p.product_name, b.product_id, w.warehouse_name, c.customer_name, d.currency
        ORDER BY p.product_code, w.warehouse_name, c.customer_name
    """, (product_filter, product_filter, customer_filter, customer_filter))

elif report == 'Original Invoice Wise Sale Report':
    rows = _fetch_report("""
        SELECT s.invoice_no AS original_invoice_no,
               s.shipment_no,
               w.warehouse_name,
               c.customer_name,
               d.currency,
               SUM(d.delivered_qty) AS sold_qty,
               SUM(d.sale_amount) AS sale_amount,
               COUNT(DISTINCT d.delivery_invoice_no) AS delivery_invoice_count
        FROM customer_deliveries d
        JOIN shipments s ON d.shipment_id = s.id
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        JOIN customers c ON d.customer_id = c.id
        WHERE (? = '' OR LOWER(s.invoice_no) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(d.delivery_invoice_no) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(c.customer_name || ' ' || COALESCE(w.warehouse_name,'')) LIKE LOWER(CONCAT('%', ?, '%')))
          /*ACCESS_FILTER*/
        GROUP BY s.invoice_no, s.shipment_no, w.warehouse_name, c.customer_name, d.currency
        ORDER BY s.invoice_no
    """, (invoice_filter, invoice_filter, delivery_invoice_filter, delivery_invoice_filter, customer_filter, customer_filter))

elif report == 'Warehouse Wise Sale Report':
    rows = _fetch_report("""
        SELECT w.warehouse_name,
               c.customer_name,
               d.currency,
               SUM(d.delivered_qty) AS sold_qty,
               SUM(d.sale_amount) AS sale_amount
        FROM customer_deliveries d
        JOIN shipments s ON d.shipment_id = s.id
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        JOIN customers c ON d.customer_id = c.id
        WHERE (? = '' OR LOWER(COALESCE(w.warehouse_name,'') || ' ' || c.customer_name) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(p.product_code || ' ' || p.product_name) LIKE LOWER(CONCAT('%', ?, '%')))
          /*ACCESS_FILTER*/
        GROUP BY w.warehouse_name, c.customer_name, d.currency
        ORDER BY w.warehouse_name, c.customer_name
    """, (customer_filter, customer_filter, product_filter, product_filter))

elif report == 'Balance Quantity Report Product Wise':
    rows = _fetch_report("""
        SELECT p.product_code,
               p.product_name,
               b.product_id,
               w.warehouse_name,
               b.currency,
               COALESCE(SUM(b.original_qty),0) AS original_qty,
               COALESCE(SUM(d.delivered_qty),0) AS delivered_qty,
               COALESCE(SUM(b.original_qty),0) - COALESCE(SUM(d.delivered_qty),0) AS balance_qty
        FROM shipment_boxes b
        JOIN shipments s ON b.shipment_id = s.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        LEFT JOIN (
            SELECT box_id, SUM(delivered_qty) AS delivered_qty
            FROM customer_deliveries
            GROUP BY box_id
        ) d ON b.id = d.box_id
        WHERE (? = '' OR LOWER(p.product_code || ' ' || p.product_name) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(COALESCE(w.warehouse_name,'')) LIKE LOWER(CONCAT('%', ?, '%')))
          /*ACCESS_FILTER*/
        GROUP BY p.product_code, p.product_name, b.product_id, w.warehouse_name, b.currency
        ORDER BY p.product_code
    """, (product_filter, product_filter, customer_filter, customer_filter))

elif report == 'Original Invoice Number Wise Payment Due':
    # Parameter-safe version. Optional filters are inserted as sanitized SQL literals.
    # Access filters still use parameters through _fetch_report.
    payment_due_filter_sql = ""
    payment_due_filter_sql += _literal_like_filter("s.invoice_no", invoice_filter)
    payment_due_filter_sql += _literal_like_filter("d.delivery_invoice_no", delivery_invoice_filter)
    payment_due_filter_sql += _literal_like_filter("c.customer_name || ' ' || COALESCE(w.warehouse_name,'')", customer_filter)
    payment_due_filter_sql += _literal_like_filter("p.product_code || ' ' || p.product_name", product_filter)
    payment_due_filter_sql += f" AND d.payment_due_date::date BETWEEN '{str(report_from_date)}'::date AND '{str(report_to_date)}'::date "

    rows = _fetch_report(f"""
        SELECT s.invoice_no AS original_invoice_no,
               d.delivery_invoice_no,
               s.shipment_no,
               w.warehouse_name,
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
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        JOIN customers c ON d.customer_id = c.id
        LEFT JOIN (
            SELECT delivery_id, SUM(payment_amount) AS payment_amount
            FROM payments
            GROUP BY delivery_id
        ) pay ON d.id = pay.delivery_id
        WHERE 1=1
          {payment_due_filter_sql}
          /*ACCESS_FILTER*/
        GROUP BY s.invoice_no, d.delivery_invoice_no, s.shipment_no, w.warehouse_name, c.customer_name, d.currency
        ORDER BY payment_due_date
    """, ())

elif report == 'Original Invoice Number Wise Balance Quantity Product Wise':
    rows = _fetch_report("""
        SELECT s.invoice_no AS original_invoice_no,
               s.shipment_no,
               w.warehouse_name,
               p.product_code,
               p.product_name,
               b.product_id,
               b.currency,
               COALESCE(SUM(b.original_qty),0) AS original_qty,
               COALESCE(SUM(d.delivered_qty),0) AS delivered_qty,
               COALESCE(SUM(b.original_qty),0) - COALESCE(SUM(d.delivered_qty),0) AS balance_qty
        FROM shipment_boxes b
        JOIN shipments s ON b.shipment_id = s.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        LEFT JOIN (
            SELECT box_id, SUM(delivered_qty) AS delivered_qty
            FROM customer_deliveries
            GROUP BY box_id
        ) d ON b.id = d.box_id
        WHERE (? = '' OR LOWER(p.product_code || ' ' || p.product_name) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(s.invoice_no) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(COALESCE(w.warehouse_name,'')) LIKE LOWER(CONCAT('%', ?, '%')))
          /*ACCESS_FILTER*/
        GROUP BY s.invoice_no, s.shipment_no, w.warehouse_name, p.product_code, p.product_name, b.product_id, b.currency
        ORDER BY s.invoice_no, p.product_code
    """, (product_filter, product_filter, invoice_filter, invoice_filter, customer_filter, customer_filter))

elif report == 'Pallet Wise Balance Quantity':
    rows = _fetch_report("""
        SELECT s.shipment_no, s.invoice_no, w.warehouse_name,
               b.fifo_row_id, b.pallet_no, b.box_no, b.product_id,
               p.product_code, p.product_name,
               b.original_qty, b.unit_price, b.currency, b.amount,
               COALESCE(d.delivered_qty,0) AS delivered_qty,
               b.original_qty - COALESCE(d.delivered_qty,0) AS balance_qty
        FROM shipment_boxes b
        JOIN shipments s ON b.shipment_id = s.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        LEFT JOIN (
            SELECT box_id, SUM(delivered_qty) AS delivered_qty
            FROM customer_deliveries
            GROUP BY box_id
        ) d ON b.id = d.box_id
        WHERE (? = '' OR LOWER(p.product_code || ' ' || p.product_name) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(s.invoice_no || ' ' || COALESCE(w.warehouse_name,'')) LIKE LOWER(CONCAT('%', ?, '%')))
          /*ACCESS_FILTER*/
        GROUP BY b.id, s.shipment_no, s.invoice_no, w.warehouse_name, b.fifo_row_id, b.pallet_no, b.box_no, b.product_id, p.product_code,
                 p.product_name, b.original_qty, b.unit_price, b.currency, b.amount, d.delivered_qty
        ORDER BY COALESCE(b.fifo_row_id,b.id), s.shipment_no, b.pallet_no
    """, (product_filter, product_filter, customer_filter, customer_filter))

elif report == 'Original Invoice Wise Balance Quantity':
    rows = _fetch_report("""
        SELECT s.invoice_no, s.shipment_no, w.warehouse_name,
               p.product_code, p.product_name, b.product_id,
               SUM(b.original_qty) AS original_qty, SUM(b.amount) AS amount,
               COALESCE(SUM(d.delivered_qty),0) AS delivered_qty,
               SUM(b.original_qty) - COALESCE(SUM(d.delivered_qty),0) AS balance_qty
        FROM shipment_boxes b
        JOIN shipments s ON b.shipment_id = s.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        LEFT JOIN (
            SELECT box_id, SUM(delivered_qty) AS delivered_qty
            FROM customer_deliveries
            GROUP BY box_id
        ) d ON b.id = d.box_id
        WHERE (? = '' OR LOWER(p.product_code || ' ' || p.product_name) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(s.invoice_no || ' ' || COALESCE(w.warehouse_name,'')) LIKE LOWER(CONCAT('%', ?, '%')))
          /*ACCESS_FILTER*/
        GROUP BY s.invoice_no, s.shipment_no, w.warehouse_name, p.product_code, p.product_name, b.product_id
        ORDER BY s.invoice_no
    """, (product_filter, product_filter, customer_filter, customer_filter))

elif report == 'Original Invoice wise payment Balance':
    rows = _fetch_report("""
        SELECT s.invoice_no AS original_invoice_no,
               d.delivery_invoice_no,
               w.warehouse_name,
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
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        JOIN customers c ON d.customer_id = c.id
        LEFT JOIN payment_terms pt ON d.payment_term_id = pt.id
        LEFT JOIN (
            SELECT delivery_id, SUM(payment_amount) AS payment_amount
            FROM payments
            GROUP BY delivery_id
        ) pay ON d.id = pay.delivery_id
        WHERE (? = '' OR LOWER(s.invoice_no) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(d.delivery_invoice_no) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(c.customer_name || ' ' || COALESCE(w.warehouse_name,'')) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(p.product_code || ' ' || p.product_name) LIKE LOWER(CONCAT('%', ?, '%')))
          /*ACCESS_FILTER*/
        GROUP BY s.invoice_no, d.delivery_invoice_no, w.warehouse_name, c.customer_name, pt.term_name, d.currency
        ORDER BY original_invoice_no, payment_due_date
    """, (invoice_filter, invoice_filter, delivery_invoice_filter, delivery_invoice_filter, customer_filter, customer_filter, product_filter, product_filter))

elif report == 'Delivery Invoice Wise Summary Report':
    rows = _fetch_report("""
        SELECT d.delivery_invoice_no, c.customer_name, s.invoice_no AS original_invoice_no,
               s.shipment_no, w.warehouse_name,
               MIN(d.delivery_date) AS delivery_date, MAX(d.payment_due_date) AS payment_due_date,
               d.currency, SUM(d.delivered_qty) AS total_qty, SUM(d.sale_amount) AS total_amount,
               COUNT(d.id) AS product_rows
        FROM customer_deliveries d
        JOIN customers c ON d.customer_id = c.id
        JOIN shipments s ON d.shipment_id = s.id
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        WHERE (? = '' OR LOWER(s.invoice_no) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(d.delivery_invoice_no) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(c.customer_name || ' ' || COALESCE(w.warehouse_name,'')) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(p.product_code || ' ' || p.product_name) LIKE LOWER(CONCAT('%', ?, '%')))
          /*ACCESS_FILTER*/
        GROUP BY d.delivery_invoice_no, c.customer_name, s.invoice_no, s.shipment_no, w.warehouse_name, d.currency
        ORDER BY MIN(d.id) DESC
    """, (invoice_filter, invoice_filter, delivery_invoice_filter, delivery_invoice_filter, customer_filter, customer_filter, product_filter, product_filter))

elif report == 'Monthly Sales Report - Product and Customer':
    rows = _fetch_report("""
        SELECT to_char(d.delivery_date::date, 'YYYY-MM') AS sales_month,
               c.customer_name, w.warehouse_name, b.product_id,
               p.product_code, p.product_name, d.currency,
               SUM(d.delivered_qty) AS total_qty,
               SUM(d.sale_amount) AS total_sales
        FROM customer_deliveries d
        JOIN customers c ON d.customer_id = c.id
        JOIN shipments s ON d.shipment_id = s.id
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        WHERE (? = '' OR LOWER(p.product_code || ' ' || p.product_name) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(c.customer_name || ' ' || COALESCE(w.warehouse_name,'')) LIKE LOWER(CONCAT('%', ?, '%')))
          /*ACCESS_FILTER*/
        GROUP BY sales_month, c.customer_name, w.warehouse_name, b.product_id, p.product_code, p.product_name, d.currency
        ORDER BY sales_month DESC, c.customer_name, p.product_code
    """, (product_filter, product_filter, customer_filter, customer_filter))

else:
    rows = _fetch_report("""
        SELECT to_char(p.payment_received_date::date, 'YYYY-MM') AS receipt_month,
               c.customer_name, w.warehouse_name, d.delivery_invoice_no, s.invoice_no AS original_invoice_no,
               b.product_id, pr.product_code, pr.product_name,
               p.payment_reference, p.payment_received_date, p.payment_amount, p.remarks
        FROM payments p
        JOIN customer_deliveries d ON p.delivery_id = d.id
        JOIN shipments s ON d.shipment_id = s.id
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products pr ON b.product_id = pr.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        JOIN customers c ON d.customer_id = c.id
        WHERE (? = '' OR LOWER(pr.product_code || ' ' || pr.product_name) LIKE LOWER(CONCAT('%', ?, '%')))
          AND (? = '' OR LOWER(c.customer_name || ' ' || COALESCE(w.warehouse_name,'') || ' ' || s.invoice_no) LIKE LOWER(CONCAT('%', ?, '%')))
          /*ACCESS_FILTER*/
        ORDER BY p.payment_received_date DESC, p.id DESC
    """, (product_filter, product_filter, customer_filter, customer_filter), product_column="b.product_id", warehouse_column="s.warehouse_id")

rows = filter_rows_by_user_access(rows)
df = report_total_footer_df(rows)
df = show_filtered_df(df.to_dict('records'), f'reports_filter_{report}', total=False)
export_buttons(df, report.replace(' ', '_').replace('-', '').lower())

render_slogan_footer()


# UPDATED_REPORT_MODULE_MARKER
