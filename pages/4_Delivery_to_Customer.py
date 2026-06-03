from common import *

page_setup()

show_header('Delivery Entry', 'Invoice-style FIFO delivery form with multi-pallet selection')
st.markdown('\n        <div class="card" style="margin-bottom:14px;">\n            <b>DELIVERY / COMMERCIAL INVOICE ENTRY</b><br>\n            Select Original Invoice + Shipment, then choose one or more pallets. Pallets are shown FIFO by shipment date and pallet number.\n        </div>\n        ', unsafe_allow_html=True)
customers = fetch_all('SELECT * FROM customers ORDER BY customer_name')
terms = fetch_all('SELECT * FROM payment_terms ORDER BY days')
invoice_shipments = fetch_all('\n            SELECT id, shipment_no, invoice_no, po_number, po_date, shipment_date\n            FROM shipments\n            ORDER BY shipment_date ASC, id ASC\n        ')
if not customers or not invoice_shipments:
    st.warning('Create Customer Master and Shipment Entry first.')
else:
    customer_map = {x['customer_name']: x['id'] for x in customers}
    term_map = {f"{x['term_name']} - {x['days']} days": x for x in terms}
    inv_map = {f"{s['invoice_no']} | Shipment {s['shipment_no']} | PO {s.get('po_number') or '-'} | Date {s['shipment_date']}": s for s in invoice_shipments}
    ctop1, ctop2 = st.columns(2)
    with ctop1:
        st.markdown('<div class="input-section-title">Original Invoice Number with Shipment Number</div>', unsafe_allow_html=True)
        selected_invoice = st.selectbox('Original Invoice Number with Shipment Number', list(inv_map.keys()), key='delivery_original_invoice_ship', label_visibility='collapsed')
    selected_ship = inv_map[selected_invoice]
    po_info_cols = st.columns(2)
    with po_info_cols[0]:
        st.text_input('PO Number', value=selected_ship.get('po_number') or '', disabled=True, key='delivery_selected_po_number')
    with po_info_cols[1]:
        st.text_input('PO Date', value=format_date_ddmmyyyy(selected_ship.get('po_date')), disabled=True, key='delivery_selected_po_date')
    available_rows = fetch_all('\n                SELECT\n                    b.*,\n                    s.shipment_no,\n                    s.invoice_no,\n                    s.shipment_date,\n                    COALESCE(s.po_number, p.po_number) AS po_number,\n                    COALESCE(s.po_date, p.po_date) AS po_date,\n                    p.product_code,\n                    p.product_name,\n                    COALESCE(del.delivered_qty, 0) AS delivered_qty,\n                    b.original_qty - COALESCE(del.delivered_qty, 0) AS balance_qty\n                FROM shipment_boxes b\n                JOIN shipments s ON b.shipment_id = s.id\n                JOIN products p ON b.product_id = p.id\n                LEFT JOIN (\n                    SELECT box_id, SUM(delivered_qty) AS delivered_qty\n                    FROM customer_deliveries\n                    GROUP BY box_id\n                ) del ON b.id = del.box_id\n                WHERE s.id = ?\n                  AND b.original_qty - COALESCE(del.delivered_qty, 0) > 0\n                ORDER BY s.shipment_date ASC, b.pallet_no ASC, b.id ASC\n            ', (selected_ship['id'],))
    if not available_rows:
        st.warning('No pending pallet quantity available for this original invoice/shipment.')
    else:
        pallet_map = {f"FIFO | Pallet {r['pallet_no']} | Box {r['box_no'] or '-'} | {r['product_code']} | Balance {r['balance_qty']} | Price {r['unit_price']} {r['currency']}": r for r in available_rows}
        selected_pallet_labels = st.multiselect('Select Pallet Numbers / Product Rows', list(pallet_map.keys()), key='delivery_multi_pallets')
        selected_pallets = [pallet_map[x] for x in selected_pallet_labels]
        c1, c2 = st.columns(2)
        with c1:
            customer = st.selectbox('Customer', list(customer_map.keys()), key='delivery_customer_v10')
            selected_customer_row = next((x for x in customers if x['customer_name'] == customer), None)
            default_term_id = selected_customer_row.get('payment_term_id') if selected_customer_row else None
            delivery_date = st.date_input('Delivery Date', value=date.today(), key='delivery_date_v10')
            delivery_invoice_no = st.text_input('Delivery Invoice Number', key='delivery_invoice_v10')
        with c2:
            term_keys = list(term_map.keys())
            default_term_key = term_keys[0]
            if default_term_id:
                for k, v in term_map.items():
                    if v['id'] == default_term_id:
                        default_term_key = k
                        break
            selected_term = st.selectbox('Payment Term', term_keys, index=term_keys.index(default_term_key), key='delivery_payment_term_v10')
            term = term_map[selected_term]
            payment_due_date = delivery_date + timedelta(days=int(term['days']))
            attachment = st.file_uploader('Attach Delivery File', key='delivery_attachment_v10')
            st.info(f'Payment Due Date: {payment_due_date}')
        st.subheader('Enter Delivery Quantity for Selected Pallets')
        delivery_inputs = []
        total_qty = 0
        total_amount = 0
        for i, row in enumerate(selected_pallets):
            dc1, dc2, dc3, dc4 = st.columns([2, 1, 1, 1])
            with dc1:
                st.write(f"{row['pallet_no']} | {row['product_code']} | Balance {row['balance_qty']}")
            with dc2:
                qty = st.number_input('Qty', min_value=0.0, max_value=float(row['balance_qty']), value=0.0, step=1.0, key=f"delivery_qty_{row['id']}_{i}")
            with dc3:
                price = st.number_input('Price', min_value=0.0, value=float(row['unit_price'] or 0), step=1.0, key=f"delivery_price_{row['id']}_{i}")
            with dc4:
                amount = qty * price
                st.write(f"{amount:,.2f} {row['currency']}")
            if qty > 0:
                total_qty += qty
                total_amount += amount
                delivery_inputs.append((row, qty, price, amount))
        st.markdown(f'<div class="total-box">Total Delivery Qty: {total_qty} &nbsp;&nbsp; | &nbsp;&nbsp; Total Amount: {total_amount:,.2f}</div>', unsafe_allow_html=True)
        st.subheader('FIFO Available Pallets')
        fifo_display_rows = []
        for r in available_rows:
            if float(r.get('balance_qty') or 0) > 0:
                fifo_display_rows.append({'shipment_no': r['shipment_no'], 'original_invoice_no': r['invoice_no'], 'po_number': r.get('po_number', ''), 'po_date': r.get('po_date', ''), 'shipment_date': r['shipment_date'], 'pallet_no': r['pallet_no'], 'box_no': r['box_no'] or '-', 'product_code': r['product_code'], 'product_name': r['product_name'], 'original_qty': r['original_qty'], 'delivered_qty': r['delivered_qty'], 'balance_qty': r['balance_qty'], 'unit_price': r['unit_price'], 'currency': r['currency']})
        show_fifo_df(fifo_display_rows, 'delivery_fifo_available')
        if st.button('Save Delivery & Print', type='primary', key='save_delivery_fifo'):
            if not delivery_invoice_no.strip():
                st.error('Delivery Invoice Number is mandatory.')
            elif not delivery_inputs:
                st.error('Select pallets and enter delivery quantity.')
            else:
                path = save_upload(attachment, f'delivery_{delivery_invoice_no}')
                first_print = None
                for row, qty, price, amount in delivery_inputs:
                    execute_query('\n                                INSERT INTO customer_deliveries\n                                (shipment_id, box_id, customer_id, delivery_date, delivered_qty, delivery_invoice_no,\n                                 payment_term_id, payment_terms_days, payment_due_date, unit_price, currency, sale_amount, attachment_path, po_number, po_date)\n                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\n                            ', (row['shipment_id'], row['id'], customer_map[customer], str(delivery_date), qty, delivery_invoice_no.strip(), term['id'], term['days'], str(payment_due_date), price, row['currency'], amount, path, row.get('po_number', ''), row.get('po_date', None)))
                    if first_print is None:
                        first_print = {'customer_name': customer, 'shipment_no': row['shipment_no'], 'original_invoice_no': row['invoice_no'], 'delivery_invoice_no': delivery_invoice_no, 'delivery_date': str(delivery_date), 'payment_term': selected_term, 'payment_due_date': str(payment_due_date), 'product_code': row['product_code'], 'product_name': row['product_name'], 'po_number': row.get('po_number', ''), 'po_date': row.get('po_date', ''), 'pallet_no': row['pallet_no'], 'box_no': row['box_no'] or '-', 'qty': total_qty, 'unit_price': price, 'currency': row['currency'], 'sale_amount': total_amount}
                notify_event('delivery', 'Delivery Created', f"Delivery Invoice: {delivery_invoice_no}\\nOriginal Invoice: {selected_ship['invoice_no']}\\nCustomer: {customer}\\nQty: {total_qty}\\nAmount: {total_amount}\\nDue Date: {payment_due_date}")
                if first_print:
                    st.session_state.last_delivery_print = first_print
                st.success('Delivery saved successfully. Email notification attempted if enabled. Print popup opened.')
if 'last_delivery_print' in st.session_state:
    html_doc = delivery_note_html(st.session_state.last_delivery_print)
    print_popup(html_doc)
    st.download_button('Download / Print Delivery Note HTML', html_doc, 'delivery_note.html', mime='text/html', key='download_delivery_note_html')
    del st.session_state.last_delivery_print
st.divider()
st.subheader('Last Delivery Entries - Delivery Invoice Wise')
delivery_invoice_rows = fetch_all('\n            SELECT d.delivery_invoice_no,\n                   MIN(d.id) AS first_id,\n                   MAX(d.delivery_date) AS delivery_date,\n                   MAX(d.payment_due_date) AS payment_due_date,\n                   c.customer_name,\n                   s.invoice_no AS original_invoice_no,\n                   s.shipment_no,\n                   d.currency,\n                   SUM(d.delivered_qty) AS total_qty,\n                   SUM(d.sale_amount) AS total_amount,\n                   COUNT(*) AS product_rows\n            FROM customer_deliveries d\n            JOIN customers c ON d.customer_id = c.id\n            JOIN shipments s ON d.shipment_id = s.id\n            GROUP BY d.delivery_invoice_no, c.customer_name, s.invoice_no, s.shipment_no, d.currency\n            ORDER BY first_id DESC\n            LIMIT 30\n        ')
if not delivery_invoice_rows:
    st.info('No delivery invoice entries available.')
else:
    invoice_options = [f"{r['delivery_invoice_no']} | Qty {r['total_qty']:,.2f} | Amount {r['total_amount']:,.2f} {r['currency']} | Due {format_date_ddmmyyyy(r['payment_due_date'])}" for r in delivery_invoice_rows]
    option_to_invoice = {opt: r['delivery_invoice_no'] for opt, r in zip(invoice_options, delivery_invoice_rows)}
    selected_delivery_invoice_label = st.selectbox('Select Delivery Invoice No', invoice_options, key='selected_delivery_invoice_for_details')
    selected_delivery_invoice_no = option_to_invoice[selected_delivery_invoice_label]
    summary_rows = []
    for r in delivery_invoice_rows:
        if r['delivery_invoice_no'] == selected_delivery_invoice_no:
            summary_rows.append({'Select': True, 'delivery_invoice_no': r['delivery_invoice_no'], 'customer_name': r['customer_name'], 'original_invoice_no': r['original_invoice_no'], 'shipment_no': r['shipment_no'], 'total_qty': r['total_qty'], 'total_amount': r['total_amount'], 'currency': r['currency'], 'payment_due_date': r['payment_due_date'], 'product_rows': r['product_rows']})
            break
    st.dataframe(pd.DataFrame(format_date_columns(summary_rows)), use_container_width=True, hide_index=True)
    action_col1, action_col2, action_col3, action_col4 = st.columns(4)
    with action_col1:
        if st.button('Reprint Delivery Invoice', key='reprint_selected_delivery_invoice'):
            data = build_delivery_invoice_print_data(selected_delivery_invoice_no)
            if data:
                html_doc = delivery_note_html(data)
                st.session_state.last_delivery_reprint = html_doc
                st.success('Reprint opened for selected delivery invoice.')
    with action_col2:
        if st.button('Send Email Delivery Invoice', key='email_selected_delivery_invoice'):
            data = build_delivery_invoice_print_data(selected_delivery_invoice_no)
            if data:
                notify_event('delivery', f'Delivery Invoice {selected_delivery_invoice_no}', f"Delivery Invoice: {selected_delivery_invoice_no}\\nCustomer: {data.get('customer_name', '')}\\nOriginal Invoice: {data.get('original_invoice_no', '')}\\nTotal Qty: {data.get('qty', 0)}\\nTotal Amount: {data.get('sale_amount', 0)} {data.get('currency', '')}\\nPayment Due Date: {data.get('payment_due_date', '')}")
                st.success('Email notification attempted for selected delivery invoice.')
    with action_col3:
        if st.button('Reopen Delivery Invoice for Modify', key=f'reopen_delivery_invoice_{selected_delivery_invoice_no}'):
            st.session_state.edit_delivery_invoice_no = selected_delivery_invoice_no
            reopen_record_message('Delivery Invoice', selected_delivery_invoice_no)
    with action_col4:
        if st.session_state.user['role'] == 'super_admin':
            delete_password = st.text_input('Password to Delete Delivery Invoice', type='password', key=f'delete_delivery_invoice_password_{selected_delivery_invoice_no}')
            if st.button('Delete Delivery Invoice', key=f'delete_delivery_invoice_btn_{selected_delivery_invoice_no}'):
                if check_delete_password(delete_password):
                    ids = fetch_all('SELECT id FROM customer_deliveries WHERE delivery_invoice_no=?', (selected_delivery_invoice_no,))
                    for row in ids:
                        try:
                            execute_query('INSERT INTO delete_audit_log (table_name, record_id, deleted_by, details) VALUES (?, ?, ?, ?)', ('customer_deliveries', row['id'], st.session_state.user.get('username', ''), f'Delivery Invoice {selected_delivery_invoice_no}'))
                        except Exception:
                            pass
                        execute_query('DELETE FROM payments WHERE delivery_id=?', (row['id'],))
                    execute_query('DELETE FROM customer_deliveries WHERE delivery_invoice_no=?', (selected_delivery_invoice_no,))
                    cleanup_orphan_transactions()
                    st.success('Delivery invoice, linked payment references, and edit records deleted successfully.')
                    st.rerun()
                else:
                    st.error('Wrong password. Delete cancelled.')
        else:
            st.info('Delete allowed for Super Admin only.')
    if 'last_delivery_reprint' in st.session_state:
        print_popup(st.session_state.last_delivery_reprint)
        st.download_button('Download Reprint Delivery Invoice HTML', st.session_state.last_delivery_reprint, 'delivery_invoice_reprint.html', mime='text/html', key='download_reprint_delivery_invoice_html')
        del st.session_state.last_delivery_reprint
    st.markdown('### Delivery Invoice Product Details')
    detail_rows = fetch_all('\n                SELECT d.id, d.delivery_invoice_no, d.delivery_date, s.invoice_no AS original_invoice_no,\n                       s.shipment_no, p.product_code, p.product_name, b.pallet_no, b.box_no,\n                       d.delivered_qty, d.unit_price, d.currency, d.sale_amount, d.payment_due_date\n                FROM customer_deliveries d\n                JOIN shipments s ON d.shipment_id = s.id\n                JOIN shipment_boxes b ON d.box_id = b.id\n                JOIN products p ON b.product_id = p.id\n                WHERE d.delivery_invoice_no=?\n                ORDER BY d.id\n            ', (selected_delivery_invoice_no,))
    show_filtered_df(edit_button_column(detail_rows, 'delivery'), f'delivery_invoice_detail_{selected_delivery_invoice_no}', total=True)
if st.session_state.user['role'] == 'super_admin':
    st.divider()
    st.subheader('Edit Delivery Entry')
    cleanup_orphan_transactions()
    old_deliveries = fetch_all('\n                SELECT d.*, c.customer_name, s.invoice_no AS original_invoice_no, s.shipment_no\n                FROM customer_deliveries d\n                JOIN customers c ON d.customer_id = c.id\n                JOIN shipments s ON d.shipment_id = s.id\n                JOIN shipment_boxes b ON d.box_id = b.id\n                ORDER BY d.id DESC\n            ')
    if old_deliveries:
        dmap = {f"{d['id']} | {d['delivery_invoice_no']} | {d['customer_name']}": d for d in old_deliveries}
        ed = dmap[st.selectbox('Select Delivery to Edit', list(dmap.keys()), key='edit_delivery_select')]
        dc1, dc2 = st.columns(2)
        with dc1:
            ed_inv = st.text_input('Edit Delivery Invoice No', ed['delivery_invoice_no'] or '', key='edit_delivery_inv')
            ed_date = st.text_input('Edit Delivery Date YYYY-MM-DD', ed['delivery_date'] or '', key='edit_delivery_date')
            ed_qty = st.number_input('Edit Delivered Qty', min_value=0.0, value=float(ed['delivered_qty'] or 0), step=1.0, key='edit_delivery_qty')
        with dc2:
            ed_price = st.number_input('Edit Unit Price', min_value=0.0, value=float(ed['unit_price'] or 0), step=1.0, key='edit_delivery_price')
            ed_currency = st.selectbox('Edit Currency', CURRENCIES, index=CURRENCIES.index(ed['currency']) if ed['currency'] in CURRENCIES else 0, key='edit_delivery_currency')
            ed_due = st.text_input('Edit Payment Due Date YYYY-MM-DD', ed['payment_due_date'] or '', key='edit_delivery_due')
        ed_amount = ed_qty * ed_price
        st.markdown(f'<div class="total-box">New Sale Amount: {ed_amount:,.2f} {ed_currency}</div>', unsafe_allow_html=True)
        if st.button('Update Delivery', type='primary', key='update_delivery'):
            execute_query('\n                        UPDATE customer_deliveries\n                        SET delivery_invoice_no=?, delivery_date=?, delivered_qty=?, unit_price=?, currency=?, sale_amount=?, payment_due_date=?\n                        WHERE id=?\n                    ', (ed_inv, ed_date, ed_qty, ed_price, ed_currency, ed_amount, ed_due, ed['id']))
            st.success('Delivery updated successfully.')
            st.rerun()

st.markdown('<div class="footer">COPYRIGHT BY FOUR STAR INDUSTRIES PVT. LTD.</div>', unsafe_allow_html=True)
