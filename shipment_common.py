from common import *
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import io

def _shipment_pdf_p(value, style):
    try:
        return Paragraph(str(value or "").replace("\n", "<br/>"), style)
    except Exception:
        return str(value or "")


def shipment_access_sql():
    product_ids = current_user_allowed_product_ids()
    warehouse_ids = current_user_allowed_warehouse_ids()
    clauses = []
    params = []
    if product_ids:
        clauses.append(" AND b.product_id IN (" + ",".join(["?"] * len(product_ids)) + ") ")
        params.extend(product_ids)
    if warehouse_ids:
        clauses.append(" AND s.warehouse_id IN (" + ",".join(["?"] * len(warehouse_ids)) + ") ")
        params.extend(warehouse_ids)
    return "".join(clauses), tuple(params)

def fetch_shipment_headers(limit=200):
    access_sql, access_params = shipment_access_sql()
    return fetch_all(f"""
        SELECT
            s.id, s.shipment_no, s.invoice_no, s.po_number, s.po_date, s.shipment_date,
            s.shipping_bill_no, s.shipping_bill_date, s.shipment_doc_date,
            s.forwarder_name, s.incoterm, s.currency, s.invoice_amount,
            sup.supplier_name, w.warehouse_name, c.customer_name
        FROM shipments s
        LEFT JOIN suppliers sup ON s.supplier_id = sup.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        LEFT JOIN customers c ON s.customer_id = c.id
        WHERE EXISTS (
            SELECT 1 FROM shipment_boxes b
            WHERE b.shipment_id = s.id
            {access_sql}
        )
        ORDER BY s.id DESC
        LIMIT {int(limit)}
    """, access_params)

def fetch_shipment_pallet_rows(shipment_id=None):
    access_sql, access_params = shipment_access_sql()
    ship_sql = ""
    ship_params = ()
    if shipment_id:
        ship_sql = " AND s.id=? "
        ship_params = (shipment_id,)
    return fetch_all(f"""
        SELECT
            b.id, b.fifo_row_id, s.id AS shipment_id, s.shipment_no, s.invoice_no,
            w.warehouse_name, b.pallet_no, b.box_no, b.product_id,
            p.product_code, p.product_name, b.po_number, b.po_date,
            b.original_qty, b.unit_price, b.currency, b.amount
        FROM shipment_boxes b
        JOIN shipments s ON b.shipment_id = s.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        WHERE 1=1
        {ship_sql}
        {access_sql}
        ORDER BY s.id DESC, COALESCE(b.fifo_row_id,b.id), b.pallet_no, b.id
    """, ship_params + access_params)

def shipment_pdf_bytes(shipment, rows):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=22, leftMargin=22, topMargin=20, bottomMargin=20)
    styles = getSampleStyleSheet()
    wrap_style = ParagraphStyle("shipment_wrap", parent=styles["Normal"], fontName="Helvetica", fontSize=6.5, leading=7.2, wordWrap="CJK")
    head_wrap = ParagraphStyle("shipment_head_wrap", parent=wrap_style, fontName="Helvetica-Bold", textColor=colors.white, alignment=1)
    story = []
    story.append(Paragraph("SHIPMENT / PALLET DETAILS", styles["Title"]))
    story.append(Spacer(1, 8))
    header_data = [
        ["Shipment No", shipment.get("shipment_no",""), "Original Invoice", shipment.get("invoice_no","")],
        ["Shipment Date", str(shipment.get("shipment_date","")), "Warehouse", shipment.get("warehouse_name","")],
        ["Supplier", shipment.get("supplier_name",""), "Customer", shipment.get("customer_name","")],
    ]
    t = Table(header_data, colWidths=[80, 165, 90, 165])
    t.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#EAF2F8")),
        ("BACKGROUND", (2,0), (2,-1), colors.HexColor("#EAF2F8")),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))
    data = [[_shipment_pdf_p(x, head_wrap) for x in ["FIFO", "Pallet", "Box", "Product", "PO", "Qty", "Price", "Amount"]]]
    total_qty = 0
    total_amount = 0
    for r in rows:
        qty = float(r.get("original_qty") or 0)
        amt = float(r.get("amount") or 0)
        total_qty += qty
        total_amount += amt
        data.append([
            _shipment_pdf_p(r.get("fifo_row_id") or r.get("id"), wrap_style),
            _shipment_pdf_p(r.get("pallet_no") or "", wrap_style),
            _shipment_pdf_p(r.get("box_no") or "", wrap_style),
            _shipment_pdf_p(r.get("product_code") or "", wrap_style),
            _shipment_pdf_p(r.get("po_number") or "", wrap_style),
            _shipment_pdf_p(f"{qty:,.3f}", wrap_style),
            _shipment_pdf_p(f"{float(r.get('unit_price') or 0):,.3f}", wrap_style),
            _shipment_pdf_p(f"{amt:,.3f}", wrap_style),
        ])
    data.append([_shipment_pdf_p("", wrap_style), _shipment_pdf_p("", wrap_style), _shipment_pdf_p("", wrap_style), _shipment_pdf_p("", wrap_style), _shipment_pdf_p("TOTAL", wrap_style), _shipment_pdf_p(f"{total_qty:,.3f}", wrap_style), _shipment_pdf_p("", wrap_style), _shipment_pdf_p(f"{total_amount:,.3f}", wrap_style)])
    table = Table(data, colWidths=[38, 68, 55, 70, 60, 55, 55, 70])
    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.35, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#003B73")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME", (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 7),
        ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#EAF2F8")),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ("ALIGN", (5,1), (-1,-1), "RIGHT"),
    ]))
    story.append(table)
    doc.build(story)
    return buf.getvalue()


def shipment_invoice_pdf_bytes(shipment, rows):
    """A4 portrait Shipment Invoice PDF in delivery-invoice-style layout."""
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
    wrap_style = ParagraphStyle("shipment_invoice_wrap", parent=styles["Normal"], fontName="Helvetica", fontSize=6.4, leading=7.0, wordWrap="CJK")
    head_wrap = ParagraphStyle("shipment_invoice_head_wrap", parent=wrap_style, fontName="Helvetica-Bold", textColor=colors.white, alignment=1)
    normal = styles["Normal"]
    title_style = styles["Title"]
    normal.fontName = "Helvetica"
    normal.fontSize = 8
    normal.leading = 9.5
    title_style.fontName = "Helvetica-Bold"
    title_style.fontSize = 15
    title_style.leading = 17

    story = []
    page_width = A4[0] - 36
    navy = colors.HexColor("#1f2f57")
    grey = colors.HexColor("#d9d9d9")
    light_total = colors.HexColor("#f3f4f6")

    title_table = Table(
        [[Paragraph("<b>FSI LOGO</b>", normal), Paragraph("<b>SHIPMENT / COMMERCIAL INVOICE</b>", title_style)]],
        colWidths=[112, page_width - 112],
        rowHeights=[44]
    )
    title_table.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 0.6, colors.black),
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
    ]))
    story.append(title_table)
    story.append(Spacer(1, 7))

    seller_text = "<b>Seller</b><br/>Four Star Industries Pvt. Ltd.<br/>Company address line here"
    shipment_text = (
        f"<b>Shipment No:</b> {shipment.get('shipment_no') or ''}<br/>"
        f"<b>Original Invoice:</b> {shipment.get('invoice_no') or ''}<br/>"
        f"<b>Shipment Date:</b> {shipment.get('shipment_date') or ''}<br/>"
        f"<b>Warehouse:</b> {shipment.get('warehouse_name') or ''}"
    )
    info_table = Table(
        [[Paragraph(seller_text, normal), Paragraph(shipment_text, normal)],
         [Paragraph(f"<b>Supplier</b><br/>{shipment.get('supplier_name') or ''}", normal),
          Paragraph(f"<b>Customer</b><br/>{shipment.get('customer_name') or ''}", normal)]],
        colWidths=[page_width/2, page_width/2],
        rowHeights=[62, 58]
    )
    info_table.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 0.6, colors.black),
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 7),
        ("RIGHTPADDING", (0,0), (-1,-1), 7),
        ("TOPPADDING", (0,0), (-1,-1), 7),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 8))

    meta_data = [
        ["Shipping Bill No:", shipment.get("shipping_bill_no") or "-", "Shipping Bill Date:", shipment.get("shipping_bill_date") or "-"],
        ["Forwarder:", shipment.get("forwarder_name") or "-", "Incoterm:", shipment.get("incoterm") or "-"],
    ]
    meta_table = Table(meta_data, colWidths=[105, page_width/2 - 105, 105, page_width/2 - 105], rowHeights=[26, 26])
    meta_table.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 0.6, colors.black),
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME", (2,0), (2,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6))

    data = [[_shipment_pdf_p(x, head_wrap) for x in ["Sr", "Product", "FSI Orig Inv #", "PO No", "PO Date", "Pallet", "Qty", "Rate", "Cur", "Amount"]]]
    total_qty = 0
    total_amount = 0
    currency = shipment.get("currency") or ""
    for i, r in enumerate(rows, 1):
        qty = float(r.get("original_qty") or 0)
        rate = float(r.get("unit_price") or 0)
        amt = float(r.get("amount") or (qty * rate) or 0)
        total_qty += qty
        total_amount += amt
        currency = r.get("currency") or currency
        data.append([
            _shipment_pdf_p(str(i), wrap_style),
            _shipment_pdf_p(str(r.get("product_code") or ""), wrap_style),
            _shipment_pdf_p(str(r.get("invoice_no") or shipment.get("invoice_no") or ""), wrap_style),
            _shipment_pdf_p(str(r.get("po_number") or ""), wrap_style),
            _shipment_pdf_p(str(r.get("po_date") or ""), wrap_style),
            _shipment_pdf_p(str(r.get("pallet_no") or ""), wrap_style),
            _shipment_pdf_p(f"{qty:,.3f}", wrap_style),
            _shipment_pdf_p(f"{rate:,.3f}", wrap_style),
            _shipment_pdf_p(str(r.get("currency") or ""), wrap_style),
            _shipment_pdf_p(f"{amt:,.3f}", wrap_style),
        ])
    data.append([_shipment_pdf_p("", wrap_style), _shipment_pdf_p("TOTAL", wrap_style), _shipment_pdf_p("", wrap_style), _shipment_pdf_p("", wrap_style), _shipment_pdf_p("", wrap_style), _shipment_pdf_p("", wrap_style), _shipment_pdf_p(f"{total_qty:,.3f}", wrap_style), _shipment_pdf_p("", wrap_style), _shipment_pdf_p(currency, wrap_style), _shipment_pdf_p(f"{total_amount:,.3f}", wrap_style)])

    body_table = Table(data, colWidths=[22, 105, 72, 52, 52, 48, 45, 45, 35, 70], repeatRows=1)
    body_table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.45, colors.black),
        ("BACKGROUND", (0,0), (-1,0), navy),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME", (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 7),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (6,1), (-1,-1), "RIGHT"),
        ("BACKGROUND", (0,-1), (-1,-1), light_total),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
    ]))
    story.append(body_table)

    story.append(Spacer(1, 120))

    footer_data = [
        [Paragraph("<b>PACKAGING DETAILS:</b>", normal), Paragraph("<b>AMOUNT SUMMARY</b>", normal)],
        [Paragraph("As per shipment packing list", normal), Table([
            ["SUBTOTAL", currency, f"{total_amount:,.3f}"],
            ["TAX", "", "-"],
            ["OTHER", "", "-"],
            ["TOTAL", currency, f"{total_amount:,.3f}"],
        ], colWidths=[72, 36, 78])]
    ]
    footer_table = Table(footer_data, colWidths=[page_width*0.68, page_width*0.32], rowHeights=[24, 82])
    footer_table.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 0.6, colors.black),
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), navy),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    story.append(footer_table)
    story.append(Spacer(1, 12))
    sign_table = Table(
        [[Paragraph("If you have any questions about this documents, please contact<br/>FSI, connect@fourstarindustries.com", normal),
          Paragraph("<b>Authorised Signatory</b>", normal)]],
        colWidths=[page_width*0.65, page_width*0.35]
    )
    sign_table.setStyle(TableStyle([
        ("ALIGN", (1,0), (1,0), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    story.append(sign_table)

    doc.build(story)
    return buffer.getvalue()

