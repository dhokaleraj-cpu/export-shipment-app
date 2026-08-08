from delivery_common import *

page_setup()
require_page_view('delivery_edit')
show_edit_permission_status('delivery_edit')
ensure_delivery_columns()
require_delivery_master_relationship_schema("Edit Delivery Invoice")
ensure_delivery_master_link_columns(show_errors=True)

show_header("Edit Delivery Invoice", "Edit the complete invoice header including Bill To, Ship To and all transaction fields")
render_delivery_subnav('delivery_edit')
access_notice()

if not current_user_can_edit("delivery_edit"):
    st.error("You have View permission but not Edit permission for Edit Delivery Invoice page. Contact Super Admin.")
    st.stop()

cleanup_orphan_transactions()

# PDF after save.
print_invoice_no = st.session_state.get("edit_delivery_last_print_invoice_no")
if print_invoice_no:
    inv_for_print, lines_for_print = get_saved_delivery_invoice_for_pdf(print_invoice_no)
    if inv_for_print and lines_for_print:
        pdf_bytes = delivery_invoice_pdf_bytes(inv_for_print, lines_for_print)
        st.success(f"Saved successfully. PDF is ready for Delivery Invoice: {print_invoice_no}")
        st.download_button(
            "Print / Download Updated Delivery Invoice PDF",
            pdf_bytes,
            file_name=f"delivery_invoice_{print_invoice_no}.pdf",
            mime="application/pdf",
            key=f"download_updated_delivery_invoice_{print_invoice_no}"
        )

st.markdown('<div class="input-section-title">Part Selection</div>', unsafe_allow_html=True)
selected_product_id, selected_product_label, _part_rows = delivery_part_selectbox(
    key="edit_delivery_part_filter",
    label="Select Part Number"
)

st.markdown('<div class="input-section-title">Delivery Date Range</div>', unsafe_allow_html=True)
range_col1, range_col2 = st.columns(2)
with range_col1:
    date_from = st.date_input("From Date", value=date.today() - timedelta(days=30), key="edit_delivery_from_date")
with range_col2:
    date_to = st.date_input("To Date", value=date.today(), key="edit_delivery_to_date")

if date_from > date_to:
    st.warning("From Date is after To Date. Dates were swapped for this search.")
    date_from, date_to = date_to, date_from

headers = fetch_delivery_invoice_headers_for_edit(
    selected_product_id=selected_product_id,
    date_from=date_from,
    date_to=date_to
)

if not headers:
    st.info("No delivery invoice found for selected Part and Date Range.")
    render_slogan_footer()
    st.stop()

header_map = {
    f"{h['delivery_invoice_no']} | Date {h.get('delivery_date')} | Original Inv {h.get('original_invoice_no')} | Qty {float(h.get('total_qty') or 0):,.2f} | Amount {float(h.get('total_amount') or 0):,.2f} {h.get('currency') or ''} | {h.get('customer_name') or ''}": h
    for h in headers
}
selected_header_key = searchable_selectbox(
    "Select Delivery Invoice",
    list(header_map.keys()),
    key="edit_delivery_invoice_header_by_date"
)
selected_header = header_map[selected_header_key]
selected_delivery_invoice_no = selected_header["delivery_invoice_no"]
selected_ship_id = selected_header.get("shipment_id")

st.info(
    f"Loaded Delivery Invoice {selected_delivery_invoice_no} | Original Invoice {selected_header.get('original_invoice_no')} | "
    f"Part Filter {selected_product_label} | Period {date_from} to {date_to}"
)

# Current selected invoice PDF download.
current_inv_for_print, current_lines_for_print = get_saved_delivery_invoice_for_pdf(selected_delivery_invoice_no)
if current_inv_for_print and current_lines_for_print:
    current_pdf_bytes = delivery_invoice_pdf_bytes(current_inv_for_print, current_lines_for_print)
    st.download_button(
        "Print / Download Current Delivery Invoice PDF",
        current_pdf_bytes,
        file_name=f"delivery_invoice_{selected_delivery_invoice_no}.pdf",
        mime="application/pdf",
        key=f"download_current_delivery_invoice_{selected_delivery_invoice_no}"
    )

# Complete common invoice/header fields. These values are applied to every row
# under the selected Delivery Invoice so the print header cannot become mixed.
st.divider()
st.subheader("Complete Delivery Invoice Header Edit")
st.info("All editable invoice-header fields are loaded from the saved record. Bill To, Ship To and Payment Term are master-linked dropdowns; you may change them manually and save the header for the entire invoice.")
st.caption("Original Invoice Number, Shipment Number, PO, Pallet and Box remain line-linked values and are controlled through the pallet rows below.")

common_header_source = dict(selected_header or {})
if current_inv_for_print:
    common_header_source.update(dict(current_inv_for_print))

# Legacy invoices may pre-date saved Customer / Ship To IDs. Infer a common
# default only when every product line resolves to the same required master chain.
if not common_header_source.get("customer_id") or not common_header_source.get("ship_to_master_id"):
    inferred_defaults = []
    for _line in (current_lines_for_print or []):
        _product_id = _line.get("product_id")
        if _product_id:
            try:
                inferred_defaults.append(fetch_product_delivery_defaults(_product_id))
            except Exception:
                pass
    _inferred_customers = {int(x.get("customer_id")) for x in inferred_defaults if x.get("customer_id")}
    _inferred_ship_tos = {int(x.get("customer_ship_to_master_id")) for x in inferred_defaults if x.get("customer_ship_to_master_id")}
    if not common_header_source.get("customer_id") and len(_inferred_customers) == 1:
        common_header_source["customer_id"] = next(iter(_inferred_customers))
    if not common_header_source.get("ship_to_master_id") and len(_inferred_ship_tos) == 1:
        common_header_source["ship_to_master_id"] = next(iter(_inferred_ship_tos))

common_key_suffix = str(selected_delivery_invoice_no or "delivery").replace(" ", "_").replace("/", "_").replace("|", "_").replace("\\", "_")

# If invoice selection changes, remove old common-header widget states so values
# are fetched from the newly selected saved record.
previous_common_invoice = st.session_state.get("_edit_delivery_previous_invoice_no")
if previous_common_invoice != selected_delivery_invoice_no:
    for _k in list(st.session_state.keys()):
        if str(_k).startswith("edit_common_"):
            try:
                del st.session_state[_k]
            except Exception:
                pass
    st.session_state["_edit_delivery_previous_invoice_no"] = selected_delivery_invoice_no

customer_rows = fetch_all("SELECT * FROM customers ORDER BY customer_name, id")
ship_to_rows = fetch_all("SELECT * FROM ship_to_masters ORDER BY COALESCE(is_active, TRUE) DESC, ship_to_name, ship_to_id, id")
term_rows = fetch_all("SELECT * FROM payment_terms ORDER BY days, id")

customer_map = {
    f'{r.get("customer_name") or "-"} | {r.get("company_code") or "-"} | ID {r.get("id")}': r
    for r in customer_rows
}
customer_label_by_id = {int(r["id"]): label for label, r in customer_map.items()}
ship_to_map = {
    f'{r.get("ship_to_name") or "-"} | {r.get("ship_to_id") or "-"} | ID {r.get("id")}' + (" | INACTIVE" if r.get("is_active") is False else ""): r
    for r in ship_to_rows
}
ship_to_label_by_id = {int(r["id"]): label for label, r in ship_to_map.items()}
term_map = {
    f'{r.get("term_name") or "-"} - {r.get("days") or 0} days | ID {r.get("id")}': r
    for r in term_rows
}
term_label_by_id = {int(r["id"]): label for label, r in term_map.items()}

# Provide an explicit master-relationship reload for invoices containing one Product.
# This is optional: the saved header remains the source until the user clicks it.
current_product_ids = sorted({int(line.get("product_id")) for line in (current_lines_for_print or []) if line.get("product_id")})
product_header_default = fetch_product_delivery_defaults(current_product_ids[0]) if len(current_product_ids) == 1 else {}
if product_header_default.get("customer_id") and product_header_default.get("effective_ship_to_master_id"):
    master_customer_name = product_header_default.get("customer_name") or "-"
    master_ship_to_rows = fetch_all("SELECT ship_to_name, ship_to_id FROM ship_to_masters WHERE id=? LIMIT 1", (product_header_default.get("effective_ship_to_master_id"),))
    master_ship_to_name = master_ship_to_rows[0].get("ship_to_name") if master_ship_to_rows else "-"
    st.caption(f"Product Master relationship available: {master_customer_name} → {master_ship_to_name}")
    if st.button(
        "Load Bill To / Ship To from Product Master Relationship",
        key=f"load_edit_delivery_product_relationship_{common_key_suffix}",
    ):
        customer_id_value = int(product_header_default["customer_id"])
        ship_to_id_value = int(product_header_default["effective_ship_to_master_id"])
        if customer_id_value in customer_label_by_id and ship_to_id_value in ship_to_label_by_id:
            st.session_state[f"edit_common_bill_to_{common_key_suffix}"] = customer_label_by_id[customer_id_value]
            st.session_state[f"edit_common_ship_to_{common_key_suffix}"] = ship_to_label_by_id[ship_to_id_value]
            term_id_value = product_header_default.get("customer_payment_term_id")
            if term_id_value and int(term_id_value) in term_label_by_id:
                st.session_state[f"edit_common_payment_term_{common_key_suffix}"] = term_label_by_id[int(term_id_value)]
            st.session_state[f"_edit_common_customer_tracker_{common_key_suffix}"] = customer_id_value
            st.rerun()

if not customer_map:
    st.error("Customer Master is empty. Create a Customer before editing the invoice header.")
    st.stop()
if not term_map:
    st.error("Payment Term Master is empty. Create a Payment Term before editing the invoice header.")
    st.stop()
if not ship_to_map:
    st.error("Ship To Master is empty. Create a Ship To before editing the Delivery Invoice header.")
    st.stop()

source_customer_id = common_header_source.get("customer_id")
source_ship_to_id = common_header_source.get("ship_to_master_id")
source_term_id = common_header_source.get("payment_term_id")
source_customer_label = customer_label_by_id.get(int(source_customer_id), list(customer_map.keys())[0]) if source_customer_id else list(customer_map.keys())[0]
source_ship_to_label = ship_to_label_by_id.get(int(source_ship_to_id), list(ship_to_map.keys())[0] if ship_to_map else "") if source_ship_to_id else (list(ship_to_map.keys())[0] if ship_to_map else "")
source_term_label = term_label_by_id.get(int(source_term_id), list(term_map.keys())[0]) if source_term_id else list(term_map.keys())[0]

st.markdown(
    f"""
    <div class="admin-saved-data-card">
        <b>Loaded Header From Saved Record:</b>
        Delivery Invoice: {common_header_source.get('delivery_invoice_no') or '-'} |
        Delivery Date: {common_header_source.get('delivery_date') or '-'} |
        Bill To: {common_header_source.get('customer_name') or '-'} |
        Ship To: {common_header_source.get('ship_to_name') or '-'} |
        Original Invoice(s): {common_header_source.get('original_invoice_no') or '-'} |
        Shipment(s): {common_header_source.get('shipment_no') or '-'}
    </div>
    """,
    unsafe_allow_html=True
)

common_row1 = st.columns(4)
with common_row1[0]:
    common_invoice_no = st.text_input(
        "Delivery Invoice No",
        common_header_source.get("delivery_invoice_no") or "",
        key=f"edit_common_delivery_invoice_no_{common_key_suffix}"
    )
with common_row1[1]:
    common_delivery_date = st.date_input(
        "Delivery Date",
        value=parse_date_for_input(common_header_source.get("delivery_date")),
        key=f"edit_common_delivery_date_{common_key_suffix}"
    )
with common_row1[2]:
    bill_to_key = f"edit_common_bill_to_{common_key_suffix}"
    common_bill_to_label = st.selectbox(
        "Customer / Bill To *",
        list(customer_map.keys()),
        index=list(customer_map.keys()).index(source_customer_label),
        key=bill_to_key
    )
    common_bill_to_row = customer_map[common_bill_to_label]
    common_customer_id = int(common_bill_to_row["id"])

# When Bill To is manually changed, load that Customer's linked Ship To and
# default Payment Term before those widgets are created.
customer_tracker_key = f"_edit_common_customer_tracker_{common_key_suffix}"
ship_to_widget_key = f"edit_common_ship_to_{common_key_suffix}"
term_widget_key = f"edit_common_payment_term_{common_key_suffix}"
if customer_tracker_key not in st.session_state:
    st.session_state[customer_tracker_key] = int(source_customer_id) if source_customer_id else common_customer_id
elif st.session_state.get(customer_tracker_key) != common_customer_id:
    linked_ship_to_id = common_bill_to_row.get("ship_to_master_id")
    if linked_ship_to_id and int(linked_ship_to_id) in ship_to_label_by_id:
        st.session_state[ship_to_widget_key] = ship_to_label_by_id[int(linked_ship_to_id)]
    elif ship_to_widget_key in st.session_state:
        del st.session_state[ship_to_widget_key]
    linked_term_id = common_bill_to_row.get("payment_term_id")
    if linked_term_id and int(linked_term_id) in term_label_by_id:
        st.session_state[term_widget_key] = term_label_by_id[int(linked_term_id)]
    st.session_state[customer_tracker_key] = common_customer_id

with common_row1[3]:
    if ship_to_map:
        if ship_to_widget_key in st.session_state and st.session_state.get(ship_to_widget_key) not in ship_to_map:
            del st.session_state[ship_to_widget_key]
        common_ship_to_label = st.selectbox(
            "Ship To *",
            list(ship_to_map.keys()),
            index=list(ship_to_map.keys()).index(source_ship_to_label) if source_ship_to_label in ship_to_map else 0,
            key=ship_to_widget_key
        )
        common_ship_to_row = ship_to_map[common_ship_to_label]
        common_ship_to_id = int(common_ship_to_row["id"])
    else:
        common_ship_to_row = {}
        common_ship_to_id = None
        st.warning("No active Ship To Master is available.")

common_row2 = st.columns(4)
with common_row2[0]:
    if term_widget_key in st.session_state and st.session_state.get(term_widget_key) not in term_map:
        del st.session_state[term_widget_key]
    common_term_label = st.selectbox(
        "Payment Term",
        list(term_map.keys()),
        index=list(term_map.keys()).index(source_term_label),
        key=term_widget_key
    )
    common_term_row = term_map[common_term_label]
with common_row2[1]:
    common_due_date = st.date_input(
        "Payment Due Date",
        value=parse_date_for_input(common_header_source.get("payment_due_date")),
        key=f"edit_common_due_date_{common_key_suffix}"
    )
with common_row2[2]:
    common_vehicle = st.text_input(
        "Vehicle Number",
        common_header_source.get("vehicle_number") or "",
        key=f"edit_common_vehicle_{common_key_suffix}"
    )
with common_row2[3]:
    common_ship_via = st.text_input(
        "Ship Via",
        common_header_source.get("ship_via") or "Road",
        key=f"edit_common_ship_via_{common_key_suffix}"
    )

common_row3 = st.columns(4)
with common_row3[0]:
    common_asn_no = st.text_input(
        "ASN Number",
        common_header_source.get("asn_number") or "",
        key=f"edit_common_asn_no_{common_key_suffix}"
    )
with common_row3[1]:
    common_asn_date = st.date_input(
        "ASN Date",
        value=parse_date_for_input(common_header_source.get("asn_date") or common_header_source.get("delivery_date")),
        key=f"edit_common_asn_date_{common_key_suffix}"
    )
with common_row3[2]:
    common_packaging = st.text_input(
        "Packaging Details",
        common_header_source.get("packaging_details") or "",
        key=f"edit_common_packaging_{common_key_suffix}"
    )
with common_row3[3]:
    common_remarks = st.text_input(
        "Remarks",
        common_header_source.get("packaging_remark") or "",
        key=f"edit_common_remarks_{common_key_suffix}"
    )

common_attachment_path = str(common_header_source.get("attachment_path") or "").strip()
attachment_cols = st.columns([1.4, 2.6])
with attachment_cols[0]:
    st.text_input(
        "Current Delivery Attachment",
        value=Path(common_attachment_path).name if common_attachment_path else "No attachment",
        disabled=True,
        key=f"edit_common_current_attachment_{common_key_suffix}"
    )
with attachment_cols[1]:
    common_attachment = st.file_uploader(
        "Replace / Attach Delivery File",
        key=f"edit_common_attachment_{common_key_suffix}"
    )

bill_to_address = str(common_bill_to_row.get("address") or "").strip() or "-"
ship_to_address = "\n".join([
    str(common_ship_to_row.get("addressline1") or "").strip(),
    str(common_ship_to_row.get("addressline2") or "").strip(),
    str(common_ship_to_row.get("addressline3") or "").strip(),
]).strip() or "-"
address_cols = st.columns(2)
with address_cols[0]:
    st.markdown(f"**Bill To Address — Customer Master**  \n{html.escape(bill_to_address).replace(chr(10), '<br>')}", unsafe_allow_html=True)
with address_cols[1]:
    st.markdown(f"**Ship To Address — Ship To Master**  \n{html.escape(ship_to_address).replace(chr(10), '<br>')}", unsafe_allow_html=True)


def _validate_common_header():
    if not str(common_invoice_no or "").strip():
        return "Delivery Invoice Number is mandatory."
    if not common_customer_id:
        return "Customer / Bill To is mandatory."
    if not str(common_bill_to_row.get("address") or "").strip():
        return "The selected Customer has no Bill To Address. Complete Customer Master before saving."
    if not common_bill_to_row.get("ship_to_master_id"):
        return "The selected Customer has no required Ship To link in Customer Master."
    if not common_ship_to_id:
        return "Ship To is mandatory. Select a Ship To Master before saving."
    if common_ship_to_row.get("is_active") is False:
        return "The selected Ship To is inactive. Select an active Ship To before saving."
    if not str(common_ship_to_row.get("addressline1") or "").strip():
        return "The selected Ship To has no Address Line 1. Complete Ship To Master before saving."
    if common_invoice_no.strip() != selected_delivery_invoice_no:
        existing = fetch_all(
            "SELECT id FROM customer_deliveries WHERE delivery_invoice_no=? LIMIT 1",
            (common_invoice_no.strip(),)
        )
        if existing:
            return f"Delivery Invoice {common_invoice_no.strip()} already exists. Use a unique invoice number."
    return ""


def _apply_common_header_to_entire_invoice():
    updated_attachment_path = common_attachment_path or None
    if common_attachment is not None:
        updated_attachment_path = save_upload(
            common_attachment,
            f"delivery_{common_invoice_no.strip() or selected_delivery_invoice_no}_header"
        )

    execute_query("""
        UPDATE customer_deliveries
        SET delivery_invoice_no=?, delivery_date=?, customer_id=?, ship_to_master_id=?,
            payment_term_id=?, payment_terms_days=?, payment_due_date=?, vehicle_number=?,
            ship_via=?, asn_number=?, asn_date=?, packaging_details=?, packaging_remark=?,
            attachment_path=?
        WHERE delivery_invoice_no=?
    """, (
        common_invoice_no.strip(), str(common_delivery_date), common_customer_id, common_ship_to_id,
        common_term_row.get("id"), common_term_row.get("days"), str(common_due_date),
        common_vehicle.strip(), common_ship_via.strip() or "Road", common_asn_no.strip(),
        str(common_asn_date), common_packaging.strip(), common_remarks.strip(),
        updated_attachment_path, selected_delivery_invoice_no
    ))
    return updated_attachment_path


if st.button(
    "SAVE - Update Complete Header for All Invoice Rows",
    type="primary",
    key=f"save_complete_delivery_header_{common_key_suffix}",
    width='stretch'
):
    header_error = _validate_common_header()
    if header_error:
        st.error(header_error)
    else:
        _apply_common_header_to_entire_invoice()
        st.session_state["edit_delivery_last_print_invoice_no"] = common_invoice_no.strip()
        st.session_state.pop("edit_delivery_invoice_header_by_date", None)
        clear_cache_after_write()
        rerun_with_success("Complete Delivery Invoice header updated for all pallet rows.")

rows = fetch_delivery_invoice_rows(selected_delivery_invoice_no, selected_product_id=selected_product_id)
if not rows:
    st.warning("No line rows found for selected delivery invoice and part filter.")
else:
    st.divider()
    st.subheader("Edit Existing Pallet Rows")
    st.caption("Select one or multiple delivery rows. Pallet rows are edited in row format. Common header fields are not repeated.")

    display_rows = []
    for r in rows:
        display_rows.append({
            "delivery_id": r.get("id"),
            "pallet_no": r.get("pallet_no"),
            "box_no": r.get("box_no") or "-",
            "product_code": r.get("product_code"),
            "product_name": r.get("product_name"),
            "delivered_qty": r.get("delivered_qty"),
            "unit_price": r.get("unit_price"),
            "currency": r.get("currency"),
            "sale_amount": r.get("sale_amount"),
        })
    st.dataframe(pd.DataFrame(display_rows), width='stretch', hide_index=True)

    row_map = {
        f"{r['id']} | Pallet {r.get('pallet_no')} | Box {r.get('box_no') or '-'} | {r.get('product_code')} | Qty {r.get('delivered_qty')}": r
        for r in rows
    }
    selected_row_keys = st.multiselect(
        "Select Delivery Rows to Edit",
        list(row_map.keys()),
        default=list(row_map.keys())[:1],
        key="edit_delivery_multirow_select"
    )
    selected_rows = [row_map[k] for k in selected_row_keys]

    update_payload = []
    if selected_rows:
        st.markdown("**Pallet Row Edit Grid**")
        hdr = st.columns([2.9, 1.7, 1.1, 1.0, 0.9, 1.0])
        for col, label in zip(hdr, ["Pallet / Box", "Product", "Quantity", "Price", "Currency", "Amount"]):
            with col:
                st.markdown(f"**{label}**")

        for idx, ed in enumerate(selected_rows):
            edit_suffix = str(ed.get("id"))
            available_for_change = fetch_available_pallets_for_edit(
                selected_ship_id=ed.get("shipment_id"),
                selected_product_id=ed.get("product_id"),
                include_box_id=ed.get("box_id")
            )
            pallet_options = []
            pallet_map = {}
            for p in available_for_change:
                current_flag = " | CURRENT" if int(p.get("id")) == int(ed.get("box_id")) else ""
                label = (
                    f"BoxID {p.get('id')} | Pallet {p.get('pallet_no')} | Box {p.get('box_no') or '-'} | "
                    f"{p.get('product_code')} | Bal {float(p.get('balance_qty') or 0):,.2f}{current_flag}"
                )
                pallet_options.append(label)
                pallet_map[label] = p

            current_option = next((x for x in pallet_options if " | CURRENT" in x), pallet_options[0] if pallet_options else None)
            if pallet_options:
                selected_pallet_label = st.selectbox(
                    "Linked Pallet / Box",
                    pallet_options,
                    index=pallet_options.index(current_option) if current_option in pallet_options else 0,
                    key=f"edit_row_pallet_{edit_suffix}",
                    label_visibility="collapsed"
                )
                selected_pallet = pallet_map[selected_pallet_label]
            else:
                selected_pallet = None

            max_qty = float((selected_pallet or {}).get("balance_qty") or 0) + (
                float(ed.get("delivered_qty") or 0)
                if selected_pallet and int(selected_pallet.get("id")) == int(ed.get("box_id"))
                else 0
            )

            row_cols = st.columns([2.9, 1.7, 1.1, 1.0, 0.9, 1.0])
            with row_cols[0]:
                # Re-render selectbox in the row column by moving the widget into this position.
                # Streamlit keeps the widget above if rendered earlier, so use a disabled text fallback when needed.
                if selected_pallet:
                    st.caption(f"{selected_pallet.get('pallet_no')} / {selected_pallet.get('box_no') or '-'}")
                else:
                    st.warning("No pallet")
            with row_cols[1]:
                product_text = ed.get("product_code") or (selected_pallet or {}).get("product_code") or ""
                st.text_input("Product", product_text, disabled=True, key=f"edit_row_product_{edit_suffix}", label_visibility="collapsed")
            with row_cols[2]:
                ed_qty = st.number_input(
                    "Quantity",
                    min_value=0.0,
                    max_value=max(max_qty, float(ed.get("delivered_qty") or 0)),
                    value=float(ed.get("delivered_qty") or 0),
                    step=1.0,
                    key=f"edit_row_qty_{edit_suffix}",
                    label_visibility="collapsed"
                )
            with row_cols[3]:
                default_price = float(ed.get("unit_price") or (selected_pallet or {}).get("unit_price") or 0)
                ed_price = st.number_input(
                    "Price",
                    min_value=0.0,
                    value=default_price,
                    step=1.0,
                    key=f"edit_row_price_{edit_suffix}",
                    label_visibility="collapsed"
                )
            with row_cols[4]:
                currency_value = ed.get("currency") or (selected_pallet or {}).get("currency") or "USD"
                ed_currency = st.selectbox(
                    "Currency",
                    CURRENCIES,
                    index=CURRENCIES.index(currency_value) if currency_value in CURRENCIES else 0,
                    key=f"edit_row_currency_{edit_suffix}",
                    label_visibility="collapsed"
                )
            with row_cols[5]:
                ed_amount = float(ed_qty or 0) * float(ed_price or 0)
                st.markdown(f"**{ed_amount:,.2f}**")

            update_payload.append({
                "delivery_id": ed["id"],
                "selected_pallet": selected_pallet,
                "delivered_qty": ed_qty,
                "unit_price": ed_price,
                "currency": ed_currency,
                "sale_amount": ed_amount,
            })

    st.divider()
    st.subheader("Add New Pallet Rows")
    st.caption("Add new pending pallets into the selected Delivery Invoice. Common header fields above will be applied.")

    add_pallet_rows = fetch_available_pallets_for_edit(selected_ship_id=selected_ship_id, selected_product_id=selected_product_id)
    add_payload = []
    if not add_pallet_rows:
        st.info("No pending pallets available to add for selected Part / Delivery Invoice.")
    else:
        add_map = {}
        for p in add_pallet_rows:
            label = (
                f"BoxID {p.get('id')} | Pallet {p.get('pallet_no')} | Box {p.get('box_no') or '-'} | "
                f"{p.get('product_code')} | Original Inv {p.get('original_invoice_no')} | Balance {float(p.get('balance_qty') or 0):,.2f} | Price {p.get('unit_price')} {p.get('currency')}"
            )
            add_map[label] = p
        selected_add_labels = st.multiselect("Select New Pallets to Add", list(add_map.keys()), key="add_pallets_to_delivery_invoice")
        selected_add_rows = [add_map[x] for x in selected_add_labels]

        if selected_add_rows:
            hdr2 = st.columns([2.9, 1.7, 1.1, 1.0, 0.9, 1.0])
            for col, label in zip(hdr2, ["Pallet / Box", "Product", "Quantity", "Price", "Currency", "Amount"]):
                with col:
                    st.markdown(f"**{label}**")

        for i, p in enumerate(selected_add_rows):
            cols = st.columns([2.9, 1.7, 1.1, 1.0, 0.9, 1.0])
            with cols[0]:
                st.caption(f"{p.get('pallet_no')} / {p.get('box_no') or '-'}")
            with cols[1]:
                st.text_input("Product", p.get("product_code") or "", disabled=True, key=f"add_row_product_{p.get('id')}_{i}", label_visibility="collapsed")
            with cols[2]:
                aqty = st.number_input(
                    "Qty",
                    min_value=0.0,
                    max_value=float(p.get("balance_qty") or 0),
                    value=0.0,
                    step=1.0,
                    key=f"add_row_qty_{p.get('id')}_{i}",
                    label_visibility="collapsed"
                )
            with cols[3]:
                aprice = st.number_input(
                    "Price",
                    min_value=0.0,
                    value=float(p.get("unit_price") or 0),
                    step=1.0,
                    key=f"add_row_price_{p.get('id')}_{i}",
                    label_visibility="collapsed"
                )
            with cols[4]:
                add_currency = st.selectbox(
                    "Currency",
                    CURRENCIES,
                    index=CURRENCIES.index(p.get("currency")) if p.get("currency") in CURRENCIES else 0,
                    key=f"add_row_currency_{p.get('id')}_{i}",
                    label_visibility="collapsed"
                )
            with cols[5]:
                amount = float(aqty or 0) * float(aprice or 0)
                st.markdown(f"**{amount:,.2f}**")

            if aqty > 0:
                add_payload.append((p, aqty, aprice, add_currency, amount))

    st.markdown("### Save Delivery Invoice Changes")
    st.warning("Please click the correct SAVE button below after editing or adding pallet rows. Updated PDF will be ready after save.")
    save_col1, save_col2 = st.columns(2)
    with save_col1:
        save_updates = st.button("SAVE - Update Selected Existing Rows", type="primary", key="save_update_existing_delivery_row_grid", width='stretch')
    with save_col2:
        save_new_rows = st.button("SAVE - Add Selected New Pallet Rows", type="primary", key="save_add_new_delivery_row_grid", width='stretch')

    if save_updates:
        if not update_payload:
            st.error("Please select delivery rows to update.")
        else:
            header_error = _validate_common_header()
            if header_error:
                st.error(header_error)
            else:
                ok = True
                for item in update_payload:
                    if not item["selected_pallet"]:
                        ok = False
                        st.error(f"Please select linked pallet for Delivery ID {item['delivery_id']}.")
                if ok:
                    _apply_common_header_to_entire_invoice()
                    for item in update_payload:
                        selected_pallet = item["selected_pallet"]
                        execute_query("""
                            UPDATE customer_deliveries
                            SET shipment_id=?, box_id=?, delivered_qty=?, unit_price=?, currency=?,
                                sale_amount=?, po_number=?, po_date=?
                            WHERE id=?
                        """, (
                            selected_pallet["shipment_id"], selected_pallet["id"],
                            item["delivered_qty"], item["unit_price"], item["currency"],
                            item["sale_amount"], selected_pallet.get("po_number", ""),
                            selected_pallet.get("po_date"), item["delivery_id"]
                        ))
                    st.session_state["edit_delivery_last_print_invoice_no"] = common_invoice_no.strip()
                    st.session_state.pop("edit_delivery_invoice_header_by_date", None)
                    clear_cache_after_write()
                    rerun_with_success("Complete header and selected delivery rows updated successfully. PDF is ready.")

    if save_new_rows:
        if not add_payload:
            st.error("Select new pallet rows and enter quantity.")
        else:
            header_error = _validate_common_header()
            if header_error:
                st.error(header_error)
            else:
                updated_header_attachment_path = _apply_common_header_to_entire_invoice()
                for p, qty, price, currency, amount in add_payload:
                    execute_query("""
                        INSERT INTO customer_deliveries
                        (shipment_id, box_id, customer_id, ship_to_master_id, delivery_date, delivered_qty,
                         delivery_invoice_no, vehicle_number, asn_number, asn_date, packaging_details,
                         packaging_remark, ship_via, payment_term_id, payment_terms_days, payment_due_date,
                         unit_price, currency, sale_amount, attachment_path, po_number, po_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        p["shipment_id"], p["id"], common_customer_id, common_ship_to_id,
                        str(common_delivery_date), qty, common_invoice_no.strip(), common_vehicle.strip(),
                        common_asn_no.strip(), str(common_asn_date), common_packaging.strip(),
                        common_remarks.strip(), common_ship_via.strip() or "Road",
                        common_term_row.get("id"), common_term_row.get("days"), str(common_due_date),
                        price, currency, amount, updated_header_attachment_path, p.get("po_number", ""), p.get("po_date", None)
                    ))
                st.session_state["edit_delivery_last_print_invoice_no"] = common_invoice_no.strip()
                st.session_state.pop("edit_delivery_invoice_header_by_date", None)
                clear_cache_after_write()
                rerun_with_success("Complete header updated and selected new pallet rows added successfully. PDF is ready.")



st.divider()
st.subheader("Delete Delivery Invoice")
st.warning("Super Admin only. This will delete all delivery rows for the selected Delivery Invoice. Shipment and pallet records will remain available for future delivery.")
if st.session_state.get("user", {}).get("role") == "super_admin":
    del_c1, del_c2 = st.columns([2, 1])
    with del_c1:
        delete_confirm = st.checkbox(
            f"I confirm to delete Delivery Invoice {selected_delivery_invoice_no}",
            key=f"delete_delivery_confirm_{selected_delivery_invoice_no}"
        )
    with del_c2:
        delete_password = st.text_input(
            "Password",
            type="password",
            key=f"delete_delivery_password_{selected_delivery_invoice_no}"
        )
    if st.button(
        "DELETE SELECTED DELIVERY INVOICE",
        type="secondary",
        key=f"delete_delivery_invoice_{selected_delivery_invoice_no}",
        width='stretch'
    ):
        if not delete_confirm:
            st.error("Please tick confirmation before deleting.")
        elif not check_delete_password(delete_password):
            st.error("Wrong password. Delete cancelled.")
        else:
            try:
                execute_query(
                    "INSERT INTO delete_audit_log (table_name, record_id, deleted_by, details) VALUES (?, ?, ?, ?)",
                    ("customer_deliveries", 0, st.session_state.user.get("username", ""), f"Deleted Delivery Invoice {selected_delivery_invoice_no}")
                )
            except Exception:
                pass
            execute_query("DELETE FROM customer_deliveries WHERE delivery_invoice_no=?", (selected_delivery_invoice_no,))
            set_success_message(f"Delivery Invoice {selected_delivery_invoice_no} deleted successfully.")
            clear_cache_after_write()
            st.rerun()
else:
    st.info("Delivery Invoice delete is available only for Super Admin.")

render_slogan_footer()
