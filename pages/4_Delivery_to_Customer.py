
import io
import base64

def build_delivery_invoice_dataframe(invoice, line_items):
    rows = []
    total_qty = 0
    total_amt = 0
    for i, item in enumerate(line_items, start=1):
        qty = float(item.get("qty") or item.get("delivered_qty") or 0)
        price = float(item.get("price") or item.get("unit_price") or 0)
        amount = float(item.get("amount") or qty * price)
        total_qty += qty
        total_amt += amount
        rows.append({
            "Sr": i,
            "Delivery Invoice No": invoice.get("delivery_invoice_no", ""),
            "Delivery Date": invoice.get("delivery_date", ""),
            "Ship To Name": invoice.get("ship_to_name", ""),
            "Ship To ID": invoice.get("ship_to_id", ""),
            "Addressline1": invoice.get("ship_to_addressline1", ""),
            "Addressline2": invoice.get("ship_to_addressline2", ""),
            "Addressline3": invoice.get("ship_to_addressline3", ""),
            "vendorGSTIN": invoice.get("ship_to_vendor_gstin", ""),
            "vendorphone": invoice.get("ship_to_vendor_phone", ""),
            "vendoremail": invoice.get("ship_to_vendor_email", ""),
            "Product Code": item.get("product_code", ""),
            "Product Name": item.get("product_name", ""),
            "Pallet No": item.get("pallet_no", ""),
            "Box No": item.get("box_no", ""),
            "PO Number": item.get("po_number", invoice.get("po_number", "")),
            "PO Date": item.get("po_date", invoice.get("po_date", "")),
            "Qty": qty,
            "Price": price,
            "Currency": item.get("currency", ""),
            "Amount": amount,
        })
    rows.append({"Sr": "", "Product Name": "TOTAL", "Qty": total_qty, "Amount": total_amt})
    return pd.DataFrame(rows)

def delivery_invoice_excel_bytes(invoice, line_items):
    df = build_delivery_invoice_dataframe(invoice, line_items)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Delivery Invoice")
    return output.getvalue()

def delivery_invoice_pdf_bytes(invoice, line_items):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=18, leftMargin=18, topMargin=18, bottomMargin=18)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("<b>DELIVERY / COMMERCIAL INVOICE</b>", styles["Title"]))
    story.append(Spacer(1, 8))
    ship_to_text = f"""
    <b>Ship To:</b> {invoice.get('ship_to_name','')}<br/>
    <b>Ship To ID:</b> {invoice.get('ship_to_id','')}<br/>
    {invoice.get('ship_to_addressline1','')}<br/>
    {invoice.get('ship_to_addressline2','')}<br/>
    {invoice.get('ship_to_addressline3','')}<br/>
    <b>vendorGSTIN:</b> {invoice.get('ship_to_vendor_gstin','')}<br/>
    <b>vendorphone:</b> {invoice.get('ship_to_vendor_phone','')}<br/>
    <b>vendoremail:</b> {invoice.get('ship_to_vendor_email','')}
    """
    invoice_text = f"""
    <b>Delivery Invoice No:</b> {invoice.get('delivery_invoice_no','')}<br/>
    <b>Delivery Date:</b> {invoice.get('delivery_date','')}<br/>
    <b>Original Invoice:</b> {invoice.get('original_invoice_no','')}<br/>
    <b>Shipment No:</b> {invoice.get('shipment_no','')}<br/>
    <b>Payment Due Date:</b> {invoice.get('payment_due_date','')}
    """
    story.append(Table([[Paragraph(ship_to_text, styles["Normal"]), Paragraph(invoice_text, styles["Normal"])]], colWidths=[390, 390]))
    story.append(Spacer(1, 10))
    data = [["Sr", "Product", "Pallet", "Box", "PO No", "PO Date", "Qty", "Price", "Cur", "Amount"]]
    total_qty = total_amt = 0
    for i, item in enumerate(line_items, start=1):
        qty = float(item.get("qty") or 0)
        price = float(item.get("price") or 0)
        amount = float(item.get("amount") or qty * price)
        total_qty += qty
        total_amt += amount
        data.append([i, f"{item.get('product_code','')} {item.get('product_name','')}", item.get("pallet_no",""), item.get("box_no",""), item.get("po_number",""), item.get("po_date",""), f"{qty:,.0f}", f"{price:,.2f}", item.get("currency",""), f"{amount:,.2f}"])
    data.append(["", "TOTAL", "", "", "", "", f"{total_qty:,.0f}", "", "", f"{total_amt:,.2f}"])
    tbl = Table(data, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1f2f57")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (6,1), (-1,-1), "RIGHT"),
    ]))
    story.append(tbl)
    doc.build(story)
    return buffer.getvalue()

def delivery_invoice_jpeg_placeholder(invoice, line_items):
    # Streamlit/JPEG generation from HTML would require browser rendering.
    # This exports a print-ready HTML file that can be saved/printed as JPEG from browser.
    html_bytes = delivery_invoice_print_html(invoice, line_items).encode("utf-8")
    return html_bytes

import html
from common import *



def delivery_print_data_to_pdf_payload(data):
    """Convert common build_delivery_invoice_print_data output to PDF helper payload."""
    invoice = {
        "delivery_invoice_no": data.get("delivery_invoice_no", ""),
        "delivery_date": data.get("delivery_date", ""),
        "payment_due_date": data.get("payment_due_date", ""),
        "customer_name": data.get("customer_name", ""),
        "original_invoice_no": data.get("original_invoice_no", ""),
        "shipment_no": data.get("shipment_no", ""),
        "po_number": data.get("po_number", ""),
        "po_date": data.get("po_date", ""),
        "ship_to_name": data.get("ship_to_name", ""),
        "ship_to_id": data.get("ship_to_id", ""),
        "ship_to_addressline1": data.get("ship_to_addressline1", ""),
        "ship_to_addressline2": data.get("ship_to_addressline2", ""),
        "ship_to_addressline3": data.get("ship_to_addressline3", ""),
        "ship_to_vendor_gstin": data.get("ship_to_vendor_gstin", ""),
        "ship_to_vendor_phone": data.get("ship_to_vendor_phone", ""),
        "ship_to_vendor_email": data.get("ship_to_vendor_email", ""),
        "vehicle_number": data.get("vehicle_number", ""),
        "asn_number": data.get("asn_number", ""),
        "asn_date": data.get("asn_date", ""),
        "packaging_details": data.get("packaging_details", ""),
    }
    line_items = []
    for item in data.get("items") or []:
        line_items.append({
            "product_code": item.get("product_code", ""),
            "product_name": item.get("product_name", ""),
            "pallet_no": item.get("pallet_no", ""),
            "box_no": item.get("box_no", ""),
            "po_number": item.get("po_number", data.get("po_number", "")),
            "po_date": format_date_ddmmyyyy(item.get("po_date") or data.get("po_date", "")),
            "qty": item.get("qty") or 0,
            "price": item.get("unit_price") or item.get("price") or 0,
            "currency": item.get("currency", data.get("currency", "")),
            "amount": item.get("amount") or 0,
        })
    return invoice, line_items

page_setup()

show_header('Delivery Entry', 'Invoice-style FIFO delivery form with multi-pallet selection')

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
invoice_shipments = fetch_all('\n            SELECT id, shipment_no, invoice_no, po_number, po_date, shipment_date\n            FROM shipments\n            ORDER BY shipment_date ASC, id ASC\n        ')
if not customers or not invoice_shipments:
    st.warning('Create Customer Master and Shipment Entry first.')
else:
    customer_map = {x['customer_name']: x['id'] for x in customers}
    term_map = {f"{x['term_name']} - {x['days']} days": x for x in terms}
    ship_to_map = {f"{x['ship_to_name']} | {x.get('ship_to_id') or '-'}": x for x in ship_to_rows}
    inv_map = {f"{s['invoice_no']} | Shipment {s['shipment_no']} | PO {s.get('po_number') or '-'} | Date {s['shipment_date']}": s for s in invoice_shipments}
    ctop1, ctop2 = st.columns(2)
    with ctop1:
        st.markdown('<div class="input-section-title">Original Invoice Number with Shipment Number</div>', unsafe_allow_html=True)
        selected_invoice = searchable_selectbox('Original Invoice Number with Shipment Number', list(inv_map.keys()), key='delivery_original_invoice_ship')
    invoice_top_col1, invoice_top_col2 = st.columns(2)
    with invoice_top_col1:
        delivery_invoice_no = st.text_input('Delivery Invoice Number', key='delivery_invoice_v10')
    with invoice_top_col2:
        delivery_date = st.date_input('Delivery Date', value=date.today(), key='delivery_date_v10')
    extra_col1, extra_col2, extra_col3, extra_col4 = st.columns(4)
    with extra_col1:
        vehicle_number = st.text_input('Vehicle Number', key='delivery_vehicle_number')
    with extra_col2:
        asn_number = st.text_input('ASN Number', key='delivery_asn_number')
    with extra_col3:
        asn_date = st.date_input('ASN Date', value=date.today(), key='delivery_asn_date')
    with extra_col4:
        packaging_details = st.text_input('Packaging Details', key='delivery_packaging_details')
    selected_ship = inv_map[selected_invoice]
    available_rows = fetch_all('\n                SELECT\n                    b.*,\n                    s.shipment_no,\n                    s.invoice_no,\n                    s.shipment_date,\n                    COALESCE(b.po_number, s.po_number) AS po_number,\n                    COALESCE(b.po_date, s.po_date) AS po_date,\n                    p.product_code,\n                    p.product_name,\n                    COALESCE(del.delivered_qty, 0) AS delivered_qty,\n                    b.original_qty - COALESCE(del.delivered_qty, 0) AS balance_qty\n                FROM shipment_boxes b\n                JOIN shipments s ON b.shipment_id = s.id\n                JOIN products p ON b.product_id = p.id\n                LEFT JOIN (\n                    SELECT box_id, SUM(delivered_qty) AS delivered_qty\n                    FROM customer_deliveries\n                    GROUP BY box_id\n                ) del ON b.id = del.box_id\n                WHERE s.id = ?\n                  AND b.original_qty - COALESCE(del.delivered_qty, 0) > 0\n                ORDER BY s.shipment_date ASC, b.pallet_no ASC, b.id ASC\n            ', (selected_ship['id'],))
    if not available_rows:
        st.warning('No pending pallet quantity available for this original invoice/shipment.')
    else:
        sort_mode = st.radio('Sort Pallet/Product Rows', ['FIFO ID', 'Pallet Number'], horizontal=True, key='delivery_fifo_sort_mode')
        if sort_mode == 'Pallet Number':
            available_rows = sorted(available_rows, key=lambda x: str(x.get('pallet_no') or ''))
        else:
            available_rows = sorted(available_rows, key=lambda x: (int(x.get('fifo_row_id') or x.get('id') or 0), str(x.get('pallet_no') or '')))
        pallet_map = {f"ID {r.get('fifo_row_id') or r.get('id')} | Pallet {r['pallet_no']} | Box {r['box_no'] or '-'} | {r['product_code']} | PO {r.get('po_number') or '-'} | PO Date {format_date_ddmmyyyy(r.get('po_date')) if r.get('po_date') else '-'} | Balance {r['balance_qty']} | Price {r['unit_price']} {r['currency']}": r for r in available_rows}
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
                st.write(f"ID {row.get('fifo_row_id') or row.get('id')} | Pallet {row['pallet_no']} | {row['product_code']} | Balance {row['balance_qty']}")
            with dc2:
                edited_po_number = st.text_input('PO Number', value=str(row.get('po_number') or ''), key=f"delivery_row_po_number_{row['id']}_{i}", label_visibility='collapsed')
            with dc3:
                try:
                    row_po_date_default = parse_db_date(row.get('po_date')) or date.today()
                except Exception:
                    row_po_date_default = date.today()
                edited_po_date = st.date_input('PO Date', value=row_po_date_default, key=f"delivery_row_po_date_{row['id']}_{i}", label_visibility='collapsed')
            with dc4:
                qty = st.number_input('Qty', min_value=0.0, max_value=float(row['balance_qty']), value=0.0, step=1.0, key=f"delivery_qty_{row['id']}_{i}", label_visibility='collapsed')
            with dc5:
                price = st.number_input('Price', min_value=0.0, value=float(row['unit_price'] or 0), step=1.0, key=f"delivery_price_{row['id']}_{i}", label_visibility='collapsed')
            with dc6:
                amount = qty * price
                st.write(f"{amount:,.2f} {row['currency']}")
            row['po_number'] = edited_po_number.strip()
            row['po_date'] = str(edited_po_date)
            if qty > 0:
                total_qty += qty
                total_amount += amount
                delivery_inputs.append((row, qty, price, amount))
        st.markdown(f'<div class="total-box">Total Delivery Qty: {total_qty} &nbsp;&nbsp; | &nbsp;&nbsp; Total Amount: {total_amount:,.2f}</div>', unsafe_allow_html=True)
        st.subheader('FIFO Available Pallets')
        fifo_display_rows = []
        for r in available_rows:
            if float(r.get('balance_qty') or 0) > 0:
                fifo_display_rows.append({'fifo_row_id': r.get('fifo_row_id') or r.get('id'), 'shipment_no': r['shipment_no'], 'original_invoice_no': r['invoice_no'], 'po_number': r.get('po_number', ''), 'po_date': r.get('po_date', ''), 'shipment_date': r['shipment_date'], 'pallet_no': r['pallet_no'], 'box_no': r['box_no'] or '-', 'product_code': r['product_code'], 'product_name': r['product_name'], 'original_qty': r['original_qty'], 'delivered_qty': r['delivered_qty'], 'balance_qty': r['balance_qty'], 'unit_price': r['unit_price'], 'currency': r['currency']})
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
                    execute_query('''
                                INSERT INTO customer_deliveries
                                (shipment_id, box_id, customer_id, ship_to_master_id, delivery_date, delivered_qty, delivery_invoice_no,
                                 vehicle_number, asn_number, asn_date, packaging_details,
                                 payment_term_id, payment_terms_days, payment_due_date, unit_price, currency, sale_amount, attachment_path, po_number, po_date)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (row['shipment_id'], row['id'], customer_map[customer], selected_ship_to.get('id'), str(delivery_date), qty, delivery_invoice_no.strip(),
                                vehicle_number.strip(), asn_number.strip(), str(asn_date), packaging_details.strip(),
                                term['id'], term['days'], str(payment_due_date), price, row['currency'], amount, path, row.get('po_number', ''), row.get('po_date', None)))
                    if first_print is None:
                        first_print = {'customer_name': customer,
                                    'ship_to_name': selected_ship_to.get('ship_to_name', ''),
                                    'ship_to_id': selected_ship_to.get('ship_to_id', ''),
                                    'ship_to_addressline1': selected_ship_to.get('addressline1', ''),
                                    'ship_to_addressline2': selected_ship_to.get('addressline2', ''),
                                    'ship_to_addressline3': selected_ship_to.get('addressline3', ''),
                                    'ship_to_vendor_gstin': selected_ship_to.get('vendor_gstin', ''),
                                    'ship_to_vendor_phone': selected_ship_to.get('vendor_phone', ''),
                                    'ship_to_vendor_email': selected_ship_to.get('vendor_email', ''), 'shipment_no': row['shipment_no'], 'original_invoice_no': row['invoice_no'], 'delivery_invoice_no': delivery_invoice_no, 'delivery_date': str(delivery_date), 'vehicle_number': vehicle_number.strip(), 'asn_number': asn_number.strip(), 'asn_date': str(asn_date), 'packaging_details': packaging_details.strip(), 'payment_term': selected_term, 'payment_due_date': str(payment_due_date), 'product_code': row['product_code'], 'product_name': row['product_name'], 'po_number': row.get('po_number', ''), 'po_date': row.get('po_date', ''), 'pallet_no': row['pallet_no'], 'box_no': row['box_no'] or '-', 'qty': total_qty, 'unit_price': price, 'currency': row['currency'], 'sale_amount': total_amount}
                notify_event('delivery', 'Delivery Created', f"Delivery Invoice: {delivery_invoice_no}\\nOriginal Invoice: {selected_ship['invoice_no']}\\nCustomer: {customer}\\nQty: {total_qty}\\nAmount: {total_amount}\\nDue Date: {payment_due_date}")
                print_data = build_delivery_invoice_print_data(delivery_invoice_no.strip()) or first_print
                if print_data:
                    st.session_state.last_delivery_print = print_data
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
    selected_delivery_invoice_label = searchable_selectbox('Select Delivery Invoice No', invoice_options, key='selected_delivery_invoice_for_details')
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
    st.markdown('<div class="sap-subtitle">Export Selected Delivery Invoice</div>', unsafe_allow_html=True)
    export_data = build_delivery_invoice_print_data(selected_delivery_invoice_no)
    if export_data:
        export_invoice, export_line_items = delivery_print_data_to_pdf_payload(export_data)
        exp1, exp2, exp3 = st.columns(3)
        with exp1:
            st.download_button(
                'Export Delivery Invoice PDF',
                delivery_invoice_pdf_bytes(export_invoice, export_line_items),
                file_name=f"delivery_invoice_{selected_delivery_invoice_no}.pdf",
                mime='application/pdf',
                key=f'export_delivery_pdf_{selected_delivery_invoice_no}',
            )
        with exp2:
            st.download_button(
                'Export Delivery Invoice Excel',
                delivery_invoice_excel_bytes(export_invoice, export_line_items),
                file_name=f"delivery_invoice_{selected_delivery_invoice_no}.xlsx",
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                key=f'export_delivery_excel_{selected_delivery_invoice_no}',
            )
        with exp3:
            st.download_button(
                'Export Delivery Invoice HTML',
                delivery_note_html(export_data),
                file_name=f"delivery_invoice_{selected_delivery_invoice_no}.html",
                mime='text/html',
                key=f'export_delivery_html_{selected_delivery_invoice_no}',
            )

    if 'last_delivery_reprint' in st.session_state:
        print_popup(st.session_state.last_delivery_reprint)
        st.download_button('Download Reprint Delivery Invoice HTML', st.session_state.last_delivery_reprint, 'delivery_invoice_reprint.html', mime='text/html', key='download_reprint_delivery_invoice_html')
        del st.session_state.last_delivery_reprint
    st.markdown('### Delivery Invoice Product Details')
    detail_rows = fetch_all('\n                SELECT d.id, d.delivery_invoice_no, d.delivery_date, s.invoice_no AS original_invoice_no,\n                       s.shipment_no, p.product_code, p.product_name, b.pallet_no, b.box_no,\n                       d.delivered_qty, d.unit_price, d.currency, d.sale_amount, d.payment_due_date, d.vehicle_number, d.asn_number, d.asn_date, d.packaging_details\n                FROM customer_deliveries d\n                JOIN shipments s ON d.shipment_id = s.id\n                JOIN shipment_boxes b ON d.box_id = b.id\n                JOIN products p ON b.product_id = p.id\n                WHERE d.delivery_invoice_no=?\n                ORDER BY d.id\n            ', (selected_delivery_invoice_no,))
    show_filtered_df(edit_button_column(detail_rows, 'delivery'), f'delivery_invoice_detail_{selected_delivery_invoice_no}', total=True)
if st.session_state.user['role'] == 'super_admin':
    st.divider()
    st.subheader('Edit Delivery Entry')
    cleanup_orphan_transactions()
    old_deliveries = fetch_all('\n                SELECT d.*, c.customer_name, s.invoice_no AS original_invoice_no, s.shipment_no\n                FROM customer_deliveries d\n                JOIN customers c ON d.customer_id = c.id\n                JOIN shipments s ON d.shipment_id = s.id\n                JOIN shipment_boxes b ON d.box_id = b.id\n                ORDER BY d.id DESC\n            ')
    if old_deliveries:
        dmap = {f"{d['id']} | {d['delivery_invoice_no']} | {d['customer_name']}": d for d in old_deliveries}
        selected_delivery_edit_key = searchable_selectbox('Select Delivery to Edit', list(dmap.keys()), key='edit_delivery_select')
        ed = dmap[selected_delivery_edit_key]
        dc1, dc2 = st.columns(2)
        with dc1:
            ed_inv = st.text_input('Edit Delivery Invoice No', ed['delivery_invoice_no'] or '', key='edit_delivery_inv')
            ed_date = st.text_input('Edit Delivery Date YYYY-MM-DD', ed['delivery_date'] or '', key='edit_delivery_date')
            ed_qty = st.number_input('Edit Delivered Qty', min_value=0.0, value=float(ed['delivered_qty'] or 0), step=1.0, key='edit_delivery_qty')
        with dc2:
            ed_price = st.number_input('Edit Unit Price', min_value=0.0, value=float(ed['unit_price'] or 0), step=1.0, key='edit_delivery_price')
            ed_currency = st.selectbox('Edit Currency', CURRENCIES, index=CURRENCIES.index(ed['currency']) if ed['currency'] in CURRENCIES else 0, key='edit_delivery_currency')
            ed_due = st.text_input('Edit Payment Due Date YYYY-MM-DD', ed['payment_due_date'] or '', key='edit_delivery_due')
            ed_vehicle = st.text_input('Edit Vehicle Number', ed.get('vehicle_number') or '', key='edit_delivery_vehicle')
            ed_asn_no = st.text_input('Edit ASN Number', ed.get('asn_number') or '', key='edit_delivery_asn_no')
            ed_asn_date = st.text_input('Edit ASN Date YYYY-MM-DD', ed.get('asn_date') or '', key='edit_delivery_asn_date')
            ed_packaging = st.text_input('Edit Packaging Details', ed.get('packaging_details') or '', key='edit_delivery_packaging')
        ed_amount = ed_qty * ed_price
        st.markdown(f'<div class="total-box">New Sale Amount: {ed_amount:,.2f} {ed_currency}</div>', unsafe_allow_html=True)
        if st.button('Update Delivery', type='primary', key='update_delivery'):
            execute_query('\n                        UPDATE customer_deliveries\n                        SET delivery_invoice_no=?, delivery_date=?, delivered_qty=?, unit_price=?, currency=?, sale_amount=?, payment_due_date=?, vehicle_number=?, asn_number=?, asn_date=?, packaging_details=?\n                        WHERE id=?\n                    ', (ed_inv, ed_date, ed_qty, ed_price, ed_currency, ed_amount, ed_due, ed_vehicle, ed_asn_no, ed_asn_date or None, ed_packaging, ed['id']))
            st.success('Delivery updated successfully.')
            st.rerun()

st.markdown('<div class="footer">COPYRIGHT BY FOUR STAR INDUSTRIES PVT. LTD.</div>', unsafe_allow_html=True)


def delivery_invoice_print_html(invoice, line_items):
    """Commercial invoice style print layout using Ship To Master details."""
    rows_html = ""
    total_qty = 0
    total_amt = 0
    for i, item in enumerate(line_items, start=1):
        qty = float(item.get("qty") or item.get("delivered_qty") or 0)
        price = float(item.get("price") or item.get("unit_price") or 0)
        amount = float(item.get("amount") or qty * price)
        total_qty += qty
        total_amt += amount
        rows_html += f"""
        <tr>
            <td>{i}</td>
            <td>{html.escape(str(item.get('product_code','')))}</td>
            <td>{html.escape(str(item.get('product_name','')))}</td>
            <td>{html.escape(str(item.get('pallet_no','')))}</td>
            <td>{html.escape(str(item.get('box_no','') or '-'))}</td>
            <td style="text-align:right;">{qty:,.0f}</td>
            <td style="text-align:right;">{price:,.2f}</td>
            <td>{html.escape(str(item.get('currency','')))}</td>
            <td style="text-align:right;">{amount:,.2f}</td>
        </tr>
        """
    return f"""
    <html>
    <head>
    <style>
    @media print {{
        body {{ margin: 0; }}
        .no-print {{ display:none; }}
    }}
    body {{ font-family: Arial, sans-serif; color:#111; }}
    .invoice-wrap {{ width: 100%; max-width: 1100px; margin: 0 auto; padding: 18px; }}
    .title {{ text-align:center; font-size: 22px; font-weight: 800; margin-bottom: 12px; }}
    .section {{ border:1px solid #111; margin-bottom:10px; }}
    .section-title {{ background:#1f2f57; color:white; font-weight:800; padding:6px 8px; }}
    .grid {{ display:grid; grid-template-columns: 1fr 1fr; }}
    .box {{ padding:8px; border-right:1px solid #111; min-height:110px; }}
    .box:last-child {{ border-right:0; }}
    table {{ width:100%; border-collapse: collapse; font-size: 12px; }}
    th {{ background:#1f2f57; color:white; padding:6px; border:1px solid #111; text-align:left; }}
    td {{ padding:6px; border:1px solid #111; vertical-align:top; }}
    .right {{ text-align:right; }}
    .bold {{ font-weight:800; }}
    </style>
    </head>
    <body>
    <div class="invoice-wrap">
        <div class="title">DELIVERY / COMMERCIAL INVOICE</div>

        <div class="section">
            <div class="section-title">Invoice Details</div>
            <table>
                <tr>
                    <td class="bold">Delivery Invoice No.</td><td>{html.escape(str(invoice.get('delivery_invoice_no','')))}</td>
                    <td class="bold">Delivery Date</td><td>{html.escape(str(invoice.get('delivery_date','')))}</td>
                </tr>
                <tr>
                    <td class="bold">Original Invoice</td><td>{html.escape(str(invoice.get('original_invoice_no','')))}</td>
                    <td class="bold">Shipment No.</td><td>{html.escape(str(invoice.get('shipment_no','')))}</td>
                </tr>
                <tr>
                    <td class="bold">PO Number</td><td>{html.escape(str(invoice.get('po_number','')))}</td>
                    <td class="bold">PO Date</td><td>{html.escape(str(invoice.get('po_date','')))}</td>
                </tr>
            </table>
        </div>

        <div class="section">
            <div class="section-title">Ship To Details</div>
            <div class="grid">
                <div class="box">
                    <div class="bold">{html.escape(str(invoice.get('ship_to_name','')))}</div>
                    <div>Ship To ID: {html.escape(str(invoice.get('ship_to_id','')))}</div>
                    <div>{html.escape(str(invoice.get('ship_to_addressline1','')))}</div>
                    <div>{html.escape(str(invoice.get('ship_to_addressline2','')))}</div>
                    <div>{html.escape(str(invoice.get('ship_to_addressline3','')))}</div>
                </div>
                <div class="box">
                    <div><span class="bold">vendorGSTIN:</span> {html.escape(str(invoice.get('ship_to_vendor_gstin','')))}</div>
                    <div><span class="bold">vendorphone:</span> {html.escape(str(invoice.get('ship_to_vendor_phone','')))}</div>
                    <div><span class="bold">vendoremail:</span> {html.escape(str(invoice.get('ship_to_vendor_email','')))}</div>
                    <div><span class="bold">Customer:</span> {html.escape(str(invoice.get('customer_name','')))}</div>
                    <div><span class="bold">Payment Due:</span> {html.escape(str(invoice.get('payment_due_date','')))}</div>
                </div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">Product Details</div>
            <table>
                <thead>
                    <tr>
                        <th>Sr.</th><th>Product Code</th><th>Description</th><th>Pallet</th><th>Box</th>
                        <th>Qty</th><th>Rate</th><th>Currency</th><th>Amount</th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
                <tfoot>
                    <tr>
                        <td colspan="5" class="right bold">TOTAL</td>
                        <td class="right bold">{total_qty:,.0f}</td>
                        <td></td><td></td>
                        <td class="right bold">{total_amt:,.2f}</td>
                    </tr>
                </tfoot>
            </table>
        </div>

        <button class="no-print" onclick="window.print()" style="padding:10px 18px;font-weight:800;">Print Invoice</button>
    </div>
    </body>
    </html>
    """
