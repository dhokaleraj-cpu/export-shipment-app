from delivery_common import *

page_setup()
require_page_view('delivery_edit')
show_edit_permission_status('delivery_edit')
ensure_delivery_columns()

show_header("Edit Delivery Invoice", "Edit pallet rows in row format, add pallets and print PDF")
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

# Common invoice/header fields, used by all selected rows and new rows.
st.divider()
st.subheader("Common Delivery Invoice Header Fields")
st.info("After changing pallet rows, use the SAVE buttons at the bottom of this page. PDF print/download will appear after save.")
st.caption("These common fields will be applied to all selected pallet rows and any new pallet rows added below.")

common_c1, common_c2, common_c3, common_c4 = st.columns(4)
with common_c1:
    common_invoice_no = st.text_input("Delivery Invoice No", selected_header.get("delivery_invoice_no") or "", key="edit_common_delivery_invoice_no")
    common_delivery_date = st.text_input("Delivery Date YYYY-MM-DD", str(selected_header.get("delivery_date") or ""), key="edit_common_delivery_date")
with common_c2:
    common_due_date = st.text_input("Payment Due Date YYYY-MM-DD", str(selected_header.get("payment_due_date") or ""), key="edit_common_due_date")
    common_vehicle = st.text_input("Vehicle Number", selected_header.get("vehicle_number") or "", key="edit_common_vehicle")
with common_c3:
    common_asn_no = st.text_input("ASN Number", selected_header.get("asn_number") or "", key="edit_common_asn_no")
    common_asn_date = st.text_input("ASN Date YYYY-MM-DD", str(selected_header.get("asn_date") or ""), key="edit_common_asn_date")
with common_c4:
    common_packaging = st.text_input("Packaging Details", selected_header.get("packaging_details") or "", key="edit_common_packaging")
    common_remarks = st.text_input("Remarks", selected_header.get("packaging_remark") or "", key="edit_common_remarks")

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
    st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)

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
                f"{p.get('product_code')} | Original Inv {p.get('invoice_no')} | Balance {float(p.get('balance_qty') or 0):,.2f} | Price {p.get('unit_price')} {p.get('currency')}"
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
        save_updates = st.button("SAVE - Update Selected Existing Rows", type="primary", key="save_update_existing_delivery_row_grid", use_container_width=True)
    with save_col2:
        save_new_rows = st.button("SAVE - Add Selected New Pallet Rows", type="primary", key="save_add_new_delivery_row_grid", use_container_width=True)

    if save_updates:
        if not update_payload:
            st.error("Please select delivery rows to update.")
        else:
            ok = True
            for item in update_payload:
                selected_pallet = item["selected_pallet"]
                if not selected_pallet:
                    ok = False
                    st.error(f"Please select linked pallet for Delivery ID {item['delivery_id']}.")
                    continue
                execute_query("""
                    UPDATE customer_deliveries
                    SET shipment_id=?,
                        box_id=?,
                        delivery_invoice_no=?,
                        delivery_date=?,
                        delivered_qty=?,
                        unit_price=?,
                        currency=?,
                        sale_amount=?,
                        payment_due_date=?,
                        vehicle_number=?,
                        asn_number=?,
                        asn_date=?,
                        packaging_details=?,
                        packaging_remark=?
                    WHERE id=?
                """, (
                    selected_pallet["shipment_id"],
                    selected_pallet["id"],
                    common_invoice_no.strip(),
                    common_delivery_date.strip(),
                    item["delivered_qty"],
                    item["unit_price"],
                    item["currency"],
                    item["sale_amount"],
                    common_due_date.strip(),
                    common_vehicle.strip(),
                    common_asn_no.strip(),
                    common_asn_date.strip() or None,
                    common_packaging.strip(),
                    common_remarks.strip(),
                    item["delivery_id"],
                ))
            if ok:
                st.session_state["edit_delivery_last_print_invoice_no"] = common_invoice_no.strip()
                set_success_message("Selected delivery rows updated successfully. PDF is ready for print/download.")
                clear_cache_after_write()
                st.rerun()

    if save_new_rows:
        if not add_payload:
            st.error("Select new pallet rows and enter quantity.")
        else:
            for p, qty, price, currency, amount in add_payload:
                execute_query("""
                    INSERT INTO customer_deliveries
                    (shipment_id, box_id, customer_id, ship_to_master_id, delivery_date, delivered_qty, delivery_invoice_no,
                     vehicle_number, asn_number, asn_date, packaging_details, packaging_remark,
                     payment_term_id, payment_terms_days, payment_due_date, unit_price, currency, sale_amount, attachment_path, po_number, po_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    p["shipment_id"],
                    p["id"],
                    selected_header.get("customer_id"),
                    selected_header.get("ship_to_master_id"),
                    common_delivery_date.strip(),
                    qty,
                    common_invoice_no.strip(),
                    common_vehicle.strip(),
                    common_asn_no.strip(),
                    common_asn_date.strip() or None,
                    common_packaging.strip(),
                    common_remarks.strip(),
                    selected_header.get("payment_term_id"),
                    selected_header.get("payment_terms_days"),
                    common_due_date.strip(),
                    price,
                    currency,
                    amount,
                    None,
                    p.get("po_number", ""),
                    p.get("po_date", None),
                ))
            st.session_state["edit_delivery_last_print_invoice_no"] = common_invoice_no.strip()
            set_success_message("Selected new pallet rows added successfully. PDF is ready for print/download.")
            clear_cache_after_write()
            st.rerun()

render_slogan_footer()
