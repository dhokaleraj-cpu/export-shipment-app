from common import *

REPORTS_VERSION = "SN 26.01"

page_setup()
require_page_view("reports")
show_edit_permission_status("reports")

show_header("Reports", "SN 26.01 - Export Shipment Monitoring System")
access_notice()

# ---------------------------------------------------------------------------
# Report list requested for SN 26.00
# ---------------------------------------------------------------------------

REPORTS = [
    "Shipment List",
    "Shipment List with Part Number",
    "Shipment List with Pallet Numbers",
    "Delivery Invoice List with Original Invoice Number",
    "Delivery Invoice List against Original Invoice Number",
    "Payment Report with Original Invoice Number",
    "Payment Due Invoice List",
    "Payment Received Report",
    "Customer Wise Shipment Report",
    "Customer Wise Delivery Report",
]


def _txt(v):
    return str(v or "").strip()


def _like_clause(expr, value):
    value = _txt(value)
    if not value:
        return "", []
    return f" AND LOWER(COALESCE({expr}, '')) LIKE ? ", [f"%{value.lower()}%"]


def _date_clause(expr, from_date, to_date):
    if not from_date or not to_date:
        return "", []
    return f" AND {expr} IS NOT NULL AND {expr}::date BETWEEN ?::date AND ?::date ", [str(from_date), str(to_date)]


def _in_clause(column_name, values):
    values = [int(v) for v in (values or []) if v not in (None, "")]
    if not values:
        return "", []
    return f" AND {column_name} IN ({','.join(['?'] * len(values))}) ", values


def _access_clause(product_column="b.product_id", warehouse_column="s.warehouse_id"):
    clauses, params = [], []
    try:
        product_ids = current_user_allowed_product_ids()
    except Exception:
        product_ids = []
    try:
        warehouse_ids = current_user_allowed_warehouse_ids()
    except Exception:
        warehouse_ids = []

    if product_column and product_ids:
        c, p = _in_clause(product_column, product_ids)
        clauses.append(c)
        params.extend(p)
    if warehouse_column and warehouse_ids:
        c, p = _in_clause(warehouse_column, warehouse_ids)
        clauses.append(c)
        params.extend(p)
    return "".join(clauses), params


def _base_filters(date_expr=None, include_delivery_invoice=True):
    clauses, params = [], []
    for clause, values in [
        _like_clause("s.invoice_no", original_invoice_filter),
        _like_clause("p.product_code || ' ' || p.product_name", part_filter),
        _like_clause("c.customer_name || ' ' || COALESCE(w.warehouse_name,'')", customer_filter),
    ]:
        clauses.append(clause)
        params.extend(values)

    if include_delivery_invoice:
        clause, values = _like_clause("d.delivery_invoice_no", delivery_invoice_filter)
        clauses.append(clause)
        params.extend(values)

    if date_expr:
        clause, values = _date_clause(date_expr, from_date, to_date)
        clauses.append(clause)
        params.extend(values)

    return "".join(clauses), params


def _shipment_filters(date_expr="s.shipment_date"):
    clauses, params = [], []
    for clause, values in [
        _like_clause("s.invoice_no", original_invoice_filter),
        _like_clause("p.product_code || ' ' || p.product_name", part_filter),
        _like_clause("c.customer_name || ' ' || COALESCE(w.warehouse_name,'')", customer_filter),
        _date_clause(date_expr, from_date, to_date),
    ]:
        clauses.append(clause)
        params.extend(values)
    return "".join(clauses), params


def _run_query(sql, params=None, product_column="b.product_id", warehouse_column="s.warehouse_id"):
    access_sql, access_params = _access_clause(product_column, warehouse_column)
    sql = sql.replace("/*ACCESS_FILTER*/", access_sql)
    final_params = tuple(params or ()) + tuple(access_params)
    if " limit " not in sql.lower():
        sql = sql.rstrip().rstrip(";") + f"\n LIMIT {int(row_limit)}"
    return fetch_all(sql, final_params)


def _format_df(rows):
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(format_date_columns(rows))


def _numeric_sum(series):
    try:
        return pd.to_numeric(series, errors="coerce").fillna(0).sum()
    except Exception:
        return 0


def _add_total_footer(df):
    if df.empty:
        return df
    total_row = {col: "" for col in df.columns}
    total_row[df.columns[0]] = "TOTAL"

    total_keywords = ["qty", "quantity", "amount", "sale", "value", "paid", "pending", "balance"]
    for col in df.columns:
        col_l = str(col).lower()
        if any(k in col_l for k in total_keywords):
            total_row[col] = _numeric_sum(df[col])

    # Count unique pallet numbers if present.
    for col in df.columns:
        if "pallet" in str(col).lower():
            try:
                total_row[col] = f"Count: {df[col].dropna().astype(str).replace('', pd.NA).dropna().nunique()}"
            except Exception:
                pass

    return pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)


def _safe_number(v):
    try:
        return f"{float(v):,.2f}"
    except Exception:
        return str(v or "")


def _period_text():
    return f"{format_date_ddmmyyyy(from_date)} to {format_date_ddmmyyyy(to_date)}"


def _report_header_html(title):
    logo_html = ""
    try:
        if LOGO_PATH.exists():
            logo_b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode("utf-8")
            logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height:54px;max-width:280px;object-fit:contain;">'
    except Exception:
        logo_html = ""

    return f"""
    <div style="width:100%;box-sizing:border-box;border:1px solid #CBD5E1;border-radius:12px;padding:12px 16px;margin:10px 0 12px 0;background:white;display:grid;grid-template-columns:1.2fr 2.2fr 1.2fr;align-items:center;gap:12px;box-shadow:0 2px 8px rgba(15,23,42,.06);">
        <div style="text-align:left;">{logo_html}</div>
        <div style="text-align:center;font-size:24px;font-weight:900;color:#003B73;line-height:1.15;">{title}</div>
        <div style="text-align:right;font-size:14px;font-weight:900;color:#334155;line-height:1.35;">Report Period<br>{_period_text()}</div>
    </div>
    """

def _report_footer_html(df):
    if df.empty:
        return ""
    amount_total = 0
    qty_total = 0
    pallet_count = ""
    for col in df.columns:
        cl = str(col).lower()
        if "amount" in cl or "sale" in cl or "value" in cl or "pending" in cl or "paid" in cl:
            amount_total += _numeric_sum(df[col])
        if "qty" in cl or "quantity" in cl:
            qty_total += _numeric_sum(df[col])
        if "pallet" in cl:
            try:
                pallet_count = str(df[col].dropna().astype(str).replace("", pd.NA).dropna().nunique())
            except Exception:
                pallet_count = ""

    return f"""
    <div style="width:100%;box-sizing:border-box;border:1px solid #003B73;border-radius:12px;background:#EAF3FC;padding:0;margin:12px 0 14px 0;overflow:hidden;box-shadow:0 2px 8px rgba(15,23,42,.08);">
        <div style="background:#003B73;color:white;font-size:16px;font-weight:900;padding:8px 12px;text-transform:uppercase;letter-spacing:.3px;">Report Footer Totals</div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0;text-align:center;">
            <div style="padding:12px;border-right:1px solid #BFD7F0;">
                <div style="font-size:13px;font-weight:900;color:#003B73;text-transform:uppercase;">Total Qty</div>
                <div style="font-size:20px;font-weight:900;color:#111827;">{_safe_number(qty_total)}</div>
            </div>
            <div style="padding:12px;border-right:1px solid #BFD7F0;">
                <div style="font-size:13px;font-weight:900;color:#003B73;text-transform:uppercase;">Total Amount</div>
                <div style="font-size:20px;font-weight:900;color:#111827;">{_safe_number(amount_total)}</div>
            </div>
            <div style="padding:12px;">
                <div style="font-size:13px;font-weight:900;color:#003B73;text-transform:uppercase;">Pallet Count</div>
                <div style="font-size:20px;font-weight:900;color:#111827;">{pallet_count}</div>
            </div>
        </div>
    </div>
    """

def _excel_bytes(df, title):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        startrow = 4
        df.to_excel(writer, index=False, sheet_name="Report", startrow=startrow)
        ws = writer.sheets["Report"]
        ws["A1"] = title
        ws["A2"] = f"Report Period: {_period_text()}"
        ws["A3"] = ""
        # Basic column sizing
        for column_cells in ws.columns:
            try:
                length = max(len(str(cell.value or "")) for cell in column_cells)
                ws.column_dimensions[column_cells[0].column_letter].width = min(max(length + 2, 12), 34)
            except Exception:
                pass
    return output.getvalue()


def _pdf_bytes(df, title):
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4), leftMargin=18, rightMargin=18, topMargin=18, bottomMargin=18)
    styles = getSampleStyleSheet()
    story = []

    logo = None
    try:
        if LOGO_PATH.exists():
            logo = Image(str(LOGO_PATH), width=150, height=42)
    except Exception:
        logo = Paragraph("FSI", styles["Normal"])

    header_data = [[
        logo or Paragraph("FSI", styles["Normal"]),
        Paragraph(f"<b>{title}</b>", styles["Title"]),
        Paragraph(f"<b>Report Period</b><br/>{_period_text()}", styles["Normal"]),
    ]]
    header = Table(header_data, colWidths=[210, 390, 170])
    header.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (1,0), (1,0), "CENTER"),
        ("ALIGN", (2,0), (2,0), "RIGHT"),
        ("BACKGROUND", (0,0), (-1,-1), colors.white),
    ]))
    story.append(header)
    story.append(Spacer(1, 10))

    pdf_df = _add_total_footer(df.copy())
    # Keep PDF width manageable
    data = [list(pdf_df.columns)] + pdf_df.astype(str).values.tolist()
    col_count = max(len(pdf_df.columns), 1)
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#003B73")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 6),
        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#EAF3FC")),
        ("TEXTCOLOR", (0,-1), (-1,-1), colors.HexColor("#003B73")),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
    ]))
    story.append(table)
    doc.build(story)
    return output.getvalue()


def _display_report(rows, title):
    df = _format_df(rows)
    st.markdown(_report_header_html(title), unsafe_allow_html=True)

    if df.empty:
        st.info("No records found for selected filters.")
        return

    st.markdown(_report_footer_html(df), unsafe_allow_html=True)
    st.dataframe(_add_total_footer(df), width="stretch", hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "Export Excel",
            data=_excel_bytes(df, title),
            file_name=f"{title.replace(' ', '_').lower()}_{date.today().isoformat()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
    with c2:
        st.download_button(
            "Export PDF",
            data=_pdf_bytes(df, title),
            file_name=f"{title.replace(' ', '_').lower()}_{date.today().isoformat()}.pdf",
            mime="application/pdf",
            width="stretch",
        )


def get_report_rows(report_name):
    if report_name == "Shipment List":
        fsql, params = _shipment_filters("s.shipment_date")
        return _run_query(f"""
            SELECT
                s.shipment_no,
                s.shipment_date,
                s.bl_number,
                w.warehouse_name,
                c.customer_name,
                s.invoice_no AS original_invoice_no,
                SUM(b.amount) AS amount
            FROM shipments s
            JOIN shipment_boxes b ON b.shipment_id = s.id
            JOIN products p ON p.id = b.product_id
            LEFT JOIN warehouses w ON w.id = s.warehouse_id
            LEFT JOIN customers c ON c.id = s.customer_id
            WHERE 1=1
            {fsql}
            /*ACCESS_FILTER*/
            GROUP BY s.shipment_no, s.shipment_date, s.bl_number, w.warehouse_name, c.customer_name, s.invoice_no
            ORDER BY s.shipment_date DESC, s.shipment_no
        """, params)

    if report_name == "Shipment List with Part Number":
        fsql, params = _shipment_filters("s.shipment_date")
        return _run_query(f"""
            SELECT
                s.shipment_no,
                s.shipment_date,
                s.invoice_no AS original_invoice_no,
                p.product_code,
                p.product_name,
                SUM(b.original_qty) AS qty,
                SUM(b.amount) AS amount
            FROM shipments s
            JOIN shipment_boxes b ON b.shipment_id = s.id
            JOIN products p ON p.id = b.product_id
            LEFT JOIN warehouses w ON w.id = s.warehouse_id
            LEFT JOIN customers c ON c.id = s.customer_id
            WHERE 1=1
            {fsql}
            /*ACCESS_FILTER*/
            GROUP BY s.shipment_no, s.shipment_date, s.invoice_no, p.product_code, p.product_name
            ORDER BY s.shipment_date DESC, s.shipment_no, p.product_code
        """, params)

    if report_name == "Shipment List with Pallet Numbers":
        fsql, params = _shipment_filters("s.shipment_date")
        return _run_query(f"""
            SELECT
                s.shipment_no,
                s.shipment_date,
                s.invoice_no AS original_invoice_no,
                b.pallet_no,
                b.box_no,
                p.product_code,
                p.product_name,
                b.original_qty AS qty
            FROM shipments s
            JOIN shipment_boxes b ON b.shipment_id = s.id
            JOIN products p ON p.id = b.product_id
            LEFT JOIN warehouses w ON w.id = s.warehouse_id
            LEFT JOIN customers c ON c.id = s.customer_id
            WHERE 1=1
            {fsql}
            /*ACCESS_FILTER*/
            ORDER BY s.shipment_date DESC, s.shipment_no, b.pallet_no, b.box_no
        """, params)

    if report_name == "Delivery Invoice List with Original Invoice Number":
        fsql, params = _base_filters("d.delivery_date")
        return _run_query(f"""
            SELECT
                d.delivery_invoice_no,
                d.delivery_date,
                s.invoice_no AS original_invoice_no,
                p.product_code,
                p.product_name,
                b.pallet_no,
                b.box_no,
                SUM(d.delivered_qty) AS qty,
                AVG(d.unit_price) AS price,
                SUM(d.sale_amount) AS amount
            FROM customer_deliveries d
            JOIN shipment_boxes b ON b.id = d.box_id
            JOIN shipments s ON s.id = d.shipment_id
            JOIN products p ON p.id = b.product_id
            LEFT JOIN warehouses w ON w.id = s.warehouse_id
            LEFT JOIN customers c ON c.id = d.customer_id
            WHERE 1=1
            {fsql}
            /*ACCESS_FILTER*/
            GROUP BY d.delivery_invoice_no, d.delivery_date, s.invoice_no, p.product_code, p.product_name, b.pallet_no, b.box_no
            ORDER BY d.delivery_date DESC, d.delivery_invoice_no
        """, params)

    if report_name == "Delivery Invoice List against Original Invoice Number":
        fsql, params = _base_filters("d.delivery_date")
        return _run_query(f"""
            SELECT
                s.invoice_no AS original_invoice_no,
                d.delivery_invoice_no,
                d.delivery_date,
                c.customer_name,
                p.product_code,
                p.product_name,
                SUM(d.delivered_qty) AS qty,
                SUM(d.sale_amount) AS amount
            FROM customer_deliveries d
            JOIN shipment_boxes b ON b.id = d.box_id
            JOIN shipments s ON s.id = d.shipment_id
            JOIN products p ON p.id = b.product_id
            LEFT JOIN warehouses w ON w.id = s.warehouse_id
            LEFT JOIN customers c ON c.id = d.customer_id
            WHERE 1=1
            {fsql}
            /*ACCESS_FILTER*/
            GROUP BY s.invoice_no, d.delivery_invoice_no, d.delivery_date, c.customer_name, p.product_code, p.product_name
            ORDER BY s.invoice_no, d.delivery_date DESC, d.delivery_invoice_no
        """, params)

    if report_name == "Payment Report with Original Invoice Number":
        fsql, params = _base_filters("COALESCE(pay.payment_received_date, d.payment_due_date)")
        return _run_query(f"""
            SELECT
                s.invoice_no AS original_invoice_no,
                d.delivery_invoice_no,
                c.customer_name,
                p.product_code,
                p.product_name,
                d.payment_due_date,
                SUM(d.sale_amount) AS invoice_amount,
                COALESCE(SUM(pay.payment_amount),0) AS paid_amount,
                SUM(d.sale_amount) - COALESCE(SUM(pay.payment_amount),0) AS pending_amount
            FROM customer_deliveries d
            JOIN shipment_boxes b ON b.id = d.box_id
            JOIN shipments s ON s.id = d.shipment_id
            JOIN products p ON p.id = b.product_id
            LEFT JOIN warehouses w ON w.id = s.warehouse_id
            LEFT JOIN customers c ON c.id = d.customer_id
            LEFT JOIN payments pay ON pay.delivery_id = d.id
            WHERE 1=1
            {fsql}
            /*ACCESS_FILTER*/
            GROUP BY s.invoice_no, d.delivery_invoice_no, c.customer_name, p.product_code, p.product_name, d.payment_due_date
            ORDER BY d.payment_due_date, s.invoice_no, d.delivery_invoice_no
        """, params)

    if report_name == "Payment Due Invoice List":
        fsql, params = _base_filters("d.payment_due_date")
        return _run_query(f"""
            SELECT
                s.invoice_no AS original_invoice_no,
                d.delivery_invoice_no,
                c.customer_name,
                d.delivery_date,
                d.payment_due_date,
                SUM(d.sale_amount) AS invoice_amount,
                COALESCE(SUM(pay.payment_amount),0) AS paid_amount,
                SUM(d.sale_amount) - COALESCE(SUM(pay.payment_amount),0) AS pending_amount,
                CASE
                    WHEN SUM(d.sale_amount) - COALESCE(SUM(pay.payment_amount),0) <= 0 THEN 'Paid'
                    WHEN MAX(d.payment_due_date)::date < CURRENT_DATE THEN 'Overdue'
                    ELSE 'Pending'
                END AS payment_status
            FROM customer_deliveries d
            JOIN shipment_boxes b ON b.id = d.box_id
            JOIN shipments s ON s.id = d.shipment_id
            JOIN products p ON p.id = b.product_id
            LEFT JOIN warehouses w ON w.id = s.warehouse_id
            LEFT JOIN customers c ON c.id = d.customer_id
            LEFT JOIN payments pay ON pay.delivery_id = d.id
            WHERE 1=1
            {fsql}
            /*ACCESS_FILTER*/
            GROUP BY s.invoice_no, d.delivery_invoice_no, c.customer_name, d.delivery_date, d.payment_due_date
            HAVING SUM(d.sale_amount) - COALESCE(SUM(pay.payment_amount),0) > 0
            ORDER BY d.payment_due_date, d.delivery_invoice_no
        """, params)

    if report_name == "Payment Received Report":
        fsql, params = _base_filters("pay.payment_received_date")
        return _run_query(f"""
            SELECT
                pay.payment_received_date,
                pay.payment_reference,
                s.invoice_no AS original_invoice_no,
                d.delivery_invoice_no,
                c.customer_name,
                p.product_code,
                p.product_name,
                SUM(pay.payment_amount) AS payment_received_amount
            FROM payments pay
            JOIN customer_deliveries d ON d.id = pay.delivery_id
            JOIN shipment_boxes b ON b.id = d.box_id
            JOIN shipments s ON s.id = d.shipment_id
            JOIN products p ON p.id = b.product_id
            LEFT JOIN warehouses w ON w.id = s.warehouse_id
            LEFT JOIN customers c ON c.id = d.customer_id
            WHERE 1=1
            {fsql}
            /*ACCESS_FILTER*/
            GROUP BY pay.payment_received_date, pay.payment_reference, s.invoice_no, d.delivery_invoice_no, c.customer_name, p.product_code, p.product_name
            ORDER BY pay.payment_received_date DESC, pay.payment_reference
        """, params)

    if report_name == "Customer Wise Shipment Report":
        fsql, params = _shipment_filters("s.shipment_date")
        return _run_query(f"""
            SELECT
                c.customer_name,
                w.warehouse_name,
                s.shipment_no,
                s.shipment_date,
                s.invoice_no AS original_invoice_no,
                p.product_code,
                p.product_name,
                SUM(b.original_qty) AS qty,
                SUM(b.amount) AS amount
            FROM shipments s
            JOIN shipment_boxes b ON b.shipment_id = s.id
            JOIN products p ON p.id = b.product_id
            LEFT JOIN warehouses w ON w.id = s.warehouse_id
            LEFT JOIN customers c ON c.id = s.customer_id
            WHERE 1=1
            {fsql}
            /*ACCESS_FILTER*/
            GROUP BY c.customer_name, w.warehouse_name, s.shipment_no, s.shipment_date, s.invoice_no, p.product_code, p.product_name
            ORDER BY c.customer_name, s.shipment_date DESC, s.shipment_no
        """, params)

    if report_name == "Customer Wise Delivery Report":
        fsql, params = _base_filters("d.delivery_date")
        return _run_query(f"""
            SELECT
                c.customer_name,
                d.delivery_invoice_no,
                d.delivery_date,
                s.invoice_no AS original_invoice_no,
                p.product_code,
                p.product_name,
                SUM(d.delivered_qty) AS qty,
                SUM(d.sale_amount) AS amount
            FROM customer_deliveries d
            JOIN shipment_boxes b ON b.id = d.box_id
            JOIN shipments s ON s.id = d.shipment_id
            JOIN products p ON p.id = b.product_id
            LEFT JOIN warehouses w ON w.id = s.warehouse_id
            LEFT JOIN customers c ON c.id = d.customer_id
            WHERE 1=1
            {fsql}
            /*ACCESS_FILTER*/
            GROUP BY c.customer_name, d.delivery_invoice_no, d.delivery_date, s.invoice_no, p.product_code, p.product_name
            ORDER BY c.customer_name, d.delivery_date DESC, d.delivery_invoice_no
        """, params)

    return []


st.markdown(
    """
    <div class="sap-grid-card">
        <div class="sap-grid-card-title">REPORT FILTERS - SN 26.00</div>
    """,
    unsafe_allow_html=True,
)

r1, r2, r3 = st.columns([2, 1, 1])
with r1:
    selected_report = searchable_selectbox("Select Report", REPORTS, key="sn26_report_select")
with r2:
    from_date = st.date_input("From Date", value=date(date.today().year, 1, 1), key="sn26_from_date")
with r3:
    to_date = st.date_input("To Date", value=date.today(), key="sn26_to_date")

f1, f2, f3, f4, f5 = st.columns([1.2, 1.2, 1.2, 1.2, .8])
with f1:
    original_invoice_filter = st.text_input("Original Invoice Number", key="sn26_original_invoice_filter")
with f2:
    part_filter = st.text_input("Part Number", key="sn26_part_filter")
with f3:
    customer_filter = st.text_input("Customer", key="sn26_customer_filter")
with f4:
    delivery_invoice_filter = st.text_input("Delivery Invoice Number", key="sn26_delivery_invoice_filter")
with f5:
    row_limit = st.selectbox("Max Rows", [100, 250, 500, 1000, 2000, 5000], index=2, key="sn26_row_limit")

generate = st.button("GENERATE REPORT", type="primary", width="stretch", key="sn26_generate_report")
st.markdown("</div>", unsafe_allow_html=True)

if from_date > to_date:
    st.warning("From Date is after To Date. Dates were swapped.")
    from_date, to_date = to_date, from_date

if not generate:
    st.info("Select report and filters, then click GENERATE REPORT.")
    render_slogan_footer()
    st.stop()

try:
    rows = get_report_rows(selected_report)
    _display_report(rows, selected_report)
except Exception as exc:
    st.error(f"Report could not load: {exc}")
    st.exception(exc)

render_slogan_footer()
