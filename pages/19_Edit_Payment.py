from payment_common import *

page_setup()
require_page_view('payment_edit')
show_edit_permission_status('payment_edit')
show_header("Edit Payment", "Modify payment receipts")
access_notice()
render_payment_subnav('payment_edit')

if not current_user_can_edit("payment_edit"):
    st.error("You have View permission but not Edit permission for Edit Payment page. Contact Super Admin.")
    st.stop()

rows = fetch_payment_rows(limit=500)
if not rows:
    st.info("No payment records available for edit.")
else:
    pmap = {f"{p['id']} | {p['delivery_invoice_no']} | {p['customer_name']} | Amount {p['payment_amount']}": p for p in rows}
    selected_key = searchable_selectbox("Select Payment to Edit", list(pmap.keys()), key="edit_payment_subpage_select")
    ep = pmap[selected_key]
    suffix = str(ep["id"])
    pc1, pc2 = st.columns(2)
    with pc1:
        ep_date = st.text_input("Edit Payment Date YYYY-MM-DD", str(ep.get("payment_received_date") or ""), key=f"edit_payment_date_{suffix}")
        ep_amount = st.number_input("Edit Payment Amount", min_value=0.0, value=float(ep.get("payment_amount") or 0), step=1.0, key=f"edit_payment_amount_{suffix}")
    with pc2:
        ep_ref = st.text_input("Edit Payment Reference", ep.get("payment_reference") or "", key=f"edit_payment_ref_{suffix}")
        ep_remarks = st.text_area("Edit Remarks", ep.get("remarks") or "", key=f"edit_payment_remarks_{suffix}")

    if st.button("Update Payment", type="primary", key=f"update_payment_{suffix}"):
        execute_query("""
            UPDATE payments
            SET payment_received_date=?, payment_amount=?, payment_reference=?, remarks=?
            WHERE id=?
        """, (ep_date.strip(), ep_amount, ep_ref.strip(), ep_remarks.strip(), ep["id"]))
        st.success("Payment updated successfully.")
        clear_cache_after_write()
        st.rerun()

    st.divider()
    st.subheader("Recent Payment Records")
    st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)

render_slogan_footer()
