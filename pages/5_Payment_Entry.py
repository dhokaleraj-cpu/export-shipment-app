from common import *

page_setup()

require_page_view('payment')
show_edit_permission_status('payment')

show_header('Payment Entry')
access_notice()
render_payment_subnav('payment')
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
            ORDER BY payment_due_date
        """, tuple(payment_access_params))
deliveries = filter_rows_by_user_access(deliveries)
if not deliveries:
    st.warning('No pending delivery invoices available.')
else:
    st.markdown('<div class="input-section-title">Search Pending Delivery Invoice</div>', unsafe_allow_html=True)
    pending_invoice_search = st.text_input(
        "Search by Original Invoice / Delivery Invoice / Customer / Shipment",
        key="payment_pending_invoice_search",
        placeholder="Type invoice number, delivery invoice, customer or shipment number"
    ).strip().lower()

    filtered_deliveries = []
    for d in deliveries:
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
        st.warning("No pending delivery invoice matched your search.")
        st.stop()

    delivery_map = {
        f"Original Inv {d['original_invoice_no']} | Delivery Inv {d['delivery_invoice_no']} | {d['customer_name']} | Shipment {d.get('shipment_no') or '-'} | Pending {float(d['pending_amount'] or 0):,.2f} {d['currency']}": d
        for d in filtered_deliveries
    }
    selected_delivery_key = searchable_selectbox('Select Pending Delivery Invoice', list(delivery_map.keys()), key='payment_delivery_select')
    selected_delivery = delivery_map[selected_delivery_key]
    st.markdown(f"""\n            <div class="card" style="margin-bottom:16px;">\n                <h3 style="margin:0;color:#003B73;">Payment Summary</h3>\n                <table style="width:100%;font-family:Aptos,Arial,sans-serif;font-weight:700;margin-top:10px;">\n                    <tr>\n                        <td><b>Original Invoice</b></td><td>{selected_delivery['original_invoice_no']}</td>\n                        <td><b>Delivery Invoice</b></td><td>{selected_delivery['delivery_invoice_no']}</td>\n                    </tr>\n                    <tr>\n                        <td><b>Customer</b></td><td>{selected_delivery['customer_name']}</td>\n                        <td><b>Due Date</b></td><td>{selected_delivery['payment_due_date']}</td>\n                    </tr>\n                    <tr>\n                        <td><b>Invoice Amount</b></td><td>{selected_delivery['total_invoice_amount']:,.2f} {selected_delivery['currency']}</td>\n                        <td><b style="color:#047857;">Received Amount</b></td><td style="color:#047857;font-weight:900;">{selected_delivery['paid_amount']:,.2f}</td>\n                    </tr>\n                    <tr>\n                        <td><b style="color:#b91c1c;">Pending Amount</b></td><td style="color:#b91c1c;font-weight:900;">{selected_delivery['pending_amount']:,.2f}</td>\n                        <td><b>Shipment No</b></td><td>{selected_delivery['shipment_no']}</td>\n                    </tr>\n                </table>\n            </div>\n            """, unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        payment_received_date = st.date_input('Payment Received Date', value=date.today(), key='payment_received_date')
        payment_amount = st.number_input('Payment Amount', min_value=0.0, max_value=float(selected_delivery['pending_amount']) if selected_delivery['pending_amount'] else None, key='payment_amount')
    with c2:
        payment_reference = st.text_input('Payment Reference', key='payment_reference')
        attachment = st.file_uploader('Attach Payment File', key='auto_file_uploader_3')
        remarks = st.text_area('Remarks', key='auto_textarea_2')
    if st.button('Save Payment', type='primary', key='save_payment'):
        path = save_upload(attachment, f"payment_{selected_delivery['delivery_invoice_no']}")
        execute_query('\n                    INSERT INTO payments (delivery_id, payment_received_date, payment_amount, payment_reference, attachment_path, remarks)\n                    VALUES (?, ?, ?, ?, ?, ?)\n                ', (selected_delivery['id'], str(payment_received_date), payment_amount, payment_reference, path, remarks))
        notify_event('payment', 'Payment Received', f"Delivery Invoice: {selected_delivery['delivery_invoice_no']}\nCustomer: {selected_delivery['customer_name']}\nAmount Received: {payment_amount}\nReference: {payment_reference}")
        st.success('Payment saved successfully. Email notification attempted if enabled.')
st.divider()
st.subheader('Last Payment Entries')
payment_action_rows = fetch_all('\n            SELECT p.id, p.payment_received_date, d.delivery_invoice_no, s.invoice_no AS original_invoice_no,\n                   c.customer_name, p.payment_amount, p.payment_reference, p.remarks\n            FROM payments p\n            JOIN customer_deliveries d ON p.delivery_id = d.id\n            JOIN shipments s ON d.shipment_id = s.id\n            JOIN customers c ON d.customer_id = c.id\n            ORDER BY p.id DESC\n            LIMIT 50\n        ')
payment_action_rows = filter_rows_by_user_access(payment_action_rows)
selected_payment_action, _ = transaction_selector(payment_action_rows, 'payment_transaction_selector', 'payment_reference')
pay_action_col1, pay_action_col2 = st.columns(2)
with pay_action_col1:
    if st.button('Reopen Selected Payment for Modify', key='reopen_selected_payment'):
        if selected_payment_action:
            st.session_state.edit_payment_id = selected_payment_action['id']
            reopen_record_message('Payment', selected_payment_action['id'])
        else:
            st.warning('Select a payment first.')
with pay_action_col2:
    delete_password_pay = st.text_input('Password to Delete Selected Payment', type='password', key='delete_selected_payment_password')
    if st.button('Delete Selected Payment', key='delete_selected_payment'):
        if not selected_payment_action:
            st.warning('Select a payment first.')
        elif delete_record_with_password('payments', selected_payment_action['id'], delete_password_pay, f"Payment {selected_payment_action.get('payment_reference', '')}"):
            st.rerun()
if st.session_state.user['role'] == 'super_admin':
    st.divider()
    st.subheader('Super Admin: Edit Old Payment Entries')
    cleanup_orphan_transactions()
    old_payments = fetch_all('\n                SELECT p.*, d.delivery_invoice_no, c.customer_name, s.invoice_no AS original_invoice_no\n                FROM payments p\n                JOIN customer_deliveries d ON p.delivery_id = d.id\n                JOIN customers c ON d.customer_id = c.id\n                JOIN shipments s ON d.shipment_id = s.id\n                ORDER BY p.id DESC\n            ')
    old_payments = filter_rows_by_user_access(old_payments)
    if old_payments:
        pmap = {f"{p['id']} | {p['delivery_invoice_no']} | Amount {p['payment_amount']}": p for p in old_payments}
        selected_payment_key = searchable_selectbox('Select Payment to Edit', list(pmap.keys()), key='edit_payment_select')
        ep = pmap[selected_payment_key]
        pc1, pc2 = st.columns(2)
        with pc1:
            ep_date = st.text_input('Edit Payment Date YYYY-MM-DD', ep['payment_received_date'] or '', key='edit_payment_date')
            ep_amount = st.number_input('Edit Payment Amount', min_value=0.0, value=float(ep['payment_amount'] or 0), step=1.0, key='edit_payment_amount')
        with pc2:
            ep_ref = st.text_input('Edit Payment Reference', ep['payment_reference'] or '', key='edit_payment_ref')
            ep_remarks = st.text_area('Edit Remarks', ep['remarks'] or '', key='edit_payment_remarks')
        if st.button('Update Payment', type='primary', key='update_payment'):
            execute_query('\n                        UPDATE payments\n                        SET payment_received_date=?, payment_amount=?, payment_reference=?, remarks=?\n                        WHERE id=?\n                    ', (ep_date, ep_amount, ep_ref, ep_remarks, ep['id']))
            st.success('Payment updated successfully.')
            st.rerun()

render_slogan_footer()
st.markdown('<div class="footer">COPYRIGHT BY FOUR STAR INDUSTRIES PVT. LTD.</div>', unsafe_allow_html=True)
