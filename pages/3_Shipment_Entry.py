from common import *


def _local_effective_product_price(product_id, effective_date=None):
    try:
        return get_effective_product_price(product_id, effective_date)
    except Exception:
        try:
            rows = fetch_all("SELECT unit_price, currency FROM products WHERE id=?", (product_id,))
            if rows:
                return float(rows[0].get("unit_price") or 0), (rows[0].get("currency") or "")
        except Exception:
            pass
    return 0.0, ""


def _customer_label(row):
    return f'{row.get("customer_name") or "-"} | {row.get("company_code") or "-"} | ID {row.get("id")}'


def _ship_to_label(row):
    return f'{row.get("ship_to_name") or "-"} | {row.get("ship_to_id") or "-"} | ID {row.get("id")}'


def _safe_widget_state(key, options):
    try:
        if key in st.session_state and st.session_state.get(key) not in options:
            del st.session_state[key]
    except Exception:
        pass


page_setup()
require_page_edit('shipment')
show_edit_permission_status('shipment')

show_header('Shipment Entry with Pallet / Product Rows', 'Product-linked Customer and Ship To selection')
access_notice()
render_shipment_subnav('shipment')
ensure_shipment_status_columns()
require_delivery_master_relationship_schema("Shipment Entry")
render_tuesday_shipment_status_popup()

suppliers = fetch_all('SELECT * FROM suppliers ORDER BY supplier_name')
customers = fetch_all('SELECT * FROM customers ORDER BY customer_name, id')
ship_to_rows = fetch_all("SELECT * FROM ship_to_masters WHERE COALESCE(is_active, TRUE)=TRUE ORDER BY ship_to_name, ship_to_id, id")
warehouses = filter_warehouse_rows_for_current_user(fetch_all('SELECT * FROM warehouses ORDER BY warehouse_name'))
warehouse_info = {w.get('warehouse_name'): w for w in warehouses}
products = filter_product_rows_for_current_user(fetch_all('SELECT * FROM products ORDER BY product_code, id'))
forwarders = fetch_all('SELECT * FROM forwarders ORDER BY forwarder_name')
incoterms = fetch_all('SELECT * FROM incoterms ORDER BY incoterm_name')

if not suppliers or not warehouses or not products or not customers or not ship_to_rows:
    st.warning('Create Supplier, Warehouse, Ship To, Customer and Product masters first. Customer Ship To and Product Customer links are required.')
else:
    supplier_map = {x['supplier_name']: x['id'] for x in suppliers}
    warehouse_map = {x['warehouse_name']: x['id'] for x in warehouses}
    forwarder_map = {x['forwarder_name']: x['id'] for x in forwarders}
    incoterm_map = {x['incoterm_name']: x['id'] for x in incoterms}

    customer_label_map = {_customer_label(x): x for x in customers}
    customer_label_by_id = {int(x['id']): label for label, x in customer_label_map.items()}
    ship_to_label_map = {_ship_to_label(x): x for x in ship_to_rows}
    ship_to_label_by_id = {int(x['id']): label for label, x in ship_to_label_map.items()}

    product_options = [f"{x['product_code']} | {x.get('product_name') or ''} | ID {x['id']}" for x in products]
    product_info = {f"{x['product_code']} | {x.get('product_name') or ''} | ID {x['id']}": x for x in products}

    if 'shipment_temp_rows' not in st.session_state:
        st.session_state.shipment_temp_rows = []

    def get_next_fifo_row_id():
        db_max = fetch_all('SELECT COALESCE(MAX(fifo_row_id), 0) AS max_id FROM shipment_boxes')
        max_db = int(db_max[0]['max_id'] or 0) if db_max else 0
        temp_ids = [int(r.get('fifo_row_id') or 0) for r in st.session_state.get('shipment_temp_rows', [])]
        max_temp = max(temp_ids) if temp_ids else 0
        return max(max_db, max_temp) + 1

    st.markdown('''
        <div class="card" style="margin-bottom:14px;">
            <b>REQUIRED MASTER FLOW</b><br>
            Select Product → Customer / Bill To loads from Product Master → Ship To loads from the selected Customer Master.
            Tick Manual Header Override only when this shipment must use a different Customer or Ship To.
        </div>
    ''', unsafe_allow_html=True)

    st.markdown('<div class="input-section-title">Product and Automatic Customer / Ship To</div>', unsafe_allow_html=True)
    rel_col1, rel_col2 = st.columns([2.4, 1.2])
    with rel_col1:
        selected_product = st.selectbox(
            'Product Code *',
            product_options,
            key='shipment_product_select_sn2713',
            help='This Product controls the automatic Customer / Bill To and Ship To relationship.',
        )
    with rel_col2:
        manual_relationship_override = st.checkbox(
            'Manual Customer / Ship To Override',
            value=False,
            key='shipment_manual_relationship_override_sn2713',
            help='Enable only when the shipment header must differ from the Product → Customer → Ship To master relationship.',
        )

    selected_product_data = product_info[selected_product]
    selected_product_id = int(selected_product_data['id'])
    linked_customer_id = int(selected_product_data.get('customer_id')) if selected_product_data.get('customer_id') else None
    linked_customer_row = next((x for x in customers if int(x.get('id') or 0) == int(linked_customer_id or 0)), {}) if linked_customer_id else {}
    # Required canonical chain: Product.customer_id -> Customer.ship_to_master_id.
    linked_ship_to_id = int(linked_customer_row.get('ship_to_master_id')) if linked_customer_row.get('ship_to_master_id') else None
    linked_ship_to_row = next((x for x in ship_to_rows if int(x.get('id') or 0) == int(linked_ship_to_id or 0)), {}) if linked_ship_to_id else {}
    linked_bill_to_address_ok = bool(str(linked_customer_row.get('address') or '').strip())
    linked_ship_to_address_ok = bool(str(linked_ship_to_row.get('addressline1') or '').strip())
    linked_ship_to_active = bool(linked_ship_to_row) and linked_ship_to_row.get('is_active') is not False
    relation_valid = bool(
        linked_customer_id and linked_customer_row and linked_bill_to_address_ok
        and linked_ship_to_id and linked_ship_to_row and linked_ship_to_active and linked_ship_to_address_ok
    )

    if relation_valid:
        st.success(
            f"Automatic relationship: {selected_product_data.get('product_code')} → "
            f"{linked_customer_row.get('customer_name')} → {linked_ship_to_row.get('ship_to_name')}"
        )
    else:
        st.error(
            'This Product does not have the complete required relationship. In Masters, Product must have Customer; '
            'Customer must have Bill To Address and an active Ship To; Ship To must have Address Line 1.'
        )

    existing_rows = st.session_state.get('shipment_temp_rows', [])
    existing_customer_id = existing_rows[0].get('header_customer_id') if existing_rows else None
    existing_ship_to_id = existing_rows[0].get('header_ship_to_master_id') if existing_rows else None
    relationship_conflict = bool(
        existing_rows
        and relation_valid
        and (
            int(existing_customer_id or 0) != int(linked_customer_id or 0)
            or int(existing_ship_to_id or 0) != int(linked_ship_to_id or 0)
        )
    )

    relation_context = f"{selected_product_id}|{len(existing_rows)}|{manual_relationship_override}"
    if st.session_state.get('_shipment_relation_context_sn2713') != relation_context:
        if not manual_relationship_override:
            target_customer_id = existing_customer_id if existing_rows else linked_customer_id
            target_ship_to_id = existing_ship_to_id if existing_rows else linked_ship_to_id
            if target_customer_id and int(target_customer_id) in customer_label_by_id:
                st.session_state['shipment_customer_select_sn2713'] = customer_label_by_id[int(target_customer_id)]
            if target_ship_to_id and int(target_ship_to_id) in ship_to_label_by_id:
                st.session_state['shipment_ship_to_select_sn2713'] = ship_to_label_by_id[int(target_ship_to_id)]
        st.session_state['_shipment_relation_context_sn2713'] = relation_context

    if relationship_conflict and not manual_relationship_override:
        st.error(
            'The selected Product belongs to a different Customer / Ship To than the unsaved shipment rows. '
            'Save or clear the existing rows, or enable Manual Customer / Ship To Override after verification.'
        )

    st.markdown('<div class="sap-grid-card"><div class="sap-grid-card-title">Original Invoice Details</div>', unsafe_allow_html=True)
    inv_top1, inv_top2 = st.columns(2)
    with inv_top1:
        invoice_no = st.text_input('Original Invoice Number', key='shipment_original_invoice_top')
    with inv_top2:
        shipment_date = st.date_input('Original Invoice Date', value=date.today(), key='shipment_original_invoice_date_top')
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div style="height:14px;"></div>', unsafe_allow_html=True)

    _safe_widget_state('shipment_customer_select_sn2713', list(customer_label_map.keys()))
    if 'shipment_customer_select_sn2713' not in st.session_state:
        fallback_customer = linked_customer_id if relation_valid else customers[0]['id']
        st.session_state['shipment_customer_select_sn2713'] = customer_label_by_id[int(fallback_customer)]

    h1, h2 = st.columns(2)
    with h1:
        shipment_no = st.text_input('Shipment Number / BL No / Seaway Bill No', key='shipment_no_bl_seaway')
        shipping_bill_no = st.text_input('Shipping Bill No.', key='shipment_shipping_bill_no')
        if forwarder_map:
            forwarder_name = st.selectbox('Forwarder Name', list(forwarder_map.keys()), key='shipment_forwarder_name')
        else:
            forwarder_name = st.text_input('Forwarder Name', key='shipment_forwarder_name')
            forwarder_map = {forwarder_name: None}
        supplier = st.selectbox('Supplier', list(supplier_map.keys()), key='shipment_supplier')
        selected_customer_label = st.selectbox(
            'Customer / Bill To *',
            list(customer_label_map.keys()),
            key='shipment_customer_select_sn2713',
            disabled=not manual_relationship_override,
        )
        selected_customer_row = customer_label_map[selected_customer_label]
        selected_customer_id = int(selected_customer_row['id'])
        if not str(selected_customer_row.get('address') or '').strip():
            st.error('The selected Customer has no Bill To Address. Complete Customer Master before Shipment Entry.')
            st.stop()
        if not selected_customer_row.get('ship_to_master_id'):
            st.error('The selected Customer does not have the required Ship To link. Update Customer Master before Shipment Entry.')
            st.stop()
        attachment = st.file_uploader('Attach Shipment File', key='auto_file_uploader_1')

    # When Customer is manually changed, load that Customer's required Ship To
    # before the Ship To widget is created.
    customer_tracker_key = '_shipment_customer_tracker_sn2713'
    if st.session_state.get(customer_tracker_key) != selected_customer_id:
        if manual_relationship_override:
            customer_ship_to_id = selected_customer_row.get('ship_to_master_id')
            if customer_ship_to_id and int(customer_ship_to_id) in ship_to_label_by_id:
                st.session_state['shipment_ship_to_select_sn2713'] = ship_to_label_by_id[int(customer_ship_to_id)]
        st.session_state[customer_tracker_key] = selected_customer_id

    _safe_widget_state('shipment_ship_to_select_sn2713', list(ship_to_label_map.keys()))
    if 'shipment_ship_to_select_sn2713' not in st.session_state:
        fallback_ship_to = selected_customer_row.get('ship_to_master_id') or linked_ship_to_id or ship_to_rows[0]['id']
        st.session_state['shipment_ship_to_select_sn2713'] = ship_to_label_by_id[int(fallback_ship_to)]

    with h2:
        shipment_doc_date = st.date_input('Shipment / BL / Seaway Bill Date', value=date.today(), key='shipment_doc_date')
        shipping_bill_date = st.date_input('Shipping Bill Date', value=date.today(), key='shipment_shipping_bill_date')
        if incoterm_map:
            incoterm = st.selectbox('Incoterm', list(incoterm_map.keys()), key='shipment_incoterm')
        else:
            incoterm = st.text_input('Incoterm', key='shipment_incoterm')
            incoterm_map = {incoterm: None}
        warehouse = st.selectbox('Warehouse', list(warehouse_map.keys()), key='shipment_warehouse')
        selected_shipment_time_days = int(warehouse_info.get(warehouse, {}).get('shipment_time_days') or 0)
        shipment_status = st.selectbox('Shipment Status', ['In Transit', 'Delivered'], index=0, key='shipment_status_select')
        warehouse_delivery_date = None
        if shipment_status == 'Delivered':
            warehouse_delivery_date = st.date_input('Delivered to WH Date', value=date.today(), key='shipment_delivered_to_wh_date')
        else:
            st.caption('In Transit: Delivered to WH Date not applicable. Coverage uses Shipment Date + Shipment Time Days.')
        selected_ship_to_label = st.selectbox(
            'Ship To *',
            list(ship_to_label_map.keys()),
            key='shipment_ship_to_select_sn2713',
            disabled=not manual_relationship_override,
        )
        selected_shipment_ship_to = ship_to_label_map[selected_ship_to_label]
        selected_ship_to_id = int(selected_shipment_ship_to['id'])
        if selected_shipment_ship_to.get('is_active') is False:
            st.error('The selected Ship To is inactive. Select an active Ship To before saving.')
            st.stop()
        if not str(selected_shipment_ship_to.get('addressline1') or '').strip():
            st.error('The selected Ship To has no Address Line 1. Complete Ship To Master before Shipment Entry.')
            st.stop()
        remarks = st.text_area('Remarks', key='auto_textarea_1')

    bill_to_address = str(selected_customer_row.get('address') or '').strip() or '-'
    ship_to_address = '\n'.join([
        str(selected_shipment_ship_to.get('addressline1') or '').strip(),
        str(selected_shipment_ship_to.get('addressline2') or '').strip(),
        str(selected_shipment_ship_to.get('addressline3') or '').strip(),
    ]).strip() or '-'
    addr1, addr2 = st.columns(2)
    with addr1:
        st.markdown(f"**Bill To Address — Customer Master**  \n{html.escape(bill_to_address).replace(chr(10), '<br>')}", unsafe_allow_html=True)
    with addr2:
        st.markdown(f"**Ship To Address — Customer-linked Ship To Master**  \n{html.escape(ship_to_address).replace(chr(10), '<br>')}", unsafe_allow_html=True)

    st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)
    st.subheader('Add Pallet / Product Row')
    st.caption('Change Product above to add another row. Products with a different automatic Customer / Ship To cannot be mixed unless Manual Header Override is enabled.')

    st.markdown('''
        <style>
        .shipment-grid-label {font-family:Aptos,Arial,sans-serif;font-size:15px;font-weight:900;color:#003B73;margin-bottom:6px;min-height:22px;}
        .amount-input-look {height:52px;border-radius:10px;background:#f3f6fa;display:flex;align-items:center;justify-content:center;font-family:Aptos,Arial,sans-serif;font-size:16px;font-weight:700;color:#1f2937;border:1px solid transparent;}
        </style>
    ''', unsafe_allow_html=True)

    r1, r2, r3, r4, r5, r6, r7, r8, r9 = st.columns([1.0, 1.0, 2.05, 1.15, 1.05, 0.85, 0.85, 0.75, 1.0])
    with r1:
        st.markdown('<div class="shipment-grid-label">Pallet Number</div>', unsafe_allow_html=True)
        pallet_no = st.text_input('Pallet Number', key='shipment_grid_pallet_no', label_visibility='collapsed')
    with r2:
        st.markdown('<div class="shipment-grid-label">Box Number</div>', unsafe_allow_html=True)
        box_no = st.text_input('Box Number', key='shipment_grid_box_no', label_visibility='collapsed')
    with r3:
        st.markdown('<div class="shipment-grid-label">Product Code</div>', unsafe_allow_html=True)
        st.text_input('Selected Product', value=f"{selected_product_data.get('product_code')} | {selected_product_data.get('product_name') or ''}", disabled=True, key=f"shipment_selected_product_display_{selected_product_id}", label_visibility='collapsed')

    auto_price, effective_currency = _local_effective_product_price(selected_product_id, shipment_date)
    auto_currency = effective_currency or selected_product_data.get('currency') or 'USD'
    product_id_for_key = str(selected_product_id)
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
        unit_price = st.number_input('Price', min_value=0.0, value=float(auto_price or 0), step=0.001, format='%.3f', key=f'shipment_grid_price_{product_id_for_key}', label_visibility='collapsed')
    with r8:
        st.markdown('<div class="shipment-grid-label">Currency</div>', unsafe_allow_html=True)
        currency = st.selectbox('Currency', CURRENCIES, index=CURRENCIES.index(auto_currency) if auto_currency in CURRENCIES else 0, key=f'shipment_grid_currency_{product_id_for_key}', label_visibility='collapsed')
    with r9:
        st.markdown('<div class="shipment-grid-label">Amount</div>', unsafe_allow_html=True)
        amount = quantity * unit_price
        st.markdown(f'<div class="amount-input-look">{amount:,.3f} {currency}</div>', unsafe_allow_html=True)

    add_disabled = bool(relationship_conflict and not manual_relationship_override)
    if st.button('Add Row to Table', type='primary', key='shipment_grid_add_row', disabled=add_disabled):
        if not pallet_no.strip():
            st.error('Pallet Number is mandatory.')
        elif quantity <= 0:
            st.error('Quantity must be greater than zero.')
        elif not relation_valid:
            st.error('Complete Product → Customer → Ship To relationship is mandatory. Update Product Master and Customer Master before adding the row.')
        elif not selected_customer_id or not selected_ship_to_id:
            st.error('Customer / Bill To and Ship To are mandatory.')
        elif not str(selected_customer_row.get('address') or '').strip():
            st.error('Bill To Address is mandatory in Customer Master.')
        elif not str(selected_shipment_ship_to.get('addressline1') or '').strip():
            st.error('Address Line 1 is mandatory in Ship To Master.')
        else:
            new_key = (pallet_no.strip(), selected_product_id)
            existing_keys = [(r['pallet_no'], r['product_id']) for r in st.session_state.shipment_temp_rows]
            old_match = fetch_all('''
                SELECT b.id, s.shipment_no
                FROM shipment_boxes b
                JOIN shipments s ON b.shipment_id=s.id
                WHERE b.pallet_no=? AND b.product_id=?
            ''', (pallet_no.strip(), selected_product_id))
            if new_key in existing_keys:
                st.error('Duplicate pallet/product row already added in this shipment.')
            elif old_match and str(old_match[0].get('shipment_no') or '').strip() != shipment_no.strip():
                st.error(f"This pallet number is already used for the same product in shipment {old_match[0]['shipment_no']}. It cannot be used again.")
            else:
                recovering_old_partial_row = bool(old_match and str(old_match[0].get('shipment_no') or '').strip() == shipment_no.strip())
                st.session_state.shipment_temp_rows.append({
                    'fifo_row_id': get_next_fifo_row_id(),
                    'pallet_no': pallet_no.strip(),
                    'box_no': (box_no or '').strip(),
                    'po_number': (row_po_number or '').strip(),
                    'po_date': str(row_po_date),
                    'product_id': selected_product_id,
                    'product_code': selected_product_data['product_code'],
                    'product_name': selected_product_data.get('product_name') or '',
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'currency': currency,
                    'amount': amount,
                    'header_customer_id': selected_customer_id,
                    'header_customer_name': selected_customer_row.get('customer_name') or '',
                    'header_ship_to_master_id': selected_ship_to_id,
                    'header_ship_to_name': selected_shipment_ship_to.get('ship_to_name') or '',
                    'master_customer_id': linked_customer_id,
                    'master_ship_to_master_id': linked_ship_to_id,
                    'manual_relationship_override': bool(manual_relationship_override),
                })
                if recovering_old_partial_row:
                    st.info('This pallet already belongs to the same Shipment Number from an earlier incomplete save. It will be reconciled safely when you save the shipment.')
                else:
                    st.success('Row added with Customer / Ship To relationship.')
                st.rerun()

    st.subheader('Current Shipment Rows')
    temp_df = pd.DataFrame(st.session_state.shipment_temp_rows)
    if not temp_df.empty:
        visible_cols = [
            'fifo_row_id', 'pallet_no', 'box_no', 'po_number', 'po_date',
            'product_code', 'product_name', 'header_customer_name', 'header_ship_to_name',
            'quantity', 'unit_price', 'currency', 'amount',
        ]
        display_df = add_total_row(temp_df[visible_cols])
        st.dataframe(style_total_row(display_df), width='stretch', hide_index=True)
        total_qty = temp_df['quantity'].sum()
        total_amount = temp_df['amount'].sum()
        st.markdown(f'<div class="total-box">Total Quantity: {total_qty} &nbsp;&nbsp; | &nbsp;&nbsp; Total Amount: {total_amount:,.3f}</div>', unsafe_allow_html=True)
        if st.button('Clear Unsaved Rows', key='clear_unsaved_shipment_rows'):
            st.session_state.shipment_temp_rows = []
            st.session_state.pop('_shipment_relation_context_sn2713', None)
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
        elif any(not r.get('master_customer_id') or not r.get('master_ship_to_master_id') for r in st.session_state.shipment_temp_rows):
            st.error('Every Product row must have the required Product → Customer → Ship To master relationship before saving.')
        elif any(int(r.get('header_customer_id') or 0) != selected_customer_id or int(r.get('header_ship_to_master_id') or 0) != selected_ship_to_id for r in st.session_state.shipment_temp_rows):
            st.error('Unsaved rows contain a different Customer / Ship To header. Clear and re-add the rows under one verified shipment header.')
        elif not str(selected_customer_row.get('address') or '').strip():
            st.error('Bill To Address is mandatory in Customer Master before saving Shipment.')
        elif not str(selected_shipment_ship_to.get('addressline1') or '').strip():
            st.error('Address Line 1 is mandatory in Ship To Master before saving Shipment.')
        else:
            try:
                total_amount = sum(r['amount'] for r in st.session_state.shipment_temp_rows)
                first_po_number = st.session_state.shipment_temp_rows[0].get('po_number', '')
                first_po_date = st.session_state.shipment_temp_rows[0].get('po_date') or None
                first_currency = st.session_state.shipment_temp_rows[0]['currency']
                path = save_upload(attachment, f'shipment_{shipment_no}')
                shipment_header = {
                    'shipment_no': shipment_no.strip(),
                    'invoice_no': invoice_no.strip(),
                    'po_number': first_po_number,
                    'po_date': first_po_date,
                    'shipment_date': str(shipment_date),
                    'supplier_id': supplier_map[supplier],
                    'warehouse_id': warehouse_map[warehouse],
                    'customer_id': selected_customer_id,
                    'ship_to_master_id': selected_ship_to_id,
                    'shipment_time_days': selected_shipment_time_days,
                    'shipment_status': shipment_status,
                    'warehouse_delivery_date': str(warehouse_delivery_date) if warehouse_delivery_date else None,
                    'invoice_amount': total_amount,
                    'currency': first_currency,
                    'attachment_path': path,
                    'remarks': remarks,
                    'shipping_bill_no': shipping_bill_no.strip(),
                    'shipping_bill_date': str(shipping_bill_date),
                    'shipment_doc_date': str(shipment_doc_date),
                    'forwarder_name': forwarder_name,
                    'incoterm': incoterm,
                    'forwarder_id': forwarder_map.get(forwarder_name),
                    'incoterm_id': incoterm_map.get(incoterm),
                }
                save_result = save_shipment_atomic(shipment_header, st.session_state.shipment_temp_rows)
                shipment_id = save_result['shipment_id']

                if save_result.get('inserted_boxes', 0) > 0 or not save_result.get('recovered'):
                    notify_event(
                        'shipment',
                        'Shipment Recovered / Completed' if save_result.get('recovered') else 'New Shipment Created',
                        f"Shipment No: {shipment_no}\nOriginal Invoice: {invoice_no}\nCustomer: {selected_customer_row.get('customer_name')}\nShip To: {selected_shipment_ship_to.get('ship_to_name')}\nAmount: {total_amount}\nCurrency: {first_currency}",
                    )
                st.session_state.shipment_temp_rows = []
                for key in (
                    '_shipment_relation_context_sn2713',
                    '_shipment_customer_tracker_sn2713',
                    'shipment_customer_select_sn2713',
                    'shipment_ship_to_select_sn2713',
                ):
                    st.session_state.pop(key, None)
                clear_cache_after_write()
                if save_result.get('recovered'):
                    rerun_with_success(
                        f"Shipment {shipment_no.strip()} recovered/completed successfully. "
                        f"Existing rows reused: {save_result.get('existing_boxes_reused', 0)}; "
                        f"new rows saved: {save_result.get('inserted_boxes', 0)}."
                    )
                else:
                    rerun_with_success('Shipment and pallet/product rows saved successfully in one database transaction.')
            except Exception as exc:
                st.error(f'Shipment save failed. The complete database transaction was rolled back; no partial shipment was created. Details: {exc}')

    st.divider()
    st.caption('Last Shipments and Edit Shipment sections are available under Shipment subpages.')
    st.info('Shipment status updates are available under Shipment > Shipment Status.')
    try:
        st.page_link('pages/16_Shipment_Status.py', label='Open Shipment Status')
    except Exception:
        pass

render_slogan_footer()
st.markdown('<div class="footer">COPYRIGHT BY FOUR STAR INDUSTRIES PVT. LTD.</div>', unsafe_allow_html=True)
