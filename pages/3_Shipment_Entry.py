from common import *

SN2722_MARKER = "SN 27.22 SIMPLE SHIPMENT HEADER ACTIVE"

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

def _product_label(row):
    return f'{row.get("product_code") or "-"} | {row.get("product_name") or ""} | ID {row.get("id")}'

page_setup()
require_page_edit('shipment')
show_edit_permission_status('shipment')
show_header('Shipment Entry with Pallet / Product Rows', 'Customer / Bill To + Ship To header; Product selected only on each item row')
access_notice()
render_shipment_subnav('shipment')
ensure_shipment_status_columns()
require_delivery_master_relationship_schema('Shipment Entry')
render_tuesday_shipment_status_popup()

# Retire the old Product-first header state. Only unsaved UI rows are cleared once.
if st.session_state.get('_shipment_ui_version') != 'SN27.22':
    st.session_state['shipment_temp_rows'] = []
    for _key in list(st.session_state.keys()):
        if str(_key).startswith((
            'shipment_product_select_', 'shipment_manual_relationship_',
            'shipment_customer_select_sn2713', 'shipment_ship_to_select_sn2713'
        )):
            st.session_state.pop(_key, None)
    st.session_state['_shipment_ui_version'] = 'SN27.22'

suppliers = fetch_all('SELECT * FROM suppliers ORDER BY supplier_name')
customers = fetch_all('SELECT * FROM customers ORDER BY customer_name, id')
ship_to_rows = fetch_all("SELECT * FROM ship_to_masters WHERE COALESCE(is_active, TRUE)=TRUE ORDER BY ship_to_name, ship_to_id, id")
warehouses = filter_warehouse_rows_for_current_user(fetch_all('SELECT * FROM warehouses ORDER BY warehouse_name'))
warehouse_info = {w.get('warehouse_name'): w for w in warehouses}
forwarders = fetch_all('SELECT * FROM forwarders ORDER BY forwarder_name')
incoterms = fetch_all('SELECT * FROM incoterms ORDER BY incoterm_name')

if not suppliers or not warehouses or not customers or not ship_to_rows:
    st.warning('Create Supplier, Warehouse, Customer and Ship To masters first.')
else:
    supplier_map = {x['supplier_name']: x['id'] for x in suppliers}
    warehouse_map = {x['warehouse_name']: x['id'] for x in warehouses}
    forwarder_map = {x['forwarder_name']: x['id'] for x in forwarders}
    incoterm_map = {x['incoterm_name']: x['id'] for x in incoterms}
    customer_label_map = {_customer_label(x): x for x in customers}
    customer_label_by_id = {int(x['id']): label for label, x in customer_label_map.items()}
    ship_to_label_map = {_ship_to_label(x): x for x in ship_to_rows}
    ship_to_label_by_id = {int(x['id']): label for label, x in ship_to_label_map.items()}

    if 'shipment_temp_rows' not in st.session_state:
        st.session_state.shipment_temp_rows = []
    existing_rows = st.session_state.get('shipment_temp_rows', [])

    st.markdown('''
        <div class="card" style="margin-bottom:14px;border:2px solid #0b6fb8;">
            <b>SN 27.22 SIMPLE SHIPMENT HEADER ACTIVE</b><br>
            Shipment header contains only <b>Customer / Bill To</b> and <b>Ship To</b>.
            There is no Product / Part selection in the shipment header.<br>
            Select Product only inside <b>Add Pallet / Product Row</b>; add different Products as separate rows under the same Shipment.
        </div>
    ''', unsafe_allow_html=True)

    locked_customer_id = None
    locked_ship_to_id = None
    if existing_rows:
        try:
            locked_customer_id = int(existing_rows[0].get('header_customer_id') or 0)
            locked_ship_to_id = int(existing_rows[0].get('header_ship_to_master_id') or 0)
        except Exception:
            pass

    customer_options = list(customer_label_map.keys())
    if existing_rows and locked_customer_id in customer_label_by_id:
        st.session_state['shipment_customer_header_sn2722'] = customer_label_by_id[locked_customer_id]
    elif st.session_state.get('shipment_customer_header_sn2722') not in customer_options:
        st.session_state.pop('shipment_customer_header_sn2722', None)

    st.markdown('<div class="input-section-title">Shipment Header</div>', unsafe_allow_html=True)
    hc1, hc2 = st.columns(2)
    with hc1:
        selected_customer_label = st.selectbox(
            'Customer / Bill To *', customer_options,
            key='shipment_customer_header_sn2722', disabled=bool(existing_rows),
            help='Customer is selected at shipment header level. Product is selected later on each item row.'
        )
    selected_customer_row = customer_label_map[selected_customer_label]
    selected_customer_id = int(selected_customer_row['id'])

    linked_ship_to_id = selected_customer_row.get('ship_to_master_id')
    try:
        linked_ship_to_id = int(linked_ship_to_id) if linked_ship_to_id else None
    except Exception:
        linked_ship_to_id = None

    ship_to_options = list(ship_to_label_map.keys())
    ship_key = f'shipment_ship_to_header_sn2722_customer_{selected_customer_id}'
    if existing_rows and locked_ship_to_id in ship_to_label_by_id:
        st.session_state[ship_key] = ship_to_label_by_id[locked_ship_to_id]
    elif st.session_state.get(ship_key) not in ship_to_options:
        st.session_state.pop(ship_key, None)
    default_ship_index = ship_to_options.index(ship_to_label_by_id[linked_ship_to_id]) if linked_ship_to_id in ship_to_label_by_id else 0

    with hc2:
        selected_ship_to_label = st.selectbox(
            'Ship To *', ship_to_options, index=default_ship_index,
            key=ship_key, disabled=bool(existing_rows),
            help='Customer-linked Ship To is the default. Change it before the first item row if required.'
        )
    selected_shipment_ship_to = ship_to_label_map[selected_ship_to_label]
    selected_ship_to_id = int(selected_shipment_ship_to['id'])

    if existing_rows:
        st.caption('Customer and Ship To are locked after the first item row. Use Clear Unsaved Rows to change the shipment header.')

    bill_to_address = str(selected_customer_row.get('address') or '').strip() or '-'
    ship_to_address = '\n'.join([
        str(selected_shipment_ship_to.get('addressline1') or '').strip(),
        str(selected_shipment_ship_to.get('addressline2') or '').strip(),
        str(selected_shipment_ship_to.get('addressline3') or '').strip(),
    ]).strip() or '-'
    addr1, addr2 = st.columns(2)
    with addr1:
        st.markdown(f"**Bill To Address**  \n{html.escape(bill_to_address).replace(chr(10), '<br>')}", unsafe_allow_html=True)
    with addr2:
        st.markdown(f"**Ship To Address**  \n{html.escape(ship_to_address).replace(chr(10), '<br>')}", unsafe_allow_html=True)

    # Product list is loaded only for the selected Customer, but there is NO header Product field.
    customer_products = filter_product_rows_for_current_user(
        fetch_all('SELECT * FROM products WHERE customer_id=? ORDER BY product_code, id', (selected_customer_id,))
    )
    product_label_map = {_product_label(x): x for x in customer_products}
    product_options = list(product_label_map.keys())

    def get_next_fifo_row_id():
        db_max = fetch_all('SELECT COALESCE(MAX(fifo_row_id), 0) AS max_id FROM shipment_boxes')
        max_db = int(db_max[0]['max_id'] or 0) if db_max else 0
        temp_ids = [int(r.get('fifo_row_id') or 0) for r in st.session_state.get('shipment_temp_rows', [])]
        return max(max_db, max(temp_ids) if temp_ids else 0) + 1

    st.markdown('<div class="sap-grid-card"><div class="sap-grid-card-title">Original Invoice Details</div>', unsafe_allow_html=True)
    inv1, inv2 = st.columns(2)
    with inv1:
        invoice_no = st.text_input('Original Invoice Number', key='shipment_original_invoice_top')
    with inv2:
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
        supplier = st.selectbox('Supplier', list(supplier_map.keys()), key='shipment_supplier')
        attachment = st.file_uploader('Attach Shipment File', key='auto_file_uploader_1')
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
        warehouse_delivery_date = st.date_input('Delivered to WH Date', value=date.today(), key='shipment_delivered_to_wh_date') if shipment_status == 'Delivered' else None
        remarks = st.text_area('Remarks', key='auto_textarea_1')

    st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)
    st.subheader('Add Pallet / Product Row')
    st.caption('Select Product here for this row. Change Product and add another row to place multiple Products in the same Shipment.')

    selected_product_data = None
    if not product_options:
        st.error('No Products are linked to the selected Customer in Product Master.')
    else:
        row_product_label = st.selectbox('Product / Part for This Row *', product_options, key=f'shipment_row_product_sn2722_customer_{selected_customer_id}')
        selected_product_data = product_label_map[row_product_label]

    if selected_product_data:
        selected_product_id = int(selected_product_data['id'])
        st.markdown('''
            <style>
            .shipment-grid-label {font-family:Aptos,Arial,sans-serif;font-size:15px;font-weight:900;color:#003B73;margin-bottom:6px;min-height:22px;}
            .amount-input-look {height:52px;border-radius:10px;background:#f3f6fa;display:flex;align-items:center;justify-content:center;font-family:Aptos,Arial,sans-serif;font-size:16px;font-weight:700;color:#1f2937;border:1px solid transparent;}
            </style>
        ''', unsafe_allow_html=True)
        r1, r2, r3, r4, r5, r6, r7, r8, r9 = st.columns([1.0,1.0,2.05,1.15,1.05,0.85,0.85,0.75,1.0])
        with r1:
            st.markdown('<div class="shipment-grid-label">Pallet Number</div>', unsafe_allow_html=True)
            pallet_no = st.text_input('Pallet Number', key='shipment_grid_pallet_no', label_visibility='collapsed')
        with r2:
            st.markdown('<div class="shipment-grid-label">Box Number</div>', unsafe_allow_html=True)
            box_no = st.text_input('Box Number', key='shipment_grid_box_no', label_visibility='collapsed')
        with r3:
            st.markdown('<div class="shipment-grid-label">Product Code</div>', unsafe_allow_html=True)
            st.text_input('Selected Product', value=f"{selected_product_data.get('product_code')} | {selected_product_data.get('product_name') or ''}", disabled=True, key=f'shipment_row_product_display_{selected_product_id}', label_visibility='collapsed')

        auto_price, effective_currency = _local_effective_product_price(selected_product_id, shipment_date)
        auto_currency = effective_currency or selected_product_data.get('currency') or 'USD'
        default_po = selected_product_data.get('po_number') or ''
        try:
            default_po_date = parse_db_date(selected_product_data.get('po_date')) or date.today()
        except Exception:
            default_po_date = date.today()
        with r4:
            st.markdown('<div class="shipment-grid-label">PO Number</div>', unsafe_allow_html=True)
            row_po_number = st.text_input('PO Number', value=default_po, key=f'shipment_grid_po_number_{selected_product_id}', label_visibility='collapsed')
        with r5:
            st.markdown('<div class="shipment-grid-label">PO Date</div>', unsafe_allow_html=True)
            row_po_date = st.date_input('PO Date', value=default_po_date, key=f'shipment_grid_po_date_{selected_product_id}', label_visibility='collapsed')
        with r6:
            st.markdown('<div class="shipment-grid-label">Quantity</div>', unsafe_allow_html=True)
            quantity = st.number_input('Quantity', min_value=0.0, step=1.0, key='shipment_grid_qty', label_visibility='collapsed')
        with r7:
            st.markdown('<div class="shipment-grid-label">Price</div>', unsafe_allow_html=True)
            unit_price = st.number_input('Price', min_value=0.0, value=float(auto_price or 0), step=0.001, format='%.3f', key=f'shipment_grid_price_{selected_product_id}', label_visibility='collapsed')
        with r8:
            st.markdown('<div class="shipment-grid-label">Currency</div>', unsafe_allow_html=True)
            currency = st.selectbox('Currency', CURRENCIES, index=CURRENCIES.index(auto_currency) if auto_currency in CURRENCIES else 0, key=f'shipment_grid_currency_{selected_product_id}', label_visibility='collapsed')
        with r9:
            st.markdown('<div class="shipment-grid-label">Amount</div>', unsafe_allow_html=True)
            amount = quantity * unit_price
            st.markdown(f'<div class="amount-input-look">{amount:,.3f} {currency}</div>', unsafe_allow_html=True)

        if st.button('Add Product Row to Shipment', type='primary', key='shipment_grid_add_row'):
            try:
                product_customer_id = int(selected_product_data.get('customer_id') or 0)
            except Exception:
                product_customer_id = 0
            if not pallet_no.strip():
                st.error('Pallet Number is mandatory.')
            elif quantity <= 0:
                st.error('Quantity must be greater than zero.')
            elif product_customer_id != selected_customer_id:
                st.error('The selected Product belongs to a different Customer and cannot be added.')
            else:
                new_key = (pallet_no.strip(), selected_product_id)
                existing_keys = [(r['pallet_no'], r['product_id']) for r in st.session_state.shipment_temp_rows]
                old_match = fetch_all('''
                    SELECT b.id, s.shipment_no FROM shipment_boxes b
                    JOIN shipments s ON b.shipment_id=s.id
                    WHERE b.pallet_no=? AND b.product_id=?
                ''', (pallet_no.strip(), selected_product_id))
                if new_key in existing_keys:
                    st.error('Duplicate pallet/product row already added in this shipment.')
                elif old_match and str(old_match[0].get('shipment_no') or '').strip() != shipment_no.strip():
                    st.error(f"This pallet is already used for the same product in shipment {old_match[0]['shipment_no']}.")
                else:
                    st.session_state.shipment_temp_rows.append({
                        'fifo_row_id': get_next_fifo_row_id(),
                        'pallet_no': pallet_no.strip(), 'box_no': (box_no or '').strip(),
                        'po_number': (row_po_number or '').strip(), 'po_date': str(row_po_date),
                        'product_id': selected_product_id, 'product_code': selected_product_data['product_code'],
                        'product_name': selected_product_data.get('product_name') or '',
                        'quantity': quantity, 'unit_price': unit_price, 'currency': currency, 'amount': amount,
                        'header_customer_id': selected_customer_id,
                        'header_customer_name': selected_customer_row.get('customer_name') or '',
                        'header_ship_to_master_id': selected_ship_to_id,
                        'header_ship_to_name': selected_shipment_ship_to.get('ship_to_name') or '',
                    })
                    st.success(f"Product {selected_product_data.get('product_code')} row added.")
                    st.rerun()

    st.subheader('Current Shipment Rows')
    temp_df = pd.DataFrame(st.session_state.shipment_temp_rows)
    if not temp_df.empty:
        visible_cols = ['fifo_row_id','pallet_no','box_no','po_number','po_date','product_code','product_name','header_customer_name','header_ship_to_name','quantity','unit_price','currency','amount']
        st.dataframe(style_total_row(add_total_row(temp_df[visible_cols])), width='stretch', hide_index=True)
        st.markdown(f'<div class="total-box">Rows: {len(temp_df)} &nbsp; | &nbsp; Products: {temp_df["product_id"].nunique()} &nbsp; | &nbsp; Total Quantity: {temp_df["quantity"].sum()} &nbsp; | &nbsp; Total Amount: {temp_df["amount"].sum():,.3f}</div>', unsafe_allow_html=True)
        if st.button('Clear Unsaved Rows', key='clear_unsaved_shipment_rows'):
            st.session_state.shipment_temp_rows = []
            st.rerun()
    else:
        st.info('No product rows added yet.')

    if st.button('Save Shipment with All Rows', type='primary', key='save_shipment_all_rows'):
        if not shipment_no.strip():
            st.error('Shipment Number is mandatory.')
        elif not invoice_no.strip():
            st.error('Original Invoice Number is mandatory.')
        elif not st.session_state.shipment_temp_rows:
            st.error('Add at least one pallet/product row before saving shipment.')
        elif any(int(r.get('header_customer_id') or 0) != selected_customer_id or int(r.get('header_ship_to_master_id') or 0) != selected_ship_to_id for r in st.session_state.shipment_temp_rows):
            st.error('Unsaved rows contain a different Customer / Ship To header. Clear and re-add the rows.')
        else:
            row_product_ids = sorted({int(r.get('product_id') or 0) for r in st.session_state.shipment_temp_rows if r.get('product_id')})
            placeholders = ','.join(['?'] * len(row_product_ids))
            product_check_rows = fetch_all(f'SELECT id, customer_id FROM products WHERE id IN ({placeholders})', tuple(row_product_ids)) if row_product_ids else []
            product_customer_by_id = {int(x['id']): int(x.get('customer_id') or 0) for x in product_check_rows}
            invalid_products = [pid for pid in row_product_ids if product_customer_by_id.get(pid) != selected_customer_id]
            if invalid_products:
                st.error('One or more Product rows are not linked to the selected Customer.')
            else:
                try:
                    total_amount = sum(r['amount'] for r in st.session_state.shipment_temp_rows)
                    path = save_upload(attachment, f'shipment_{shipment_no}')
                    first = st.session_state.shipment_temp_rows[0]
                    header = {
                        'shipment_no': shipment_no.strip(), 'invoice_no': invoice_no.strip(),
                        'po_number': first.get('po_number',''), 'po_date': first.get('po_date') or None,
                        'shipment_date': str(shipment_date), 'supplier_id': supplier_map[supplier],
                        'warehouse_id': warehouse_map[warehouse], 'customer_id': selected_customer_id,
                        'ship_to_master_id': selected_ship_to_id, 'shipment_time_days': selected_shipment_time_days,
                        'shipment_status': shipment_status,
                        'warehouse_delivery_date': str(warehouse_delivery_date) if warehouse_delivery_date else None,
                        'invoice_amount': total_amount, 'currency': first['currency'], 'attachment_path': path,
                        'remarks': remarks, 'shipping_bill_no': shipping_bill_no.strip(),
                        'shipping_bill_date': str(shipping_bill_date), 'shipment_doc_date': str(shipment_doc_date),
                        'forwarder_name': forwarder_name, 'incoterm': incoterm,
                        'forwarder_id': forwarder_map.get(forwarder_name), 'incoterm_id': incoterm_map.get(incoterm),
                    }
                    result = save_shipment_atomic(header, st.session_state.shipment_temp_rows)
                    notify_event('shipment', 'Shipment Recovered / Completed' if result.get('recovered') else 'New Shipment Created', f"Shipment No: {shipment_no}\nOriginal Invoice: {invoice_no}\nCustomer: {selected_customer_row.get('customer_name')}\nShip To: {selected_shipment_ship_to.get('ship_to_name')}\nProducts: {len(row_product_ids)}\nAmount: {total_amount}")
                    st.session_state.shipment_temp_rows = []
                    clear_cache_after_write()
                    rerun_with_success(f'Shipment saved successfully with {len(row_product_ids)} Product(s).')
                except Exception as exc:
                    st.error(f'Shipment save failed. The database transaction was rolled back. Details: {exc}')

render_slogan_footer()
st.markdown('<div class="footer">COPYRIGHT BY FOUR STAR INDUSTRIES PVT. LTD.</div>', unsafe_allow_html=True)
