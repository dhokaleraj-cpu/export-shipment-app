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

# ---------------------------------------------------------------------------
# Pending Delivery Invoice query
# Important: do not rely on Super Admin role. Any user with View can see the
# form; Save is controlled by Add permission.
# ---------------------------------------------------------------------------
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

deliveries = fetch_all(f"""
    SELECT
        MIN(d.id) AS id,
        d.delivery_invoice_no,
        s.invoice_no AS original_invoice_no,
        s.shipment_no,
        c.customer_name,
        MAX(b.product_id) AS product_id,
        MAX(s.warehouse_id) AS warehouse_id,
        MAX(w.warehouse_name) AS warehouse_name,
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
    {payment_access_sql}
    GROUP BY d.delivery_invoice_no, s.invoice_no, s.shipment_no, c.customer_name, d.currency
    HAVING
        SUM(d.sale_amount) - COALESCE((
            SELECT SUM(p.payment_amount)
            FROM payments p
            JOIN customer_deliveries d2 ON p.delivery_id = d2.id
            WHERE d2.delivery_invoice_no = d.delivery_invoice_no
        ), 0) > 0
    ORDER BY MAX(d.payment_due_date), d.delivery_invoice_no
""", tuple(payment_access_params))

# A final safety filter. If user has all product/warehouse access, this leaves rows unchanged.
deliveries = filter_rows_by_user_access(deliveries)

st.markdown('<div class="input-section-title">Search Pending Delivery Invoice</div>', unsafe_allow_html=True)
pending_invoice_search = st.text_input(
    "Search by Original Invoice / Delivery Invoice / Customer / Shipment",
    key="payment_pending_invoice_search",
    placeholder="Type invoice number, delivery invoice, customer or shipment number"
).strip().lower()

filtered_deliveries = []
for d in deliveries or []:
    search_text = " ".join([
        str(d.get("original_invoice_no") or ""),
        str(d.get("delivery_invoice_no") or ""),
        str(d.get("customer_name") or ""),
        str(d.get("shipment_no") or ""),
        str(d.get("warehouse_name") or ""),
        str(d.get("pending_amount") or ""),
        str(d.get("currency") or ""),
    ]).lower()
    if not pending_invoice_search or pending_invoice_search in search_text:
        filtered_deliveries.append(d)

if not filtered_deliveries:
    st.warning('No pending delivery invoices available for your current product/warehouse access or search text.')
    st.info('If you expect pending invoices here, confirm that the user has View + Add rights for Payment and product/warehouse access for the related part/warehouse.')
else:
    delivery_map = {
        f"Original Inv {d.get('original_invoice_no') or '-'} | Delivery Inv {d.get('delivery_invoice_no') or '-'} | {d.get('customer_name') or '-'} | Shipment {d.get('shipment_no') or '-'} | Pending {float(d.get('pending_amount') or 0):,.2f} {d.get('currency') or ''}": d
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
                    <td><b>Invoice Amount</b></td><td>{float(selected_delivery.get('total_invoice_amount') or 0):,.2f} {selected_delivery.get('currency') or ''}</td>
                    <td><b style="color:#047857;">Received Amount</b></td><td style="color:#047857;font-weight:900;">{float(selected_delivery.get('paid_amount') or 0):,.2f}</td>
                </tr>
                <tr>
                    <td><b style="color:#b91c1c;">Pending Amount</b></td><td style="color:#b91c1c;font-weight:900;">{float(selected_delivery.get('pending_amount') or 0):,.2f}</td>
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
