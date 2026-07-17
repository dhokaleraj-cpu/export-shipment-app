from common import *

REPORTS_DEPLOY_VERSION = "2026-07-13-POSTGRESQL-SAFE-NO-OLD-LINE-293"

page_setup()

require_page_view("reports")
show_edit_permission_status("reports")

show_header("Reports - Fast Filter Table Grid", "PostgreSQL-safe report engine")
access_notice()

st.success("REPORT MODULE UPDATED: PostgreSQL-safe engine. Select filters, then click GENERATE REPORT.")
st.caption("Reports deployment version: " + REPORTS_DEPLOY_VERSION)
st.code(REPORTS_DEPLOY_VERSION)

# ---------------------------------------------------------------------------
# PostgreSQL-safe helpers
# ---------------------------------------------------------------------------

def _txt_filter(text):
    return str(text or "").strip()


def _in_clause(column_name, values):
    values = [int(v) for v in (values or []) if v not in (None, "")]
    if not values:
        return "", []
    return f" AND {column_name} IN ({','.join(['%s'] * len(values))}) ", values


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


def _like_clause(column_expr, value):
    value = _txt_filter(value)
    if not value:
        return "", []
    return f" AND LOWER(COALESCE({column_expr}, '')) LIKE %s ", [f"%{value.lower()}%"]


def _date_clause(column_expr, from_date, to_date):
    if not from_date or not to_date:
        return "", []
    return f" AND {column_expr} IS NOT NULL AND {column_expr}::date BETWEEN %s::date AND %s::date ", [str(from_date), str(to_date)]


def _fetch_report(sql, params=None, product_column="b.product_id", warehouse_column="s.warehouse_id"):
    access_sql, access_params = _access_clause(product_column, warehouse_column)
    final_sql = sql.replace("/*ACCESS_FILTER*/", access_sql)

    final_params = list(params or []) + list(access_params)

    if " limit " not in final_sql.lower():
        final_sql = final_sql.rstrip().rstrip(";") + f"\n LIMIT {int(row_limit)}"

    expected_params = final_sql.count("%s")
    if expected_params != len(final_params):
        st.error(
            f"Report parameter mismatch prevented. SQL expects {expected_params}, received {len(final_params)}. "
            f"Report: {report}"
        )
        st.code(final_sql)
        st.stop()

    return fetch_all(final_sql, tuple(final_params))


def _show_report(rows, file_name):
    if not rows:
        st.info("No records found for selected filters.")
        return

    df = pd.DataFrame(format_date_columns(rows))
    try:
        df_display = report_total_footer_df(df) if "report_total_footer_df" in globals() else df
    except Exception:
        df_display = df

    st.dataframe(df_display, width="stretch", hide_index=True)
    try:
        export_buttons(df, file_name)
    except Exception:
        pass


def _common_delivery_filters(date_column="d.delivery_date"):
    clauses = []
    params = []
    for clause, p in [
        _like_clause("p.product_code || ' ' || p.product_name", product_filter),
        _like_clause("c.customer_name || ' ' || COALESCE(w.warehouse_name,'')", customer_filter),
        _like_clause("s.invoice_no", invoice_filter),
        _like_clause("d.delivery_invoice_no", delivery_invoice_filter),
        _date_clause(date_column, report_from_date, report_to_date),
    ]:
        clauses.append(clause)
        params.extend(p)
    return "".join(clauses), params


def _common_shipment_filters(date_column="s.shipment_date"):
    clauses = []
    params = []
    for clause, p in [
        _like_clause("p.product_code || ' ' || p.product_name", product_filter),
        _like_clause("COALESCE(w.warehouse_name,'')", customer_filter),
        _like_clause("s.invoice_no", invoice_filter),
        _date_clause(date_column, report_from_date, report_to_date),
    ]:
        clauses.append(clause)
        params.extend(p)
    return "".join(clauses), params


# ---------------------------------------------------------------------------
# UI filters
# ---------------------------------------------------------------------------

report_options = [
    "Delivery to Customer Product Wise Sale Report",
    "Product Wise and Delivery Invoice Wise Report for Original Invoice Number",
    "Product Wise Stock Report",
    "Product Wise Sale Report",
    "Original Invoice Wise Sale Report",
    "Warehouse Wise Sale Report",
    "Balance Quantity Report Product Wise",
    "Original Invoice Number Wise Payment Due",
    "Original Invoice Number Wise Balance Quantity Product Wise",
    "Pallet Wise Balance Quantity",
    "Original Invoice Wise Balance Quantity",
    "Original Invoice wise payment Balance",
    "Delivery Invoice Wise Summary Report",
    "Monthly Sales Report - Product and Customer",
    "Monthly Payment Receipt Report",
]

report = searchable_selectbox("Select Report", report_options, key="reports_select_report")

st.markdown(
    '<div class="sap-grid-card"><div class="sap-grid-card-title">UPDATED REPORT FILTERS - POSTGRESQL SAFE / FILTER FIRST</div>',
    unsafe_allow_html=True,
)
st.caption("Select filters first, then click GENERATE REPORT. This page does not auto-load heavy data.")

f1, f2, f3, f4 = st.columns(4)
with f1:
    product_filter = _txt_filter(st.text_input("Part Number / Product Code", key="reports_product_filter", placeholder="Example: 40256626"))
with f2:
    customer_filter = _txt_filter(st.text_input("Customer / Warehouse", key="reports_customer_filter", placeholder="Customer or warehouse"))
with f3:
    invoice_filter = _txt_filter(st.text_input("Original Invoice Number", key="reports_invoice_filter", placeholder="Original invoice"))
with f4:
    delivery_invoice_filter = _txt_filter(st.text_input("Delivery Invoice Number", key="reports_delivery_invoice_filter", placeholder="Delivery invoice"))

f5, f6, f7 = st.columns([1, 1, 1])
with f5:
    report_from_date = st.date_input("From Date", value=date(date.today().year, 1, 1), key="reports_from_date")
with f6:
    report_to_date = st.date_input("To Date", value=date.today(), key="reports_to_date")
with f7:
    row_limit = st.selectbox("Max Rows", [100, 250, 500, 1000, 2000], index=1, key="reports_row_limit")

generate_report = st.button("GENERATE REPORT", type="primary", key="reports_generate_button", width="stretch")
st.markdown("</div>", unsafe_allow_html=True)

if report in [
    "Original Invoice Number Wise Payment Due",
    "Original Invoice wise payment Balance",
    "Monthly Payment Receipt Report",
]:
    st.info("Payment report filters active: Part Number, Customer, Original Invoice Number, Delivery Invoice Number, Date Range, Max Rows.")

if not generate_report:
    st.info("No report loaded yet. Select Report + filters and click GENERATE REPORT.")
    render_slogan_footer()
    st.stop()

if report_from_date > report_to_date:
    st.warning("From Date is after To Date. Dates were swapped for this report.")
    report_from_date, report_to_date = report_to_date, report_from_date


# ---------------------------------------------------------------------------
# Report queries
# ---------------------------------------------------------------------------

rows = []

if report == "Delivery to Customer Product Wise Sale Report":
    filter_sql, filter_params = _common_delivery_filters("d.delivery_date")
    rows = _fetch_report(f"""
        SELECT d.delivery_invoice_no, d.delivery_date, s.invoice_no AS original_invoice_no,
               s.shipment_no, w.warehouse_name, c.customer_name, b.product_id,
               p.product_code, p.product_name, d.currency,
               SUM(d.delivered_qty) AS delivered_qty,
               AVG(d.unit_price) AS average_price,
               SUM(d.sale_amount) AS sale_amount
        FROM customer_deliveries d
        JOIN shipments s ON d.shipment_id = s.id
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        JOIN customers c ON d.customer_id = c.id
        WHERE 1=1
        {filter_sql}
        /*ACCESS_FILTER*/
        GROUP BY d.delivery_invoice_no, d.delivery_date, s.invoice_no, s.shipment_no,
                 w.warehouse_name, c.customer_name, b.product_id, p.product_code, p.product_name, d.currency
        ORDER BY d.delivery_date DESC, d.delivery_invoice_no, p.product_code
    """, filter_params)

elif report == "Product Wise and Delivery Invoice Wise Report for Original Invoice Number":
    filter_sql, filter_params = _common_delivery_filters("d.delivery_date")
    rows = _fetch_report(f"""
        SELECT s.invoice_no AS original_invoice_no, d.delivery_invoice_no, w.warehouse_name,
               b.product_id, p.product_code, p.product_name, c.customer_name, d.currency,
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
        WHERE 1=1
        {filter_sql}
        /*ACCESS_FILTER*/
        GROUP BY s.invoice_no, d.delivery_invoice_no, w.warehouse_name, b.product_id,
                 p.product_code, p.product_name, c.customer_name, d.currency
        ORDER BY s.invoice_no, d.delivery_invoice_no, p.product_code
    """, filter_params)

elif report in ["Product Wise Stock Report", "Balance Quantity Report Product Wise"]:
    filter_sql, filter_params = _common_shipment_filters("s.shipment_date")
    rows = _fetch_report(f"""
        SELECT p.product_code, p.product_name, b.product_id, w.warehouse_name, b.currency,
               COALESCE(SUM(b.original_qty),0) AS original_qty,
               COALESCE(SUM(del.delivered_qty),0) AS delivered_qty,
               COALESCE(SUM(b.original_qty),0) - COALESCE(SUM(del.delivered_qty),0) AS balance_qty,
               COALESCE(SUM((b.original_qty - COALESCE(del.delivered_qty,0)) * b.unit_price),0) AS balance_amount
        FROM shipment_boxes b
        JOIN shipments s ON b.shipment_id = s.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        LEFT JOIN (
            SELECT box_id, SUM(delivered_qty) AS delivered_qty
            FROM customer_deliveries
            GROUP BY box_id
        ) del ON b.id = del.box_id
        WHERE 1=1
        {filter_sql}
        /*ACCESS_FILTER*/
        GROUP BY p.product_code, p.product_name, b.product_id, w.warehouse_name, b.currency
        ORDER BY p.product_code, w.warehouse_name
    """, filter_params)

elif report == "Product Wise Sale Report":
    filter_sql, filter_params = _common_delivery_filters("d.delivery_date")
    rows = _fetch_report(f"""
        SELECT p.product_code, p.product_name, b.product_id, w.warehouse_name,
               c.customer_name, d.currency,
               SUM(d.delivered_qty) AS sold_qty,
               SUM(d.sale_amount) AS sale_amount
        FROM customer_deliveries d
        JOIN shipments s ON d.shipment_id = s.id
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        JOIN customers c ON d.customer_id = c.id
        WHERE 1=1
        {filter_sql}
        /*ACCESS_FILTER*/
        GROUP BY p.product_code, p.product_name, b.product_id, w.warehouse_name, c.customer_name, d.currency
        ORDER BY p.product_code, w.warehouse_name, c.customer_name
    """, filter_params)

elif report == "Original Invoice Wise Sale Report":
    filter_sql, filter_params = _common_delivery_filters("d.delivery_date")
    rows = _fetch_report(f"""
        SELECT s.invoice_no AS original_invoice_no, s.shipment_no, w.warehouse_name,
               c.customer_name, d.currency,
               SUM(d.delivered_qty) AS sold_qty,
               SUM(d.sale_amount) AS sale_amount,
               COUNT(DISTINCT d.delivery_invoice_no) AS delivery_invoice_count
        FROM customer_deliveries d
        JOIN shipments s ON d.shipment_id = s.id
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        JOIN customers c ON d.customer_id = c.id
        WHERE 1=1
        {filter_sql}
        /*ACCESS_FILTER*/
        GROUP BY s.invoice_no, s.shipment_no, w.warehouse_name, c.customer_name, d.currency
        ORDER BY s.invoice_no
    """, filter_params)

elif report == "Warehouse Wise Sale Report":
    filter_sql, filter_params = _common_delivery_filters("d.delivery_date")
    rows = _fetch_report(f"""
        SELECT w.warehouse_name, c.customer_name, d.currency,
               SUM(d.delivered_qty) AS sold_qty,
               SUM(d.sale_amount) AS sale_amount
        FROM customer_deliveries d
        JOIN shipments s ON d.shipment_id = s.id
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        JOIN customers c ON d.customer_id = c.id
        WHERE 1=1
        {filter_sql}
        /*ACCESS_FILTER*/
        GROUP BY w.warehouse_name, c.customer_name, d.currency
        ORDER BY w.warehouse_name, c.customer_name
    """, filter_params)

elif report == "Original Invoice Number Wise Payment Due":
    filter_sql, filter_params = _common_delivery_filters("d.payment_due_date")
    rows = _fetch_report(f"""
        SELECT s.invoice_no AS original_invoice_no, d.delivery_invoice_no, s.shipment_no,
               w.warehouse_name, c.customer_name, d.currency,
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
        {filter_sql}
        /*ACCESS_FILTER*/
        GROUP BY s.invoice_no, d.delivery_invoice_no, s.shipment_no, w.warehouse_name, c.customer_name, d.currency
        ORDER BY payment_due_date
    """, filter_params)

elif report == "Original Invoice Number Wise Balance Quantity Product Wise":
    filter_sql, filter_params = _common_shipment_filters("s.shipment_date")
    rows = _fetch_report(f"""
        SELECT s.invoice_no AS original_invoice_no, s.shipment_no, w.warehouse_name,
               p.product_code, p.product_name, b.product_id, b.currency,
               COALESCE(SUM(b.original_qty),0) AS original_qty,
               COALESCE(SUM(del.delivered_qty),0) AS delivered_qty,
               COALESCE(SUM(b.original_qty),0) - COALESCE(SUM(del.delivered_qty),0) AS balance_qty
        FROM shipment_boxes b
        JOIN shipments s ON b.shipment_id = s.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        LEFT JOIN (
            SELECT box_id, SUM(delivered_qty) AS delivered_qty
            FROM customer_deliveries
            GROUP BY box_id
        ) del ON b.id = del.box_id
        WHERE 1=1
        {filter_sql}
        /*ACCESS_FILTER*/
        GROUP BY s.invoice_no, s.shipment_no, w.warehouse_name, p.product_code, p.product_name, b.product_id, b.currency
        ORDER BY s.invoice_no, p.product_code
    """, filter_params)

elif report == "Pallet Wise Balance Quantity":
    filter_sql, filter_params = _common_shipment_filters("s.shipment_date")
    rows = _fetch_report(f"""
        SELECT s.shipment_no, s.invoice_no, w.warehouse_name,
               b.fifo_row_id, b.pallet_no, b.box_no, b.product_id,
               p.product_code, p.product_name, b.original_qty, b.unit_price,
               b.currency, b.amount,
               COALESCE(del.delivered_qty,0) AS delivered_qty,
               b.original_qty - COALESCE(del.delivered_qty,0) AS balance_qty
        FROM shipment_boxes b
        JOIN shipments s ON b.shipment_id = s.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        LEFT JOIN (
            SELECT box_id, SUM(delivered_qty) AS delivered_qty
            FROM customer_deliveries
            GROUP BY box_id
        ) del ON b.id = del.box_id
        WHERE 1=1
        {filter_sql}
        /*ACCESS_FILTER*/
        ORDER BY s.invoice_no, COALESCE(b.fifo_row_id,b.id), b.pallet_no, b.box_no
    """, filter_params)

elif report == "Original Invoice Wise Balance Quantity":
    filter_sql, filter_params = _common_shipment_filters("s.shipment_date")
    rows = _fetch_report(f"""
        SELECT s.invoice_no AS original_invoice_no, s.shipment_no, w.warehouse_name,
               b.currency,
               COALESCE(SUM(b.original_qty),0) AS original_qty,
               COALESCE(SUM(del.delivered_qty),0) AS delivered_qty,
               COALESCE(SUM(b.original_qty),0) - COALESCE(SUM(del.delivered_qty),0) AS balance_qty
        FROM shipment_boxes b
        JOIN shipments s ON b.shipment_id = s.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        LEFT JOIN (
            SELECT box_id, SUM(delivered_qty) AS delivered_qty
            FROM customer_deliveries
            GROUP BY box_id
        ) del ON b.id = del.box_id
        WHERE 1=1
        {filter_sql}
        /*ACCESS_FILTER*/
        GROUP BY s.invoice_no, s.shipment_no, w.warehouse_name, b.currency
        ORDER BY s.invoice_no
    """, filter_params)

elif report == "Original Invoice wise payment Balance":
    filter_sql, filter_params = _common_delivery_filters("d.payment_due_date")
    rows = _fetch_report(f"""
        SELECT s.invoice_no AS original_invoice_no, d.delivery_invoice_no,
               w.warehouse_name, c.customer_name,
               MIN(d.delivery_date) AS delivery_date,
               MAX(d.payment_due_date) AS payment_due_date,
               d.currency,
               SUM(d.delivered_qty) AS delivered_qty,
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
        {filter_sql}
        /*ACCESS_FILTER*/
        GROUP BY s.invoice_no, d.delivery_invoice_no, w.warehouse_name, c.customer_name, d.currency
        ORDER BY original_invoice_no, payment_due_date
    """, filter_params)

elif report == "Delivery Invoice Wise Summary Report":
    filter_sql, filter_params = _common_delivery_filters("d.delivery_date")
    rows = _fetch_report(f"""
        SELECT d.delivery_invoice_no, c.customer_name, s.invoice_no AS original_invoice_no,
               s.shipment_no, w.warehouse_name,
               MIN(d.delivery_date) AS delivery_date,
               MAX(d.payment_due_date) AS payment_due_date,
               d.currency,
               SUM(d.delivered_qty) AS total_qty,
               SUM(d.sale_amount) AS total_amount,
               COUNT(d.id) AS product_rows
        FROM customer_deliveries d
        JOIN customers c ON d.customer_id = c.id
        JOIN shipments s ON d.shipment_id = s.id
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        WHERE 1=1
        {filter_sql}
        /*ACCESS_FILTER*/
        GROUP BY d.delivery_invoice_no, c.customer_name, s.invoice_no, s.shipment_no, w.warehouse_name, d.currency
        ORDER BY MIN(d.id) DESC
    """, filter_params)

elif report == "Monthly Sales Report - Product and Customer":
    filter_sql, filter_params = _common_delivery_filters("d.delivery_date")
    rows = _fetch_report(f"""
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
        WHERE 1=1
        {filter_sql}
        /*ACCESS_FILTER*/
        GROUP BY sales_month, c.customer_name, w.warehouse_name, b.product_id, p.product_code, p.product_name, d.currency
        ORDER BY sales_month DESC, c.customer_name, p.product_code
    """, filter_params)

elif report == "Monthly Payment Receipt Report":
    filter_sql, filter_params = _common_delivery_filters("pmt.payment_received_date")
    rows = _fetch_report(f"""
        SELECT to_char(pmt.payment_received_date::date, 'YYYY-MM') AS payment_month,
               pmt.payment_received_date,
               c.customer_name,
               s.invoice_no AS original_invoice_no,
               d.delivery_invoice_no,
               w.warehouse_name,
               pr.product_code,
               pr.product_name,
               pmt.payment_reference,
               SUM(pmt.payment_amount) AS payment_amount
        FROM payments pmt
        JOIN customer_deliveries d ON pmt.delivery_id = d.id
        JOIN customers c ON d.customer_id = c.id
        JOIN shipments s ON d.shipment_id = s.id
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products pr ON b.product_id = pr.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        WHERE 1=1
        {filter_sql}
        /*ACCESS_FILTER*/
        GROUP BY payment_month, pmt.payment_received_date, c.customer_name, s.invoice_no, d.delivery_invoice_no,
                 w.warehouse_name, pr.product_code, pr.product_name, pmt.payment_reference
        ORDER BY payment_month DESC, pmt.payment_received_date DESC
    """, filter_params)

else:
    st.warning("Report not configured.")
    rows = []

_show_report(rows, "report_" + report.lower().replace(" ", "_").replace("/", "_"))
render_slogan_footer()
