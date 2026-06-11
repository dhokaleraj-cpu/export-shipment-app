from common import *

page_setup()

require_page_edit('shipment')
show_edit_permission_status('shipment')

show_header('Shipment Entry with Pallet / Product Rows')
suppliers = fetch_all('SELECT * FROM suppliers ORDER BY supplier_name')
customers = fetch_all('SELECT * FROM customers ORDER BY customer_name')
ship_to_rows = fetch_all("SELECT * FROM ship_to_masters WHERE COALESCE(is_active, TRUE)=TRUE ORDER BY ship_to_name, ship_to_id")
warehouses = fetch_all('SELECT * FROM warehouses ORDER BY warehouse_name')
warehouse_info = {w.get('warehouse_name'): w for w in warehouses}
products = fetch_all('SELECT * FROM products ORDER BY product_code')
forwarders = fetch_all('SELECT * FROM forwarders ORDER BY forwarder_name')
incoterms = fetch_all('SELECT * FROM incoterms ORDER BY incoterm_name')
if not suppliers or not warehouses or (not products) or not customers:
    st.warning('Create Supplier, Warehouse, Product and Customer masters first.')
else:
    supplier_map = {x['supplier_name']: x['id'] for x in suppliers}
    customer_map = {x['customer_name']: x['id'] for x in customers}
    ship_to_map = {f"{x['ship_to_name']} | {x.get('ship_to_id') or '-'}": x for x in ship_to_rows}
    warehouse_map = {x['warehouse_name']: x['id'] for x in warehouses}
    forwarder_map = {x['forwarder_name']: x['id'] for x in forwarders}
    incoterm_map = {x['incoterm_name']: x['id'] for x in incoterms}
    product_options = [f"{x['product_code']} | {x['product_name']}" for x in products]
    product_info = {f"{x['product_code']} | {x['product_name']}": x for x in products}

    def get_next_fifo_row_id():
        db_max = fetch_all('SELECT COALESCE(MAX(fifo_row_id), 0) AS max_id FROM shipment_boxes')
        max_db = int(db_max[0]['max_id'] or 0) if db_max else 0
        temp_ids = [int(r.get('fifo_row_id') or 0) for r in st.session_state.get('shipment_temp_rows', [])]
        max_temp = max(temp_ids) if temp_ids else 0
        return max(max_db, max_temp) + 1


    st.markdown('<div class="sap-grid-card"><div class="sap-grid-card-title">Original Invoice Details</div>', unsafe_allow_html=True)
    inv_top1, inv_top2 = st.columns(2)
    with inv_top1:
        invoice_no = st.text_input('Original Invoice Number', key='shipment_original_invoice_top')
    with inv_top2:
        shipment_date = st.date_input('Original Invoice Date', value=date.today(), key='shipment_original_invoice_date_top')
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div style="height:14px;"></div>', unsafe_allow_html=True)
    h1, h2 = st.columns(2)
    with h1:
        shipment_no = st.text_input('Shipment Number / BL No / Seaway Bill No', key='shipment_no_bl_seaway')
        shipping_bill_no = st.text_input('Shipping Bill No.', key='shipment_shipping_bill_no')
        if forwarder_map:
            forwarder_name = st.selectbox('Forwarder Name', list(forwarder_map.keys()), key='shipment_forwarder_name')
        else:
            forwarder_name = st.text_input('Forwarder Name', key='shipment_forwarder_name')
            forwarder_map = {forwarder_name: None}
        po_number = ''  # PO Number is now captured row-wise in Add Pallet/Product Row
        supplier = st.selectbox('Supplier', list(supplier_map.keys()), key='shipment_supplier')
        customer = st.selectbox('Customer', list(customer_map.keys()), key='shipment_customer_select')
        attachment = st.file_uploader('Attach Shipment File', key='auto_file_uploader_1')
    with h2:
        shipment_doc_date = st.date_input('Shipment / BL / Seaway Bill Date', value=date.today(), key='shipment_doc_date')
        shipping_bill_date = st.date_input('Shipping Bill Date', value=date.today(), key='shipment_shipping_bill_date')
        if incoterm_map:
            incoterm = st.selectbox('Incoterm', list(incoterm_map.keys()), key='shipment_incoterm')
        else:
            incoterm = st.text_input('Incoterm', key='shipment_incoterm')
            incoterm_map = {incoterm: None}
        po_date = None  # PO Date is now captured row-wise in Add Pallet/Product Row
        warehouse = st.selectbox('Warehouse', list(warehouse_map.keys()), key='shipment_warehouse')
        selected_shipment_time_days = int(warehouse_info.get(warehouse, {}).get('shipment_time_days') or 0)
        if ship_to_map:
            shipment_ship_to_key = st.selectbox('Ship To', list(ship_to_map.keys()), key='shipment_ship_to_select')
            selected_shipment_ship_to = ship_to_map[shipment_ship_to_key]
        else:
            selected_shipment_ship_to = {}
            st.warning('Create Ship To Master if you want to link Ship To in shipment.')
        remarks = st.text_area('Remarks', key='auto_textarea_1')
    st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)
    st.subheader('Add Pallet/Product Row')
    if 'shipment_temp_rows' not in st.session_state:
        st.session_state.shipment_temp_rows = []
    st.markdown('\n            <style>\n            .shipment-grid-label {\n                font-family: Aptos, Arial, sans-serif;\n                font-size: 15px;\n                font-weight: 900;\n                color: #003B73;\n                margin-bottom: 6px;\n                min-height: 22px;\n            }\n            .amount-input-look {\n                height: 52px;\n                border-radius: 10px;\n                background: #f3f6fa;\n                display: flex;\n                align-items: center;\n                justify-content: center;\n                font-family: Aptos, Arial, sans-serif;\n                font-size: 16px;\n                font-weight: 700;\n                color: #1f2937;\n                border: 1px solid transparent;\n                margin-top: 0px;\n            }\n            div[data-testid="stHorizontalBlock"] div[data-testid="column"] {\n                padding-top: 2px;\n            }\n            </style>\n            ', unsafe_allow_html=True)
    r1, r2, r3, r4, r5, r6, r7, r8, r9 = st.columns([1.0, 1.0, 2.05, 1.15, 1.05, 0.85, 0.85, 0.75, 1.0])
    with r1:
        st.markdown('<div class="shipment-grid-label">Pallet Number</div>', unsafe_allow_html=True)
        pallet_no = st.text_input('Pallet Number', key='shipment_grid_pallet_no', label_visibility='collapsed')
    with r2:
        st.markdown('<div class="shipment-grid-label">Box Number</div>', unsafe_allow_html=True)
        box_no = st.text_input('Box Number', key='shipment_grid_box_no', label_visibility='collapsed')
    with r3:
        st.markdown('<div class="shipment-grid-label">Product Code</div>', unsafe_allow_html=True)
        selected_product = st.selectbox('Product Code', product_options, key='shipment_product_select', label_visibility='collapsed')

    selected_product_data = product_info[selected_product]
    auto_price = float(selected_product_data.get('unit_price') or 0)
    auto_currency = selected_product_data.get('currency') or 'USD'
    product_id_for_key = str(selected_product_data.get('id') or selected_product).replace(' ', '_').replace('|', '_').replace('/', '_')

    # PO comes from Product Master by default and can be manually overridden row-wise.
    default_row_po_number = selected_product_data.get('po_number') or ''
    try:
        default_row_po_date = parse_db_date(selected_product_data.get('po_date')) or date.today()
    except Exception:
        default_row_po_date = date.today()

    with r4:
        st.markdown('<div class="shipment-grid-label">PO Number</div>', unsafe_allow_html=True)
        row_po_number = st.text_input('PO Number', value=default_row_po_number, key=f'shipment_grid_po_number_{product_id_for_key}', label_visibility='collapsed')
    with r5:
        st.markdown('<div class="shipment-grid-label">PO Date</div>', unsafe_allow_html=True)
        row_po_date = st.date_input('PO Date', value=default_row_po_date, key=f'shipment_grid_po_date_{product_id_for_key}', label_visibility='collapsed')
    with r6:
        st.markdown('<div class="shipment-grid-label">Quantity</div>', unsafe_allow_html=True)
        quantity = st.number_input('Quantity', min_value=0.0, step=1.0, key='shipment_grid_qty', label_visibility='collapsed')
    with r7:
        st.markdown('<div class="shipment-grid-label">Price</div>', unsafe_allow_html=True)
        unit_price = st.number_input('Price', min_value=0.0, value=auto_price, step=1.0, key=f'shipment_grid_price_{product_id_for_key}', label_visibility='collapsed')
    with r8:
        st.markdown('<div class="shipment-grid-label">Currency</div>', unsafe_allow_html=True)
        currency = st.selectbox('Currency', CURRENCIES, index=CURRENCIES.index(auto_currency) if auto_currency in CURRENCIES else 0, key=f'shipment_grid_currency_{product_id_for_key}', label_visibility='collapsed')
    with r9:
        st.markdown('<div class="shipment-grid-label">Amount</div>', unsafe_allow_html=True)
        amount = quantity * unit_price
        st.markdown(f'<div class="amount-input-look">{amount:,.2f} {currency}</div>', unsafe_allow_html=True)
    st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
    if st.button('Add Row to Table', type='primary', key='shipment_grid_add_row'):
        if not pallet_no.strip():
            st.error('Pallet Number is mandatory.')
        elif quantity <= 0:
            st.error('Quantity must be greater than zero.')
        else:
            new_key = (pallet_no.strip(), selected_product_data['id'])
            existing_keys = [(r['pallet_no'], r['product_id']) for r in st.session_state.shipment_temp_rows]
            old_match = fetch_all('\n                        SELECT b.id, s.shipment_no\n                        FROM shipment_boxes b\n                        JOIN shipments s ON b.shipment_id = s.id\n                        WHERE b.pallet_no = ? AND b.product_id = ?\n                    ', (pallet_no.strip(), selected_product_data['id']))
            if new_key in existing_keys:
                st.error('Duplicate pallet/product row already added in this shipment.')
            elif old_match:
                st.error(f"This pallet number is already used for the same product in shipment {old_match[0]['shipment_no']}. It cannot be used again.")
            else:
                st.session_state.shipment_temp_rows.append({'fifo_row_id': get_next_fifo_row_id(), 'pallet_no': pallet_no.strip(), 'box_no': (box_no or '').strip(), 'po_number': (row_po_number or '').strip(), 'po_date': str(row_po_date), 'product_id': selected_product_data['id'], 'product_code': selected_product_data['product_code'], 'product_name': selected_product_data['product_name'], 'quantity': quantity, 'unit_price': unit_price, 'currency': currency, 'amount': amount})
                st.success('Row added.')
    st.subheader('Current Shipment Rows')
    temp_df = pd.DataFrame(st.session_state.shipment_temp_rows)
    if not temp_df.empty:
        display_df = add_total_row(temp_df[['fifo_row_id', 'pallet_no', 'box_no', 'po_number', 'po_date', 'product_code', 'product_name', 'quantity', 'unit_price', 'currency', 'amount']])
        st.dataframe(style_total_row(display_df), use_container_width=True, hide_index=True)
        total_qty = temp_df['quantity'].sum()
        total_amount = temp_df['amount'].sum()
        st.markdown(f'<div class="total-box">Total Quantity: {total_qty} &nbsp;&nbsp; | &nbsp;&nbsp; Total Amount: {total_amount:,.2f}</div>', unsafe_allow_html=True)
        if st.button('Clear Unsaved Rows', key='clear_unsaved_shipment_rows'):
            st.session_state.shipment_temp_rows = []
            st.rerun()
    else:
        st.info('No rows added yet.')
    if st.button('Save Shipment with All Rows', type='primary', key='save_shipment_all_rows'):
        if not shipment_no.strip():
            st.error('Shipment Number is mandatory.')
        elif not invoice_no.strip():
            st.error('Original Invoice Number is mandatory.')
        elif not st.session_state.shipment_temp_rows:
            st.error('Add at least one pallet/product row before saving shipment.')
        else:
            try:
                total_amount = sum((r['amount'] for r in st.session_state.shipment_temp_rows))
                first_po_number = st.session_state.shipment_temp_rows[0].get('po_number', '')
                first_po_date = st.session_state.shipment_temp_rows[0].get('po_date') or None
                first_currency = st.session_state.shipment_temp_rows[0]['currency']
                path = save_upload(attachment, f'shipment_{shipment_no}')
                execute_query('\n                            INSERT INTO shipments (shipment_no, invoice_no, po_number, po_date, shipment_date, supplier_id, warehouse_id, customer_id, ship_to_master_id, shipment_time_days, invoice_amount, currency, attachment_path, remarks, shipping_bill_no, shipping_bill_date, shipment_doc_date, forwarder_name, incoterm, forwarder_id, incoterm_id)\n                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\n                        ', (shipment_no, invoice_no, first_po_number, first_po_date, str(shipment_date), supplier_map[supplier], warehouse_map[warehouse], customer_map[customer], selected_shipment_ship_to.get('id'), selected_shipment_time_days, total_amount, first_currency, path, remarks, shipping_bill_no, str(shipping_bill_date), str(shipment_doc_date), forwarder_name, incoterm, forwarder_map.get(forwarder_name), incoterm_map.get(incoterm)))
                shipment_id = fetch_all('SELECT id FROM shipments WHERE shipment_no=?', (shipment_no,))[0]['id']
                for row in st.session_state.shipment_temp_rows:
                    old_match = fetch_all('\n                                SELECT b.id FROM shipment_boxes b\n                                WHERE b.pallet_no = ? AND b.product_id = ?\n                            ', (row['pallet_no'], row['product_id']))
                    if old_match:
                        raise sqlite3.IntegrityError(f"Pallet {row['pallet_no']} already used for product {row['product_code']}")
                    execute_query('\n                                INSERT INTO shipment_boxes (shipment_id, fifo_row_id, pallet_no, box_no, po_number, po_date, product_id, original_qty, unit_price, currency, amount)\n                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\n                            ', (shipment_id, row.get('fifo_row_id'), row['pallet_no'], row['box_no'], row.get('po_number',''), row.get('po_date') or None, row['product_id'], row['quantity'], row['unit_price'], row['currency'], row['amount']))
                st.session_state.shipment_temp_rows = []
                notify_event('shipment', 'New Shipment Created', f'Shipment No: {shipment_no}\nOriginal Invoice: {invoice_no}\nPO Number: {first_po_number}\nPO Date: {first_po_date}\nAmount: {total_amount}\nCurrency: {first_currency}')
                st.success('Shipment and pallet/product rows saved successfully. Email notification attempted if enabled.')
            except Exception as e:
                st.error(f'Shipment save failed. Existing database entries were not changed. Details: {e}')
    st.divider()
    st.subheader('Last Shipment Entries')
    shipment_rows_for_actions = fetch_all('\n                SELECT s.id, s.shipment_no, s.invoice_no, s.po_number, s.po_date, s.shipment_date, s.shipping_bill_no, s.shipping_bill_date,\n                       s.shipment_doc_date, s.forwarder_name, s.incoterm,\n                       sup.supplier_name, w.warehouse_name, s.currency, s.invoice_amount\n                FROM shipments s\n                LEFT JOIN suppliers sup ON s.supplier_id = sup.id\n                LEFT JOIN warehouses w ON s.warehouse_id = w.id\n                ORDER BY s.id DESC\n                LIMIT 50\n            ')
    shipment_display_df = pd.DataFrame(shipment_rows_for_actions)
    if not shipment_display_df.empty:
        st.dataframe(style_total_row(shipment_display_df), use_container_width=True, hide_index=True)
        export_buttons(add_total_row(shipment_display_df), "shipment_last_entries_report")
    selected_shipment_action, _ = transaction_selector(shipment_rows_for_actions, 'shipment_transaction_selector', 'shipment_no')
    ship_action_col1, ship_action_col2 = st.columns(2)
    with ship_action_col1:
        if st.button('Reopen Selected Shipment for Modify', key='reopen_selected_shipment'):
            if selected_shipment_action:
                st.session_state.edit_shipment_id = selected_shipment_action['id']
                reopen_record_message('Shipment', selected_shipment_action['id'])
            else:
                st.warning('Select a shipment first.')
    with ship_action_col2:
        delete_password_ship = st.text_input('Password to Delete Selected Shipment', type='password', key='delete_selected_shipment_password')
        if st.button('Delete Selected Shipment', key='delete_selected_shipment'):
            if not selected_shipment_action:
                st.warning('Select a shipment first.')
            elif check_delete_password(delete_password_ship):
                # Protect linked transactional data.
                # Shipment boxes cannot be deleted when Delivery records already exist,
                # because customer_deliveries.box_id has a foreign-key link to shipment_boxes.id.
                linked_deliveries = fetch_all("""
                    SELECT COUNT(*) AS c
                    FROM customer_deliveries d
                    JOIN shipment_boxes b ON d.box_id = b.id
                    WHERE b.shipment_id=?
                """, (selected_shipment_action['id'],))
                delivery_count = int(linked_deliveries[0].get('c') or 0) if linked_deliveries else 0

                if delivery_count > 0:
                    st.error(
                        f"Cannot delete Shipment {selected_shipment_action['shipment_no']} because {delivery_count} delivery record(s) are linked with its pallet/product rows. "
                        "To preserve historical data, use Modify/Edit instead of Delete."
                    )
                else:
                    execute_query('DELETE FROM shipment_boxes WHERE shipment_id=?', (selected_shipment_action['id'],))
                    delete_record_with_password('shipments', selected_shipment_action['id'], delete_password_ship, f"Shipment {selected_shipment_action['shipment_no']}")
                    st.success('Shipment deleted successfully.')
                    clear_cache_after_write()
                    st.rerun()
            else:
                st.error('Wrong password. Delete cancelled.')
    st.subheader('Saved Shipment / Pallet Stock')
    show_filtered_df(fetch_all('\n                SELECT s.shipment_no, s.invoice_no, b.fifo_row_id, b.pallet_no, b.box_no, p.product_code, p.product_name,\n                       b.po_number, b.po_date, b.original_qty, b.unit_price, b.currency, b.amount\n                FROM shipment_boxes b\n                JOIN shipments s ON b.shipment_id = s.id\n                JOIN products p ON b.product_id = p.id\n                ORDER BY b.id DESC\n            '), 'auto_filter_key_1', total=True)
    if st.session_state.user['role'] == 'super_admin':
        st.divider()
        st.subheader('Super Admin: Edit Old Shipment Header')
        old_shipments = fetch_all('\n                    SELECT s.*, sup.supplier_name, w.warehouse_name, c.customer_name, stm.ship_to_name, stm.ship_to_id\n                    FROM shipments s\n                    LEFT JOIN suppliers sup ON s.supplier_id = sup.id\n                    LEFT JOIN warehouses w ON s.warehouse_id = w.id\n                    LEFT JOIN customers c ON s.customer_id = c.id\n                    LEFT JOIN ship_to_masters stm ON s.ship_to_master_id = stm.id\n                    ORDER BY s.id DESC\n                ')
        if old_shipments:
            ship_map = {f"{s['id']} | {s['shipment_no']} | Invoice {s['invoice_no']}": s for s in old_shipments}
            default_ship_key = None
            if st.session_state.get('edit_shipment_id'):
                default_ship_key = next((k for k, v in ship_map.items() if v['id'] == st.session_state.edit_shipment_id), None)
            ship_keys = list(ship_map.keys())
            default_ship_index = ship_keys.index(default_ship_key) if default_ship_key in ship_keys else 0
            selected_ship_key = searchable_selectbox('Select Shipment to Edit', ship_keys, key='edit_shipment_header_select', default_index=default_ship_index)
            edit_ship = ship_map[selected_ship_key]
            suppliers2 = fetch_all('SELECT * FROM suppliers ORDER BY supplier_name')
            warehouses2 = fetch_all('SELECT * FROM warehouses ORDER BY warehouse_name')
            customers2 = fetch_all('SELECT * FROM customers ORDER BY customer_name')
            ship_to2 = fetch_all("SELECT * FROM ship_to_masters WHERE COALESCE(is_active, TRUE)=TRUE ORDER BY ship_to_name, ship_to_id")
            supplier_names = [x['supplier_name'] for x in suppliers2]
            warehouse_names = [x['warehouse_name'] for x in warehouses2]
            customer_names = [x['customer_name'] for x in customers2]
            ship_to_labels = [f"{x['ship_to_name']} | {x.get('ship_to_id') or '-'}" for x in ship_to2]
            supplier_id_map = {x['supplier_name']: x['id'] for x in suppliers2}
            warehouse_id_map = {x['warehouse_name']: x['id'] for x in warehouses2}
            customer_id_map = {x['customer_name']: x['id'] for x in customers2}
            ship_to_id_map = {f"{x['ship_to_name']} | {x.get('ship_to_id') or '-'}": x['id'] for x in ship_to2}
            sh1, sh2 = st.columns(2)
            with sh1:
                edit_shipment_no = st.text_input('Edit Shipment Number', edit_ship['shipment_no'], key='edit_header_shipment_no')
                edit_invoice_no = st.text_input('Edit Original Invoice Number', edit_ship['invoice_no'], key='edit_header_invoice_no')
                edit_shipment_date = st.text_input('Edit Shipment Date YYYY-MM-DD', edit_ship['shipment_date'] or '', key='edit_header_date')
            with sh2:
                current_supplier = edit_ship.get('supplier_name') if edit_ship.get('supplier_name') in supplier_names else supplier_names[0] if supplier_names else ''
                current_warehouse = edit_ship.get('warehouse_name') if edit_ship.get('warehouse_name') in warehouse_names else warehouse_names[0] if warehouse_names else ''
                edit_supplier = st.selectbox('Edit Supplier', supplier_names, index=supplier_names.index(current_supplier) if current_supplier in supplier_names else 0, key='edit_header_supplier')
                edit_warehouse = st.selectbox('Edit Warehouse', warehouse_names, index=warehouse_names.index(current_warehouse) if current_warehouse in warehouse_names else 0, key='edit_header_warehouse')
                edit_remarks = st.text_area('Edit Remarks', edit_ship['remarks'] or '', key='edit_header_remarks')
                current_customer = edit_ship.get('customer_name') if edit_ship.get('customer_name') in customer_names else customer_names[0] if customer_names else ''
                edit_customer = st.selectbox('Edit Customer', customer_names, index=customer_names.index(current_customer) if current_customer in customer_names else 0, key='edit_header_customer')
                current_ship_to_label = next((lbl for lbl in ship_to_labels if lbl.startswith(str(edit_ship.get('ship_to_name') or '') + ' |')), ship_to_labels[0] if ship_to_labels else '')
                edit_ship_to = st.selectbox('Edit Ship To', ship_to_labels, index=ship_to_labels.index(current_ship_to_label) if current_ship_to_label in ship_to_labels else 0, key='edit_header_ship_to')
            if st.button('Update Shipment Header', type='primary', key='update_shipment_header'):
                if not edit_shipment_no.strip() or not edit_invoice_no.strip():
                    st.error('Shipment Number and Original Invoice Number are mandatory.')
                else:
                    try:
                        execute_query('\n                                    UPDATE shipments\n                                    SET shipment_no=?, invoice_no=?, shipment_date=?, supplier_id=?, warehouse_id=?, customer_id=?, ship_to_master_id=?, remarks=?\n                                    WHERE id=?\n                                ', (edit_shipment_no.strip(), edit_invoice_no.strip(), edit_shipment_date.strip(), supplier_id_map[edit_supplier], warehouse_id_map[edit_warehouse], customer_id_map.get(edit_customer), ship_to_id_map.get(edit_ship_to), edit_remarks, edit_ship['id']))
                        st.success('Shipment header updated successfully.')
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error('Duplicate shipment number found.')
    if st.session_state.user['role'] == 'super_admin':
        st.divider()
        st.subheader('Super Admin: Edit Old Pallet / Product Entry')
        old_rows = fetch_all('\n                    SELECT b.id, b.fifo_row_id, s.shipment_no, s.invoice_no, b.pallet_no, b.box_no,\n                           p.product_code, p.product_name, b.po_number, b.po_date, b.original_qty, b.unit_price, b.currency, b.amount\n                    FROM shipment_boxes b\n                    JOIN shipments s ON b.shipment_id = s.id\n                    JOIN products p ON b.product_id = p.id\n                    ORDER BY b.id DESC\n                ')
        if old_rows:
            row_map = {f"{r['id']} | {r['shipment_no']} | Pallet {r['pallet_no']} | {r['product_code']} | Qty {r['original_qty']}": r for r in old_rows}
            selected_old_key = searchable_selectbox('Select Old Row to Edit', list(row_map.keys()), key='super_edit_old_row')
            selected_old = row_map[selected_old_key]
            e1, e2, e3, e4, e5, e6 = st.columns(6)
            with e1:
                edit_fifo_row_id = st.number_input('Edit FIFO ID', min_value=1, value=int(selected_old.get('fifo_row_id') or selected_old.get('id') or 1), step=1)
                edit_pallet = st.text_input('Edit Pallet No', selected_old['pallet_no'])
            with e2:
                edit_box = st.text_input('Edit Box No', selected_old['box_no'] or '')
            with e3:
                edit_po_number = st.text_input('Edit PO Number', selected_old.get('po_number') or '')
            with e4:
                edit_po_date = st.text_input('Edit PO Date YYYY-MM-DD', str(selected_old.get('po_date') or ''))
            with e5:
                edit_qty = st.number_input('Edit Quantity', min_value=0.0, value=float(selected_old['original_qty'] or 0), step=1.0)
            with e6:
                edit_price = st.number_input('Edit Price', min_value=0.0, value=float(selected_old['unit_price'] or 0), step=1.0)
            edit_currency = st.selectbox('Edit Currency', CURRENCIES, index=CURRENCIES.index(selected_old['currency']) if selected_old['currency'] in CURRENCIES else 0, key='super_edit_currency')
            edit_amount = edit_qty * edit_price
            st.markdown(f'<div class="total-box">New Amount: {edit_amount:,.2f} {edit_currency}</div>', unsafe_allow_html=True)
            if st.button('Update Old Row', type='primary'):
                try:
                    execute_query('\n                                UPDATE shipment_boxes\n                                SET fifo_row_id=?, pallet_no=?, box_no=?, po_number=?, po_date=?, original_qty=?, unit_price=?, currency=?, amount=?\n                                WHERE id=?\n                            ', (edit_fifo_row_id, edit_pallet.strip(), edit_box.strip(), edit_po_number.strip(), edit_po_date.strip() or None, edit_qty, edit_price, edit_currency, edit_amount, selected_old['id']))
                    st.success('Old row updated successfully.')
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error('Cannot update. This pallet number is already used for same product.')
        else:
            st.info('No old rows available for editing.')

render_slogan_footer()
st.markdown('<div class="footer">COPYRIGHT BY FOUR STAR INDUSTRIES PVT. LTD.</div>', unsafe_allow_html=True)
