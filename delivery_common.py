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
    packaging_remark = str(invoice.get("packaging_remark") or "")
    packaging_text = ""
    if packaging:
        packaging_text += "Packaging Details: " + packaging
    if packaging_remark:
        packaging_text += ("\n" if packaging_text else "") + "Remarks: " + packaging_remark
    packaging_value = Paragraph(packaging_text.replace("\n", "<br/>"), normal)

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
    """Fetch saved delivery invoice details and line items for PDF reprint.

    Access is applied at line-item SQL level before PDF generation.
    """
    access_sql, access_params = _delivery_access_filter_sql("b", "s")

    header_rows = fetch_all(f"""
        SELECT
            d.delivery_invoice_no,
            MIN(d.delivery_date) AS delivery_date,
            MAX(d.payment_due_date) AS payment_due_date,
            MAX(d.vehicle_number) AS vehicle_number,
            MAX(d.asn_number) AS asn_number,
            MAX(d.asn_date) AS asn_date,
            MAX(d.packaging_details) AS packaging_details,
            MAX(d.packaging_remark) AS packaging_remark,
            MAX(d.currency) AS currency,
            c.customer_name,
            c.address AS customer_address,
            c.company_code AS customer_company_code,
            c.phone AS customer_phone,
            c.email AS customer_email,
            s.invoice_no AS original_invoice_no,
            s.shipment_no,
            MAX(s.warehouse_id) AS warehouse_id,
            MAX(w.warehouse_name) AS warehouse_name,
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
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        LEFT JOIN ship_to_masters stm ON d.ship_to_master_id = stm.id
        WHERE d.delivery_invoice_no=?
        {access_sql}
        GROUP BY d.delivery_invoice_no, c.customer_name, c.address, c.company_code, c.phone, c.email,
                 s.invoice_no, s.shipment_no, stm.ship_to_name, stm.ship_to_id,
                 stm.addressline1, stm.addressline2, stm.addressline3,
                 stm.vendor_gstin, stm.vendor_phone, stm.vendor_email
        ORDER BY MIN(d.id)
        LIMIT 1
    """, (delivery_invoice_no,) + access_params)
    if not header_rows:
        return None, []

    invoice = dict(header_rows[0])
    invoice["seller_name"] = "Four Star Industries Pvt. Ltd."
    invoice["seller_address"] = ""

    item_rows = fetch_all(f"""
        SELECT
            d.delivery_invoice_no,
            s.invoice_no AS original_invoice_no,
            b.po_number,
            b.po_date,
            b.pallet_no,
            b.box_no,
            b.product_id,
            s.warehouse_id,
            w.warehouse_name,
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
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        WHERE d.delivery_invoice_no=?
        {access_sql}
        ORDER BY COALESCE(b.fifo_row_id,b.id), b.pallet_no, p.product_code
    """, (delivery_invoice_no,) + access_params)
    line_items = [dict(r) for r in item_rows]
    if not line_items:
        return None, []
    return invoice, line_items


def delivery_invoice_jpeg_placeholder(invoice, line_items):
    # Streamlit/JPEG generation from HTML would require browser rendering.
    # This exports a print-ready HTML file that can be saved/printed as JPEG from browser.
    html_bytes = delivery_invoice_print_html(invoice, line_items).encode("utf-8")
    return html_bytes

import html
from common import *

# Fast delivery-page access helpers.
# Blank Product Access = all products; blank Warehouse Access = all warehouses.
def _delivery_access_filter_sql(product_alias="b", warehouse_alias="s"):
    clauses = []
    params = []
    try:
        product_ids = current_user_allowed_product_ids()
    except Exception:
        product_ids = []
    try:
        warehouse_ids = current_user_allowed_warehouse_ids()
    except Exception:
        warehouse_ids = []

    if product_ids:
        placeholders = ",".join(["?"] * len(product_ids))
        clauses.append(f" AND {product_alias}.product_id IN ({placeholders}) ")
        params.extend(product_ids)
    if warehouse_ids:
        placeholders = ",".join(["?"] * len(warehouse_ids))
        clauses.append(f" AND {warehouse_alias}.warehouse_id IN ({placeholders}) ")
        params.extend(warehouse_ids)
    return "".join(clauses), tuple(params)


def generate_delivery_invoice_no(original_invoice_no, delivery_date_value):
    """Generate Delivery Invoice No from Shipment Entry Original Invoice Number.

    Format: ED900003-MMDDYY-01
    Sequence is counted for same original invoice number and delivery date.
    """
    original_invoice_no = str(original_invoice_no or "").strip()
    if not original_invoice_no:
        return ""
    try:
        date_part = delivery_date_value.strftime("%m%d%y")
        delivery_date_text = str(delivery_date_value)
    except Exception:
        parsed_date = parse_db_date(delivery_date_value) or date.today()
        date_part = parsed_date.strftime("%m%d%y")
        delivery_date_text = str(parsed_date)

    prefix = f"{original_invoice_no}-{date_part}-"
    rows = fetch_all("""
        SELECT DISTINCT d.delivery_invoice_no
        FROM customer_deliveries d
        JOIN shipments s ON d.shipment_id = s.id
        WHERE s.invoice_no=?
          AND d.delivery_date::date=?::date
          AND d.delivery_invoice_no LIKE ?
    """, (original_invoice_no, delivery_date_text, prefix + "%"))

    max_seq = 0
    for r in rows:
        value = str(r.get("delivery_invoice_no") or "")
        if value.startswith(prefix):
            suffix = value.replace(prefix, "", 1).split("-")[0]
            try:
                max_seq = max(max_seq, int(suffix))
            except Exception:
                pass
    return f"{prefix}{max_seq + 1:02d}"

def ensure_delivery_columns():
    """Non-destructive delivery page migrations."""
    for sql in [
        "ALTER TABLE customer_deliveries ADD COLUMN IF NOT EXISTS packaging_remark TEXT",
    ]:
        try:
            execute_query(sql)
        except Exception:
            pass


def fetch_delivery_part_options():
    """Parts having positive balance quantity and allowed by current user's access."""
    access_sql, access_params = _delivery_access_filter_sql("b", "s")
    return fetch_all(f"""
        SELECT DISTINCT
            b.product_id,
            p.product_code,
            p.product_name
        FROM shipment_boxes b
        JOIN shipments s ON b.shipment_id = s.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN (
            SELECT box_id, SUM(delivered_qty) AS delivered_qty
            FROM customer_deliveries
            GROUP BY box_id
        ) del ON b.id = del.box_id
        WHERE b.original_qty - COALESCE(del.delivered_qty, 0) > 0
        {access_sql}
        ORDER BY p.product_code, p.product_name
    """, access_params)


def delivery_part_selectbox(key="delivery_part_filter", label="Part Number Filter"):
    part_rows = fetch_delivery_part_options()
    options = ["All Parts"] + [
        f"{r['product_code']} | {r.get('product_name') or ''} | {r['product_id']}"
        for r in part_rows
    ]
    selected = st.selectbox(label, options, key=key)
    selected_product_id = None
    if selected and selected != "All Parts":
        try:
            selected_product_id = int(str(selected).split("|")[-1].strip())
        except Exception:
            selected_product_id = None
    return selected_product_id, selected, part_rows


def selected_part_sql(selected_product_id, alias="b"):
    if selected_product_id:
        return f" AND {alias}.product_id=? ", (selected_product_id,)
    return "", ()


def fetch_available_invoice_shipments(selected_product_id=None):
    """Original invoice/shipment list only where pending balance qty exists."""
    access_sql, access_params = _delivery_access_filter_sql("b", "s")
    part_sql, part_params = selected_part_sql(selected_product_id, "b")
    return fetch_all(f"""
        SELECT
            s.id,
            s.shipment_no,
            s.invoice_no,
            s.po_number,
            s.po_date,
            s.shipment_date,
            s.warehouse_id,
            w.warehouse_name,
            SUM(b.original_qty - COALESCE(del.delivered_qty, 0)) AS balance_qty
        FROM shipments s
        JOIN shipment_boxes b ON b.shipment_id = s.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        LEFT JOIN (
            SELECT box_id, SUM(delivered_qty) AS delivered_qty
            FROM customer_deliveries
            GROUP BY box_id
        ) del ON b.id = del.box_id
        WHERE b.original_qty - COALESCE(del.delivered_qty, 0) > 0
        {access_sql}
        {part_sql}
        GROUP BY s.id, s.shipment_no, s.invoice_no, s.po_number, s.po_date, s.shipment_date, s.warehouse_id, w.warehouse_name
        HAVING SUM(b.original_qty - COALESCE(del.delivered_qty, 0)) > 0
        ORDER BY s.shipment_date ASC, s.id ASC
    """, access_params + part_params)


def fetch_fifo_available_rows(selected_ship_id=None, selected_product_id=None):
    access_sql, access_params = _delivery_access_filter_sql("b", "s")
    part_sql, part_params = selected_part_sql(selected_product_id, "b")
    ship_sql = ""
    ship_params = ()
    if selected_ship_id:
        ship_sql = " AND s.id=? "
        ship_params = (selected_ship_id,)

    return fetch_all(f"""
        SELECT
            b.*,
            s.shipment_no,
            s.invoice_no,
            s.shipment_date,
            s.warehouse_id,
            w.warehouse_name,
            COALESCE(b.po_number, s.po_number) AS po_number,
            COALESCE(b.po_date, s.po_date) AS po_date,
            p.product_code,
            p.product_name,
            COALESCE(del.delivered_qty, 0) AS delivered_qty,
            b.original_qty - COALESCE(del.delivered_qty, 0) AS balance_qty
        FROM shipment_boxes b
        JOIN shipments s ON b.shipment_id = s.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        LEFT JOIN (
            SELECT box_id, SUM(delivered_qty) AS delivered_qty
            FROM customer_deliveries
            GROUP BY box_id
        ) del ON b.id = del.box_id
        WHERE b.original_qty - COALESCE(del.delivered_qty, 0) > 0
        {ship_sql}
        {access_sql}
        {part_sql}
        ORDER BY s.shipment_date ASC, COALESCE(b.fifo_row_id,b.id), b.pallet_no, b.id
    """, ship_params + access_params + part_params)




def render_delivery_subnav(active_key="delivery"):
    """Show Delivery subpages under the main Delivery module."""
    items = [
        ("delivery", "Delivery Entry", "pages/4_Delivery_to_Customer.py"),
        ("delivery_reprint", "Reprint Invoice", "pages/10_Reprint_Invoice.py"),
        ("delivery_fifo", "FIFO Available Pallets", "pages/11_FIFO_Available_Pallets.py"),
        ("delivery_edit", "Edit Delivery Invoice", "pages/12_Edit_Delivery_Invoice.py"),
    ]
    allowed_items = []
    for key, label, target in items:
        try:
            page_def = get_page_definition_by_key(key)
            if page_def and can_user_access_page(page_def):
                allowed_items.append((key, label, target))
        except Exception:
            allowed_items.append((key, label, target))

    if not allowed_items:
        return

    st.markdown(
        """
        <div style="border:1px solid #d9e2ec;border-radius:14px;background:#ffffff;
                    padding:10px 12px;margin:8px 0 16px 0;box-shadow:0 2px 8px rgba(15,23,42,.06);">
            <div style="font-weight:900;color:#003B73;font-size:14px;margin-bottom:8px;">Delivery</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    cols = st.columns(len(allowed_items))
    for col, (key, label, target) in zip(cols, allowed_items):
        with col:
            if key == active_key:
                st.markdown(
                    f"<div style='background:#003B73;color:white;border-radius:10px;padding:9px 10px;"
                    f"text-align:center;font-weight:900;'>{label}</div>",
                    unsafe_allow_html=True
                )
            else:
                st.page_link(target, label=label)


# Allow split Delivery pages to import internal helper names such as _delivery_access_filter_sql.
__all__ = [name for name in globals() if not name.startswith("__")]
