from common import *

page_setup()

require_page_view('payment')
show_edit_permission_status('payment')

show_header('Payment Entry')
access_notice()
render_payment_subnav('payment')

can_add_payment = current_user_can_add('payment')
if can_add_payment:
    st.caption('Payment Add permission: Enabled for this user.')
else:
    st.caption('Payment Add permission: Disabled. User can view pending invoices but cannot save new payment entries.')


# Fast pending-payment lookup indexes. Non-destructive and safe to run repeatedly.
for _idx_sql in [
    "CREATE INDEX IF NOT EXISTS idx_payments_delivery_id ON payments(delivery_id)",
    "CREATE INDEX IF NOT EXISTS idx_customer_deliveries_invoice_no ON customer_deliveries(delivery_invoice_no)",
    "CREATE INDEX IF NOT EXISTS idx_customer_deliveries_box_id ON customer_deliveries(box_id)",
    "CREATE INDEX IF NOT EXISTS idx_customer_deliveries_shipment_id ON customer_deliveries(shipment_id)",
    "CREATE INDEX IF NOT EXISTS idx_customer_deliveries_due_date ON customer_deliveries(payment_due_date)",
    "CREATE INDEX IF NOT EXISTS idx_shipment_boxes_product_id ON shipment_boxes(product_id)",
    "CREATE INDEX IF NOT EXISTS idx_shipments_warehouse_id ON shipments(warehouse_id)",
    "CREATE INDEX IF NOT EXISTS idx_shipments_invoice_no ON shipments(invoice_no)",
]:
    try:
        execute_query(_idx_sql)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Fast Pending Delivery Invoice query
# ---------------------------------------------------------------------------
# Search is applied inside SQL and only unpaid/pending invoices are returned.
# Default limit avoids loading all invoices. Paid invoices are excluded by HAVING pending_amount > 0.

st.markdown('<div class="input-section-title">Search Pending Delivery Invoice</div>', unsafe_allow_html=True)
pending_invoice_search = st.text_input(
    "Search by Original Invoice / Delivery Invoice / Customer / Shipment",
    key="payment_pending_invoice_search",
    placeholder="Type invoice number, delivery invoice, customer or shipment number"
).strip()

limit_col1, limit_col2 = st.columns([1, 4])
with limit_col1:
    pending_limit = st.selectbox(
        "Max Pending Rows",
        [50, 100, 200, 500],
        index=1,
        key="payment_pending_invoice_limit"
    )

payment_product_ids = current_user_allowed_product_ids()
payment_warehouse_ids = current_user_allowed_warehouse_ids()
payment_access_clauses = []
payment_access_params = []
if payment_product_ids:
    payment_access_clauses.append(" AND b.product_id IN (" + ",".join(["?"] * len(payment_product_ids)) + ") ")
    payment_access_params.extend(payment_product_ids)
if payment_warehouse_ids:
    payment_access_clauses.append(" AND s.warehouse_id IN (" + ",".join(["?"] * len(payment_warehouse_ids)) + ") ")
    payment_access_params.extend(payment_warehouse_ids)
payment_access_sql = "".join(payment_access_clauses)

search_sql = ""
search_params = []
if pending_invoice_search:
    search_sql = """
        AND (
            LOWER(COALESCE(base.delivery_invoice_no,'')) LIKE ?
            OR LOWER(COALESCE(base.original_invoice_no,'')) LIKE ?
            OR LOWER(COALESCE(base.customer_name,'')) LIKE ?
            OR LOWER(COALESCE(base.shipment_no,'')) LIKE ?
            OR LOWER(COALESCE(base.warehouse_name,'')) LIKE ?
        )
    """
    like_value = "%" + pending_invoice_search.lower() + "%"
    search_params = [like_value, like_value, like_value, like_value, like_value]

deliveries = fetch_all(f"""
    WITH delivery_base AS (
        SELECT
            d.id AS delivery_id,
            d.delivery_invoice_no,
            s.invoice_no AS original_invoice_no,
            s.shipment_no,
            c.customer_name,
            b.product_id,
            s.warehouse_id,
            w.warehouse_name,
            d.currency,
            d.payment_due_date,
            d.sale_amount
        FROM customer_deliveries d
        JOIN customers c ON d.customer_id = c.id
        JOIN shipments s ON d.shipment_id = s.id
        JOIN shipment_boxes b ON d.box_id = b.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        WHERE COALESCE(d.delivery_invoice_no, '') <> ''
        {payment_access_sql}
    ),
    invoice_totals AS (
        SELECT
            MIN(delivery_id) AS id,
            delivery_invoice_no,
            MAX(original_invoice_no) AS original_invoice_no,
            MAX(shipment_no) AS shipment_no,
            MAX(customer_name) AS customer_name,
            MAX(product_id) AS product_id,
            MAX(warehouse_id) AS warehouse_id,
            MAX(warehouse_name) AS warehouse_name,
            MAX(currency) AS currency,
            MAX(payment_due_date) AS payment_due_date,
            SUM(COALESCE(sale_amount, 0)) AS total_invoice_amount
        FROM delivery_base
        GROUP BY delivery_invoice_no
    ),
    payment_totals AS (
        SELECT
            d.delivery_invoice_no,
            SUM(COALESCE(p.payment_amount, 0)) AS paid_amount
        FROM payments p
        JOIN customer_deliveries d ON p.delivery_id = d.id
        GROUP BY d.delivery_invoice_no
    )
    SELECT
        base.id,
        base.delivery_invoice_no,
        base.original_invoice_no,
        base.shipment_no,
        base.customer_name,
        base.product_id,
        base.warehouse_id,
        base.warehouse_name,
        base.currency,
        base.payment_due_date,
        base.total_invoice_amount,
        COALESCE(pay.paid_amount, 0) AS paid_amount,
        base.total_invoice_amount - COALESCE(pay.paid_amount, 0) AS pending_amount
    FROM invoice_totals base
    LEFT JOIN payment_totals pay ON base.delivery_invoice_no = pay.delivery_invoice_no
    WHERE base.total_invoice_amount - COALESCE(pay.paid_amount, 0) > 0
    {search_sql}
    ORDER BY base.payment_due_date NULLS LAST, base.delivery_invoice_no
    LIMIT {int(pending_limit)}
""", tuple(payment_access_params + search_params))

filtered_deliveries = deliveries or []

if not filtered_deliveries:
    st.warning('No pending delivery invoices available for your current product/warehouse access or search text.')
    st.info('If you expect pending invoices here, confirm that the user has View + Add rights for Payment and product/warehouse access for the related part/warehouse.')
else:
    delivery_map = {
        f"Original Inv {d.get('original_invoice_no') or '-'} | Delivery Inv {d.get('delivery_invoice_no') or '-'} | {d.get('customer_name') or '-'} | Shipment {d.get('shipment_no') or '-'} | Pending {float(d.get('pending_amount') or 0):,.3f} {d.get('currency') or ''}": d
        for d in filtered_deliveries
    }
    selected_delivery_key = searchable_selectbox(
        'Select Pending Delivery Invoice',
        list(delivery_map.keys()),
        key='payment_delivery_select'
    )
    selected_delivery = delivery_map[selected_delivery_key]

    st.markdown(f"""
        <div class="card" style="margin-bottom:16px;">
            <h3 style="margin:0;color:#003B73;">Payment Summary</h3>
            <table style="width:100%;font-family:Aptos,Arial,sans-serif;font-weight:700;margin-top:10px;">
                <tr>
                    <td><b>Original Invoice</b></td><td>{selected_delivery.get('original_invoice_no') or '-'}</td>
                    <td><b>Delivery Invoice</b></td><td>{selected_delivery.get('delivery_invoice_no') or '-'}</td>
                </tr>
                <tr>
                    <td><b>Customer</b></td><td>{selected_delivery.get('customer_name') or '-'}</td>
                    <td><b>Due Date</b></td><td>{selected_delivery.get('payment_due_date') or '-'}</td>
                </tr>
                <tr>
                    <td><b>Invoice Amount</b></td><td>{float(selected_delivery.get('total_invoice_amount') or 0):,.3f} {selected_delivery.get('currency') or ''}</td>
                    <td><b style="color:#047857;">Received Amount</b></td><td style="color:#047857;font-weight:900;">{float(selected_delivery.get('paid_amount') or 0):,.3f}</td>
                </tr>
                <tr>
                    <td><b style="color:#b91c1c;">Pending Amount</b></td><td style="color:#b91c1c;font-weight:900;">{float(selected_delivery.get('pending_amount') or 0):,.3f}</td>
                    <td><b>Shipment No</b></td><td>{selected_delivery.get('shipment_no') or '-'}</td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        payment_received_date = st.date_input('Payment Received Date', value=date.today(), key='payment_received_date')
        payment_amount = st.number_input(
            'Payment Amount',
            min_value=0.0,
            max_value=float(selected_delivery.get('pending_amount') or 0),
            value=0.0,
            step=1.0,
            key='payment_amount'
        )
    with c2:
        payment_reference = st.text_input('Payment Reference', key='payment_reference')
        attachment = st.file_uploader('Attach Payment File', key='payment_attachment_file')
        remarks = st.text_area('Remarks', key='payment_remarks')

    if st.button('Save Payment', type='primary', key='save_payment', disabled=not can_add_payment):
        if not current_user_can_add('payment'):
            st.error('You do not have Add permission for Payment Entry. Contact Super Admin.')
            st.stop()
        if payment_amount <= 0:
            st.error('Payment amount must be greater than zero.')
            st.stop()
        if payment_amount > float(selected_delivery.get('pending_amount') or 0):
            st.error('Payment amount cannot be more than pending amount.')
            st.stop()

        path = save_upload(attachment, f"payment_{selected_delivery['delivery_invoice_no']}")
        execute_query("""
            INSERT INTO payments (delivery_id, payment_received_date, payment_amount, payment_reference, attachment_path, remarks)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            selected_delivery['id'],
            str(payment_received_date),
            payment_amount,
            payment_reference,
            path,
            remarks
        ))
        notify_event(
            'payment',
            'Payment Received',
            f"Delivery Invoice: {selected_delivery['delivery_invoice_no']}\n"
            f"Customer: {selected_delivery['customer_name']}\n"
            f"Amount Received: {payment_amount}\n"
            f"Reference: {payment_reference}"
        )
        set_success_message('Payment saved successfully. Email notification attempted if enabled.')
        clear_cache_after_write()
        st.rerun()

# Payment history table removed from Payment Entry for faster loading.
# Use Payment Due and Edit Payment subpages for review/edit work.
st.divider()
st.info("Payment history was moved out of this entry screen for faster loading. Use Payment Due or Edit Payment subpages.")

render_slogan_footer()
