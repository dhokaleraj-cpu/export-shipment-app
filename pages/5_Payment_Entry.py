from payment_common import *

SN2722_PAYMENT_MARKER = "SN 27.22 EXPLICIT LINE-ITEM PAYMENT ACTIVE"

page_setup()
require_page_view('payment')
show_edit_permission_status('payment')
show_header('Payment Entry', 'Select exact Original Invoice / Product line(s) and allocate payment')
access_notice()
render_payment_subnav('payment')
can_add_payment = current_user_can_add('payment')

st.markdown('''
<div class="card" style="margin-bottom:14px;border:2px solid #0b6fb8;">
<b>SN 27.22 EXPLICIT LINE-ITEM PAYMENT ACTIVE</b><br>
Select a Delivery Invoice, tick the exact Original Invoice / Product line(s), and enter the allocation amount for each selected line.
</div>
''', unsafe_allow_html=True)

try:
    ensure_payment_allocation_schema()
except Exception as exc:
    st.error(f'Payment line-allocation schema could not be prepared: {exc}')
    st.stop()

search_text = st.text_input('Search by Original Invoice / Delivery Invoice / Customer / Shipment', key='payment_search_sn2722').strip().lower()
try:
    due_rows = fetch_payment_due_rows() or []
except Exception as exc:
    st.error(f'Pending invoices could not be loaded: {exc}')
    st.stop()

if search_text:
    due_rows = [r for r in due_rows if search_text in ' | '.join([
        str(r.get('original_invoice_no') or ''), str(r.get('delivery_invoice_no') or ''),
        str(r.get('customer_name') or ''), str(r.get('shipment_no') or ''), str(r.get('warehouse_name') or '')
    ]).lower()]

if not due_rows:
    st.warning('No pending Delivery Invoice is available for the current access/search.')
else:
    delivery_map = {f"Delivery Inv {d.get('delivery_invoice_no') or '-'} | Original Inv {d.get('original_invoice_no') or '-'} | {d.get('customer_name') or '-'} | Pending {float(d.get('pending_amount') or 0):,.3f} {d.get('currency') or ''}": d for d in due_rows}
    selected_key = searchable_selectbox('Select Pending Delivery Invoice', list(delivery_map.keys()), key='payment_delivery_select_sn2722')
    selected_delivery = delivery_map[selected_key]
    delivery_invoice_no = selected_delivery.get('delivery_invoice_no') or ''

    st.markdown(f'''
    <div class="card" style="margin-bottom:14px;">
      <h3 style="margin:0;color:#003B73;">Payment Summary</h3>
      <table style="width:100%;font-family:Aptos,Arial,sans-serif;font-weight:700;margin-top:10px;">
        <tr><td><b>Delivery Invoice</b></td><td>{delivery_invoice_no or '-'}</td><td><b>Original Invoice(s)</b></td><td>{selected_delivery.get('original_invoice_no') or '-'}</td></tr>
        <tr><td><b>Customer</b></td><td>{selected_delivery.get('customer_name') or '-'}</td><td><b>Due Date</b></td><td>{selected_delivery.get('payment_due_date') or '-'}</td></tr>
        <tr><td><b>Invoice Amount</b></td><td>{float(selected_delivery.get('total_invoice_amount') or 0):,.3f}</td><td><b>Already Received</b></td><td>{float(selected_delivery.get('paid_amount') or 0):,.3f}</td></tr>
        <tr><td><b>Pending Amount</b></td><td>{float(selected_delivery.get('pending_amount') or 0):,.3f}</td><td><b>Shipment No</b></td><td>{selected_delivery.get('shipment_no') or '-'}</td></tr>
      </table>
    </div>
    ''', unsafe_allow_html=True)

    pending_lines = [r for r in fetch_payment_line_rows(delivery_invoice_no) if float(r.get('pending_amount') or 0) > 0.0005]
    st.markdown('<div class="input-section-title">Line Item Allocation — Tick Required Line(s)</div>', unsafe_allow_html=True)

    if not pending_lines:
        st.success('All line items under this Delivery Invoice are already fully paid.')
    else:
        if st.session_state.get('_payment_invoice_sn2722') != delivery_invoice_no:
            for k in list(st.session_state.keys()):
                if str(k).startswith(('pay_line_select_sn2722_', 'pay_line_amount_sn2722_')):
                    st.session_state.pop(k, None)
            st.session_state['_payment_invoice_sn2722'] = delivery_invoice_no

        hdr = st.columns([0.55,1.25,1.05,2.0,1.0,1.0,1.0,1.15])
        for c,t in zip(hdr,['Select','Original Invoice','Product Code','Product Name','Invoice Amount','Already Paid','Pending','Allocate Amount']):
            c.markdown(f'**{t}**')

        allocations = []
        errors = []
        for line in pending_lines:
            line_id = int(line.get('anchor_delivery_id') or 0)
            pending = float(line.get('pending_amount') or 0)
            cols = st.columns([0.55,1.25,1.05,2.0,1.0,1.0,1.0,1.15])
            selected = cols[0].checkbox('Select', key=f'pay_line_select_sn2722_{delivery_invoice_no}_{line_id}', label_visibility='collapsed')
            cols[1].write(line.get('original_invoice_no') or '-')
            cols[2].write(line.get('product_code') or '-')
            cols[3].write(line.get('product_name') or '-')
            cols[4].write(f"{float(line.get('invoice_amount') or 0):,.3f}")
            cols[5].write(f"{float(line.get('paid_amount') or 0):,.3f}")
            cols[6].write(f"{pending:,.3f}")
            amount = cols[7].number_input('Allocate Amount', min_value=0.0, max_value=max(0.0,pending), step=1.0, format='%.3f', key=f'pay_line_amount_sn2722_{delivery_invoice_no}_{line_id}', label_visibility='collapsed', disabled=not selected)
            if selected:
                if amount <= 0:
                    errors.append(f"{line.get('original_invoice_no') or '-'} / {line.get('product_code') or '-'}: enter allocation amount.")
                else:
                    allocations.append({'delivery_id': line_id, 'amount': float(amount), 'original_invoice_no': line.get('original_invoice_no') or '', 'product_code': line.get('product_code') or ''})
            st.divider()

        total = sum(x['amount'] for x in allocations)
        a,b,c = st.columns(3)
        a.metric('Selected Lines', len(allocations))
        b.metric('Payment Receipt Total', f"{total:,.3f} {selected_delivery.get('currency') or ''}")
        c.metric('Balance After Receipt', f"{max(0.0,float(selected_delivery.get('pending_amount') or 0)-total):,.3f}")
        for e in errors:
            st.warning(e)

        c1,c2 = st.columns(2)
        with c1:
            payment_received_date = st.date_input('Payment Received Date', value=date.today(), key='payment_date_sn2722')
            payment_reference = st.text_input('Payment Reference', key='payment_ref_sn2722')
        with c2:
            attachment = st.file_uploader('Attach Payment File', key='payment_file_sn2722')
            remarks = st.text_area('Remarks', key='payment_remarks_sn2722')

        if st.button('Save Payment with Selected Line Item(s)', type='primary', key='save_payment_sn2722', disabled=not can_add_payment):
            if errors:
                st.error('Correct the line allocation warnings before saving.')
                st.stop()
            if not allocations:
                st.error('Tick at least one line item and enter its allocation amount.')
                st.stop()
            if total > float(selected_delivery.get('pending_amount') or 0) + 0.0005:
                st.error('Allocated total cannot exceed Delivery Invoice pending balance.')
                st.stop()
            path = save_upload(attachment, f'payment_{delivery_invoice_no}')
            try:
                result = save_invoice_payment_allocated_atomic(delivery_invoice_no, str(payment_received_date), allocations, payment_reference, path, remarks)
            except Exception as exc:
                st.error(f'Payment save failed: {exc}')
                st.stop()
            clear_cache_after_write()
            set_success_message(f"Payment {total:,.3f} saved against {len(allocations)} selected line item(s). Pending balance: {float(result.get('pending_after') or 0):,.3f}.")
            st.rerun()

render_slogan_footer()
