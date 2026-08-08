from delivery_common import *


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
require_page_view('delivery')
show_edit_permission_status('delivery')
ensure_delivery_columns()
require_delivery_master_relationship_schema("Delivery Entry")

show_header('Delivery Entry', 'Product → Customer / Bill To → Customer Ship To')
access_notice()
render_delivery_subnav('delivery')

st.markdown('''
<div class="card" style="margin-bottom:14px;">
    <b>DELIVERY / COMMERCIAL INVOICE ENTRY</b><br>
    Select the Product first. Customer / Bill To is loaded from Product Master and Ship To is loaded from that Customer Master.
    Both dropdowns remain manually changeable before saving the Delivery Invoice.
</div>
''', unsafe_allow_html=True)

customers = fetch_all('SELECT * FROM customers ORDER BY customer_name, id')
terms = fetch_all('SELECT * FROM payment_terms ORDER BY days, id')
ship_to_rows = fetch_all("SELECT * FROM ship_to_masters WHERE COALESCE(is_active, TRUE)=TRUE ORDER BY ship_to_name, ship_to_id, id")
part_rows_for_delivery = fetch_delivery_part_options()

if not customers or not terms or not ship_to_rows or not part_rows_for_delivery:
    st.warning('Create Ship To, Customer, Product, Payment Term and Shipment records first, and confirm pending balance quantity exists.')
    render_slogan_footer()
    st.stop()

customer_label_map = {_customer_label(row): row for row in customers}
customer_label_by_id = {int(row['id']): label for label, row in customer_label_map.items()}
term_map = {f"{x['term_name']} - {x['days']} days | ID {x['id']}": x for x in terms}
term_label_by_id = {int(row['id']): label for label, row in term_map.items()}
ship_to_map = {_ship_to_label(row): row for row in ship_to_rows}
ship_to_label_by_id = {int(row['id']): label for label, row in ship_to_map.items()}

part_options_delivery = [
    f"{r['product_code']} | {r.get('product_name') or ''} | ID {r['product_id']}"
    for r in part_rows_for_delivery
]
part_map = {label: row for label, row in zip(part_options_delivery, part_rows_for_delivery)}

st.markdown('<div class="input-section-title">1. Product Selection</div>', unsafe_allow_html=True)
selected_product_label = st.selectbox(
    'Product / Part Number *',
    part_options_delivery,
    key='delivery_entry_part_filter_sn2713',
    help='The selected Product controls the automatic Customer / Bill To and Ship To relationship.',
)
selected_product_row = part_map[selected_product_label]
selected_product_id = int(selected_product_row['product_id'])
product_defaults = fetch_product_delivery_defaults(selected_product_id)
auto_customer_id = product_defaults.get('customer_id')
auto_ship_to_id = product_defaults.get('customer_ship_to_master_id')
auto_term_id = product_defaults.get('customer_payment_term_id')

if not auto_customer_id:
    st.error('Required Product Master field is missing: Customer / Bill To. Open Masters → Product and link a Customer before Delivery Entry.')
    render_slogan_footer()
    st.stop()
if not auto_ship_to_id:
    st.error('Required Customer Master field is missing: Ship To. Open Masters → Customer and link a Ship To before Delivery Entry.')
    render_slogan_footer()
    st.stop()
if not str(product_defaults.get('customer_address') or '').strip():
    st.error('The Product-linked Customer has no Bill To Address. Complete Customer Master before Delivery Entry.')
    render_slogan_footer()
    st.stop()
if int(auto_customer_id) not in customer_label_by_id or int(auto_ship_to_id) not in ship_to_label_by_id:
    st.error('The Product master relationship points to an unavailable Customer or inactive Ship To. Correct the master relationship before Delivery Entry.')
    render_slogan_footer()
    st.stop()
auto_ship_to_row = ship_to_map[ship_to_label_by_id[int(auto_ship_to_id)]]
if not str(auto_ship_to_row.get('addressline1') or '').strip():
    st.error('The Product-linked Customer Ship To has no Address Line 1. Complete Ship To Master before Delivery Entry.')
    render_slogan_footer()
    st.stop()

product_context = str(selected_product_id)
if st.session_state.get('_delivery_product_context_sn2713') != product_context:
    st.session_state['delivery_customer_sn2713'] = customer_label_by_id[int(auto_customer_id)]
    st.session_state['delivery_ship_to_sn2713'] = ship_to_label_by_id[int(auto_ship_to_id)]
    if auto_term_id and int(auto_term_id) in term_label_by_id:
        st.session_state['delivery_payment_term_sn2713'] = term_label_by_id[int(auto_term_id)]
    else:
        st.session_state.pop('delivery_payment_term_sn2713', None)
    st.session_state['_delivery_customer_tracker_sn2713'] = int(auto_customer_id)
    st.session_state['_delivery_product_context_sn2713'] = product_context

_safe_widget_state('delivery_customer_sn2713', list(customer_label_map.keys()))
_safe_widget_state('delivery_ship_to_sn2713', list(ship_to_map.keys()))
_safe_widget_state('delivery_payment_term_sn2713', list(term_map.keys()))

st.markdown('<div class="input-section-title">2. Automatic Customer / Bill To and Ship To</div>', unsafe_allow_html=True)
relationship_col1, relationship_col2 = st.columns(2)
with relationship_col1:
    selected_customer_label = st.selectbox(
        'Customer / Bill To *',
        list(customer_label_map.keys()),
        key='delivery_customer_sn2713',
        help='Loaded from Product Master. You may change it manually for this Delivery Invoice.',
    )
    selected_customer_row = customer_label_map[selected_customer_label]
    selected_customer_id = int(selected_customer_row['id'])

if not str(selected_customer_row.get('address') or '').strip():
    st.error('The selected Customer has no Bill To Address. Complete Customer Master before using this Customer.')
    render_slogan_footer()
    st.stop()
if not selected_customer_row.get('ship_to_master_id'):
    st.error('The selected Customer does not have the required Ship To link. Update Customer Master before using this Customer.')
    render_slogan_footer()
    st.stop()

# If Customer is changed manually, load the selected Customer's Ship To and
# Payment Term before those widgets are created.
customer_tracker = st.session_state.get('_delivery_customer_tracker_sn2713')
if customer_tracker != selected_customer_id:
    customer_default_ship_to_id = selected_customer_row.get('ship_to_master_id')
    if customer_default_ship_to_id and int(customer_default_ship_to_id) in ship_to_label_by_id:
        st.session_state['delivery_ship_to_sn2713'] = ship_to_label_by_id[int(customer_default_ship_to_id)]
    else:
        st.session_state.pop('delivery_ship_to_sn2713', None)
    customer_term_id = selected_customer_row.get('payment_term_id')
    if customer_term_id and int(customer_term_id) in term_label_by_id:
        st.session_state['delivery_payment_term_sn2713'] = term_label_by_id[int(customer_term_id)]
    else:
        st.session_state.pop('delivery_payment_term_sn2713', None)
    st.session_state['_delivery_customer_tracker_sn2713'] = selected_customer_id

_safe_widget_state('delivery_ship_to_sn2713', list(ship_to_map.keys()))
if 'delivery_ship_to_sn2713' not in st.session_state:
    default_ship_to_id = selected_customer_row.get('ship_to_master_id')
    if default_ship_to_id and int(default_ship_to_id) in ship_to_label_by_id:
        st.session_state['delivery_ship_to_sn2713'] = ship_to_label_by_id[int(default_ship_to_id)]
    else:
        st.session_state['delivery_ship_to_sn2713'] = list(ship_to_map.keys())[0]

with relationship_col2:
    selected_ship_to_label = st.selectbox(
        'Ship To *',
        list(ship_to_map.keys()),
        key='delivery_ship_to_sn2713',
        help='Loaded from the selected Customer Master. You may change it manually for this Delivery Invoice.',
    )
    selected_ship_to = ship_to_map[selected_ship_to_label]
    selected_ship_to_id = int(selected_ship_to['id'])

if selected_ship_to.get('is_active') is False:
    st.error('The selected Ship To is inactive. Select an active Ship To before Delivery Entry.')
    render_slogan_footer()
    st.stop()
if not str(selected_ship_to.get('addressline1') or '').strip():
    st.error('The selected Ship To has no Address Line 1. Complete Ship To Master before Delivery Entry.')
    render_slogan_footer()
    st.stop()

if selected_customer_id == int(auto_customer_id) and selected_ship_to_id == int(auto_ship_to_id):
    st.success(
        f"Loaded from Masters: {selected_product_row.get('product_code')} → "
        f"{selected_customer_row.get('customer_name')} → {selected_ship_to.get('ship_to_name')}"
    )
else:
    st.warning('Manual Customer / Ship To override is active for this Delivery Invoice. Verify the addresses before saving.')

bill_to_address = str(selected_customer_row.get('address') or '').strip() or '-'
ship_to_address = '\n'.join([
    str(selected_ship_to.get('addressline1') or '').strip(),
    str(selected_ship_to.get('addressline2') or '').strip(),
    str(selected_ship_to.get('addressline3') or '').strip(),
]).strip() or '-'
address_col1, address_col2 = st.columns(2)
with address_col1:
    st.markdown(f"**Bill To Address — Customer Master**  \n{html.escape(bill_to_address).replace(chr(10), '<br>')}", unsafe_allow_html=True)
with address_col2:
    st.markdown(f"**Ship To Address — Ship To Master**  \n{html.escape(ship_to_address).replace(chr(10), '<br>')}", unsafe_allow_html=True)

invoice_shipments = fetch_available_invoice_shipments(selected_product_id)
if not invoice_shipments:
    st.warning('No pending shipment balance is available for the selected Product.')
    render_slogan_footer()
    st.stop()

st.markdown('<div class="input-section-title">3. Original Invoice / Shipment Selection</div>', unsafe_allow_html=True)
inv_map = {
    f"{s['invoice_no']} | Shipment {s['shipment_no']} | Balance {float(s.get('balance_qty') or 0):,.3f} | PO {s.get('po_number') or '-'} | Date {s['shipment_date']}": s
    for s in invoice_shipments
}
invoice_labels = list(inv_map.keys())
selected_invoice_labels = st.multiselect(
    'Select one or multiple Original Invoice / Shipment Numbers *',
    invoice_labels,
    default=invoice_labels[:1],
    key='delivery_original_invoice_ship_multi_sn2713',
    help='Only shipments containing the selected Product and pending quantity are listed.',
)
if not selected_invoice_labels:
    st.warning('Select at least one Original Invoice / Shipment to continue.')
    render_slogan_footer()
    st.stop()

selected_ships = [inv_map[x] for x in selected_invoice_labels if x in inv_map]
selected_ship = selected_ships[0]
selected_ship_ids = [s.get('id') for s in selected_ships if s.get('id')]
selected_original_invoice_numbers = sorted({str(s.get('invoice_no') or '') for s in selected_ships if s.get('invoice_no')})
selected_shipment_numbers = sorted({str(s.get('shipment_no') or '') for s in selected_ships if s.get('shipment_no')})
st.caption(f"Selected Original Invoices: {', '.join(selected_original_invoice_numbers) or '-'}")
st.caption(f"Selected Shipments: {', '.join(selected_shipment_numbers) or '-'}")

st.markdown('<div class="input-section-title">4. Delivery Invoice Header</div>', unsafe_allow_html=True)
header_row1 = st.columns(4)
with header_row1[0]:
    delivery_date = st.date_input('Delivery Date *', value=date.today(), key='delivery_date_sn2713')

invoice_no_for_auto = selected_original_invoice_numbers[0] if selected_original_invoice_numbers else selected_ship.get('invoice_no')
auto_delivery_invoice_no = generate_delivery_invoice_no(invoice_no_for_auto, delivery_date)
auto_source_key = f"{invoice_no_for_auto}|{delivery_date}|{','.join(map(str, selected_ship_ids))}"
if st.session_state.get('delivery_invoice_auto_source_sn2713') != auto_source_key:
    st.session_state['delivery_invoice_sn2713'] = auto_delivery_invoice_no
    st.session_state['delivery_invoice_auto_source_sn2713'] = auto_source_key
with header_row1[1]:
    delivery_invoice_no = st.text_input('Delivery Invoice Number *', key='delivery_invoice_sn2713')
with header_row1[2]:
    _safe_widget_state('delivery_payment_term_sn2713', list(term_map.keys()))
    if 'delivery_payment_term_sn2713' not in st.session_state:
        customer_term_id = selected_customer_row.get('payment_term_id')
        st.session_state['delivery_payment_term_sn2713'] = (
            term_label_by_id[int(customer_term_id)]
            if customer_term_id and int(customer_term_id) in term_label_by_id
            else list(term_map.keys())[0]
        )
    selected_term_label = st.selectbox('Payment Term *', list(term_map.keys()), key='delivery_payment_term_sn2713')
    selected_term = term_map[selected_term_label]
with header_row1[3]:
    payment_due_date = delivery_date + timedelta(days=int(selected_term.get('days') or 0))
    st.date_input('Payment Due Date', value=payment_due_date, disabled=True, key='delivery_due_date_display_sn2713')

header_row2 = st.columns(4)
with header_row2[0]:
    vehicle_number = st.text_input('Vehicle Number', key='delivery_vehicle_number_sn2713')
with header_row2[1]:
    ship_via = st.text_input('Ship Via', value='Road', key='delivery_ship_via_sn2713')
with header_row2[2]:
    asn_number = st.text_input('ASN Number', key='delivery_asn_number_sn2713')
with header_row2[3]:
    asn_date = st.date_input('ASN Date', value=date.today(), key='delivery_asn_date_sn2713')

header_row3 = st.columns([1.3, 1.3, 1.4])
with header_row3[0]:
    packaging_details = st.text_input('Packaging Details', key='delivery_packaging_details_sn2713')
with header_row3[1]:
    packaging_remark = st.text_input('Remarks', key='delivery_remarks_sn2713')
with header_row3[2]:
    attachment = st.file_uploader('Attach Delivery File', key='delivery_attachment_sn2713')

selected_warehouse_names = ', '.join(sorted({str(s.get('warehouse_name') or '') for s in selected_ships if s.get('warehouse_name')}))
st.text_input('Linked Warehouse(s)', value=selected_warehouse_names, disabled=True, key='delivery_linked_warehouse_display_sn2713')

available_rows = []
for shipment in selected_ships:
    available_rows.extend(fetch_fifo_available_rows(shipment['id'], selected_product_id))
seen_box_ids = set()
unique_available_rows = []
for row in available_rows:
    box_id = row.get('id')
    if box_id in seen_box_ids:
        continue
    seen_box_ids.add(box_id)
    unique_available_rows.append(row)
available_rows = unique_available_rows

if not available_rows:
    st.warning('No pending pallet quantity is available for the selected Product and Original Invoice / Shipment selection.')
else:
    st.markdown('<div class="input-section-title">5. FIFO Pallet / Box Selection</div>', unsafe_allow_html=True)
    sort_mode = st.radio('Sort Pallet / Product Rows', ['FIFO ID', 'Pallet Number'], horizontal=True, key='delivery_fifo_sort_mode_sn2713')
    if sort_mode == 'Pallet Number':
        available_rows = sorted(available_rows, key=lambda x: str(x.get('pallet_no') or ''))
    else:
        available_rows = sorted(available_rows, key=lambda x: (int(x.get('fifo_row_id') or x.get('id') or 0), str(x.get('pallet_no') or '')))

    pallet_map = {
        f"Orig Inv {r.get('invoice_no') or '-'} | Shipment {r.get('shipment_no') or '-'} | ID {r.get('fifo_row_id') or r.get('id')} | "
        f"Pallet {r.get('pallet_no')} | Box {r.get('box_no') or '-'} | {r.get('product_code')} | "
        f"PO {r.get('po_number') or '-'} | PO Date {format_date_ddmmyyyy(r.get('po_date')) if r.get('po_date') else '-'} | "
        f"Balance {float(r.get('balance_qty') or 0):,.3f}": r
        for r in available_rows
    }
    selected_pallet_labels = st.multiselect(
        'Select Pallet Numbers / Product Rows *',
        list(pallet_map.keys()),
        key='delivery_multi_pallets_sn2713',
    )
    selected_pallets = [pallet_map[x] for x in selected_pallet_labels]

    st.subheader('Enter Delivery Quantity for Selected Pallets')
    delivery_inputs = []
    total_qty = 0.0
    total_amount = 0.0
    if selected_pallets:
        column_header = st.columns([2.2, 1.0, 1.0, 0.8, 0.8, 0.9])
        for col, label in zip(column_header, ['Pallet / Product', 'PO Number', 'PO Date', 'Qty', 'Price', 'Amount']):
            with col:
                st.markdown(f'**{label}**')

    for index, row in enumerate(selected_pallets):
        cols = st.columns([2.2, 1.0, 1.0, 0.8, 0.8, 0.9])
        with cols[0]:
            st.write(
                f"Orig Inv {row.get('invoice_no') or '-'} | FIFO {row.get('fifo_row_id') or row.get('id')} | "
                f"Pallet {row.get('pallet_no')} | Box {row.get('box_no') or '-'} | Balance {float(row.get('balance_qty') or 0):,.3f}"
            )
        with cols[1]:
            edited_po_number = st.text_input('PO Number', value=str(row.get('po_number') or ''), key=f"delivery_row_po_number_sn2713_{row['id']}_{index}", label_visibility='collapsed')
        with cols[2]:
            try:
                row_po_date_default = parse_db_date(row.get('po_date')) or date.today()
            except Exception:
                row_po_date_default = date.today()
            edited_po_date = st.date_input('PO Date', value=row_po_date_default, key=f"delivery_row_po_date_sn2713_{row['id']}_{index}", label_visibility='collapsed')
        with cols[3]:
            qty_key = f"delivery_qty_sn2713_{row['id']}"
            qty = st.number_input('Qty', min_value=0.0, max_value=float(row.get('balance_qty') or 0), value=float(st.session_state.get(qty_key, 0.0) or 0.0), step=1.0, key=qty_key, label_visibility='collapsed')
        with cols[4]:
            price_key = f"delivery_price_sn2713_{row['id']}"
            effective_price, effective_currency = _local_effective_product_price(row.get('product_id'), delivery_date)
            default_price = effective_price if effective_price else float(row.get('unit_price') or 0)
            if effective_currency:
                row['currency'] = effective_currency
            price = st.number_input('Price', min_value=0.0, value=float(st.session_state.get(price_key, default_price) or 0), step=0.001, format='%.3f', key=price_key, label_visibility='collapsed')
        with cols[5]:
            amount = qty * price
            st.write(f"{amount:,.3f} {row.get('currency') or ''}")

        row['po_number'] = edited_po_number.strip()
        row['po_date'] = str(edited_po_date)
        if qty > 0:
            total_qty += qty
            total_amount += amount
            delivery_inputs.append((row, qty_key, price_key))

    st.markdown(f'<div class="total-box">Total Delivery Qty: {total_qty:,.3f} &nbsp;&nbsp; | &nbsp;&nbsp; Total Amount: {total_amount:,.3f}</div>', unsafe_allow_html=True)

    if st.button('Save Delivery & Print', type='primary', key='save_delivery_fifo_sn2713'):
        if not delivery_invoice_no.strip():
            st.error('Delivery Invoice Number is mandatory.')
        elif not selected_customer_id:
            st.error('Customer / Bill To is mandatory.')
        elif not selected_ship_to_id:
            st.error('Ship To is mandatory.')
        elif not str(selected_customer_row.get('address') or '').strip():
            st.error('Bill To Address is mandatory in Customer Master.')
        elif not str(selected_ship_to.get('addressline1') or '').strip():
            st.error('Address Line 1 is mandatory in Ship To Master.')
        elif not delivery_inputs:
            st.error('Select one or more pallets and enter delivery quantity.')
        else:
            path = save_upload(attachment, f'delivery_{delivery_invoice_no}')
            first_print = None
            save_error = False

            for row, qty_key, price_key in delivery_inputs:
                qty = float(st.session_state.get(qty_key, 0) or 0)
                effective_price, effective_currency = _local_effective_product_price(row.get('product_id'), delivery_date)
                default_price = effective_price if effective_price else float(row.get('unit_price') or 0)
                price = float(st.session_state.get(price_key, default_price) or 0)
                if effective_currency:
                    row['currency'] = effective_currency
                amount = qty * price

                balance_rows = fetch_all('''
                    SELECT b.original_qty - COALESCE(del.delivered_qty, 0) AS balance_qty
                    FROM shipment_boxes b
                    LEFT JOIN (
                        SELECT box_id, SUM(delivered_qty) AS delivered_qty
                        FROM customer_deliveries
                        GROUP BY box_id
                    ) del ON b.id=del.box_id
                    WHERE b.id=?
                ''', (row['id'],))
                current_balance = float((balance_rows[0].get('balance_qty') if balance_rows else row.get('balance_qty')) or 0)
                if qty <= 0:
                    continue
                if qty > current_balance:
                    st.error(f"Qty mismatch for pallet {row.get('pallet_no')}: entered {qty}, available balance is {current_balance}.")
                    save_error = True
                    continue

                execute_query('''
                    INSERT INTO customer_deliveries
                    (shipment_id, box_id, customer_id, ship_to_master_id, delivery_date, delivered_qty,
                     delivery_invoice_no, vehicle_number, asn_number, asn_date, packaging_details,
                     packaging_remark, ship_via, payment_term_id, payment_terms_days, payment_due_date,
                     unit_price, currency, sale_amount, attachment_path, po_number, po_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['shipment_id'], row['id'], selected_customer_id, selected_ship_to_id,
                    str(delivery_date), qty, delivery_invoice_no.strip(), vehicle_number.strip(),
                    asn_number.strip(), str(asn_date), packaging_details.strip(), packaging_remark.strip(),
                    ship_via.strip() or 'Road', selected_term['id'], selected_term['days'], str(payment_due_date),
                    price, row.get('currency') or '', amount, path, row.get('po_number', ''), row.get('po_date'),
                ))

                if first_print is None:
                    first_print = {
                        'customer_name': selected_customer_row.get('customer_name', ''),
                        'customer_address': selected_customer_row.get('address', ''),
                        'customer_company_code': selected_customer_row.get('company_code', ''),
                        'customer_phone': selected_customer_row.get('phone', ''),
                        'customer_email': selected_customer_row.get('email', ''),
                        'ship_to_name': selected_ship_to.get('ship_to_name', ''),
                        'ship_to_id': selected_ship_to.get('ship_to_id', ''),
                        'ship_to_addressline1': selected_ship_to.get('addressline1', ''),
                        'ship_to_addressline2': selected_ship_to.get('addressline2', ''),
                        'ship_to_addressline3': selected_ship_to.get('addressline3', ''),
                        'ship_to_vendor_gstin': selected_ship_to.get('vendor_gstin', ''),
                        'ship_to_vendor_phone': selected_ship_to.get('vendor_phone', ''),
                        'ship_to_vendor_email': selected_ship_to.get('vendor_email', ''),
                        'shipment_no': row.get('shipment_no', ''),
                        'original_invoice_no': row.get('invoice_no', ''),
                        'delivery_invoice_no': delivery_invoice_no.strip(),
                        'delivery_date': str(delivery_date),
                        'vehicle_number': vehicle_number.strip(),
                        'ship_via': ship_via.strip() or 'Road',
                        'asn_number': asn_number.strip(),
                        'asn_date': str(asn_date),
                        'packaging_details': packaging_details.strip(),
                        'packaging_remark': packaging_remark.strip(),
                        'payment_term': selected_term_label,
                        'payment_due_date': str(payment_due_date),
                        'product_code': row.get('product_code', ''),
                        'product_name': row.get('product_name', ''),
                        'po_number': row.get('po_number', ''),
                        'po_date': row.get('po_date', ''),
                        'pallet_no': row.get('pallet_no', ''),
                        'box_no': row.get('box_no', ''),
                        'qty': total_qty,
                        'unit_price': price,
                        'currency': row.get('currency', ''),
                        'sale_amount': total_amount,
                    }

            if save_error:
                st.stop()

            notify_event(
                'delivery',
                'Delivery Created',
                f"Delivery Invoice: {delivery_invoice_no}\nProduct: {selected_product_row.get('product_code')}\nCustomer: {selected_customer_row.get('customer_name')}\nShip To: {selected_ship_to.get('ship_to_name')}\nQty: {total_qty}\nAmount: {total_amount}\nDue Date: {payment_due_date}",
            )
            print_data = build_delivery_invoice_print_data(delivery_invoice_no.strip()) or first_print
            if print_data:
                st.session_state.last_delivery_print = print_data
            st.session_state.last_delivery_pdf_invoice_no = delivery_invoice_no.strip()
            st.session_state['delivery_invoice_auto_source_sn2713'] = ''
            clear_cache_after_write()
            st.success('Delivery saved successfully with Product-linked Customer and Customer-linked Ship To.')
            st.rerun()

if 'last_delivery_pdf_invoice_no' in st.session_state:
    pdf_invoice_no = st.session_state.get('last_delivery_pdf_invoice_no')
    invoice, lines = get_saved_delivery_invoice_for_pdf(pdf_invoice_no)
    if invoice and lines:
        try:
            pdf_bytes = delivery_invoice_pdf_bytes(invoice, lines)
            st.download_button('Print / Download Delivery Invoice PDF', pdf_bytes, f'delivery_invoice_{pdf_invoice_no}.pdf', mime='application/pdf', key='download_delivery_invoice_pdf_after_save_sn2713')
        except Exception as pdf_error:
            st.error(f'Delivery Invoice PDF generation failed: {pdf_error}')
    else:
        st.warning('Delivery was saved, but saved invoice lines were not found for PDF generation.')
    del st.session_state.last_delivery_pdf_invoice_no

if 'last_delivery_print' in st.session_state:
    html_doc = delivery_note_html(st.session_state.last_delivery_print)
    print_popup(html_doc)
    st.download_button('Download Delivery Invoice HTML Backup', html_doc, 'delivery_invoice_print.html', mime='text/html', key='download_delivery_note_html_sn2713')
    del st.session_state.last_delivery_print

render_slogan_footer()
