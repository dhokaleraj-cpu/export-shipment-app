from common import *

page_setup()

require_page_edit('shipment')
show_edit_permission_status('shipment')

show_header('Shipment Entry with Pallet / Product Rows')
access_notice()
render_shipment_subnav('shipment')
suppliers = fetch_all('SELECT * FROM suppliers ORDER BY supplier_name')
customers = fetch_all('SELECT * FROM customers ORDER BY customer_name')
ship_to_rows = fetch_all("SELECT * FROM ship_to_masters WHERE COALESCE(is_active, TRUE)=TRUE ORDER BY ship_to_name, ship_to_id")
warehouses = filter_warehouse_rows_for_current_user(fetch_all('SELECT * FROM warehouses ORDER BY warehouse_name'))
warehouse_info = {w.get('warehouse_name'): w for w in warehouses}
products = filter_product_rows_for_current_user(fetch_all('SELECT * FROM products ORDER BY product_code'))
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
    st.caption('Last Shipments and Edit Shipment sections moved to separate subpages for faster Shipment Entry loading.')

render_slogan_footer()
st.markdown('<div class="footer">COPYRIGHT BY FOUR STAR INDUSTRIES PVT. LTD.</div>', unsafe_allow_html=True)
