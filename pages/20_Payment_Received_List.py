from payment_common import *

page_setup()
require_page_view("payment_list")
show_edit_permission_status("payment_list")
show_header("Payment Received List", "Select payment receipts by checkbox and delete with password")
access_notice()
render_payment_subnav("payment_list")

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    part_number = st.text_input("Part Number", key="payment_list_part")
with c2:
    customer = st.text_input("Customer", key="payment_list_customer")
with c3:
    original_invoice_no = st.text_input("Original Invoice Number", key="payment_list_original_invoice")
with c4:
    delivery_invoice_no = st.text_input("Delivery Invoice Number", key="payment_list_delivery_invoice")
with c5:
    row_limit = st.selectbox("Rows", [100, 250, 500, 1000, 2000], index=2, key="payment_list_limit")

rows = fetch_payment_rows(
    limit=row_limit,
    part_number=part_number,
    customer=customer,
    original_invoice_no=original_invoice_no,
    delivery_invoice_no=delivery_invoice_no,
)

if not rows:
    st.info("No payment received records found for selected filters.")
    render_slogan_footer()
    st.stop()

df_source = pd.DataFrame(format_date_columns(rows))
if "Select" not in df_source.columns:
    df_source.insert(0, "Select", False)

edited_df = st.data_editor(
    df_source,
    use_container_width=True,
    hide_index=True,
    key="payment_received_checkbox_grid",
    column_config={
        "Select": st.column_config.CheckboxColumn("Select", help="Tick payment receipts to delete", default=False)
    },
    disabled=[c for c in df_source.columns if c != "Select"],
)

selected_df = edited_df[edited_df["Select"] == True] if "Select" in edited_df.columns else pd.DataFrame()
selected_payment_ids = selected_df["id"].dropna().astype(int).tolist() if not selected_df.empty and "id" in selected_df.columns else []

st.info(f"Selected Payment Receipts: {len(selected_payment_ids)}")
export_buttons(edited_df.drop(columns=["Select"], errors="ignore"), "payment_received_list")

st.divider()
st.subheader("Delete Selected Payment Receipts")
st.warning("Super Admin only. Tick payment receipts in the table above, confirm, enter password, then delete.")

if st.session_state.get("user", {}).get("role") == "super_admin":
    del_c1, del_c2 = st.columns([2, 1])
    with del_c1:
        delete_confirm = st.checkbox(
            f"I confirm to delete {len(selected_payment_ids)} selected Payment Receipt(s)",
            key="payment_received_checkbox_delete_confirm"
        )
    with del_c2:
        delete_password = st.text_input("Password", type="password", key="payment_received_checkbox_delete_password")
    if st.button("DELETE SELECTED PAYMENT RECEIPTS", type="secondary", key="payment_received_checkbox_delete_button", use_container_width=True):
        if not selected_payment_ids:
            st.error("Please tick at least one Payment Receipt in the table.")
        elif not delete_confirm:
            st.error("Please tick confirmation before deleting.")
        elif not check_delete_password(delete_password):
            st.error("Wrong password. Delete cancelled.")
        else:
            placeholders = ",".join(["?"] * len(selected_payment_ids))
            try:
                execute_query(
                    "INSERT INTO delete_audit_log (table_name, record_id, deleted_by, details) VALUES (?, ?, ?, ?)",
                    ("payments", 0, st.session_state.user.get("username", ""), "Deleted selected Payment Receipt IDs: " + ", ".join(map(str, selected_payment_ids))),
                )
            except Exception:
                pass
            execute_query(f"DELETE FROM payments WHERE id IN ({placeholders})", tuple(selected_payment_ids))
            set_success_message(f"Deleted {len(selected_payment_ids)} Payment Receipt(s) successfully.")
            clear_cache_after_write()
            st.rerun()
else:
    st.info("Delete selected Payment Receipts is available only for Super Admin.")

render_slogan_footer()
