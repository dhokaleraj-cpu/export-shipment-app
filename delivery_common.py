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
            "Original Invoice No": item.get("original_invoice_no", invoice.get("original_invoice_no", "")),
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


def _delivery_company_master():
    """Fetch company settings/master. Safe fallback to empty dict."""
    try:
        rows = fetch_all("SELECT * FROM company_settings WHERE id=1")
        return rows[0] if rows else {}
    except Exception:
        return {}

def _company_value(company, *keys):
    for key in keys:
        try:
            value = company.get(key)
            if value not in (None, ""):
                return value
        except Exception:
            pass
    return ""

def _company_logo_cell(company, normal_style):
    """Company logo from master path where available, otherwise existing app logo."""
    logo_path_value = _company_value(company, "logo_path", "company_logo", "logo_file", "logo", "logo_url")
    candidates = []
    try:
        if logo_path_value:
            candidates.append(Path(str(logo_path_value)))
    except Exception:
        pass
    try:
        candidates.append(LOGO_PATH)
    except Exception:
        pass

    for logo_path in candidates:
        try:
            if logo_path and Path(logo_path).exists():
                return RLImage(str(logo_path), width=130, height=42)
        except Exception:
            continue
    return Paragraph("<b>FSI</b>", normal_style)

def _company_address_text(company):
    name = _company_value(company, "company_name", "name", "legal_name")
    address = _company_value(company, "address", "company_address", "registered_address", "plant_address")
    company_code = _company_value(company, "company_code", "code")
    phone = _company_value(company, "phone", "company_phone", "contact_no")
    email = _company_value(company, "email", "company_email", "contact_email")

    lines = ["<b>Seller</b>"]
    if name:
        lines.append(str(name))
    if address:
        lines.append(str(address).replace("\n", "<br/>"))
    if company_code:
        lines.append(f"<b>Company Code:</b> {company_code}")
    if phone:
        lines.append(f"<b>Phone:</b> {phone}")
    if email:
        lines.append(f"<b>Email:</b> {email}")
    return "<br/>".join(lines)

def _company_bank_text(company):
    """Bank details from company master only. No hardcoded bank values."""
    fields = [
        ("Bank Name", ("bank_name", "bank", "bank_branch_name")),
        ("Branch", ("branch", "bank_branch")),
        ("A/C No.", ("bank_account_no", "account_no", "bank_account_number", "account_number", "ac_no")),
        ("Account Type", ("account_type", "bank_account_type")),
        ("IFSC Code", ("bank_ifsc_code", "ifsc_code", "ifsc")),
        ("MICR Code", ("bank_micr_code", "micr_code", "micr")),
        ("SWIFT Code", ("bank_swift_code", "swift_code", "swift")),
        ("Beneficiary Name", ("beneficiary_name", "bank_beneficiary_name")),
        ("GSTIN", ("gstin", "company_gstin")),
        ("PAN", ("pan", "company_pan")),
        ("CIN", ("cin", "company_cin")),
    ]
    rows = ["<b>BANK DETAILS</b>"]
    for label, keys in fields:
        value = _company_value(company, *keys)
        if value:
            rows.append(f"<b>{label}:</b> {value}")
    if len(rows) == 1:
        rows.append("Bank details not available in Company Master.")
    return "<br/>".join(rows)

def delivery_invoice_pdf_bytes(invoice, line_items):
    """A4 PDF Delivery Invoice with organized header grid and master-based company/bank details."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16,
        leftMargin=16,
        topMargin=14,
        bottomMargin=14,
    )
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    normal.fontName = "Helvetica"
    normal.fontSize = 7.4
    normal.leading = 8.6
    wrap = ParagraphStyle("delivery_wrap", parent=normal, wordWrap="CJK", fontSize=7.2, leading=8.4)
    bold = ParagraphStyle("delivery_bold", parent=normal, fontName="Helvetica-Bold", fontSize=7.6, leading=8.8, wordWrap="CJK")
    title = ParagraphStyle("delivery_title", parent=normal, fontName="Helvetica-Bold", fontSize=16, leading=18, alignment=1, textColor=colors.HexColor("#003B73"))

    def _p(value, style=normal):
        safe = str(value or "").replace("\n", "<br/>")
        return Paragraph(safe, style)

    company = _delivery_company_master()
    story = []
    page_width = A4[0] - 32
    navy = colors.HexColor("#003B73")
    soft_blue = colors.HexColor("#EAF3FC")
    light = colors.HexColor("#F3F7FB")

    # Top header: company logo from master/current logo, title, and invoice no/date grid on right.
    invoice_grid = Table([
        [_p("<b>Delivery Invoice No.</b>", bold), _p(invoice.get("delivery_invoice_no") or "", bold)],
        [_p("<b>Delivery Date</b>", bold), _p(format_date_ddmmyyyy(invoice.get("delivery_date") or ""), bold)],
    ], colWidths=[82, 110], rowHeights=[25, 25])
    invoice_grid.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.45, colors.black),
        ("BACKGROUND", (0,0), (0,-1), navy),
        ("TEXTCOLOR", (0,0), (0,-1), colors.white),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("LEFTPADDING", (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5),
    ]))

    top_header = Table(
        [[_company_logo_cell(company, bold), _p("<b>Delivery Invoice</b>", title), invoice_grid]],
        colWidths=[150, page_width - 150 - 192, 192],
        rowHeights=[58],
    )
    top_header.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 0.6, colors.black),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (0,0), (0,0), "LEFT"),
        ("ALIGN", (1,0), (1,0), "CENTER"),
        ("ALIGN", (2,0), (2,0), "RIGHT"),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("BACKGROUND", (0,0), (-1,-1), colors.white),
    ]))
    story.append(top_header)
    story.append(Spacer(1, 6))

    seller = _company_address_text(company)
    shipto = (
        f"<b>Ship To</b><br/>{invoice.get('ship_to_name') or ''}<br/>"
        f"{invoice.get('ship_to_addressline1') or ''}<br/>"
        f"{invoice.get('ship_to_addressline2') or ''}<br/>"
        f"{invoice.get('ship_to_addressline3') or ''}<br/>"
        f"<b>Vendor GSTIN:</b> {invoice.get('ship_to_vendor_gstin') or ''}<br/>"
        f"<b>Phone:</b> {invoice.get('ship_to_vendor_phone') or ''}<br/>"
        f"<b>Email:</b> {invoice.get('ship_to_vendor_email') or ''}"
    )
    billto = (
        f"<b>Bill To / Customer</b><br/>{invoice.get('customer_name') or ''}<br/>"
        f"{invoice.get('customer_address') or ''}<br/>"
        f"<b>Phone:</b> {invoice.get('customer_phone') or ''}<br/>"
        f"<b>Email:</b> {invoice.get('customer_email') or ''}"
    )
    # Original invoice intentionally excluded from header. It remains in line-item table.
    details_rows = [
        ["Shipment No.", invoice.get("shipment_no") or ""],
        ["Vehicle", invoice.get("vehicle_number") or ""],
        ["ASN", invoice.get("asn_number") or ""],
        ["ASN Date", format_date_ddmmyyyy(invoice.get("asn_date") or "")],
        ["Due Date", format_date_ddmmyyyy(invoice.get("payment_due_date") or "")],
    ]
    details_table = Table([[_p(f"<b>{k}</b>", bold), _p(v, wrap)] for k, v in details_rows], colWidths=[78, (page_width/2) - 78])
    details_table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.30, colors.black),
        ("BACKGROUND", (0,0), (0,-1), soft_blue),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5),
    ]))

    header_table = Table([
        [_p(seller, wrap), _p(shipto, wrap)],
        [_p(billto, wrap), details_table],
    ], colWidths=[page_width/2, page_width/2], rowHeights=[92, 104])
    header_table.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 0.5, colors.black),
        ("GRID", (0,0), (-1,-1), 0.35, colors.black),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 7),
        ("RIGHTPADDING", (0,0), (-1,-1), 7),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 7))

    data = [[
        _p("Sr", bold), _p("Product", bold), _p("Pallet", bold), _p("Original Invoice No", bold),
        _p("PO No", bold), _p("PO Date", bold), _p("Qty", bold), _p("Price", bold),
        _p("Cur", bold), _p("Amount", bold)
    ]]
    total_qty = 0.0
    total_amt = 0.0
    for idx, item in enumerate(line_items or [], 1):
        qty = float(item.get("qty") or item.get("delivered_qty") or 0)
        price = float(item.get("price") or item.get("unit_price") or 0)
        amount = float(item.get("amount") or item.get("sale_amount") or qty * price)
        total_qty += qty
        total_amt += amount
        data.append([
            _p(idx, wrap),
            _p(f"{item.get('product_code','')}<br/>{item.get('product_name','')}", wrap),
            _p(item.get("pallet_no") or "", wrap),
            _p(item.get("original_invoice_no") or invoice.get("original_invoice_no") or "", wrap),
            _p(item.get("po_number") or "", wrap),
            _p(format_date_ddmmyyyy(item.get("po_date") or ""), wrap),
            _p(f"{qty:,.3f}", wrap),
            _p(f"{price:,.3f}", wrap),
            _p(item.get("currency") or invoice.get("currency") or "", wrap),
            _p(f"{amount:,.3f}", wrap),
        ])

    data.append([
        _p("", bold), _p("TOTAL", bold), _p("", bold), _p("", bold), _p("", bold), _p("", bold),
        _p(f"{total_qty:,.3f}", bold), _p("", bold),
        _p(invoice.get("currency") or (line_items[0].get('currency') if line_items else ''), bold),
        _p(f"{total_amt:,.3f}", bold)
    ])

    item_table = Table(data, colWidths=[23, 112, 52, 86, 48, 48, 44, 44, 31, 58], repeatRows=1)
    item_table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.35, colors.black),
        ("BACKGROUND", (0,0), (-1,0), navy),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
        ("ALIGN", (6,1), (-1,-1), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("FONTSIZE", (0,0), (-1,-1), 6.7),
        ("BACKGROUND", (0,-1), (-1,-1), light),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ("LEFTPADDING", (0,0), (-1,-1), 3),
        ("RIGHTPADDING", (0,0), (-1,-1), 3),
    ]))
    story.append(item_table)
    story.append(Spacer(1, 6))

    packaging = (invoice.get("packaging_details") or "")
    if invoice.get("packaging_remark"):
        packaging += ("\n" if packaging else "") + str(invoice.get("packaging_remark"))

    bank_details_text = _company_bank_text(company)

    footer_table = Table([
        [_p("<b>PACKAGING DETAILS</b>", bold), _p("<b>AMOUNT SUMMARY</b>", bold), "", ""],
        [_p(packaging, wrap), _p("SUBTOTAL", bold), _p(invoice.get("currency") or "", wrap), _p(f"{total_amt:,.3f}", wrap)],
        ["", _p("TAX", bold), "", _p("-", wrap)],
        ["", _p("OTHER", bold), "", _p("-", wrap)],
        ["", _p("TOTAL", bold), _p(invoice.get("currency") or "", bold), _p(f"{total_amt:,.3f}", bold)],
        [_p(bank_details_text, wrap), "", "", ""],
    ], colWidths=[page_width-186, 82, 36, 68])
    footer_table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,4), 0.35, colors.black),
        ("BOX", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), navy),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("SPAN", (1,0), (3,0)),
        ("SPAN", (0,1), (0,4)),
        ("SPAN", (0,5), (3,5)),
        ("ALIGN", (1,1), (3,4), "RIGHT"),
        ("BACKGROUND", (1,4), (3,4), light),
        ("FONTNAME", (1,4), (3,4), "Helvetica-Bold"),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("FONTSIZE", (0,0), (-1,-1), 7),
        ("LEFTPADDING", (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(footer_table)
    story.append(Spacer(1, 6))
    story.append(Table([[
        _p(f"If you have any questions, please contact { _company_value(company, 'company_name', 'name') or 'Company' } { _company_value(company, 'email', 'company_email') or '' }", normal),
        _p("<b>Authorised Signatory</b>", bold)
    ]], colWidths=[page_width-170, 170]))

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
            STRING_AGG(DISTINCT s.invoice_no, ', ' ORDER BY s.invoice_no) AS original_invoice_no,
            STRING_AGG(DISTINCT s.shipment_no, ', ' ORDER BY s.shipment_no) AS shipment_no,
            MAX(s.warehouse_id) AS warehouse_id,
            STRING_AGG(DISTINCT COALESCE(w.warehouse_name,''), ', ' ORDER BY COALESCE(w.warehouse_name,'')) AS warehouse_name,
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
                 stm.ship_to_name, stm.ship_to_id,
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
        ("delivery_list", "Delivery Invoice List", "pages/15_Delivery_Invoice_List.py"),
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





def fetch_delivery_invoice_headers(selected_product_id=None, selected_invoice_no=None):
    """Delivery invoice headers available for current user's product/warehouse access."""
    access_sql, access_params = _delivery_access_filter_sql("b", "s")
    part_sql, part_params = selected_part_sql(selected_product_id, "b")
    invoice_sql = ""
    invoice_params = ()
    if selected_invoice_no:
        invoice_sql = " AND s.invoice_no=? "
        invoice_params = (selected_invoice_no,)

    return fetch_all(f"""
        SELECT
            d.delivery_invoice_no,
            MIN(d.id) AS first_id,
            MAX(d.delivery_date) AS delivery_date,
            MAX(d.payment_due_date) AS payment_due_date,
            MAX(d.vehicle_number) AS vehicle_number,
            MAX(d.asn_number) AS asn_number,
            MAX(d.asn_date) AS asn_date,
            MAX(d.packaging_details) AS packaging_details,
            MAX(d.packaging_remark) AS packaging_remark,
            MAX(d.customer_id) AS customer_id,
            MAX(d.ship_to_master_id) AS ship_to_master_id,
            MAX(d.payment_term_id) AS payment_term_id,
            MAX(d.payment_terms_days) AS payment_terms_days,
            c.customer_name,
            s.invoice_no AS original_invoice_no,
            s.shipment_no,
            MAX(s.warehouse_id) AS warehouse_id,
            MAX(w.warehouse_name) AS warehouse_name,
            d.currency,
            SUM(d.delivered_qty) AS total_qty,
            SUM(d.sale_amount) AS total_amount,
            COUNT(*) AS product_rows
        FROM customer_deliveries d
        JOIN customers c ON d.customer_id = c.id
        JOIN shipments s ON d.shipment_id = s.id
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        WHERE 1=1
        {access_sql}
        {part_sql}
        {invoice_sql}
        GROUP BY d.delivery_invoice_no, c.customer_name, s.invoice_no, s.shipment_no, d.currency
        ORDER BY MIN(d.id) DESC
    """, access_params + part_params + invoice_params)


def fetch_delivery_invoice_rows(delivery_invoice_no, selected_product_id=None):
    """Rows of one delivery invoice with pallet/product data."""
    access_sql, access_params = _delivery_access_filter_sql("b", "s")
    part_sql, part_params = selected_part_sql(selected_product_id, "b")
    return fetch_all(f"""
        SELECT
            d.*,
            c.customer_name,
            s.invoice_no AS original_invoice_no,
            s.shipment_no,
            s.warehouse_id,
            w.warehouse_name,
            b.product_id,
            p.product_code,
            p.product_name,
            b.pallet_no,
            b.box_no,
            b.fifo_row_id,
            b.original_qty,
            b.unit_price AS shipment_unit_price,
            b.currency AS shipment_currency
        FROM customer_deliveries d
        JOIN customers c ON d.customer_id = c.id
        JOIN shipments s ON d.shipment_id = s.id
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        WHERE d.delivery_invoice_no=?
        {access_sql}
        {part_sql}
        ORDER BY d.id
    """, (delivery_invoice_no,) + access_params + part_params)


def fetch_available_pallets_for_edit(selected_ship_id=None, selected_product_id=None, include_box_id=None):
    """Available pallet/box rows for Edit Delivery.

    User request: allow selection of any available-quantity pallet from the database.
    selected_ship_id is intentionally ignored so pallets from all shipments can be selected.
    include_box_id lets the current linked box remain selectable even if balance is zero.
    """
    access_sql, access_params = _delivery_access_filter_sql("b", "s")
    part_sql, part_params = selected_part_sql(selected_product_id, "b")
    include_sql = ""
    include_params = ()
    if include_box_id:
        include_sql = " OR b.id=? "
        include_params = (include_box_id,)

    return fetch_all(f"""
        SELECT
            b.id,
            b.shipment_id,
            b.fifo_row_id,
            b.pallet_no,
            b.box_no,
            b.product_id,
            b.po_number,
            b.po_date,
            b.original_qty,
            b.unit_price,
            b.currency,
            s.shipment_no,
            s.invoice_no AS original_invoice_no,
            s.shipment_date,
            s.warehouse_id,
            w.warehouse_name,
            p.product_code,
            p.product_name,
            COALESCE(del.delivered_qty, 0) AS already_delivered_qty,
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
        WHERE (
            b.original_qty - COALESCE(del.delivered_qty, 0) > 0
            {include_sql}
        )
        {access_sql}
        {part_sql}
        ORDER BY s.shipment_date ASC NULLS LAST, COALESCE(b.fifo_row_id,b.id), b.pallet_no, b.id
        LIMIT 1000
    """, include_params + access_params + part_params)





def fetch_delivery_invoice_headers_for_edit(selected_product_id=None, date_from=None, date_to=None):
    """Delivery invoice headers for Edit page filtered by part, date range and user access."""
    access_sql, access_params = _delivery_access_filter_sql("b", "s")
    part_sql, part_params = selected_part_sql(selected_product_id, "b")
    date_sql = ""
    date_params = ()
    if date_from and date_to:
        date_sql = " AND d.delivery_date::date BETWEEN ?::date AND ?::date "
        date_params = (str(date_from), str(date_to))

    return fetch_all(f"""
        SELECT
            d.delivery_invoice_no,
            MIN(d.id) AS first_id,
            MAX(d.delivery_date) AS delivery_date,
            MAX(d.payment_due_date) AS payment_due_date,
            MAX(d.vehicle_number) AS vehicle_number,
            MAX(d.asn_number) AS asn_number,
            MAX(d.asn_date) AS asn_date,
            MAX(d.packaging_details) AS packaging_details,
            MAX(d.packaging_remark) AS packaging_remark,
            MAX(d.customer_id) AS customer_id,
            MAX(d.ship_to_master_id) AS ship_to_master_id,
            MAX(d.payment_term_id) AS payment_term_id,
            MAX(d.payment_terms_days) AS payment_terms_days,
            c.customer_name,
            s.invoice_no AS original_invoice_no,
            s.shipment_no,
            MAX(s.id) AS shipment_id,
            MAX(s.warehouse_id) AS warehouse_id,
            MAX(w.warehouse_name) AS warehouse_name,
            d.currency,
            SUM(d.delivered_qty) AS total_qty,
            SUM(d.sale_amount) AS total_amount,
            COUNT(*) AS product_rows
        FROM customer_deliveries d
        JOIN customers c ON d.customer_id = c.id
        JOIN shipments s ON d.shipment_id = s.id
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        WHERE 1=1
        {access_sql}
        {part_sql}
        {date_sql}
        GROUP BY d.delivery_invoice_no, c.customer_name, s.invoice_no, s.shipment_no, d.currency
        ORDER BY MAX(d.delivery_date) DESC, MIN(d.id) DESC
    """, access_params + part_params + date_params)


# Allow split Delivery pages to import internal helper names such as _delivery_access_filter_sql.
__all__ = [name for name in globals() if not name.startswith("__")]
