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
            "Original Invoice No": item.get("original_invoice_no", invoice.get("original_invoice_no", "")),
            "PO Number": item.get("po_number", invoice.get("po_number", "")),
            "PO Date": item.get("po_date", invoice.get("po_date", "")),
            "Pallet No": item.get("pallet_no", ""),
            "Box No": item.get("box_no", ""),
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
    """Bank details used on the delivery invoice footer.

    Company-master values are used when matching fields exist. The approved
    Four Star bank details from the reference delivery-invoice format are the
    non-destructive fallback, so the footer never becomes blank on existing
    databases whose company_settings table has no bank columns.
    """
    account_no = _company_value(
        company,
        "bank_account_no", "account_no", "bank_account_number",
        "account_number", "ac_no",
    ) or "004330150000003"
    ifsc = _company_value(company, "bank_ifsc_code", "ifsc_code", "ifsc") or "BKID0000043"
    micr = _company_value(company, "bank_micr_code", "micr_code", "micr") or "400013080"
    swift = _company_value(company, "bank_swift_code", "swift_code", "swift") or "BKIDINBBPPD"

    return "<br/>".join([
        f"<b>BANK ACCOUNT NO :</b> {account_no}",
        f"<b>BANK IFSC CODE :</b> {ifsc}",
        f"<b>BANK MICR CODE :</b> {micr}",
        f"<b>BANK SWIFT CODE :</b> {swift}",
    ])


def delivery_invoice_pdf_bytes(invoice, line_items):
    """Generate the A4 Delivery / Commercial Invoice in the approved reference style.

    The layout is intentionally restrained: white title/header areas, black grid
    borders, neutral-grey information cells and charcoal section headers. Delivery
    Invoice No./Date are shown in a structured grid, company address is explicit,
    and the page distribution is tuned to cover the full A4 sheet more evenly.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=10,
        leftMargin=10,
        topMargin=10,
        bottomMargin=10,
        title=f"Delivery / Commercial Invoice {invoice.get('delivery_invoice_no') or ''}",
        author="Four Star Industries Private Limited",
    )

    styles = getSampleStyleSheet()
    normal = ParagraphStyle(
        "delivery_normal_sn2707",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.4,
        leading=8.8,
        textColor=colors.HexColor("#111111"),
        wordWrap="CJK",
    )
    small = ParagraphStyle(
        "delivery_small_sn2707",
        parent=normal,
        fontSize=6.8,
        leading=8.0,
    )
    bold = ParagraphStyle(
        "delivery_bold_sn2707",
        parent=normal,
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=8.8,
    )
    section_head = ParagraphStyle(
        "delivery_section_head_sn2707",
        parent=bold,
        textColor=colors.white,
        alignment=0,
    )
    section_head_center = ParagraphStyle(
        "delivery_section_head_center_sn2707",
        parent=section_head,
        alignment=1,
    )
    title_style = ParagraphStyle(
        "delivery_title_sn2707",
        parent=bold,
        fontName="Helvetica-Bold",
        fontSize=16.5,
        leading=19,
        alignment=1,
        textColor=colors.HexColor("#111111"),
    )
    right = ParagraphStyle(
        "delivery_right_sn2707",
        parent=normal,
        alignment=2,
    )
    right_bold = ParagraphStyle(
        "delivery_right_bold_sn2707",
        parent=bold,
        alignment=2,
    )
    center = ParagraphStyle(
        "delivery_center_sn2707",
        parent=normal,
        alignment=1,
    )
    item_header = ParagraphStyle(
        "delivery_item_header_sn2707",
        parent=section_head_center,
        fontSize=5.7,
        leading=6.4,
        wordWrap="CJK",
    )
    item_text = ParagraphStyle(
        "delivery_item_text_sn2707",
        parent=normal,
        fontSize=6.15,
        leading=7.0,
        wordWrap="CJK",
    )
    item_center = ParagraphStyle(
        "delivery_item_center_sn2707",
        parent=item_text,
        alignment=1,
    )
    item_right = ParagraphStyle(
        "delivery_item_right_sn2707",
        parent=item_text,
        alignment=2,
    )
    item_right_bold = ParagraphStyle(
        "delivery_item_right_bold_sn2707",
        parent=item_right,
        fontName="Helvetica-Bold",
    )

    def _escape(value):
        return html.escape(str(value or "")).replace("\n", "<br/>")

    def _p(value, style=normal):
        return Paragraph(_escape(value), style)

    def _rich(markup, style=normal):
        return Paragraph(str(markup or ""), style)

    def _fmt_date(value):
        return format_date_ddmmyyyy(value or "")

    company = _delivery_company_master()
    story = []
    page_width = A4[0] - 32
    charcoal = colors.HexColor("#343A40")
    soft_gray = colors.HexColor("#EEF0F2")
    bank_gray = colors.HexColor("#D9D9D9")
    border = colors.HexColor("#1F2328")
    grid_width = 0.65

    company_name = _company_value(company, "company_name", "name", "legal_name") or "Four Star Industries Private Limited"
    company_address = _company_value(company, "address", "company_address", "registered_address", "plant_address")
    company_address_markup = _escape(str(company_address)).replace("\n", "<br/>") if company_address else ""
    company_code = _company_value(company, "company_code", "code")
    company_phone = _company_value(company, "phone", "company_phone", "contact_no")
    company_email = _company_value(company, "email", "company_email", "contact_email")
    company_tax = _company_value(company, "tax_id", "gstin", "company_gstin")

    payment_days = invoice.get("payment_terms_days")
    payment_term = invoice.get("payment_term") or invoice.get("payment_term_name") or ""
    if not payment_term and payment_days not in (None, ""):
        try:
            payment_term = f"{int(float(payment_days))} Days"
        except Exception:
            payment_term = f"{payment_days} Days"

    # Reference-style white title header: logo at left and centred black title.
    top_header = Table(
        [[_company_logo_cell(company, bold), _rich("<b>DELIVERY / COMMERCIAL INVOICE</b>", title_style)]],
        colWidths=[142, page_width - 142],
        rowHeights=[54],
    )
    top_header.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.8, border),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("LEFTPADDING", (0, 0), (0, 0), 7),
        ("RIGHTPADDING", (0, 0), (0, 0), 7),
        ("LEFTPADDING", (1, 0), (1, 0), 5),
        ("RIGHTPADDING", (1, 0), (1, 0), 5),
    ]))
    story.append(top_header)
    story.append(Spacer(1, 4))

    seller_lines = ["<b>Seller</b>", f"<b>{_escape(company_name)}</b>"]
    if company_address_markup:
        seller_lines.append(f"<b>Address:</b><br/>{company_address_markup}")
    if company_phone:
        seller_lines.append(f"<b>Phone:</b> {_escape(company_phone)}")
    if company_email:
        seller_lines.append(f"<b>Email:</b> {_escape(company_email)}")
    if company_tax:
        seller_lines.append(f"<b>Tax ID / GSTIN:</b> {_escape(company_tax)}")
    seller_lines.append("")
    seller_lines.append(f"<b>Company Code:</b> {_escape(company_code)}")

    invoice_grid = Table([
        [_rich("<b>Delivery Invoice No</b>", bold), _p(invoice.get("delivery_invoice_no") or "", bold)],
        [_rich("<b>Delivery Date</b>", bold), _p(_fmt_date(invoice.get("delivery_date")) or "", bold)],
    ], colWidths=[110, (page_width / 2) - 110], rowHeights=[45, 45])
    invoice_grid.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), grid_width, border),
        ("BACKGROUND", (0, 0), (0, -1), soft_gray),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    seller_meta = Table([
        [_rich("<br/>".join(seller_lines), normal), invoice_grid],
    ], colWidths=[page_width / 2, page_width / 2], rowHeights=[90])
    seller_meta.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), grid_width, border),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("VALIGN", (0, 0), (0, 0), "TOP"),
        ("VALIGN", (1, 0), (1, 0), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 7),
        ("RIGHTPADDING", (0, 0), (0, 0), 7),
        ("TOPPADDING", (0, 0), (0, 0), 7),
        ("BOTTOMPADDING", (0, 0), (0, 0), 6),
        ("LEFTPADDING", (1, 0), (1, 0), 0),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
        ("TOPPADDING", (1, 0), (1, 0), 0),
        ("BOTTOMPADDING", (1, 0), (1, 0), 0),
    ]))
    story.append(seller_meta)

    customer_lines = ["<b>Bill To</b>", f"<b>{_escape(invoice.get('customer_name'))}</b>"]
    if invoice.get("customer_company_code"):
        customer_lines.append(f"<b>Customer ID:</b> {_escape(invoice.get('customer_company_code'))}")
    if invoice.get("customer_address"):
        customer_lines.append(_escape(invoice.get("customer_address")))
    if invoice.get("customer_phone"):
        customer_lines.append(f"<b>Phone:</b> {_escape(invoice.get('customer_phone'))}")
    if invoice.get("customer_email"):
        customer_lines.append(f"<b>Email:</b> {_escape(invoice.get('customer_email'))}")

    ship_lines = ["<b>Ship To</b>", f"<b>{_escape(invoice.get('ship_to_name'))}</b>"]
    if invoice.get("ship_to_id"):
        ship_lines.append(f"<b>Ship To ID:</b> {_escape(invoice.get('ship_to_id'))}")
    for key in ("ship_to_addressline1", "ship_to_addressline2", "ship_to_addressline3"):
        if invoice.get(key):
            ship_lines.append(_escape(invoice.get(key)))
    if invoice.get("ship_to_vendor_gstin"):
        ship_lines.append(f"<b>Vendor GSTIN:</b> {_escape(invoice.get('ship_to_vendor_gstin'))}")
    if invoice.get("ship_to_vendor_phone"):
        ship_lines.append(f"<b>Phone:</b> {_escape(invoice.get('ship_to_vendor_phone'))}")
    if invoice.get("ship_to_vendor_email"):
        ship_lines.append(f"<b>Email:</b> {_escape(invoice.get('ship_to_vendor_email'))}")

    party_table = Table([
        [_rich("<br/>".join(ship_lines), normal), _rich("<br/>".join(customer_lines), normal)],
    ], colWidths=[page_width / 2, page_width / 2], rowHeights=[102])
    party_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), grid_width, border),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(party_table)
    story.append(Spacer(1, 4))

    asn_display = str(invoice.get("asn_number") or "")
    if invoice.get("asn_date"):
        asn_date_text = _fmt_date(invoice.get("asn_date"))
        asn_display = f"{asn_display} / {asn_date_text}" if asn_display else asn_date_text

    details = Table([
        [_rich("<b>Payment Due Date:</b>", bold), _p(_fmt_date(invoice.get("payment_due_date"))),
         _rich("<b>Vehicle Number:</b>", bold), _p(invoice.get("vehicle_number") or invoice.get("vehicle_no") or "")],
        [_rich("<b>Payment Term:</b>", bold), _p(payment_term),
         _rich("<b>Ship Via:</b>", bold), _p(invoice.get("ship_via") or "Road")],
        [_rich("<b>Shipment Number:</b>", bold), _p(invoice.get("shipment_no") or ""),
         _rich("<b>ASN Number / Date:</b>", bold), _p(asn_display)],
    ], colWidths=[112, 160, 112, page_width - 384], rowHeights=[28, 28, 28])
    details.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), grid_width, border),
        ("BACKGROUND", (0, 0), (0, -1), soft_gray),
        ("BACKGROUND", (2, 0), (2, -1), soft_gray),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(details)
    story.append(Spacer(1, 5))

    item_data = [[
        _rich("<b>SR</b>", item_header),
        _rich("<b>PRODUCT</b>", item_header),
        _rich("<b>FSI ORIG.<br/>INV. #</b>", item_header),
        _rich("<b>PO NO.</b>", item_header),
        _rich("<b>PO DATE</b>", item_header),
        _rich("<b>PALLET<br/>NO.</b>", item_header),
        _rich("<b>BOX<br/>NO.</b>", item_header),
        _rich("<b>QTY</b>", item_header),
        _rich("<b>RATE</b>", item_header),
        _rich("<b>CUR</b>", item_header),
        _rich("<b>AMOUNT</b>", item_header),
    ]]

    total_qty = 0.0
    total_amount = 0.0
    for idx, item in enumerate(line_items or [], start=1):
        qty = float(item.get("qty") or item.get("delivered_qty") or 0)
        price = float(item.get("price") or item.get("unit_price") or 0)
        amount = float(item.get("amount") or item.get("sale_amount") or qty * price)
        total_qty += qty
        total_amount += amount

        description_parts = [
            str(item.get("product_code") or "").strip(),
            str(item.get("product_name") or "").strip(),
        ]
        description = " ".join(part for part in description_parts if part)

        item_data.append([
            _p(idx, item_center),
            _p(description, item_text),
            _p(item.get("original_invoice_no") or "", item_center),
            _p(item.get("po_number") or "", item_center),
            _p(_fmt_date(item.get("po_date")), item_center),
            _p(item.get("pallet_no") or "", item_center),
            _p(item.get("box_no") or "", item_center),
            _p(f"{qty:,.3f}", item_right),
            _p(f"{price:,.3f}", item_right),
            _p(item.get("currency") or invoice.get("currency") or "", item_center),
            _p(f"{amount:,.3f}", item_right),
        ])

    currency = invoice.get("currency") or (line_items[0].get("currency") if line_items else "")
    item_data.append([
        "",
        _rich("<b>TOTAL</b>", item_right_bold),
        "",
        "",
        "",
        "",
        "",
        _p(f"{total_qty:,.3f}", item_right_bold),
        "",
        _p(currency, item_center),
        _p(f"{total_amount:,.3f}", item_right_bold),
    ])

    item_widths = [24, 104, 66, 53, 49, 43, 47, 44, 43, 28, page_width - 501]
    item_table = Table(item_data, colWidths=item_widths, repeatRows=1)
    item_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), grid_width, border),
        ("BACKGROUND", (0, 0), (-1, 0), charcoal),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), soft_gray),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("SPAN", (1, -1), (6, -1)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
        ("ALIGN", (2, 1), (6, -2), "CENTER"),
        ("ALIGN", (7, 1), (8, -1), "RIGHT"),
        ("ALIGN", (9, 1), (9, -1), "CENTER"),
        ("ALIGN", (10, 1), (10, -1), "RIGHT"),
        ("ALIGN", (1, -1), (6, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(item_table)

    # The approved sample keeps the summary near the lower part of the page.
    # The gap reduces automatically as additional item rows are added.
    item_count = max(1, len(line_items or []))
    footer_gap = max(10, min(88, 88 - ((item_count - 1) * 12)))
    story.append(Spacer(1, footer_gap))

    packaging = str(invoice.get("packaging_details") or "")
    if invoice.get("packaging_remark"):
        packaging = f"{packaging}\n{invoice.get('packaging_remark')}" if packaging else str(invoice.get("packaging_remark"))

    tax_amount = float(invoice.get("tax_amount") or 0)
    other_amount = float(invoice.get("other_amount") or 0)
    grand_total = total_amount + tax_amount + other_amount
    bank_details = _company_bank_text(company)

    footer = Table([
        [_rich("<b>PACKAGING DETAILS:</b>", section_head), _rich("<b>AMOUNT SUMMARY</b>", section_head), "", ""],
        [_p(packaging, normal), _rich("<b>SUBTOTAL</b>", right_bold), _p(currency, center), _p(f"{total_amount:,.3f}", right)],
        ["", _rich("<b>TAX</b>", right_bold), _p(currency if tax_amount else "", center), _p(f"{tax_amount:,.3f}" if tax_amount else "-", right)],
        ["", _rich("<b>OTHER</b>", right_bold), _p(currency if other_amount else "", center), _p(f"{other_amount:,.3f}" if other_amount else "-", right)],
        ["", _rich("<b>TOTAL</b>", right_bold), _p(currency, center), _p(f"{grand_total:,.3f}", right_bold)],
        [_rich(f"<b>BANK DETAILS:</b><br/>{bank_details}", normal), "", "", ""],
    ], colWidths=[page_width - 206, 82, 44, 80], rowHeights=[24, 30, 28, 28, 31, 80])
    footer.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -2), grid_width, border),
        ("BOX", (0, -1), (-1, -1), grid_width, border),
        ("SPAN", (1, 0), (3, 0)),
        ("SPAN", (0, 1), (0, 4)),
        ("SPAN", (0, 5), (3, 5)),
        ("BACKGROUND", (0, 0), (0, 0), charcoal),
        ("BACKGROUND", (1, 0), (3, 0), charcoal),
        ("BACKGROUND", (1, 4), (3, 4), soft_gray),
        ("BACKGROUND", (0, 5), (3, 5), bank_gray),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ("VALIGN", (1, 1), (3, 4), "MIDDLE"),
        ("ALIGN", (1, 1), (1, 4), "RIGHT"),
        ("ALIGN", (2, 1), (2, 4), "CENTER"),
        ("ALIGN", (3, 1), (3, 4), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(footer)

    contact_text = "If you have any questions about this document, please contact"
    if company_email:
        contact_text += f"<br/>{_escape(company_name)}, {_escape(company_email)}"
    else:
        contact_text += f"<br/>{_escape(company_name)}"
    contact_signature = Table([
        [_rich(contact_text, small), _rich("<b>Authorised Signatory</b>", right_bold)],
    ], colWidths=[page_width * 0.66, page_width * 0.34], rowHeights=[34])
    contact_signature.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(contact_signature)

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
            MAX(d.payment_term_id) AS payment_term_id,
            MAX(d.payment_terms_days) AS payment_terms_days,
            MAX(pt.term_name) AS payment_term_name,
            MAX(d.customer_id) AS customer_id,
            MAX(d.ship_to_master_id) AS ship_to_master_id,
            MAX(d.vehicle_number) AS vehicle_number,
            MAX(d.ship_via) AS ship_via,
            MAX(d.asn_number) AS asn_number,
            MAX(d.asn_date) AS asn_date,
            MAX(d.packaging_details) AS packaging_details,
            MAX(d.packaging_remark) AS packaging_remark,
            MAX(d.attachment_path) AS attachment_path,
            MAX(d.currency) AS currency,
            MAX(c.customer_name) AS customer_name,
            MAX(c.address) AS customer_address,
            MAX(c.company_code) AS customer_company_code,
            MAX(c.phone) AS customer_phone,
            MAX(c.email) AS customer_email,
            STRING_AGG(DISTINCT s.invoice_no, ', ' ORDER BY s.invoice_no) AS original_invoice_no,
            STRING_AGG(DISTINCT s.shipment_no, ', ' ORDER BY s.shipment_no) AS shipment_no,
            MAX(s.warehouse_id) AS warehouse_id,
            STRING_AGG(DISTINCT COALESCE(w.warehouse_name,''), ', ' ORDER BY COALESCE(w.warehouse_name,'')) AS warehouse_name,
            MAX(stm.ship_to_name) AS ship_to_name,
            MAX(stm.ship_to_id) AS ship_to_id,
            MAX(stm.addressline1) AS ship_to_addressline1,
            MAX(stm.addressline2) AS ship_to_addressline2,
            MAX(stm.addressline3) AS ship_to_addressline3,
            MAX(stm.vendor_gstin) AS ship_to_vendor_gstin,
            MAX(stm.vendor_phone) AS ship_to_vendor_phone,
            MAX(stm.vendor_email) AS ship_to_vendor_email
        FROM customer_deliveries d
        JOIN customers c ON d.customer_id = c.id
        JOIN shipments s ON d.shipment_id = s.id
        JOIN shipment_boxes b ON d.box_id = b.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN payment_terms pt ON d.payment_term_id = pt.id
        LEFT JOIN warehouses w ON s.warehouse_id = w.id
        LEFT JOIN ship_to_masters stm ON COALESCE(d.ship_to_master_id, s.ship_to_master_id, c.ship_to_master_id) = stm.id
        WHERE d.delivery_invoice_no=?
        {access_sql}
        GROUP BY d.delivery_invoice_no
        ORDER BY MIN(d.id)
        LIMIT 1
    """, (delivery_invoice_no,) + access_params)
    if not header_rows:
        return None, []

    invoice = dict(header_rows[0])
    invoice["seller_name"] = "Four Star Industries Pvt. Ltd."
    invoice["seller_address"] = ""
    invoice["ship_via"] = invoice.get("ship_via") or "Road"
    term_name = str(invoice.get("payment_term_name") or "").strip()
    term_days = invoice.get("payment_terms_days")
    if term_name and term_days not in (None, ""):
        try:
            invoice["payment_term"] = f"{term_name} - {int(float(term_days))} Days"
        except Exception:
            invoice["payment_term"] = f"{term_name} - {term_days} Days"
    elif term_name:
        invoice["payment_term"] = term_name
    elif term_days not in (None, ""):
        try:
            invoice["payment_term"] = f"{int(float(term_days))} Days"
        except Exception:
            invoice["payment_term"] = f"{term_days} Days"

    item_rows = fetch_all(f"""
        SELECT
            d.delivery_invoice_no,
            s.invoice_no AS original_invoice_no,
            COALESCE(d.po_number, b.po_number, s.po_number, p.po_number) AS po_number,
            COALESCE(d.po_date, b.po_date, s.po_date, p.po_date) AS po_date,
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
    # Browser-printable HTML backup for environments where direct JPEG rendering
    # is not available. Kept for backward compatibility with existing buttons.
    payload = dict(invoice or {})
    payload["items"] = [dict(item or {}) for item in (line_items or [])]
    return delivery_note_html(payload).encode("utf-8")

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
    """Verify the additive delivery/header/master schema before rendering."""
    require_delivery_master_relationship_schema("Delivery module")


def fetch_delivery_part_options():
    """Parts having positive balance quantity and allowed by current user's access."""
    access_sql, access_params = _delivery_access_filter_sql("b", "s")
    return fetch_all(f"""
        SELECT DISTINCT
            b.product_id,
            p.product_code,
            p.product_name,
            p.customer_id,
            c.ship_to_master_id AS customer_ship_to_master_id
        FROM shipment_boxes b
        JOIN shipments s ON b.shipment_id = s.id
        JOIN products p ON b.product_id = p.id
        LEFT JOIN customers c ON p.customer_id = c.id
        LEFT JOIN (
            SELECT box_id, SUM(delivered_qty) AS delivered_qty
            FROM customer_deliveries
            GROUP BY box_id
        ) del ON b.id = del.box_id
        WHERE b.original_qty - COALESCE(del.delivered_qty, 0) > 0
        {access_sql}
        ORDER BY p.product_code, p.product_name
    """, access_params)


def fetch_product_delivery_defaults(product_id):
    """Return Product-linked Bill To and effective Ship To defaults.

    Canonical SN 27.12 chain: Product.customer_id -> Customer.ship_to_master_id.
    Customer.ship_to_master_id is the required Ship To source. Returned IDs are
    defaults; the transaction header remains manually changeable before save.
    """
    if not product_id:
        return {}
    rows = fetch_all("""
        SELECT
            p.id AS product_id,
            p.product_code,
            p.product_name,
            p.customer_id,
            c.customer_name,
            c.company_code AS customer_company_code,
            c.address AS customer_address,
            c.phone AS customer_phone,
            c.email AS customer_email,
            c.payment_term_id AS customer_payment_term_id,
            c.ship_to_master_id AS customer_ship_to_master_id,
            c.ship_to_master_id AS effective_ship_to_master_id,
            CASE
                WHEN c.ship_to_master_id IS NOT NULL THEN 'Customer Master'
                ELSE ''
            END AS ship_to_source
        FROM products p
        LEFT JOIN customers c ON p.customer_id = c.id
        WHERE p.id=?
        LIMIT 1
    """, (product_id,))
    return dict(rows[0]) if rows else {}


def fetch_customer_delivery_default(customer_id):
    """Return the selected Customer's payment-term and default Ship To link."""
    if not customer_id:
        return {}
    rows = fetch_all("""
        SELECT id AS customer_id, customer_name, company_code, address, phone, email,
               payment_term_id, ship_to_master_id
        FROM customers
        WHERE id=?
        LIMIT 1
    """, (customer_id,))
    return dict(rows[0]) if rows else {}


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
            s.customer_id,
            s.ship_to_master_id,
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
        GROUP BY s.id, s.shipment_no, s.invoice_no, s.po_number, s.po_date, s.shipment_date, s.warehouse_id, s.customer_id, s.ship_to_master_id, w.warehouse_name
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
            MAX(d.ship_via) AS ship_via,
            MAX(d.asn_number) AS asn_number,
            MAX(d.asn_date) AS asn_date,
            MAX(d.packaging_details) AS packaging_details,
            MAX(d.packaging_remark) AS packaging_remark,
            MAX(d.attachment_path) AS attachment_path,
            MAX(d.customer_id) AS customer_id,
            MAX(d.ship_to_master_id) AS ship_to_master_id,
            MAX(d.payment_term_id) AS payment_term_id,
            MAX(d.payment_terms_days) AS payment_terms_days,
            MAX(c.customer_name) AS customer_name,
            STRING_AGG(DISTINCT s.invoice_no, ', ' ORDER BY s.invoice_no) AS original_invoice_no,
            STRING_AGG(DISTINCT s.shipment_no, ', ' ORDER BY s.shipment_no) AS shipment_no,
            MAX(s.id) AS shipment_id,
            MAX(s.warehouse_id) AS warehouse_id,
            STRING_AGG(DISTINCT COALESCE(w.warehouse_name,''), ', ' ORDER BY COALESCE(w.warehouse_name,'')) AS warehouse_name,
            MAX(d.currency) AS currency,
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
        GROUP BY d.delivery_invoice_no
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
            MAX(d.ship_via) AS ship_via,
            MAX(d.asn_number) AS asn_number,
            MAX(d.asn_date) AS asn_date,
            MAX(d.packaging_details) AS packaging_details,
            MAX(d.packaging_remark) AS packaging_remark,
            MAX(d.attachment_path) AS attachment_path,
            MAX(d.customer_id) AS customer_id,
            MAX(d.ship_to_master_id) AS ship_to_master_id,
            MAX(d.payment_term_id) AS payment_term_id,
            MAX(d.payment_terms_days) AS payment_terms_days,
            MAX(c.customer_name) AS customer_name,
            STRING_AGG(DISTINCT s.invoice_no, ', ' ORDER BY s.invoice_no) AS original_invoice_no,
            STRING_AGG(DISTINCT s.shipment_no, ', ' ORDER BY s.shipment_no) AS shipment_no,
            MAX(s.id) AS shipment_id,
            MAX(s.warehouse_id) AS warehouse_id,
            STRING_AGG(DISTINCT COALESCE(w.warehouse_name,''), ', ' ORDER BY COALESCE(w.warehouse_name,'')) AS warehouse_name,
            MAX(d.currency) AS currency,
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
        GROUP BY d.delivery_invoice_no
        ORDER BY MAX(d.delivery_date) DESC, MIN(d.id) DESC
    """, access_params + part_params + date_params)


# Allow split Delivery pages to import internal helper names such as _delivery_access_filter_sql.
__all__ = [name for name in globals() if not name.startswith("__")]
