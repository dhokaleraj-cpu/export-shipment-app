from shipment_common import *

page_setup()
require_page_view('shipment_edit')
show_edit_permission_status('shipment_edit')
show_header("Edit Shipment", "Edit shipment header and pallet/product rows")
access_notice()
render_shipment_subnav('shipment_edit')

# PDF print/download area after save.
last_print_shipment_id = st.session_state.get("edit_shipment_last_print_id")
if last_print_shipment_id:
    try:
        saved_ship_rows = [s for s in fetch_shipment_headers(limit=1000) if int(s.get("id")) == int(last_print_shipment_id)]
        if saved_ship_rows:
            saved_shipment = saved_ship_rows[0]
            saved_rows = fetch_shipment_pallet_rows(saved_shipment["id"])
            if saved_rows:
                shipment_invoice_pdf = shipment_invoice_pdf_bytes(saved_shipment, saved_rows)
                st.success(f"Saved successfully. Shipment Invoice PDF is ready for: {saved_shipment.get('invoice_no') or saved_shipment.get('shipment_no')}")
                st.download_button(
                    "Print / Download Updated Shipment Invoice PDF",
                    shipment_invoice_pdf,
                    file_name=f"shipment_invoice_{saved_shipment.get('invoice_no') or saved_shipment.get('shipment_no')}.pdf",
                    mime="application/pdf",
                    key=f"download_updated_shipment_invoice_{saved_shipment.get('id')}"
                )
                shipment_details_pdf = shipment_pdf_bytes(saved_shipment, saved_rows)
                st.download_button(
                    "Print / Download Updated Shipment Details PDF",
                    shipment_details_pdf,
                    file_name=f"shipment_details_{saved_shipment.get('shipment_no')}.pdf",
                    mime="application/pdf",
                    key=f"download_updated_shipment_details_{saved_shipment.get('id')}"
                )
    except Exception as print_err:
        st.warning(f"Saved successfully, but PDF print could not be prepared: {print_err}")

if not current_user_can_edit("shipment_edit"):
    st.error("You have View permission but not Edit permission for Edit Shipment page. Contact Super Admin.")
    st.stop()

st.subheader("Edit Shipment Header")
st.info("Use the SAVE buttons below. Shipment Invoice PDF print/download will appear after save.")
shipments = fetch_shipment_headers(limit=500)
if not shipments:
    st.info("No shipments available for edit.")
else:
    ship_map = {f"{s['id']} | {s['shipment_no']} | Invoice {s['invoice_no']}": s for s in shipments}
    selected_ship_key = searchable_selectbox("Select Shipment to Edit", list(ship_map.keys()), key="edit_shipment_page_select")
    selected_ship = ship_map[selected_ship_key]
    selected_ship_id = selected_ship["id"]

    current_rows_for_pdf = fetch_shipment_pallet_rows(selected_ship_id)
    if current_rows_for_pdf:
        current_invoice_pdf = shipment_invoice_pdf_bytes(selected_ship, current_rows_for_pdf)
        st.download_button(
            "Print / Download Current Shipment Invoice PDF",
            current_invoice_pdf,
            file_name=f"shipment_invoice_{selected_ship.get('invoice_no') or selected_ship.get('shipment_no')}.pdf",
            mime="application/pdf",
            key=f"current_shipment_invoice_pdf_{selected_ship_id}"
        )

    suppliers = fetch_all("SELECT * FROM suppliers ORDER BY supplier_name")
    warehouses = filter_warehouse_rows_for_current_user(fetch_all("SELECT * FROM warehouses ORDER BY warehouse_name"))
    customers = fetch_all("SELECT * FROM customers ORDER BY customer_name")
    ship_to_rows = fetch_all("SELECT * FROM ship_to_masters WHERE COALESCE(is_active, TRUE)=TRUE ORDER BY ship_to_name, ship_to_id")

    supplier_names = [x["supplier_name"] for x in suppliers]
    warehouse_names = [x["warehouse_name"] for x in warehouses]
    customer_names = [x["customer_name"] for x in customers]
    ship_to_labels = [f"{x['ship_to_name']} | {x.get('ship_to_id') or '-'}" for x in ship_to_rows]
    supplier_id_map = {x["supplier_name"]: x["id"] for x in suppliers}
    warehouse_id_map = {x["warehouse_name"]: x["id"] for x in warehouses}
    customer_id_map = {x["customer_name"]: x["id"] for x in customers}
    ship_to_id_map = {f"{x['ship_to_name']} | {x.get('ship_to_id') or '-'}": x["id"] for x in ship_to_rows}

    suffix = str(selected_ship_id)
    h1, h2 = st.columns(2)
    with h1:
        edit_shipment_no = st.text_input("Edit Shipment Number", selected_ship.get("shipment_no") or "", key=f"edit_ship_no_{suffix}")
        edit_invoice_no = st.text_input("Edit Original Invoice Number", selected_ship.get("invoice_no") or "", key=f"edit_inv_no_{suffix}")
        edit_shipment_date = st.text_input("Edit Shipment Date YYYY-MM-DD", str(selected_ship.get("shipment_date") or ""), key=f"edit_ship_date_{suffix}")
    with h2:
        current_supplier = selected_ship.get("supplier_name") if selected_ship.get("supplier_name") in supplier_names else supplier_names[0] if supplier_names else ""
        current_warehouse = selected_ship.get("warehouse_name") if selected_ship.get("warehouse_name") in warehouse_names else warehouse_names[0] if warehouse_names else ""
        edit_supplier = st.selectbox("Edit Supplier", supplier_names, index=supplier_names.index(current_supplier) if current_supplier in supplier_names else 0, key=f"edit_supplier_{suffix}")
        edit_warehouse = st.selectbox("Edit Warehouse", warehouse_names, index=warehouse_names.index(current_warehouse) if current_warehouse in warehouse_names else 0, key=f"edit_warehouse_{suffix}")
        current_customer = selected_ship.get("customer_name") if selected_ship.get("customer_name") in customer_names else customer_names[0] if customer_names else ""
        edit_customer = st.selectbox("Edit Customer", customer_names, index=customer_names.index(current_customer) if current_customer in customer_names else 0, key=f"edit_customer_{suffix}")
        current_ship_to = ship_to_labels[0] if ship_to_labels else ""
        edit_ship_to = st.selectbox("Edit Ship To", ship_to_labels, index=ship_to_labels.index(current_ship_to) if current_ship_to in ship_to_labels else 0, key=f"edit_ship_to_{suffix}")

    if st.button("SAVE - Update Shipment Header & Prepare PDF", type="primary", key=f"save_update_ship_header_{suffix}", use_container_width=True):
        execute_query("""
            UPDATE shipments
            SET shipment_no=?, invoice_no=?, shipment_date=?, supplier_id=?, warehouse_id=?, customer_id=?, ship_to_master_id=?
            WHERE id=?
        """, (
            edit_shipment_no.strip(),
            edit_invoice_no.strip(),
            edit_shipment_date.strip(),
            supplier_id_map.get(edit_supplier),
            warehouse_id_map.get(edit_warehouse),
            customer_id_map.get(edit_customer),
            ship_to_id_map.get(edit_ship_to),
            selected_ship_id,
        ))
        st.session_state["edit_shipment_last_print_id"] = selected_ship_id
        set_success_message("Shipment header updated successfully. PDF is ready for print/download.")
        clear_cache_after_write()
        st.rerun()

    st.divider()
    st.subheader("Edit Pallet / Product Row")
    rows = fetch_shipment_pallet_rows(selected_ship_id)
    if rows:
        row_map = {f"{r['id']} | Pallet {r['pallet_no']} | {r['product_code']} | Qty {r['original_qty']}": r for r in rows}
        selected_row_key = searchable_selectbox("Select Pallet/Product Row", list(row_map.keys()), key="edit_shipment_pallet_row")
        selected_row = row_map[selected_row_key]
        rs = str(selected_row["id"])
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            fifo_id = st.number_input("FIFO ID", min_value=1, value=int(selected_row.get("fifo_row_id") or selected_row.get("id") or 1), step=1, key=f"edit_fifo_{rs}")
            pallet_no = st.text_input("Pallet No", selected_row.get("pallet_no") or "", key=f"edit_pallet_{rs}")
        with c2:
            box_no = st.text_input("Box No", selected_row.get("box_no") or "", key=f"edit_box_{rs}")
            po_number = st.text_input("PO Number", selected_row.get("po_number") or "", key=f"edit_po_{rs}")
        with c3:
            po_date = st.text_input("PO Date YYYY-MM-DD", str(selected_row.get("po_date") or ""), key=f"edit_po_date_{rs}")
            qty = st.number_input("Quantity", min_value=0.0, value=float(selected_row.get("original_qty") or 0), step=1.0, key=f"edit_qty_{rs}")
        with c4:
            price = st.number_input("Price", min_value=0.0, value=float(selected_row.get("unit_price") or 0), step=1.0, key=f"edit_price_{rs}")
            currency = st.selectbox("Currency", CURRENCIES, index=CURRENCIES.index(selected_row.get("currency")) if selected_row.get("currency") in CURRENCIES else 0, key=f"edit_currency_{rs}")
        with c5:
            amount = qty * price
            st.metric("Amount", f"{amount:,.2f} {currency}")

        if st.button("SAVE - Update Pallet / Product Row & Prepare PDF", type="primary", key=f"save_update_pallet_row_{rs}", use_container_width=True):
            execute_query("""
                UPDATE shipment_boxes
                SET fifo_row_id=?, pallet_no=?, box_no=?, po_number=?, po_date=?, original_qty=?, unit_price=?, currency=?, amount=?
                WHERE id=?
            """, (fifo_id, pallet_no.strip(), box_no.strip(), po_number.strip(), po_date.strip() or None, qty, price, currency, amount, selected_row["id"]))
            st.session_state["edit_shipment_last_print_id"] = selected_ship_id
            set_success_message("Pallet / product row updated successfully. PDF is ready for print/download.")
            clear_cache_after_write()
            st.rerun()
    else:
        st.info("No pallet rows available for selected shipment.")

render_slogan_footer()
