from common import *

def payment_access_sql():
    product_ids = current_user_allowed_product_ids()
    warehouse_ids = current_user_allowed_warehouse_ids()
    clauses = []
    params = []
    if product_ids:
        clauses.append(" AND b.product_id IN (" + ",".join(["?"] * len(product_ids)) + ") ")
        params.extend(product_ids)
    if warehouse_ids:
        clauses.append(" AND s.warehouse_id IN (" + ",".join(["?"] * len(warehouse_ids)) + ") ")
        params.extend(warehouse_ids)
    return "".join(clauses), tuple(params)

def fetch_payment_due_rows():
    access_sql, access_params = payment_access_sql()
    return fetch_all(f"""
        SELECT
            MIN(d.id) AS id,
            d.delivery_invoice_no,
            s.invoice_no AS original_invoice_no,
            s.shipment_no,
            w.warehouse_name,
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
        JOIN shipment_boxes b ON d.box_id = b.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        WHERE 1=1
        {access_sql}
        GROUP BY d.delivery_invoice_no, s.invoice_no, s.shipment_no, w.warehouse_name, c.customer_name, d.currency
        HAVING SUM(d.sale_amount) - COALESCE((
            SELECT SUM(p.payment_amount)
            FROM payments p
            JOIN customer_deliveries d2 ON p.delivery_id = d2.id
            WHERE d2.delivery_invoice_no = d.delivery_invoice_no
        ), 0) > 0
        ORDER BY payment_due_date
    """, access_params)

def fetch_payment_rows(limit=500, part_number=None, customer=None, original_invoice_no=None, delivery_invoice_no=None):
    access_sql, access_params = payment_access_sql()
    filters = []
    params = list(access_params)
    if part_number:
        filters.append(" AND LOWER(pr.product_code) LIKE ? ")
        params.append("%" + str(part_number).strip().lower() + "%")
    if customer:
        filters.append(" AND LOWER(c.customer_name) LIKE ? ")
        params.append("%" + str(customer).strip().lower() + "%")
    if original_invoice_no:
        filters.append(" AND LOWER(s.invoice_no) LIKE ? ")
        params.append("%" + str(original_invoice_no).strip().lower() + "%")
    if delivery_invoice_no:
        filters.append(" AND LOWER(d.delivery_invoice_no) LIKE ? ")
        params.append("%" + str(delivery_invoice_no).strip().lower() + "%")
    filter_sql = "".join(filters)
    return fetch_all(f"""
        SELECT
            p.id,
            p.payment_received_date,
            p.payment_amount,
            p.payment_reference,
            p.remarks,
            d.delivery_invoice_no,
            s.invoice_no AS original_invoice_no,
            s.shipment_no,
            w.warehouse_name,
            c.customer_name,
            b.product_id,
            pr.product_code,
            pr.product_name
        FROM payments p
        JOIN customer_deliveries d ON p.delivery_id = d.id
        JOIN shipments s ON d.shipment_id = s.id
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products pr ON b.product_id = pr.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        JOIN customers c ON d.customer_id = c.id
        WHERE 1=1
        {access_sql}
        {filter_sql}
        ORDER BY p.id DESC
        LIMIT {int(limit)}
    """, tuple(params))


def render_payment_subnav(active_key="payment"):
    """Show Payment subpages under the main Payment module."""
    items = [
        ("payment", "Payment Entry", "pages/5_Payment_Entry.py"),
        ("payment_due", "Payment Due", "pages/18_Payment_Due.py"),
        ("payment_edit", "Edit Payment", "pages/19_Edit_Payment.py"),
        ("payment_list", "Payment Received List", "pages/20_Payment_Received_List.py"),
    ]
    allowed_items = []
    for key, label, target in items:
        try:
            page_def = get_page_definition_by_key(key)
            if page_def and can_user_access_page(page_def):
                allowed_items.append((key, label, target))
        except Exception:
            allowed_items.append((key, label, target))
    if not allowed_items:
        return
    st.markdown("<div style='border:1px solid #d9e2ec;border-radius:14px;background:#ffffff;padding:10px 12px;margin:8px 0 16px 0;'><b style='color:#003B73;'>Payment</b></div>", unsafe_allow_html=True)
    cols = st.columns(len(allowed_items))
    for col, (key, label, target) in zip(cols, allowed_items):
        with col:
            if key == active_key:
                st.markdown(f"<div style='background:#003B73;color:white;border-radius:10px;padding:9px;text-align:center;font-weight:900;'>{label}</div>", unsafe_allow_html=True)
            else:
                st.page_link(target, label=label)
