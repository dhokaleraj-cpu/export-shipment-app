from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Image as RLImage

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
    """One-page A4 portrait PDF Delivery Invoice.

    Print and reprint both use this same PDF-only layout.
    Footer is a single unified table so Amount Summary grid aligns exactly
    with the footer border.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18,
        leftMargin=18,
        topMargin=16,
        bottomMargin=14
    )

    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    small = styles["BodyText"]
    title_style = styles["Title"]
    heading_style = styles["Heading2"]

    for style in [normal, small, title_style, heading_style]:
        style.fontName = "Helvetica"

    # Increased readable A4 font size.
    normal.fontSize = 8.1
    normal.leading = 9.5
    small.fontSize = 7.6
    small.leading = 8.8
    title_style.fontName = "Helvetica-Bold"
    title_style.fontSize = 15.4
    title_style.leading = 17
    heading_style.fontName = "Helvetica-Bold"
    heading_style.fontSize = 10.8
    heading_style.leading = 12.5

    white_header_style = ParagraphStyle(
        "white_header_style",
        parent=normal,
        fontName="Helvetica-Bold",
        fontSize=8.3,
        leading=9.8,
        textColor=colors.white,
    )

    story = []
    page_width = A4[0] - 36
    navy = colors.HexColor("#1f2f57")
    grey = colors.HexColor("#d9d9d9")
    light_total = colors.HexColor("#f3f4f6")

    logo_cell = Paragraph("<b>FSI LOGO</b>", heading_style)
    try:
        if LOGO_PATH.exists():
            logo_cell = RLImage(str(LOGO_PATH), width=86, height=32)
    except Exception:
        logo_cell = Paragraph("<b>FSI LOGO</b>", heading_style)

    title_table = Table(
        [[logo_cell, Paragraph("<b>DELIVERY / COMMERCIAL INVOICE</b>", title_style)]],
        colWidths=[112, page_width - 112],
        rowHeights=[44]
    )
    title_table.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 0.5, colors.black),
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (0,0), (0,0), "CENTER"),
        ("ALIGN", (1,0), (1,0), "CENTER"),
    ]))
    story.append(title_table)
    story.append(Spacer(1, 4))

    seller_name = invoice.get("seller_name") or invoice.get("company_name") or "Four Star Industries Pvt. Ltd."
    seller_address = invoice.get("seller_address") or invoice.get("company_address") or ""
    company_code = invoice.get("customer_company_code") or invoice.get("company_code") or ""

    seller = f"""<b>Seller</b><br/>
{seller_name}<br/>
{seller_address}<br/>
<b>Company Code:</b> {company_code}"""

    invoice_details = f"""<b>Delivery Invoice No:</b> {invoice.get('delivery_invoice_no','')}<br/>
Delivery Date: {invoice.get('delivery_date','')}"""

    ship = f"""<b>Ship To</b><br/>
{invoice.get('ship_to_name','')}<br/>
{invoice.get('ship_to_addressline1','')}<br/>
{invoice.get('ship_to_addressline2','')}<br/>
{invoice.get('ship_to_addressline3','')}"""

    bill = f"""<b>Bill To</b><br/>
{invoice.get('customer_name','')}<br/>
{invoice.get('customer_address','')}"""

    addr_table = Table(
        [
            [Paragraph(seller, normal), Paragraph(invoice_details, normal)],
            [Paragraph(ship, normal), Paragraph(bill, normal)],
        ],
        colWidths=[page_width / 2, page_width / 2],
        rowHeights=[70, 78]
    )
    addr_table.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 0.5, colors.black),
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 7),
        ("RIGHTPADDING", (0,0), (-1,-1), 7),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(addr_table)
    story.append(Spacer(1, 4))

    info_style = ParagraphStyle(
        "invoice_info_style",
        parent=normal,
        fontName="Helvetica",
        fontSize=8.1,
        leading=9.5,
        wordWrap="CJK",
    )
    info_data = [
        [
            Paragraph("<b>Payment Due Date:</b>", info_style),
            Paragraph(str(invoice.get("payment_due_date","")), info_style),
            Paragraph("<b>Vehicle Number:</b>", info_style),
            Paragraph(str(invoice.get("vehicle_number","")), info_style),
        ],
        [
            Paragraph("<b>ASN Number:</b>", info_style),
            Paragraph(str(invoice.get("asn_number","")), info_style),
            Paragraph("<b>ASN Date:</b>", info_style),
            Paragraph(str(invoice.get("asn_date","")), info_style),
        ],
    ]
    info_table = Table(
        info_data,
        colWidths=[page_width * 0.225, page_width * 0.275, page_width * 0.225, page_width * 0.275],
        rowHeights=[24, 24]
    )
    info_table.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 0.5, colors.black),
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 4))

    data = [[
        "Sr", "Product", "FSI Orig Inv #", "PO No", "PO Date",
        "Pallet", "Qty", "Rate", "Cur", "Amount"
    ]]

    total_qty = 0.0
    total_amt = 0.0
    currency_set = set()

    for i, item in enumerate(line_items, start=1):
        qty = float(item.get("qty") or item.get("delivered_qty") or 0)
        price = float(item.get("price") or item.get("unit_price") or 0)
        amount = float(item.get("amount") or qty * price)
        currency = str(item.get("currency") or invoice.get("currency") or "$")
        if currency:
            currency_set.add(currency)
        total_qty += qty
        total_amt += amount

        product_text = f"{item.get('product_code','')} {item.get('product_name','')}"
        data.append([
            str(i),
            Paragraph(str(product_text), small),
            str(item.get("original_invoice_no") or invoice.get("original_invoice_no", "")),
            str(item.get("po_number") or ""),
            str(item.get("po_date") or ""),
            str(item.get("pallet_no") or ""),
            f"{qty:,.0f}",
            f"{price:,.2f}",
            currency,
            f"{amount:,.2f}",
        ])

    invoice_currency = ", ".join(sorted(currency_set)) if currency_set else "$"
    data.append(["", "TOTAL", "", "", "", "", f"{total_qty:,.0f}", "", invoice_currency, f"{total_amt:,.2f}"])

    body_widths = [24, 112, 76, 55, 52, 48, 42, 50, 35, 52]
    body_table = Table(data, repeatRows=1, colWidths=body_widths)
    body_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), navy),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.45, colors.black),
        ("BOX", (0,0), (-1,-1), 0.5, colors.black),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 7.7),
        ("ALIGN", (6,1), (-1,-1), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 3),
        ("RIGHTPADDING", (0,0), (-1,-1), 3),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    story.append(body_table)

    # Footer position: push toward bottom while avoiding a second page.
    row_count = len(line_items)
    if row_count <= 2:
        story.append(Spacer(1, 128))
    elif row_count <= 4:
        story.append(Spacer(1, 100))
    elif row_count <= 6:
        story.append(Spacer(1, 65))
    else:
        story.append(Spacer(1, 28))

    packaging = str(invoice.get("packaging_details") or "")
    packaging_value = Paragraph(packaging.replace("\n", "<br/>"), normal)

    bank_details = Paragraph(
        "<b>BANK DETAILS:</b><br/>"
        "BANK ACCOUNT NO : 004330150000003<br/>"
        "BANK IFSC CODE : BKID0000043<br/>"
        "BANK MICR CODE : 400013080<br/>"
        "BANK SWIFT CODE : BKIDINBBPPD",
        normal
    )

    subtotal = total_amt
    grand_total = subtotal

    # Unified footer table. No nested subtotal table, so grid lines align exactly
    # with the footer border and the amount section never has an inset mismatch.
    left_w = page_width - 180
    label_w = 82
    cur_w = 30
    amt_w = 68

    footer_data = [
        [
            Paragraph("<b>PACKAGING DETAILS:</b>", white_header_style),
            Paragraph("<b>AMOUNT SUMMARY</b>", white_header_style),
            "",
            "",
        ],
        [packaging_value, "SUBTOTAL", invoice_currency, f"{subtotal:,.2f}"],
        ["", "TAX", "", "-"],
        ["", "OTHER", "", "-"],
        ["", "TOTAL", invoice_currency, f"{grand_total:,.2f}"],
        [bank_details, "", "", ""],
    ]

    footer_table = Table(
        footer_data,
        colWidths=[left_w, label_w, cur_w, amt_w],
        rowHeights=[24, 21, 21, 21, 23, 66]
    )
    footer_table.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 0.5, colors.black),
        ("GRID", (0,0), (-1,4), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), navy),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("SPAN", (1,0), (3,0)),
        ("SPAN", (0,1), (0,4)),
        ("SPAN", (0,5), (3,5)),
        ("BACKGROUND", (0,5), (0,5), grey),
        ("BOX", (0,5), (3,5), 0.5, colors.black),
        ("BACKGROUND", (1,4), (3,4), light_total),
        ("LINEABOVE", (1,4), (3,4), 0.8, colors.black),
        ("FONTNAME", (1,4), (3,4), "Helvetica-Bold"),
        ("ALIGN", (1,1), (3,4), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("FONTSIZE", (0,0), (-1,-1), 8.1),
        ("LEFTPADDING", (0,0), (-1,-1), 7),
        ("RIGHTPADDING", (0,0), (-1,-1), 7),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(footer_table)
    story.append(Spacer(1, 7))

    contact_table = Table([
        [Paragraph("If you have any questions about this documents, please contact<br/>FSI, connect@fourstarindustries.com", normal),
         Paragraph("<b>Authorised Signatory</b>", normal)]
    ], colWidths=[page_width - 170, 170])
    contact_table.setStyle(TableStyle([
        ("ALIGN", (0,0), (0,0), "CENTER"),
        ("ALIGN", (1,0), (1,0), "RIGHT"),
        ("FONTSIZE", (0,0), (-1,-1), 8.1),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    story.append(contact_table)

    doc.build(story)
    return buffer.getvalue()


def get_saved_delivery_invoice_for_pdf(delivery_invoice_no):
    """Fetch saved delivery invoice details and line items for PDF reprint."""
    header_rows = fetch_all("""
        SELECT
            d.delivery_invoice_no,
            MIN(d.delivery_date) AS delivery_date,
            MAX(d.payment_due_date) AS payment_due_date,
            MAX(d.vehicle_number) AS vehicle_number,
            MAX(d.asn_number) AS asn_number,
            MAX(d.asn_date) AS asn_date,
            MAX(d.packaging_details) AS packaging_details,
            MAX(d.currency) AS currency,
            c.customer_name,
            c.address AS customer_address,
            c.company_code AS customer_company_code,
            c.phone AS customer_phone,
            c.email AS customer_email,
            s.invoice_no AS original_invoice_no,
            s.shipment_no,
            stm.ship_to_name,
            stm.ship_to_id,
            stm.addressline1 AS ship_to_addressline1,
            stm.addressline2 AS ship_to_addressline2,
            stm.addressline3 AS ship_to_addressline3,
            stm.vendor_gstin AS ship_to_vendor_gstin,
            stm.vendor_phone AS ship_to_vendor_phone,
            stm.vendor_email AS ship_to_vendor_email
        FROM customer_deliveries d
        JOIN customers c ON d.customer_id = c.id
        JOIN shipments s ON d.shipment_id = s.id
        LEFT JOIN ship_to_masters stm ON d.ship_to_master_id = stm.id
        WHERE d.delivery_invoice_no=?
        GROUP BY d.delivery_invoice_no, c.customer_name, c.address, c.company_code, c.phone, c.email,
                 s.invoice_no, s.shipment_no, stm.ship_to_name, stm.ship_to_id,
                 stm.addressline1, stm.addressline2, stm.addressline3,
                 stm.vendor_gstin, stm.vendor_phone, stm.vendor_email
        ORDER BY MIN(d.id)
        LIMIT 1
    """, (delivery_invoice_no,))
    if not header_rows:
        return None, []

    invoice = dict(header_rows[0])
    invoice["seller_name"] = "Four Star Industries Pvt. Ltd."
    invoice["seller_address"] = ""

    item_rows = fetch_all("""
        SELECT
            d.delivery_invoice_no,
            s.invoice_no AS original_invoice_no,
            b.po_number,
            b.po_date,
            b.pallet_no,
            b.box_no,
            p.product_code,
            p.product_name,
            d.delivered_qty AS qty,
            d.unit_price AS price,
            d.currency,
            d.sale_amount AS amount
        FROM customer_deliveries d
        JOIN shipments s ON d.shipment_id = s.id
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products p ON b.product_id = p.id
        WHERE d.delivery_invoice_no=?
        ORDER BY COALESCE(b.fifo_row_id,b.id), b.pallet_no, p.product_code
    """, (delivery_invoice_no,))
    line_items = [dict(r) for r in item_rows]
    return invoice, line_items


def delivery_invoice_jpeg_placeholder(invoice, line_items):
    # Streamlit/JPEG generation from HTML would require browser rendering.
    # This exports a print-ready HTML file that can be saved/printed as JPEG from browser.
    html_bytes = delivery_invoice_print_html(invoice, line_items).encode("utf-8")
    return html_bytes

import html
from common import *

page_setup()

require_page_view('delivery')
show_edit_permission_status('delivery')

access_notice()
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
        selected_invoice = st.selectbox('Original Invoice Number with Shipment Number', list(inv_map.keys()), key='delivery_original_invoice_ship', label_visibility='collapsed')
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
                                    'ship_to_vendor_email': selected_ship_to.get('vendor_email', ''), 'shipment_no': row['shipment_no'], 'original_invoice_no': row['invoice_no'], 'delivery_invoice_no': delivery_invoice_no, 'delivery_date': str(delivery_date), 'vehicle_number': vehicle_number.strip(), 'asn_number': asn_number.strip(), 'asn_date': str(asn_date), 'packaging_details': packaging_details.strip(), 'payment_term': selected_term, 'payment_due_date': str(payment_due_date), 'product_code': row['product_code'], 'product_name': row['product_name'], 'po_number': row.get('po_number', ''), 'po_date': row.get('po_date', ''), 'pallet_no': row['pallet_no'], 'box_no': row['box_no'] or '-', 'qty': total_qty, 'unit_price': price, 'currency': row['currency'], 'sale_amount': total_amount}
                notify_event('delivery', 'Delivery Created', f"Delivery Invoice: {delivery_invoice_no}\\nOriginal Invoice: {selected_ship['invoice_no']}\\nCustomer: {customer}\\nQty: {total_qty}\\nAmount: {total_amount}\\nDue Date: {payment_due_date}")
                print_data = build_delivery_invoice_print_data(delivery_invoice_no.strip()) or first_print
                if print_data:
                    st.session_state.last_delivery_print = print_data
                st.success('Delivery saved successfully. Email notification attempted if enabled. Print popup opened.')
if 'last_delivery_print' in st.session_state:
    html_doc = delivery_note_html(st.session_state.last_delivery_print)
    print_popup(html_doc)
    st.download_button('Download Delivery Note PDF Only', html_doc, 'delivery_note.pdf', mime='text/html', key='download_delivery_note_html')
    del st.session_state.last_delivery_print
st.divider()
show_header("Reprint Delivery Invoice PDF", "Generate saved Delivery Invoice again in the approved PDF format")

saved_delivery_invoices_for_reprint = fetch_all("""
    SELECT
        d.delivery_invoice_no,
        MIN(d.delivery_date) AS delivery_date,
        c.customer_name,
        s.invoice_no AS original_invoice_no,
        SUM(d.delivered_qty) AS total_qty,
        SUM(d.sale_amount) AS total_amount,
        MAX(d.currency) AS currency
    FROM customer_deliveries d
    JOIN customers c ON d.customer_id = c.id
    JOIN shipments s ON d.shipment_id = s.id
    GROUP BY d.delivery_invoice_no, c.customer_name, s.invoice_no
    ORDER BY MIN(d.id) DESC
    LIMIT 200
""")

if saved_delivery_invoices_for_reprint:
    reprint_options = [
        f"{r['delivery_invoice_no']} | Original Inv {r['original_invoice_no']} | {r['customer_name']} | {r['total_qty']:,.0f} Qty | {r['total_amount']:,.2f} {r['currency']}"
        for r in saved_delivery_invoices_for_reprint
    ]
    selected_reprint_key = searchable_selectbox(
        "Select Delivery Invoice for PDF Reprint",
        reprint_options,
        key="delivery_invoice_pdf_reprint_select"
    )
    selected_reprint_invoice_no = selected_reprint_key.split(" | ")[0].strip()

    invoice_for_reprint, line_items_for_reprint = get_saved_delivery_invoice_for_pdf(selected_reprint_invoice_no)
    if invoice_for_reprint and line_items_for_reprint:
        pdf_bytes_reprint = delivery_invoice_pdf_bytes(invoice_for_reprint, line_items_for_reprint)
        st.download_button(
            "Reprint Delivery Invoice PDF",
            data=pdf_bytes_reprint,
            file_name=f"delivery_invoice_reprint_{selected_reprint_invoice_no}.pdf",
            mime="application/pdf",
            key="reprint_delivery_invoice_pdf_button"
        )
    else:
        st.warning("No saved line items found for selected Delivery Invoice.")
else:
    st.info("No saved Delivery Invoices available for reprint.")

st.divider()
st.subheader('Last Delivery Entries - Delivery Invoice Wise')
delivery_invoice_rows = fetch_all('\n            SELECT d.delivery_invoice_no,\n                   MIN(d.id) AS first_id,\n                   MAX(d.delivery_date) AS delivery_date,\n                   MAX(d.payment_due_date) AS payment_due_date,\n                   c.customer_name,\n                   s.invoice_no AS original_invoice_no,\n                   s.shipment_no,\n                   d.currency,\n                   SUM(d.delivered_qty) AS total_qty,\n                   SUM(d.sale_amount) AS total_amount,\n                   COUNT(*) AS product_rows\n            FROM customer_deliveries d\n            JOIN customers c ON d.customer_id = c.id\n            JOIN shipments s ON d.shipment_id = s.id\n            GROUP BY d.delivery_invoice_no, c.customer_name, c.company_code, s.invoice_no, s.shipment_no, d.currency\n            ORDER BY first_id DESC\n            LIMIT 30\n        ')
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
    if 'last_delivery_reprint' in st.session_state:
        print_popup(st.session_state.last_delivery_reprint)
        st.download_button('Download Reprint Delivery Invoice HTML', st.session_state.last_delivery_reprint, 'delivery_invoice_reprint.html', mime='text/html', key='download_reprint_delivery_invoice_html')
        del st.session_state.last_delivery_reprint
    summary_df = pd.DataFrame(summary_rows)
    if not summary_df.empty:
        st.dataframe(style_total_row(summary_df), use_container_width=True, hide_index=True)
        export_buttons(add_total_row(summary_df), "delivery_invoice_summary_total_row")
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



st.divider()
st.markdown('<div class="sap-subtitle">Export Saved Delivery Invoice</div>', unsafe_allow_html=True)
try:
    saved_delivery_invoices = fetch_all("""
        SELECT d.delivery_invoice_no,
               MIN(d.id) AS first_id,
               MAX(d.delivery_date) AS delivery_date,
               MAX(d.payment_due_date) AS payment_due_date,
               MAX(d.vehicle_number) AS vehicle_number,
               MAX(d.asn_number) AS asn_number,
               MAX(d.asn_date) AS asn_date,
               MAX(d.packaging_details) AS packaging_details,
               c.customer_name,
               c.address AS customer_address,
               c.company_code AS customer_company_code,
               c.phone AS customer_phone,
               c.email AS customer_email,
               s.invoice_no AS original_invoice_no,
               s.shipment_no,
               d.currency,
               SUM(d.delivered_qty) AS total_qty,
               SUM(d.sale_amount) AS total_amount,
               COUNT(*) AS product_rows
        FROM customer_deliveries d
        JOIN customers c ON d.customer_id = c.id
        JOIN shipments s ON d.shipment_id = s.id
        GROUP BY d.delivery_invoice_no, c.customer_name, c.company_code, s.invoice_no, s.shipment_no, d.currency
        ORDER BY first_id DESC
        LIMIT 100
    """)
    if not saved_delivery_invoices:
        st.info("No saved delivery invoices available for export.")
    else:
        saved_invoice_map = {
            f"{r['delivery_invoice_no']} | Original {r['original_invoice_no']} | {r['customer_name']} | Qty {r['total_qty']}": r
            for r in saved_delivery_invoices
        }
        selected_saved_invoice_key = searchable_selectbox(
            "Select Saved Delivery Invoice for Export",
            list(saved_invoice_map.keys()),
            key="saved_delivery_invoice_export_select",
        )
        selected_saved_invoice = saved_invoice_map[selected_saved_invoice_key]

        saved_line_rows = fetch_all("""
            SELECT d.*, b.pallet_no, b.box_no, b.fifo_row_id, p.product_code, p.product_name,
                   COALESCE(d.po_number, b.po_number, s.po_number) AS po_number_linked,
                   COALESCE(d.po_date, b.po_date, s.po_date) AS po_date_linked,
                   stm.ship_to_name, stm.ship_to_id, stm.addressline1, stm.addressline2, stm.addressline3,
                   stm.vendor_gstin, stm.vendor_phone, stm.vendor_email
            FROM customer_deliveries d
            JOIN shipment_boxes b ON d.box_id = b.id
            JOIN shipments s ON d.shipment_id = s.id
            JOIN products p ON b.product_id = p.id
            LEFT JOIN ship_to_masters stm ON d.ship_to_master_id = stm.id
            WHERE d.delivery_invoice_no=?
            ORDER BY COALESCE(b.fifo_row_id, b.id), b.pallet_no
        """, (selected_saved_invoice["delivery_invoice_no"],))

        if saved_line_rows:
            first_line = saved_line_rows[0]
            export_invoice = {
                "delivery_invoice_no": selected_saved_invoice.get("delivery_invoice_no", ""),
                "delivery_date": str(selected_saved_invoice.get("delivery_date") or ""),
                "payment_due_date": str(selected_saved_invoice.get("payment_due_date") or ""),
                "customer_name": selected_saved_invoice.get("customer_name", ""),
                "customer_address": selected_saved_invoice.get("customer_address", ""),
                "customer_company_code": selected_saved_invoice.get("customer_company_code", ""),
                "customer_phone": selected_saved_invoice.get("customer_phone", ""),
                "customer_email": selected_saved_invoice.get("customer_email", ""),
                "seller_name": "Four Star Industries Pvt. Ltd.",
                "seller_address": "",
                "customer_address": selected_saved_invoice.get("customer_address", ""),
                "customer_company_code": selected_saved_invoice.get("customer_company_code", ""),
                "customer_phone": selected_saved_invoice.get("customer_phone", ""),
                "customer_email": selected_saved_invoice.get("customer_email", ""),
                "original_invoice_no": selected_saved_invoice.get("original_invoice_no", ""),
                "shipment_no": selected_saved_invoice.get("shipment_no", ""),
                "vehicle_number": selected_saved_invoice.get("vehicle_number", ""),
                "asn_number": selected_saved_invoice.get("asn_number", ""),
                "asn_date": str(selected_saved_invoice.get("asn_date") or ""),
                "packaging_details": selected_saved_invoice.get("packaging_details", ""),
                "ship_to_name": first_line.get("ship_to_name", ""),
                "ship_to_id": first_line.get("ship_to_id", ""),
                "ship_to_addressline1": first_line.get("addressline1", ""),
                "ship_to_addressline2": first_line.get("addressline2", ""),
                "ship_to_addressline3": first_line.get("addressline3", ""),
                "ship_to_vendor_gstin": first_line.get("vendor_gstin", ""),
                "ship_to_vendor_phone": first_line.get("vendor_phone", ""),
                "ship_to_vendor_email": first_line.get("vendor_email", ""),
            }

            export_line_items = []
            for row in saved_line_rows:
                export_line_items.append({
                    "fifo_row_id": row.get("fifo_row_id"),
                    "original_invoice_no": row.get("invoice_no") or row.get("original_invoice_no") or selected_saved_invoice.get("original_invoice_no",""),
                    "product_code": row.get("product_code", ""),
                    "product_name": row.get("product_name", ""),
                    "pallet_no": row.get("pallet_no", ""),
                    "box_no": row.get("box_no", ""),
                    "po_number": row.get("po_number_linked", ""),
                    "po_date": format_date_ddmmyyyy(row.get("po_date_linked")) if row.get("po_date_linked") else "",
                    "qty": row.get("delivered_qty") or 0,
                    "price": row.get("unit_price") or 0,
                    "currency": row.get("currency") or "",
                    "amount": row.get("sale_amount") or 0,
                })
            st.download_button(
                "Generate Delivery Invoice PDF",
                delivery_invoice_pdf_bytes(export_invoice, export_line_items),
                file_name=f"delivery_invoice_{selected_saved_invoice['delivery_invoice_no']}.pdf",
                mime="application/pdf",
                key="saved_delivery_invoice_pdf_export",
            )
            st.info("Delivery Invoice print is available in PDF only.")
            with st.expander("Preview Selected Delivery Invoice", expanded=False):
                components.html(delivery_invoice_print_html(export_invoice, export_line_items), height=900, scrolling=True)
except Exception as export_error:
    st.warning(f"Saved delivery invoice export could not load: {export_error}")



render_slogan_footer()
st.markdown('<div class="footer">COPYRIGHT BY FOUR STAR INDUSTRIES PVT. LTD.</div>', unsafe_allow_html=True)


def delivery_invoice_print_html(invoice, line_items):
    """Delivery invoice print layout with customer/ship-to header and PO in product table."""
    rows_html = ""
    total_qty = 0
    total_amt = 0
    currency_set = set()

    for i, item in enumerate(line_items, start=1):
        qty = float(item.get("qty") or item.get("delivered_qty") or 0)
        price = float(item.get("price") or item.get("unit_price") or 0)
        amount = float(item.get("amount") or qty * price)
        cur = str(item.get("currency") or "")
        if cur:
            currency_set.add(cur)
        total_qty += qty
        total_amt += amount
        rows_html += f"""
        <tr>
            <td>{i}</td>
            <td>{html.escape(str(item.get('product_code','')))}</td>
            <td>{html.escape(str(item.get('product_name','')))}</td>
            <td>{html.escape(str(item.get('original_invoice_no', invoice.get('original_invoice_no',''))))}</td>
            <td>{html.escape(str(item.get('po_number','')))}</td>
            <td>{html.escape(str(item.get('po_date','')))}</td>
            <td>{html.escape(str(item.get('pallet_no','')))}</td>
            <td>{html.escape(str(item.get('box_no','') or '-'))}</td>
            <td style="text-align:right;">{qty:,.0f}</td>
            <td style="text-align:right;">{price:,.2f}</td>
            <td>{html.escape(cur)}</td>
            <td style="text-align:right;">{amount:,.2f}</td>
        </tr>
        """
    total_currency = ", ".join(sorted(currency_set))

    return f"""
    <html>
    <head>
    <style>
    @media print {{ body {{ margin: 0; }} .no-print {{ display:none; }} }}
    body {{ font-family: Arial, sans-serif; color:#111; }}
    .invoice-wrap {{ width: 100%; max-width: 1180px; margin: 0 auto; padding: 18px; }}
    .title {{ text-align:center; font-size: 22px; font-weight: 800; margin-bottom: 12px; }}
    .section {{ border:1px solid #111; margin-bottom:10px; }}
    .section-title {{ background:#1f2f57; color:white; font-weight:800; padding:6px 8px; }}
    .grid3 {{ display:grid; grid-template-columns: 1fr 1fr 1fr; }}
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
            <div class="section-title">Header Details</div>
            <div class="grid3">
                <div class="box">
                    <div class="bold">Customer</div>
                    <div>{html.escape(str(invoice.get('customer_name','')))}</div>
                    <div>{html.escape(str(invoice.get('customer_address','')))}</div>
                    <div>{html.escape(str(invoice.get('customer_phone','')))}</div>
                    <div>{html.escape(str(invoice.get('customer_email','')))}</div>
                </div>
                <div class="box">
                    <div class="bold">Ship To</div>
                    <div>{html.escape(str(invoice.get('ship_to_name','')))}</div>
                    <div>Ship To ID: {html.escape(str(invoice.get('ship_to_id','')))}</div>
                    <div>{html.escape(str(invoice.get('ship_to_addressline1','')))}</div>
                    <div>{html.escape(str(invoice.get('ship_to_addressline2','')))}</div>
                    <div>{html.escape(str(invoice.get('ship_to_addressline3','')))}</div>
                    <div>GSTIN: {html.escape(str(invoice.get('ship_to_vendor_gstin','')))}</div>
                </div>
                <div class="box">
                    <div class="bold">Invoice Details</div>
                    <div>Delivery Invoice No.: {html.escape(str(invoice.get('delivery_invoice_no','')))}</div>
                    <div>Delivery Date: {html.escape(str(invoice.get('delivery_date','')))}</div>
                    <div>Payment Due: {html.escape(str(invoice.get('payment_due_date','')))}</div>
                    <div>Vehicle No.: {html.escape(str(invoice.get('vehicle_number','')))}</div>
                    <div>ASN No.: {html.escape(str(invoice.get('asn_number','')))}</div>
                    <div>ASN Date: {html.escape(str(invoice.get('asn_date','')))}</div>
                    <div>Packaging: {html.escape(str(invoice.get('packaging_details','')))}</div>
                </div>
            </div>
        </div>
        <div class="section">
            <div class="section-title">Product Details</div>
            <table>
                <thead><tr>
                    <th>Sr.</th><th>Product Code</th><th>Description</th><th>Original Invoice No.</th>
                    <th>PO No.</th><th>PO Date</th><th>Pallet</th><th>Box</th>
                    <th>Qty</th><th>Rate</th><th>Currency</th><th>Amount</th>
                </tr></thead>
                <tbody>
                    {rows_html}
                    <tr><td colspan="8" class="right bold">TOTAL</td><td class="right bold">{total_qty:,.0f}</td><td></td><td class="bold">{html.escape(total_currency)}</td><td class="right bold">{total_amt:,.2f}</td></tr>
                </tbody>
            </table>
        </div>
        <button class="no-print" onclick="window.print()" style="padding:10px 18px;font-weight:800;">Print Invoice</button>
    </div>
    </body>
    </html>
    """
