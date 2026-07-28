from shipment_common import *

page_setup()
require_page_view('shipment_last')
show_edit_permission_status('shipment_last')
show_header("Last Shipments", "Shipment headers, pallet rows and Shipment Invoice PDF reprint")
access_notice()
render_shipment_subnav('shipment_last')

shipments = fetch_shipment_headers(limit=500)
if not shipments:
    st.info("No shipments available as per your product/warehouse access.")
    render_slogan_footer()
    st.stop()

ship_map = {
    f"{s['id']} | {s['shipment_no']} | Invoice {s['invoice_no']} | {s.get('warehouse_name') or ''}": s
    for s in shipments
}
selected_keys = st.multiselect(
    "Select one or multiple Shipment Invoices",
    list(ship_map.keys()),
    default=list(ship_map.keys())[:1],
    key="last_shipments_multi_select"
)
selected_shipments = [ship_map[k] for k in selected_keys if k in ship_map]

if not selected_shipments:
    st.info("Select at least one Shipment Invoice.")
    render_slogan_footer()
    st.stop()

st.subheader("Selected Shipment Headers")
st.dataframe(pd.DataFrame(format_date_columns(selected_shipments)), width='stretch', hide_index=True)

all_rows = []
for selected_shipment in selected_shipments:
    rows = fetch_shipment_pallet_rows(selected_shipment["id"])
    for r in rows or []:
        rr = dict(r)
        rr["selected_shipment_no"] = selected_shipment.get("shipment_no")
        rr["selected_invoice_no"] = selected_shipment.get("invoice_no")
        all_rows.append(rr)

st.subheader("Pallet / Product Rows")
if all_rows:
    df = pd.DataFrame(format_date_columns(all_rows))
    st.dataframe(style_total_row(df), width='stretch', hide_index=True)
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
st.warning(
    "Super Admin only. This will delete selected shipment invoice(s), shipment pallet rows, related delivery rows and related payment receipts. "
    "Use only for wrong/duplicate shipment invoice entries."
)
selected_shipment_ids = [int(s.get("id")) for s in selected_shipments if s.get("id") is not None]
selected_shipment_invoice_labels = [
    f"{s.get('invoice_no') or '-'} / {s.get('shipment_no') or '-'}"
    for s in selected_shipments
]
if st.session_state.get("user", {}).get("role") == "super_admin":
    del_c1, del_c2 = st.columns([2, 1])
    with del_c1:
        delete_confirm = st.checkbox(
            f"I confirm to delete {len(selected_shipment_ids)} selected Shipment Invoice(s)",
            key="bulk_delete_shipment_invoice_confirm"
        )
    with del_c2:
        delete_password = st.text_input(
            "Password",
            type="password",
            key="bulk_delete_shipment_invoice_password"
        )

    if st.button(
        "DELETE SELECTED SHIPMENT INVOICES",
        type="secondary",
        key="bulk_delete_shipment_invoices",
        width='stretch'
    ):
        if not selected_shipment_ids:
            st.error("Please select at least one Shipment Invoice.")
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
                    (
                        "shipments",
                        0,
                        st.session_state.user.get("username", ""),
                        "Bulk deleted Shipment Invoices: " + ", ".join(selected_shipment_invoice_labels),
                    ),
                )
            except Exception:
                pass

            # Delete child records first to avoid FK/linked-record errors.
            execute_query(
                f"""
                DELETE FROM payments
                WHERE delivery_id IN (
                    SELECT id FROM customer_deliveries
                    WHERE shipment_id IN ({placeholders})
                )
                """,
                params,
            )
            execute_query(
                f"DELETE FROM customer_deliveries WHERE shipment_id IN ({placeholders})",
                params,
            )
            execute_query(
                f"DELETE FROM shipment_boxes WHERE shipment_id IN ({placeholders})",
                params,
            )
            execute_query(
                f"DELETE FROM shipments WHERE id IN ({placeholders})",
                params,
            )
            set_success_message(f"Deleted {len(selected_shipment_ids)} Shipment Invoice(s) successfully.")
            clear_cache_after_write()
            st.rerun()
else:
    st.info("Bulk Shipment Invoice delete is available only for Super Admin.")


render_slogan_footer()
