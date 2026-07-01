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

def fetch_payment_rows(limit=500):
    access_sql, access_params = payment_access_sql()
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
        ORDER BY p.id DESC
        LIMIT {int(limit)}
    """, access_params)
