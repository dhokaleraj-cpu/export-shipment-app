from delivery_common import *

page_setup()
require_page_view("delivery_list")
show_edit_permission_status("delivery_list")
show_header("Delivery Invoice List", "Select invoices by checkbox and delete with password")
access_notice()
render_delivery_subnav("delivery_list")

selected_product_id, selected_part_label, _part_rows = delivery_part_selectbox(
    key="delivery_list_part",
    label="Part Number"
)

c1, c2, c3, c4 = st.columns(4)
with c1:
    date_from = st.date_input("Delivery From", value=date(date.today().year, 1, 1), key="delivery_list_from")
with c2:
    date_to = st.date_input("Delivery To", value=date.today(), key="delivery_list_to")
with c3:
    original_invoice_search = st.text_input("Original Invoice Number", key="delivery_list_original_invoice")
with c4:
    delivery_invoice_search = st.text_input("Delivery Invoice Number", key="delivery_list_delivery_invoice")

rows = fetch_delivery_invoice_headers_for_edit(selected_product_id=selected_product_id, date_from=date_from, date_to=date_to)
filtered = []
for r in rows:
    if original_invoice_search and original_invoice_search.lower() not in str(r.get("original_invoice_no") or "").lower():
        continue
    if delivery_invoice_search and delivery_invoice_search.lower() not in str(r.get("delivery_invoice_no") or "").lower():
        continue
    filtered.append(r)

if not filtered:
    st.info("No delivery invoices found for selected filters.")
    render_slogan_footer()
    st.stop()

df_source = pd.DataFrame(format_date_columns(filtered))
if "Select" not in df_source.columns:
    df_source.insert(0, "Select", False)

edited_df = st.data_editor(
    df_source,
    use_container_width=True,
    hide_index=True,
    key="delivery_invoice_checkbox_grid",
    column_config={
        "Select": st.column_config.CheckboxColumn("Select", help="Tick invoices to view/delete together", default=False)
    },
    disabled=[c for c in df_source.columns if c != "Select"],
)

selected_df = edited_df[edited_df["Select"] == True] if "Select" in edited_df.columns else pd.DataFrame()
selected_invoices = selected_df["delivery_invoice_no"].dropna().astype(str).tolist() if not selected_df.empty and "delivery_invoice_no" in selected_df.columns else []

st.info(f"Selected Delivery Invoices: {len(selected_invoices)}")
export_buttons(edited_df.drop(columns=["Select"], errors="ignore"), "delivery_invoice_list")

if selected_invoices:
    st.subheader("Selected Delivery Invoice Line Details")
    all_lines = []
    for inv_no in selected_invoices:
        inv_header, line_items = get_saved_delivery_invoice_for_pdf(inv_no)
        for line in line_items or []:
            row = dict(line)
            row["selected_delivery_invoice_no"] = inv_no
            all_lines.append(row)
    if all_lines:
        line_df = pd.DataFrame(format_date_columns(all_lines))
        st.dataframe(line_df, use_container_width=True, hide_index=True)
        export_buttons(line_df, "selected_delivery_invoice_lines")
    else:
        st.info("No line details found for selected delivery invoices.")

st.divider()
st.subheader("Delete Selected Delivery Invoices")
st.warning("Super Admin only. Tick invoices in the table above, confirm, enter password, then delete. Shipment and pallet stock will remain available.")

if st.session_state.get("user", {}).get("role") == "super_admin":
    del_c1, del_c2 = st.columns([2, 1])
    with del_c1:
        delete_confirm = st.checkbox(
            f"I confirm to delete {len(selected_invoices)} selected Delivery Invoice(s)",
            key="delivery_invoice_checkbox_delete_confirm"
        )
    with del_c2:
        delete_password = st.text_input("Password", type="password", key="delivery_invoice_checkbox_delete_password")
    if st.button("DELETE SELECTED DELIVERY INVOICES", type="secondary", key="delivery_invoice_checkbox_delete_button", use_container_width=True):
        if not selected_invoices:
            st.error("Please tick at least one Delivery Invoice in the table.")
        elif not delete_confirm:
            st.error("Please tick confirmation before deleting.")
        elif not check_delete_password(delete_password):
            st.error("Wrong password. Delete cancelled.")
        else:
            placeholders = ",".join(["?"] * len(selected_invoices))
            try:
                execute_query(
                    "INSERT INTO delete_audit_log (table_name, record_id, deleted_by, details) VALUES (?, ?, ?, ?)",
                    ("customer_deliveries", 0, st.session_state.user.get("username", ""), "Deleted selected Delivery Invoices: " + ", ".join(selected_invoices)),
                )
            except Exception:
                pass
            execute_query(f"DELETE FROM customer_deliveries WHERE delivery_invoice_no IN ({placeholders})", tuple(selected_invoices))
            set_success_message(f"Deleted {len(selected_invoices)} Delivery Invoice(s) successfully.")
            clear_cache_after_write()
            st.rerun()
else:
    st.info("Delete selected Delivery Invoices is available only for Super Admin.")

render_slogan_footer()
