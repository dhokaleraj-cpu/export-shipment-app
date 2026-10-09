from payment_common import *

SN2723_EDIT_PAYMENT_MARKER = "SN 27.23 EDIT PAYMENT LINE ALLOCATION ACTIVE"

page_setup()
require_page_view('payment_edit')
show_edit_permission_status('payment_edit')
show_header("Edit Payment", "Edit receipt and exact Original Invoice / Product line allocation")
access_notice()
render_payment_subnav('payment_edit')

if not current_user_can_edit("payment_edit"):
    st.error("You have View permission but not Edit permission for Edit Payment page. Contact Super Admin.")
    st.stop()

try:
    ensure_payment_allocation_schema()
except Exception as exc:
    st.error(f"Payment line-allocation schema could not be prepared: {exc}")
    st.stop()

st.markdown('''
<div class="card" style="margin-bottom:14px;border:2px solid #0b6fb8;">
<b>SN 27.23 EDIT PAYMENT LINE ALLOCATION ACTIVE</b><br>
Select a receipt, tick the exact Original Invoice / Product line(s) it belongs to and edit the amount for each line.
The receipt total is always the sum of the line allocations.
</div>
''', unsafe_allow_html=True)

COLS = [0.55, 1.25, 1.05, 2.0, 1.0, 1.0, 1.0, 1.15]
HEADERS = ['Select', 'Original Invoice', 'Product Code', 'Product Name', 'Invoice Amount', 'Already Paid', 'Pending', 'Allocate Amount']

rows = fetch_payment_rows(limit=500)
if not rows:
    st.info("No payment records available for edit.")
else:
    pmap = {
        f"{p['id']} | Delivery {p['delivery_invoice_no']} | Originals {p.get('original_invoice_no') or '-'} | "
        f"Amount {float(p.get('payment_amount') or 0):,.3f} | {p.get('allocation_mode') or ''}": p
        for p in rows
    }
    selected_key = searchable_selectbox("Select Payment to Edit", list(pmap.keys()), key="edit_payment_subpage_select")
    ep = pmap[selected_key]
    pid = int(ep["id"])
    suffix = str(pid)
    receipt_amount = float(ep.get('payment_amount') or 0)

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Invoice Amount", f"{float(ep.get('total_invoice_amount') or 0):,.3f}")
    s2.metric("This Receipt Amount", f"{receipt_amount:,.3f}")
    s3.metric("Total Invoice Received", f"{float(ep.get('invoice_paid_amount') or 0):,.3f}")
    s4.metric("Current Invoice Pending", f"{float(ep.get('invoice_pending_amount') or 0):,.3f}")

    # Line balances EXCLUDING this receipt = what this receipt may cover.
    line_rows = fetch_payment_line_rows(ep['delivery_invoice_no'], exclude_payment_id=pid)
    explicit_rows = fetch_payment_allocations(pid)
    existing_map = {int(r.get('anchor_delivery_id')): float(r.get('allocated_amount') or 0) for r in explicit_rows}
    is_legacy = not existing_map

    if is_legacy:
        # Legacy receipt: no saved allocation. Prefill a FIFO suggestion only;
        # nothing changes in the database until the user clicks Update.
        remaining = receipt_amount
        for line in line_rows:
            if remaining <= 0.0005:
                break
            amount = min(float(line.get('pending_amount') or 0), remaining)
            if amount > 0.0005:
                existing_map[int(line.get('anchor_delivery_id'))] = amount
                remaining -= amount
        st.warning(
            "This is a legacy payment receipt with no saved line allocation. The lines below are prefilled with a FIFO suggestion. "
            "Review them and click Update to convert this receipt to exact line allocation."
        )
    else:
        saved_total = sum(existing_map.values())
        if abs(saved_total - receipt_amount) > 0.001:
            st.warning(
                f"Saved receipt amount {receipt_amount:,.3f} does not match its line allocations {saved_total:,.3f} "
                "(it was changed by the old Edit Payment screen). Review the lines and click Update to correct it. "
                "After Update, the receipt amount will equal the sum of the line allocations."
            )

    # Reset widget state when a different receipt is chosen.
    if st.session_state.get('_edit_payment_pid_sn2723') != pid:
        for k in list(st.session_state.keys()):
            if str(k).startswith(('edit_pay_line_select_sn2723_', 'edit_pay_line_amount_sn2723_')):
                st.session_state.pop(k, None)
        st.session_state['_edit_payment_pid_sn2723'] = pid

    st.markdown('<div class="input-section-title">Line Item Allocation — Tick Required Line(s)</div>', unsafe_allow_html=True)
    if not line_rows:
        st.error("No line items were found for this Delivery Invoice.")
        st.stop()

    hdr = st.columns(COLS)
    for c, t in zip(hdr, HEADERS):
        c.markdown(f'**{t}**')

    allocations, errors = [], []
    for line in line_rows:
        line_id = int(line.get('anchor_delivery_id') or 0)
        available = float(line.get('pending_amount') or 0)
        prefill = float(existing_map.get(line_id, 0.0))
        sel_key = f'edit_pay_line_select_sn2723_{pid}_{line_id}'
        amt_key = f'edit_pay_line_amount_sn2723_{pid}_{line_id}'
        if sel_key not in st.session_state:
            st.session_state[sel_key] = prefill > 0.0005
        if amt_key not in st.session_state:
            st.session_state[amt_key] = float(min(prefill, available)) if prefill > 0 else 0.0
        cols = st.columns(COLS)
        selected = cols[0].checkbox('Select', key=sel_key, label_visibility='collapsed')
        cols[1].write(line.get('original_invoice_no') or '-')
        cols[2].write(line.get('product_code') or '-')
        cols[3].write(line.get('product_name') or '-')
        cols[4].write(f"{float(line.get('invoice_amount') or 0):,.3f}")
        cols[5].write(f"{float(line.get('paid_amount') or 0):,.3f}")
        cols[6].write(f"{available:,.3f}")
        amount = cols[7].number_input(
            'Allocate Amount', min_value=0.0, max_value=max(0.0, available), step=1.0, format='%.3f',
            key=amt_key, label_visibility='collapsed', disabled=not selected,
        )
        if selected:
            if amount <= 0:
                errors.append(f"{line.get('original_invoice_no') or '-'} / {line.get('product_code') or '-'}: enter allocation amount.")
            else:
                allocations.append({'delivery_id': line_id, 'amount': float(amount)})
        st.divider()
    st.caption("Already Paid / Pending exclude this receipt, so Pending is the maximum this receipt can cover on each line.")

    allocation_total = sum(float(x['amount']) for x in allocations)
    a1, a2, a3 = st.columns(3)
    a1.metric('Selected Lines', len(allocations))
    a2.metric('Edited Receipt Total', f"{allocation_total:,.3f}")
    a3.metric('Change vs Saved Receipt', f"{allocation_total - receipt_amount:+,.3f}")
    for msg in errors:
        st.warning(msg)

    pc1, pc2 = st.columns(2)
    with pc1:
        ep_date = st.date_input(
            "Payment Received Date",
            value=parse_db_date(ep.get("payment_received_date")) or date.today(),
            key=f"edit_payment_date_sn2723_{suffix}",
        )
        ep_ref = st.text_input("Payment Reference", ep.get("payment_reference") or "", key=f"edit_payment_ref_sn2723_{suffix}")
    with pc2:
        ep_remarks = st.text_area("Remarks", ep.get("remarks") or "", key=f"edit_payment_remarks_sn2723_{suffix}")

    if st.button("Update Payment and Line Allocation", type="primary", key=f"update_payment_sn2723_{suffix}"):
        if errors:
            st.error('Correct the line allocation warnings before updating.')
            st.stop()
        if not allocations:
            st.error('Select at least one line item and enter an allocation amount.')
            st.stop()
        try:
            update_invoice_payment_allocated_atomic(pid, str(ep_date), allocations, ep_ref.strip(), ep_remarks.strip())
        except Exception as exc:
            st.error(f"Payment update failed. Nothing was changed. Details: {exc}")
            st.stop()
        clear_cache_after_write()
        for k in list(st.session_state.keys()):
            if str(k).startswith(('edit_pay_line_select_sn2723_', 'edit_pay_line_amount_sn2723_')):
                st.session_state.pop(k, None)
        set_success_message(f"Payment receipt {pid} updated: {allocation_total:,.3f} across {len(allocations)} line item(s).")
        st.rerun()

    st.divider()
    st.subheader("Recent Payment Records")
    st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)

render_slogan_footer()
