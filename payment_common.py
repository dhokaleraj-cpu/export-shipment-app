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
    """Pending payment rows, one row per complete Delivery Invoice."""
    access_sql, access_params = payment_access_sql()
    return fetch_all(f"""
        WITH visible_invoices AS (
            SELECT DISTINCT d.delivery_invoice_no
            FROM customer_deliveries d
            JOIN shipments s ON d.shipment_id=s.id
            JOIN shipment_boxes b ON d.box_id=b.id
            WHERE COALESCE(d.delivery_invoice_no,'') <> ''
            {access_sql}
        ),
        invoice_lines AS (
            SELECT
                d.id,
                d.delivery_invoice_no,
                s.invoice_no AS original_invoice_no,
                s.shipment_no,
                w.warehouse_name,
                c.customer_name,
                d.currency,
                d.payment_due_date,
                d.sale_amount
            FROM customer_deliveries d
            JOIN customers c ON d.customer_id = c.id
            JOIN shipments s ON d.shipment_id = s.id
            JOIN shipment_boxes b ON d.box_id = b.id
            LEFT JOIN warehouses w ON s.warehouse_id = w.id
            JOIN visible_invoices v ON v.delivery_invoice_no=d.delivery_invoice_no
        ),
        invoice_totals AS (
            SELECT
                MIN(id) AS id,
                delivery_invoice_no,
                STRING_AGG(DISTINCT original_invoice_no, ', ' ORDER BY original_invoice_no) AS original_invoice_no,
                STRING_AGG(DISTINCT shipment_no, ', ' ORDER BY shipment_no) AS shipment_no,
                STRING_AGG(DISTINCT warehouse_name, ', ' ORDER BY warehouse_name) AS warehouse_name,
                MAX(customer_name) AS customer_name,
                MAX(currency) AS currency,
                MAX(payment_due_date) AS payment_due_date,
                SUM(COALESCE(sale_amount, 0)) AS total_invoice_amount
            FROM invoice_lines
            GROUP BY delivery_invoice_no
        ),
        payment_totals AS (
            SELECT
                anchor.delivery_invoice_no,
                SUM(COALESCE(p.payment_amount, 0)) AS paid_amount
            FROM payments p
            JOIN customer_deliveries anchor ON anchor.id = p.delivery_id
            WHERE COALESCE(anchor.delivery_invoice_no, '') <> ''
            GROUP BY anchor.delivery_invoice_no
        )
        SELECT
            i.id,
            i.delivery_invoice_no,
            i.original_invoice_no,
            i.shipment_no,
            i.warehouse_name,
            i.customer_name,
            i.currency,
            i.payment_due_date,
            i.total_invoice_amount,
            COALESCE(p.paid_amount, 0) AS paid_amount,
            GREATEST(i.total_invoice_amount - COALESCE(p.paid_amount, 0), 0) AS pending_amount
        FROM invoice_totals i
        LEFT JOIN payment_totals p ON p.delivery_invoice_no = i.delivery_invoice_no
        WHERE i.total_invoice_amount - COALESCE(p.paid_amount, 0) > 0.0005
        ORDER BY i.payment_due_date NULLS LAST, i.delivery_invoice_no
    """, access_params)


def fetch_payment_line_rows(delivery_invoice_no, exclude_payment_id=0):
    """Return selectable Original-Invoice/Product lines with true line balances.

    SN 27.17 explicit allocations are respected exactly. Older receipts without
    allocation rows remain untouched and are treated as legacy FIFO allocations
    only against the remaining line capacity.
    """
    invoice_no = str(delivery_invoice_no or "").strip()
    if not invoice_no:
        return []
    exclude_id = int(exclude_payment_id or 0)
    return fetch_all("""
        WITH line_groups AS (
            SELECT
                MIN(d.id) AS anchor_delivery_id,
                d.delivery_invoice_no,
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
            WHERE d.delivery_invoice_no=?
            GROUP BY d.delivery_invoice_no, s.invoice_no, b.product_id, p.product_code, p.product_name, COALESCE(d.unit_price,0)
        ),
        explicit_paid AS (
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
            WHERE d.delivery_invoice_no=? AND pay.id<>?
            GROUP BY s.invoice_no, b.product_id, COALESCE(d.unit_price,0)
        ),
        legacy_total AS (
            SELECT COALESCE(SUM(pay.payment_amount),0) AS legacy_paid
            FROM payments pay
            JOIN customer_deliveries anchor ON anchor.id=pay.delivery_id
            WHERE anchor.delivery_invoice_no=?
              AND pay.id<>?
              AND NOT EXISTS (SELECT 1 FROM payment_allocations pa WHERE pa.payment_id=pay.id)
        ),
        remaining AS (
            SELECT
                lg.*,
                COALESCE(ep.explicit_paid,0) AS explicit_paid,
                GREATEST(lg.invoice_amount-COALESCE(ep.explicit_paid,0),0) AS remaining_capacity,
                COALESCE(lt.legacy_paid,0) AS legacy_paid
            FROM line_groups lg
            LEFT JOIN explicit_paid ep
              ON ep.original_invoice_no=lg.original_invoice_no
             AND ep.product_id=lg.product_id
             AND ep.unit_price=lg.unit_price
            CROSS JOIN legacy_total lt
        ),
        running AS (
            SELECT
                r.*,
                COALESCE(
                    SUM(r.remaining_capacity) OVER (
                        ORDER BY r.anchor_delivery_id, r.original_invoice_no, r.product_code
                        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                    ),0
                ) AS prior_remaining_capacity
            FROM remaining r
        ),
        allocated AS (
            SELECT
                x.*,
                GREATEST(
                    LEAST(x.remaining_capacity, x.legacy_paid-x.prior_remaining_capacity),
                    0
                ) AS legacy_allocated
            FROM running x
        )
        SELECT
            anchor_delivery_id,
            delivery_invoice_no,
            original_invoice_no,
            product_id,
            product_code,
            product_name,
            unit_price,
            currency,
            delivered_qty,
            invoice_amount,
            LEAST(invoice_amount, explicit_paid+legacy_allocated) AS paid_amount,
            GREATEST(invoice_amount-(explicit_paid+legacy_allocated),0) AS pending_amount,
            explicit_paid AS explicit_paid_amount,
            legacy_allocated AS legacy_paid_amount
        FROM allocated
        ORDER BY anchor_delivery_id, original_invoice_no, product_code
    """, (invoice_no, invoice_no, exclude_id, invoice_no, exclude_id))


def fetch_payment_allocations(payment_id):
    """Existing explicit allocation rows for one receipt, grouped exactly like the UI lines."""
    return fetch_all("""
        WITH allocation_groups AS (
            SELECT
                d.delivery_invoice_no,
                s.invoice_no AS original_invoice_no,
                b.product_id,
                COALESCE(d.unit_price,0) AS unit_price,
                SUM(COALESCE(pa.allocated_amount,0)) AS allocated_amount
            FROM payment_allocations pa
            JOIN customer_deliveries d ON d.id=pa.delivery_id
            JOIN shipments s ON s.id=d.shipment_id
            JOIN shipment_boxes b ON b.id=d.box_id
            WHERE pa.payment_id=?
            GROUP BY d.delivery_invoice_no, s.invoice_no, b.product_id, COALESCE(d.unit_price,0)
        ),
        line_groups AS (
            SELECT
                MIN(d.id) AS anchor_delivery_id,
                d.delivery_invoice_no,
                s.invoice_no AS original_invoice_no,
                b.product_id,
                p.product_code,
                p.product_name,
                COALESCE(d.unit_price,0) AS unit_price
            FROM customer_deliveries d
            JOIN shipments s ON s.id=d.shipment_id
            JOIN shipment_boxes b ON b.id=d.box_id
            JOIN products p ON p.id=b.product_id
            GROUP BY d.delivery_invoice_no, s.invoice_no, b.product_id, p.product_code, p.product_name, COALESCE(d.unit_price,0)
        )
        SELECT
            lg.anchor_delivery_id,
            lg.original_invoice_no,
            lg.product_id,
            lg.product_code,
            lg.product_name,
            lg.unit_price,
            ag.allocated_amount
        FROM allocation_groups ag
        JOIN line_groups lg
          ON lg.delivery_invoice_no=ag.delivery_invoice_no
         AND lg.original_invoice_no=ag.original_invoice_no
         AND lg.product_id=ag.product_id
         AND lg.unit_price=ag.unit_price
        ORDER BY lg.anchor_delivery_id
    """, (int(payment_id),))


def fetch_payment_rows(limit=500, part_number=None, customer=None, original_invoice_no=None, delivery_invoice_no=None):
    """Return receipt headers with complete Delivery-Invoice and line-allocation context."""
    access_sql, access_params = payment_access_sql()
    filters = []
    params = list(access_params)
    if part_number:
        filters.append(" AND LOWER(COALESCE(inv.product_code,'')) LIKE ? ")
        params.append("%" + str(part_number).strip().lower() + "%")
    if customer:
        filters.append(" AND LOWER(COALESCE(inv.customer_name,'')) LIKE ? ")
        params.append("%" + str(customer).strip().lower() + "%")
    if original_invoice_no:
        filters.append(" AND LOWER(COALESCE(inv.original_invoice_no,'')) LIKE ? ")
        params.append("%" + str(original_invoice_no).strip().lower() + "%")
    if delivery_invoice_no:
        filters.append(" AND LOWER(COALESCE(inv.delivery_invoice_no,'')) LIKE ? ")
        params.append("%" + str(delivery_invoice_no).strip().lower() + "%")
    filter_sql = "".join(filters)

    return fetch_all(f"""
        WITH visible_invoices AS (
            SELECT DISTINCT d.delivery_invoice_no
            FROM customer_deliveries d
            JOIN shipments s ON d.shipment_id=s.id
            JOIN shipment_boxes b ON d.box_id=b.id
            WHERE COALESCE(d.delivery_invoice_no,'') <> ''
            {access_sql}
        ),
        invoice_lines AS (
            SELECT
                d.id,
                d.delivery_invoice_no,
                s.invoice_no AS original_invoice_no,
                s.shipment_no,
                w.warehouse_name,
                c.customer_name,
                b.product_id,
                pr.product_code,
                pr.product_name,
                d.sale_amount
            FROM customer_deliveries d
            JOIN shipments s ON d.shipment_id = s.id
            JOIN shipment_boxes b ON d.box_id = b.id
            JOIN products pr ON b.product_id = pr.id
            LEFT JOIN warehouses w ON s.warehouse_id = w.id
            JOIN customers c ON d.customer_id = c.id
            JOIN visible_invoices v ON v.delivery_invoice_no=d.delivery_invoice_no
        ),
        invoice_summary AS (
            SELECT
                delivery_invoice_no,
                STRING_AGG(DISTINCT original_invoice_no, ', ' ORDER BY original_invoice_no) AS original_invoice_no,
                STRING_AGG(DISTINCT shipment_no, ', ' ORDER BY shipment_no) AS shipment_no,
                STRING_AGG(DISTINCT warehouse_name, ', ' ORDER BY warehouse_name) AS warehouse_name,
                MAX(customer_name) AS customer_name,
                MIN(product_id) AS product_id,
                STRING_AGG(DISTINCT product_code, ', ' ORDER BY product_code) AS product_code,
                STRING_AGG(DISTINCT product_name, ', ' ORDER BY product_name) AS product_name,
                SUM(COALESCE(sale_amount,0)) AS total_invoice_amount
            FROM invoice_lines
            GROUP BY delivery_invoice_no
        ),
        payment_base AS (
            SELECT
                p.id,
                p.payment_received_date,
                p.payment_amount,
                p.payment_reference,
                p.remarks,
                p.attachment_path,
                anchor.delivery_invoice_no
            FROM payments p
            JOIN customer_deliveries anchor ON anchor.id = p.delivery_id
        ),
        payment_totals AS (
            SELECT delivery_invoice_no, SUM(COALESCE(payment_amount,0)) AS invoice_paid_amount
            FROM payment_base
            GROUP BY delivery_invoice_no
        ),
        allocation_summary AS (
            SELECT
                pa.payment_id,
                SUM(COALESCE(pa.allocated_amount,0)) AS allocated_total,
                COUNT(*) AS allocation_count,
                STRING_AGG(
                    DISTINCT s.invoice_no || ' / ' || pr.product_code || ': ' || TO_CHAR(pa.allocated_amount, 'FM9999999990.000'),
                    ', ' ORDER BY s.invoice_no || ' / ' || pr.product_code || ': ' || TO_CHAR(pa.allocated_amount, 'FM9999999990.000')
                ) AS allocation_summary
            FROM payment_allocations pa
            JOIN customer_deliveries d ON d.id=pa.delivery_id
            JOIN shipments s ON s.id=d.shipment_id
            JOIN shipment_boxes b ON b.id=d.box_id
            JOIN products pr ON pr.id=b.product_id
            GROUP BY pa.payment_id
        )
        SELECT
            pay.id,
            pay.payment_received_date,
            pay.payment_amount,
            pay.payment_reference,
            pay.remarks,
            pay.attachment_path,
            inv.delivery_invoice_no,
            inv.original_invoice_no,
            inv.shipment_no,
            inv.warehouse_name,
            inv.customer_name,
            inv.product_id,
            inv.product_code,
            inv.product_name,
            inv.total_invoice_amount,
            COALESCE(t.invoice_paid_amount,0) AS invoice_paid_amount,
            GREATEST(inv.total_invoice_amount - COALESCE(t.invoice_paid_amount,0),0) AS invoice_pending_amount,
            GREATEST(inv.total_invoice_amount - (COALESCE(t.invoice_paid_amount,0) - COALESCE(pay.payment_amount,0)),0) AS max_edit_amount,
            CASE WHEN COALESCE(a.allocation_count,0)>0 THEN 'Line Allocated' ELSE 'Legacy / Auto' END AS allocation_mode,
            COALESCE(a.allocation_count,0) AS allocation_count,
            COALESCE(a.allocated_total,0) AS allocated_total,
            COALESCE(a.allocation_summary,'') AS allocation_summary
        FROM payment_base pay
        JOIN invoice_summary inv ON inv.delivery_invoice_no = pay.delivery_invoice_no
        LEFT JOIN payment_totals t ON t.delivery_invoice_no = pay.delivery_invoice_no
        LEFT JOIN allocation_summary a ON a.payment_id=pay.id
        WHERE 1=1
        {filter_sql}
        ORDER BY pay.id DESC
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
