from shipment_common import *

page_setup()
require_page_view('shipment_last')
show_edit_permission_status('shipment_last')
show_header("Last Shipments", "Select shipment invoices by checkbox and delete with password")
access_notice()
render_shipment_subnav('shipment_last')

shipments = fetch_shipment_headers(limit=500)
if not shipments:
    st.info("No shipments available as per your product/warehouse access.")
    render_slogan_footer()
    st.stop()

header_df_source = pd.DataFrame(format_date_columns(shipments))
if "Select" not in header_df_source.columns:
    header_df_source.insert(0, "Select", False)

edited_headers = st.data_editor(
    header_df_source,
    use_container_width=True,
    hide_index=True,
    key="shipment_invoice_checkbox_grid",
    column_config={
        "Select": st.column_config.CheckboxColumn("Select", help="Tick shipment invoices to view/delete together", default=False)
    },
    disabled=[c for c in header_df_source.columns if c != "Select"],
)

selected_header_df = edited_headers[edited_headers["Select"] == True] if "Select" in edited_headers.columns else pd.DataFrame()
selected_shipment_ids = selected_header_df["id"].dropna().astype(int).tolist() if not selected_header_df.empty and "id" in selected_header_df.columns else []
selected_shipments = [s for s in shipments if int(s.get("id")) in selected_shipment_ids]

st.info(f"Selected Shipment Invoices: {len(selected_shipments)}")
export_buttons(edited_headers.drop(columns=["Select"], errors="ignore"), "shipment_invoice_list")

if selected_shipments:
    all_rows = []
    for selected_shipment in selected_shipments:
        rows = fetch_shipment_pallet_rows(selected_shipment["id"])
        for r in rows or []:
            rr = dict(r)
            rr["selected_shipment_no"] = selected_shipment.get("shipment_no")
            rr["selected_invoice_no"] = selected_shipment.get("invoice_no")
            all_rows.append(rr)

    st.subheader("Selected Shipment Pallet / Product Rows")
    if all_rows:
        df = pd.DataFrame(format_date_columns(all_rows))
        st.dataframe(style_total_row(df), use_container_width=True, hide_index=True)
        export_buttons(add_total_row(df), "selected_shipment_pallet_rows")
    else:
        st.info("No pallet rows found for selected shipment(s).")

    st.subheader("PDF Reprint")
    for selected_shipment in selected_shipments:
        rows = fetch_shipment_pallet_rows(selected_shipment["id"])
        if not rows:
            continue
        s_id = selected_shipment.get("id")
        pdf_bytes = shipment_pdf_bytes(selected_shipment, rows)
        st.download_button(
            f"Print / Download Shipment Details PDF - {selected_shipment.get('invoice_no') or selected_shipment.get('shipment_no')}",
            pdf_bytes,
            file_name=f"shipment_details_{selected_shipment.get('shipment_no')}.pdf",
            mime="application/pdf",
            key=f"shipment_pdf_print_download_{s_id}"
        )
        shipment_invoice_pdf = shipment_invoice_pdf_bytes(selected_shipment, rows)
        st.download_button(
            f"Reprint Shipment Invoice PDF - {selected_shipment.get('invoice_no') or selected_shipment.get('shipment_no')}",
            shipment_invoice_pdf,
            file_name=f"shipment_invoice_{selected_shipment.get('invoice_no') or selected_shipment.get('shipment_no')}.pdf",
            mime="application/pdf",
            key=f"shipment_invoice_reprint_pdf_download_{s_id}"
        )

st.divider()
st.subheader("Delete Selected Shipment Invoices")
st.warning("Super Admin only. Tick shipment invoices in the table above, confirm, enter password, then delete. This deletes related payments, deliveries, shipment boxes, and shipment headers.")

selected_shipment_invoice_labels = [f"{s.get('invoice_no') or '-'} / {s.get('shipment_no') or '-'}" for s in selected_shipments]

if st.session_state.get("user", {}).get("role") == "super_admin":
    del_c1, del_c2 = st.columns([2, 1])
    with del_c1:
        delete_confirm = st.checkbox(
            f"I confirm to delete {len(selected_shipment_ids)} selected Shipment Invoice(s)",
            key="shipment_invoice_checkbox_delete_confirm"
        )
    with del_c2:
        delete_password = st.text_input("Password", type="password", key="shipment_invoice_checkbox_delete_password")
    if st.button("DELETE SELECTED SHIPMENT INVOICES", type="secondary", key="shipment_invoice_checkbox_delete_button", use_container_width=True):
        if not selected_shipment_ids:
            st.error("Please tick at least one Shipment Invoice in the table.")
        elif not delete_confirm:
            st.error("Please tick confirmation before deleting.")
        elif not check_delete_password(delete_password):
            st.error("Wrong password. Delete cancelled.")
        else:
            placeholders = ",".join(["?"] * len(selected_shipment_ids))
            params = tuple(selected_shipment_ids)
            try:
                execute_query(
                    "INSERT INTO delete_audit_log (table_name, record_id, deleted_by, details) VALUES (?, ?, ?, ?)",
                    ("shipments", 0, st.session_state.user.get("username", ""), "Deleted selected Shipment Invoices: " + ", ".join(selected_shipment_invoice_labels)),
                )
            except Exception:
                pass
            execute_query(f"DELETE FROM payments WHERE delivery_id IN (SELECT id FROM customer_deliveries WHERE shipment_id IN ({placeholders}))", params)
            execute_query(f"DELETE FROM customer_deliveries WHERE shipment_id IN ({placeholders})", params)
            execute_query(f"DELETE FROM shipment_boxes WHERE shipment_id IN ({placeholders})", params)
            execute_query(f"DELETE FROM shipments WHERE id IN ({placeholders})", params)
            set_success_message(f"Deleted {len(selected_shipment_ids)} Shipment Invoice(s) successfully.")
            clear_cache_after_write()
            st.rerun()
else:
    st.info("Delete selected Shipment Invoices is available only for Super Admin.")

render_slogan_footer()
