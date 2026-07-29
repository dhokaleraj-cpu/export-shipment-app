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


page_setup()
require_page_view('delivery')
show_edit_permission_status('delivery')
ensure_delivery_columns()

show_header('Delivery Entry', 'Invoice-style FIFO delivery form with multi-pallet selection')
access_notice()
render_delivery_subnav('delivery')

st.markdown("""
<style>
/* Delivery Entry sub-headings / field labels */
.input-section-title,
[data-testid="stWidgetLabel"] p,
[data-testid="stFileUploaderDropzoneInstructions"] div,
.stSelectbox label p,
.stTextInput label p,
.stDateInput label p,
.stFileUploader label p,
.stMultiSelect label p,
label p {
    font-family: Aptos, Arial, sans-serif !important;
    font-size: 1.2rem !important;
    font-weight: 800 !important;
    line-height: 1.35 !important;
    color: #1f2937 !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown('\n        <div class="card" style="margin-bottom:14px;">\n            <b>DELIVERY / COMMERCIAL INVOICE ENTRY</b><br>\n            Select Original Invoice + Shipment, then choose one or more pallets. Pallets are shown FIFO by shipment date and pallet number.\n        </div>\n        ', unsafe_allow_html=True)
customers = fetch_all('SELECT * FROM customers ORDER BY customer_name')
terms = fetch_all('SELECT * FROM payment_terms ORDER BY days')
ship_to_rows = fetch_all("SELECT * FROM ship_to_masters WHERE COALESCE(is_active, TRUE)=TRUE ORDER BY ship_to_name, ship_to_id")

part_rows_for_delivery = fetch_delivery_part_options()
part_options_delivery = ["All Parts"] + [
    f"{r['product_code']} | {r.get('product_name') or ''} | {r['product_id']}"
    for r in part_rows_for_delivery
]

st.markdown('<div class="input-section-title">Part Selection</div>', unsafe_allow_html=True)
selected_product_label = st.selectbox(
    'Select Part Number to filter Original Invoice / Shipment',
    part_options_delivery,
    key='delivery_entry_part_filter',
    label_visibility='collapsed',
    help='Original Invoice / Shipment list will show only balance quantity for the selected part.'
)

selected_product_id = None
if selected_product_label and selected_product_label != "All Parts":
    try:
        selected_product_id = int(str(selected_product_label).split("|")[-1].strip())
    except Exception:
        selected_product_id = None

invoice_shipments = fetch_available_invoice_shipments(selected_product_id)

if not customers or not invoice_shipments:
    st.warning('Create Customer Master and Shipment Entry first, or no balance quantity is available for the selected Part / user access.')
else:
    customer_map = {x['customer_name']: x['id'] for x in customers}
    term_map = {f"{x['term_name']} - {x['days']} days": x for x in terms}
    ship_to_map = {f"{x['ship_to_name']} | {x.get('ship_to_id') or '-'}": x for x in ship_to_rows}
    inv_map = {f"{s['invoice_no']} | Shipment {s['shipment_no']} | Balance {float(s.get('balance_qty') or 0):,.3f} | PO {s.get('po_number') or '-'} | Date {s['shipment_date']}": s for s in invoice_shipments}
    invoice_labels = list(inv_map.keys())
    ctop1, ctop2 = st.columns(2)
    with ctop1:
        st.markdown('<div class="input-section-title">Original Invoice Number with Shipment Number</div>', unsafe_allow_html=True)
        selected_invoice_labels = st.multiselect(
            'Select one or multiple Original Invoice / Shipment Numbers',
            invoice_labels,
            default=invoice_labels[:1],
            key='delivery_original_invoice_ship_multi',
            label_visibility='collapsed',
            help='Select multiple original invoices/shipments to deliver pallets under one delivery invoice.'
        )
    if not selected_invoice_labels:
        st.warning('Select at least one Original Invoice / Shipment to continue delivery entry.')
        st.stop()
    selected_ships = [inv_map[x] for x in selected_invoice_labels if x in inv_map]
    selected_ship = selected_ships[0]
    selected_ship_ids = [s.get('id') for s in selected_ships if s.get('id')]
    selected_original_invoice_numbers = sorted(set(str(s.get('invoice_no') or '') for s in selected_ships if s.get('invoice_no')))
    selected_original_invoices_summary = ', '.join(selected_original_invoice_numbers)
    selected_shipment_numbers_summary = ', '.join(sorted(set(str(s.get('shipment_no') or '') for s in selected_ships if s.get('shipment_no'))))
    st.caption(f"Selected Original Invoices: {selected_original_invoices_summary or '-'}")
    st.caption(f"Selected Shipments: {selected_shipment_numbers_summary or '-'}")
    invoice_top_col1, invoice_top_col2 = st.columns(2)
    with invoice_top_col1:
        delivery_date = st.date_input('Delivery Date', value=date.today(), key='delivery_date_v10')
    invoice_no_for_auto = selected_original_invoice_numbers[0] if selected_original_invoice_numbers else selected_ship.get('invoice_no')
    auto_delivery_invoice_no = generate_delivery_invoice_no(invoice_no_for_auto, delivery_date)
    auto_source_key = f"{invoice_no_for_auto}|{delivery_date}|{','.join(map(str, selected_ship_ids))}"
    if st.session_state.get('delivery_invoice_auto_source') != auto_source_key:
        st.session_state['delivery_invoice_v10'] = auto_delivery_invoice_no
        st.session_state['delivery_invoice_auto_source'] = auto_source_key
    with invoice_top_col2:
        delivery_invoice_no = st.text_input('Delivery Invoice Number', key='delivery_invoice_v10', help='Auto format uses first selected Original Invoice Number + MMDDYY + running sequence.')
        st.caption(f"Auto generated from first selected Original Invoice No: {invoice_no_for_auto or '-'}")
    extra_col1, extra_col2, extra_col3, extra_col4, extra_col5 = st.columns(5)
    with extra_col1:
        vehicle_number = st.text_input('Vehicle Number', key='delivery_vehicle_number')
    with extra_col2:
        asn_number = st.text_input('ASN Number', key='delivery_asn_number')
    with extra_col3:
        asn_date = st.date_input('ASN Date', value=date.today(), key='delivery_asn_date')
    with extra_col4:
        packaging_details = st.text_input('Packaging Details', key='delivery_packaging_details')
    with extra_col5:
        packaging_remark = st.text_input('Remarks', key='delivery_remarks')
    selected_warehouse_names = ', '.join(sorted(set(str(s.get('warehouse_name') or '') for s in selected_ships if s.get('warehouse_name'))))
    st.text_input('Linked Warehouse(s)', value=selected_warehouse_names, disabled=True, key='delivery_linked_warehouse_display')
    available_rows = []
    for _ship in selected_ships:
        try:
            available_rows.extend(fetch_fifo_available_rows(_ship['id'], selected_product_id))
        except Exception:
            pass
    _seen_box_ids = set()
    _unique_available_rows = []
    for _r in available_rows:
        _bid = _r.get('id')
        if _bid in _seen_box_ids:
            continue
        _seen_box_ids.add(_bid)
        _unique_available_rows.append(_r)
    available_rows = _unique_available_rows
    if not available_rows:
        st.warning('No pending pallet quantity available for the selected original invoice/shipment list.')
    else:
        sort_mode = st.radio('Sort Pallet/Product Rows', ['FIFO ID', 'Pallet Number'], horizontal=True, key='delivery_fifo_sort_mode')
        if sort_mode == 'Pallet Number':
            available_rows = sorted(available_rows, key=lambda x: str(x.get('pallet_no') or ''))
        else:
            available_rows = sorted(available_rows, key=lambda x: (int(x.get('fifo_row_id') or x.get('id') or 0), str(x.get('pallet_no') or '')))
        pallet_map = {f"Orig Inv {r.get('invoice_no') or '-'} | Shipment {r.get('shipment_no') or '-'} | ID {r.get('fifo_row_id') or r.get('id')} | Pallet {r['pallet_no']} | Box {r['box_no'] or '-'} | {r['product_code']} | PO {r.get('po_number') or '-'} | PO Date {format_date_ddmmyyyy(r.get('po_date')) if r.get('po_date') else '-'} | Balance {float(r.get('balance_qty') or 0):,.3f} | Price {float(r.get('unit_price') or 0):,.3f} {r['currency']}": r for r in available_rows}
        selected_pallet_labels = st.multiselect('Select Pallet Numbers / Product Rows', list(pallet_map.keys()), key='delivery_multi_pallets')
        selected_pallets = [pallet_map[x] for x in selected_pallet_labels]
        c1, c2 = st.columns(2)
        with c1:
            customer = st.selectbox('Customer', list(customer_map.keys()), key='delivery_customer_v10')
            selected_customer_row = next((x for x in customers if x['customer_name'] == customer), None)
            default_term_id = selected_customer_row.get('payment_term_id') if selected_customer_row else None
            if ship_to_map:
                selected_ship_to_key = st.selectbox('Ship To', list(ship_to_map.keys()), key='delivery_ship_to_master')
                selected_ship_to = ship_to_map[selected_ship_to_key]
            else:
                selected_ship_to_key = ''
                selected_ship_to = {}
                st.warning('Create Ship To Master for delivery invoice print details.')
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
            dc1, dc2, dc3, dc4, dc5, dc6 = st.columns([1.6, 1.15, 1.05, 0.8, 0.8, 0.9])
            with dc1:
                st.write(f"Orig Inv {row.get('invoice_no') or '-'} | ID {row.get('fifo_row_id') or row.get('id')} | Pallet {row['pallet_no']} | {row['product_code']} | Balance {float(row.get('balance_qty') or 0):,.3f}")
            with dc2:
                edited_po_number = st.text_input('PO Number', value=str(row.get('po_number') or ''), key=f"delivery_row_po_number_{row['id']}_{i}", label_visibility='collapsed')
            with dc3:
                try:
                    row_po_date_default = parse_db_date(row.get('po_date')) or date.today()
                except Exception:
                    row_po_date_default = date.today()
                edited_po_date = st.date_input('PO Date', value=row_po_date_default, key=f"delivery_row_po_date_{row['id']}_{i}", label_visibility='collapsed')
            with dc4:
                qty_key = f"delivery_qty_{row['id']}"
                qty = st.number_input('Qty', min_value=0.0, max_value=float(row['balance_qty']), value=float(st.session_state.get(qty_key, 0.0) or 0.0), step=1.0, key=qty_key, label_visibility='collapsed')
            with dc5:
                price_key = f"delivery_price_{row['id']}"
                effective_delivery_price, effective_delivery_currency = _local_effective_product_price(row.get('product_id'), delivery_date)
                default_delivery_price = effective_delivery_price if effective_delivery_price else float(row.get('unit_price') or 0)
                if effective_delivery_currency:
                    row['currency'] = effective_delivery_currency
                price = st.number_input('Price', min_value=0.0, value=float(st.session_state.get(price_key, default_delivery_price) or 0), step=0.001, format='%.3f', key=price_key, label_visibility='collapsed')
            with dc6:
                amount = qty * price
                st.write(f"{amount:,.3f} {row['currency']}")
            row['po_number'] = edited_po_number.strip()
            row['po_date'] = str(edited_po_date)
            if qty > 0:
                total_qty += qty
                total_amount += amount
                delivery_inputs.append((row, qty_key, price_key))
        st.markdown(f'<div class="total-box">Total Delivery Qty: {total_qty} &nbsp;&nbsp; | &nbsp;&nbsp; Total Amount: {total_amount:,.3f}</div>', unsafe_allow_html=True)
        st.caption('Pending pallet list moved to separate page for faster Delivery Entry loading.')
        if st.button('Save Delivery & Print', type='primary', key='save_delivery_fifo'):
            if not delivery_invoice_no.strip():
                st.error('Delivery Invoice Number is mandatory.')
            elif not delivery_inputs:
                st.error('Select pallets and enter delivery quantity.')
            else:
                path = save_upload(attachment, f'delivery_{delivery_invoice_no}')
                first_print = None
                save_error = False
                for row, qty_key, price_key in delivery_inputs:
                    qty = float(st.session_state.get(qty_key, 0) or 0)
                    effective_save_price, effective_save_currency = _local_effective_product_price(row.get('product_id'), delivery_date)
                    default_save_price = effective_save_price if effective_save_price else float(row.get('unit_price') or 0)
                    price = float(st.session_state.get(price_key, default_save_price) or 0)
                    if effective_save_currency:
                        row['currency'] = effective_save_currency
                    amount = qty * price
                    current_balance_rows = fetch_all('''
                        SELECT b.original_qty - COALESCE(del.delivered_qty, 0) AS balance_qty
                        FROM shipment_boxes b
                        LEFT JOIN (
                            SELECT box_id, SUM(delivered_qty) AS delivered_qty
                            FROM customer_deliveries
                            GROUP BY box_id
                        ) del ON b.id = del.box_id
                        WHERE b.id=?
                    ''', (row['id'],))
                    current_balance = float((current_balance_rows[0].get('balance_qty') if current_balance_rows else row.get('balance_qty')) or 0)
                    if qty <= 0:
                        continue
                    if qty > current_balance:
                        st.error(f"Qty mismatch for pallet {row.get('pallet_no')}: entered {qty}, available balance is {current_balance}. Refresh and try again.")
                        save_error = True
                        continue
                    execute_query('''
                                INSERT INTO customer_deliveries
                                (shipment_id, box_id, customer_id, ship_to_master_id, delivery_date, delivered_qty, delivery_invoice_no,
                                 vehicle_number, asn_number, asn_date, packaging_details, packaging_remark,
                                 payment_term_id, payment_terms_days, payment_due_date, unit_price, currency, sale_amount, attachment_path, po_number, po_date)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (row['shipment_id'], row['id'], customer_map[customer], selected_ship_to.get('id'), str(delivery_date), qty, delivery_invoice_no.strip(),
                                vehicle_number.strip(), asn_number.strip(), str(asn_date), packaging_details.strip(), packaging_remark.strip(),
                                term['id'], term['days'], str(payment_due_date), price, row['currency'], amount, path, row.get('po_number', ''), row.get('po_date', None)))
                    if first_print is None:
                        first_print = {'customer_name': customer,
                                    'customer_address': selected_customer_row.get('address','') if 'selected_customer_row' in locals() else '',
                                    'customer_company_code': selected_customer_row.get('company_code','') if 'selected_customer_row' in locals() else '',
                                    'customer_phone': selected_customer_row.get('phone','') if 'selected_customer_row' in locals() else '',
                                    'customer_email': selected_customer_row.get('email','') if 'selected_customer_row' in locals() else '',
                                    'seller_name': 'Four Star Industries Pvt. Ltd.',
                                    'seller_address': '',
                                    'customer_address': selected_customer_row.get('address','') if 'selected_customer_row' in locals() else '',
                                    'customer_company_code': selected_customer_row.get('company_code','') if 'selected_customer_row' in locals() else '',
                                    'customer_phone': selected_customer_row.get('phone','') if 'selected_customer_row' in locals() else '',
                                    'customer_email': selected_customer_row.get('email','') if 'selected_customer_row' in locals() else '',
                                    'ship_to_name': selected_ship_to.get('ship_to_name', ''),
                                    'ship_to_id': selected_ship_to.get('ship_to_id', ''),
                                    'ship_to_addressline1': selected_ship_to.get('addressline1', ''),
                                    'ship_to_addressline2': selected_ship_to.get('addressline2', ''),
                                    'ship_to_addressline3': selected_ship_to.get('addressline3', ''),
                                    'ship_to_vendor_gstin': selected_ship_to.get('vendor_gstin', ''),
                                    'ship_to_vendor_phone': selected_ship_to.get('vendor_phone', ''),
                                    'ship_to_vendor_email': selected_ship_to.get('vendor_email', ''), 'shipment_no': row['shipment_no'], 'original_invoice_no': row['invoice_no'], 'delivery_invoice_no': delivery_invoice_no, 'delivery_date': str(delivery_date), 'vehicle_number': vehicle_number.strip(), 'asn_number': asn_number.strip(), 'asn_date': str(asn_date), 'packaging_details': packaging_details.strip(), 'payment_term': selected_term, 'payment_due_date': str(payment_due_date), 'product_code': row['product_code'], 'product_name': row['product_name'], 'po_number': row.get('po_number', ''), 'po_date': row.get('po_date', ''), 'pallet_no': row['pallet_no'], 'original_invoice_no': row.get('invoice_no') or '', 'qty': total_qty, 'unit_price': price, 'currency': row['currency'], 'sale_amount': total_amount}
                if save_error:
                    st.stop()
                notify_event('delivery', 'Delivery Created', f"Delivery Invoice: {delivery_invoice_no}\\nOriginal Invoice: {selected_ship['invoice_no']}\\nCustomer: {customer}\\nQty: {total_qty}\\nAmount: {total_amount}\\nDue Date: {payment_due_date}")
                print_data = build_delivery_invoice_print_data(delivery_invoice_no.strip()) or first_print
                if print_data:
                    st.session_state.last_delivery_print = print_data
                st.session_state.last_delivery_pdf_invoice_no = delivery_invoice_no.strip()
                st.session_state['delivery_invoice_auto_source'] = ''
                st.success('Delivery saved successfully. Email notification attempted if enabled. Print popup opened.')
                st.rerun()
if 'last_delivery_pdf_invoice_no' in st.session_state:
    _pdf_invoice_no = st.session_state.get('last_delivery_pdf_invoice_no')
    _invoice, _lines = get_saved_delivery_invoice_for_pdf(_pdf_invoice_no)
    if _invoice and _lines:
        try:
            _pdf_bytes = delivery_invoice_pdf_bytes(_invoice, _lines)
            st.download_button('Print / Download Delivery Invoice PDF', _pdf_bytes, f'delivery_invoice_{_pdf_invoice_no}.pdf', mime='application/pdf', key='download_delivery_invoice_pdf_after_save')
        except Exception as _pdf_error:
            st.error(f'Delivery Invoice PDF generation failed: {_pdf_error}')
    else:
        st.warning('Delivery was saved, but saved invoice lines were not found for PDF generation.')
    del st.session_state.last_delivery_pdf_invoice_no
if 'last_delivery_print' in st.session_state:
    html_doc = delivery_note_html(st.session_state.last_delivery_print)
    print_popup(html_doc)
    st.download_button('Download Delivery Invoice HTML Backup', html_doc, 'delivery_invoice_print.html', mime='text/html', key='download_delivery_note_html')
    del st.session_state.last_delivery_print

render_slogan_footer()
