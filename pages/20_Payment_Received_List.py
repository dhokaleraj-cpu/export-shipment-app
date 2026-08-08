from payment_common import *

page_setup()
require_page_view("payment_list")
show_edit_permission_status("payment_list")
show_header("Payment Received List", "SN 27.13 — select multiple receipts and password-delete")
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

raw_df = pd.DataFrame(format_date_columns(rows))
display_df = raw_df.copy()
display_df.insert(0, "Select", False)

st.markdown(
    """
    <div class="card" style="margin-bottom:10px;">
      <b>PAYMENT RECEIPT SELECTION</b><br>
      Tick one or more receipts in the Select column. Delete removes only the selected payment receipt rows; Delivery Invoices remain unchanged and their pending payment recalculates automatically.
    </div>
    """,
    unsafe_allow_html=True,
)

readonly_cols = [col for col in display_df.columns if col != "Select"]
edited_df = st.data_editor(
    display_df,
    width="stretch",
    hide_index=True,
    disabled=readonly_cols,
    column_config={
        "Select": st.column_config.CheckboxColumn(
            "Select",
            help="Tick payment receipts to delete",
            default=False,
        ),
    },
    key="payment_received_bulk_delete_editor_sn2713",
)

selected_df = edited_df[edited_df["Select"] == True].copy()
selected_payment_ids = [
    int(value)
    for value in selected_df.get("id", pd.Series(dtype=int)).tolist()
    if str(value) not in ("", "None", "nan")
]
selected_amount = 0.0
if not selected_df.empty and "payment_amount" in selected_df.columns:
    selected_amount = pd.to_numeric(selected_df["payment_amount"], errors="coerce").fillna(0).sum()

m1, m2, m3 = st.columns(3)
m1.metric("Records Shown", len(raw_df))
m2.metric("Selected for Delete", len(selected_payment_ids))
m3.metric("Selected Payment Amount", f"{float(selected_amount):,.3f}")

export_buttons(raw_df, "payment_received_list")

st.divider()
st.subheader("Delete Selected Payment Receipts")
can_delete = (
    bool(current_user_can_edit("payment_list"))
    and st.session_state.get("user", {}).get("role") in ("admin", "super_admin")
)
if not can_delete:
    st.info("Payment deletion requires Admin/Super Admin with Edit permission on Payment Received List.")
else:
    st.warning("Password confirmation is mandatory. This deletes only the ticked payment receipt records.")
    dc1, dc2 = st.columns([2, 1])
    with dc1:
        delete_confirm = st.checkbox(
            f"I confirm deletion of {len(selected_payment_ids)} selected payment receipt(s)",
            key="payment_received_bulk_delete_confirm_sn2713",
        )
    with dc2:
        delete_password = st.text_input(
            "Login Password",
            type="password",
            key="payment_received_bulk_delete_password_sn2713",
        )

    if st.button(
        "DELETE SELECTED PAYMENT RECEIPTS",
        type="secondary",
        width="stretch",
        key="payment_received_bulk_delete_button_sn2713",
    ):
        if not selected_payment_ids:
            st.error("Tick at least one payment receipt in the Select column.")
        elif not delete_confirm:
            st.error("Tick the confirmation checkbox before deleting.")
        elif not check_delete_password(delete_password):
            st.error("Wrong password. Delete cancelled.")
        else:
            placeholders = ",".join(["?"] * len(selected_payment_ids))
            try:
                execute_query(
                    "INSERT INTO delete_audit_log (table_name, record_id, deleted_by, details) VALUES (?, ?, ?, ?)",
                    (
                        "payments",
                        0,
                        st.session_state.get("user", {}).get("username", ""),
                        "Bulk deleted payment receipt IDs: " + ", ".join(str(x) for x in selected_payment_ids),
                    ),
                )
            except Exception:
                pass
            execute_query(
                f"DELETE FROM payments WHERE id IN ({placeholders})",
                tuple(selected_payment_ids),
            )
            clear_cache_after_write()
            set_success_message(f"Deleted {len(selected_payment_ids)} selected payment receipt(s) successfully.")
            st.rerun()

render_slogan_footer()
