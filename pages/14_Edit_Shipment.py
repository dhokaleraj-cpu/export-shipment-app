from shipment_common import *

page_setup()
require_page_view('shipment_edit')
show_edit_permission_status('shipment_edit')
require_delivery_master_relationship_schema("Edit Shipment")
show_header('Edit Shipment', 'Edit shipment header, Customer / Bill To, Ship To and pallet rows')
access_notice()
render_shipment_subnav('shipment_edit')

last_print_shipment_id = st.session_state.get('edit_shipment_last_print_id')
if last_print_shipment_id:
    try:
        saved_ship_rows = [s for s in fetch_shipment_headers(limit=1000) if int(s.get('id')) == int(last_print_shipment_id)]
        if saved_ship_rows:
            saved_shipment = saved_ship_rows[0]
            saved_rows = fetch_shipment_pallet_rows(saved_shipment['id'])
            if saved_rows:
                shipment_invoice_pdf = shipment_invoice_pdf_bytes(saved_shipment, saved_rows)
                st.success(f"Saved successfully. Shipment Invoice PDF is ready for: {saved_shipment.get('invoice_no') or saved_shipment.get('shipment_no')}")
                st.download_button(
                    'Print / Download Updated Shipment Invoice PDF',
                    shipment_invoice_pdf,
                    file_name=f"shipment_invoice_{saved_shipment.get('invoice_no') or saved_shipment.get('shipment_no')}.pdf",
                    mime='application/pdf',
                    key=f"download_updated_shipment_invoice_{saved_shipment.get('id')}",
                )
                shipment_details_pdf = shipment_pdf_bytes(saved_shipment, saved_rows)
                st.download_button(
                    'Print / Download Updated Shipment Details PDF',
                    shipment_details_pdf,
                    file_name=f"shipment_details_{saved_shipment.get('shipment_no')}.pdf",
                    mime='application/pdf',
                    key=f"download_updated_shipment_details_{saved_shipment.get('id')}",
                )
    except Exception as print_err:
        st.warning(f'Saved successfully, but PDF print could not be prepared: {print_err}')

if not current_user_can_edit('shipment_edit'):
    st.error('You have View permission but not Edit permission for Edit Shipment page. Contact Super Admin.')
    st.stop()

st.subheader('Edit Shipment Header')
st.info('Customer / Bill To and Ship To are available in the common Shipment header and are saved for the complete Shipment.')
shipments = fetch_shipment_headers(limit=500)
if not shipments:
    st.info('No shipments available for edit.')
else:
    ship_map = {f"{s['id']} | {s['shipment_no']} | Invoice {s['invoice_no']}": s for s in shipments}
    selected_ship_key = searchable_selectbox('Select Shipment to Edit', list(ship_map.keys()), key='edit_shipment_page_select')
    selected_ship = ship_map[selected_ship_key]
    selected_ship_id = selected_ship['id']

    current_rows_for_pdf = fetch_shipment_pallet_rows(selected_ship_id)
    if current_rows_for_pdf:
        current_invoice_pdf = shipment_invoice_pdf_bytes(selected_ship, current_rows_for_pdf)
        st.download_button(
            'Print / Download Current Shipment Invoice PDF',
            current_invoice_pdf,
            file_name=f"shipment_invoice_{selected_ship.get('invoice_no') or selected_ship.get('shipment_no')}.pdf",
            mime='application/pdf',
            key=f'current_shipment_invoice_pdf_{selected_ship_id}',
        )

    suppliers = fetch_all('SELECT * FROM suppliers ORDER BY supplier_name')
    warehouses = filter_warehouse_rows_for_current_user(fetch_all('SELECT * FROM warehouses ORDER BY warehouse_name'))
    customers = fetch_all('SELECT * FROM customers ORDER BY customer_name, id')
    ship_to_rows = fetch_all("SELECT * FROM ship_to_masters WHERE COALESCE(is_active, TRUE)=TRUE ORDER BY ship_to_name, ship_to_id, id")

    supplier_map = {f"{x.get('supplier_name')} | ID {x.get('id')}": x for x in suppliers}
    warehouse_map = {f"{x.get('warehouse_name')} | ID {x.get('id')}": x for x in warehouses}
    customer_map = {f"{x.get('customer_name')} | {x.get('company_code') or '-'} | ID {x.get('id')}": x for x in customers}
    ship_to_map = {f"{x.get('ship_to_name')} | {x.get('ship_to_id') or '-'} | ID {x.get('id')}": x for x in ship_to_rows}

    supplier_label_by_id = {int(x['id']): label for label, x in supplier_map.items()}
    warehouse_label_by_id = {int(x['id']): label for label, x in warehouse_map.items()}
    customer_label_by_id = {int(x['id']): label for label, x in customer_map.items()}
    ship_to_label_by_id = {int(x['id']): label for label, x in ship_to_map.items()}

    if not supplier_map or not warehouse_map or not customer_map or not ship_to_map:
        st.error('Supplier, Warehouse, Customer and Ship To masters are required before editing Shipment header.')
        st.stop()

    suffix = str(selected_ship_id)
    state_context_key = '_edit_shipment_header_context_sn2713'
    if st.session_state.get(state_context_key) != selected_ship_id:
        st.session_state[f'edit_customer_sn2713_{suffix}'] = customer_label_by_id.get(
            int(selected_ship.get('customer_id') or 0), list(customer_map.keys())[0]
        )
        st.session_state[f'edit_ship_to_sn2713_{suffix}'] = ship_to_label_by_id.get(
            int(selected_ship.get('ship_to_master_id') or 0), list(ship_to_map.keys())[0]
        )
        st.session_state[f'_edit_customer_tracker_sn2713_{suffix}'] = int(selected_ship.get('customer_id') or 0)
        st.session_state[state_context_key] = selected_ship_id

    # Show the first Product's current master relationship as a reference.
    first_product_relation = {}
    if current_rows_for_pdf:
        first_product_id = current_rows_for_pdf[0].get('product_id')
        relation_rows = fetch_all('''
            SELECT p.customer_id, c.customer_name, c.ship_to_master_id,
                   stm.ship_to_name, stm.ship_to_id
            FROM products p
            LEFT JOIN customers c ON c.id=p.customer_id
            LEFT JOIN ship_to_masters stm ON stm.id=c.ship_to_master_id
            WHERE p.id=?
            LIMIT 1
        ''', (first_product_id,))
        first_product_relation = relation_rows[0] if relation_rows else {}
        st.caption(
            f"First Product Master relationship: {first_product_relation.get('customer_name') or 'Customer not linked'} → "
            f"{first_product_relation.get('ship_to_name') or 'Ship To not linked'}"
        )

    h1, h2 = st.columns(2)
    with h1:
        edit_shipment_no = st.text_input('Edit Shipment Number', selected_ship.get('shipment_no') or '', key=f'edit_ship_no_{suffix}')
        edit_invoice_no = st.text_input('Edit Original Invoice Number', selected_ship.get('invoice_no') or '', key=f'edit_inv_no_{suffix}')
        edit_shipment_date = st.text_input('Edit Shipment Date YYYY-MM-DD', str(selected_ship.get('shipment_date') or ''), key=f'edit_ship_date_{suffix}')
        current_supplier_label = supplier_label_by_id.get(int(selected_ship.get('supplier_id') or 0), list(supplier_map.keys())[0])
        edit_supplier_label = st.selectbox('Edit Supplier', list(supplier_map.keys()), index=list(supplier_map.keys()).index(current_supplier_label), key=f'edit_supplier_{suffix}')
        current_warehouse_label = warehouse_label_by_id.get(int(selected_ship.get('warehouse_id') or 0), list(warehouse_map.keys())[0])
        edit_warehouse_label = st.selectbox('Edit Warehouse', list(warehouse_map.keys()), index=list(warehouse_map.keys()).index(current_warehouse_label), key=f'edit_warehouse_{suffix}')

    with h2:
        edit_customer_label = st.selectbox('Edit Customer / Bill To *', list(customer_map.keys()), key=f'edit_customer_sn2713_{suffix}')
        edit_customer_row = customer_map[edit_customer_label]
        edit_customer_id = int(edit_customer_row['id'])

        tracker_key = f'_edit_customer_tracker_sn2713_{suffix}'
        ship_to_key = f'edit_ship_to_sn2713_{suffix}'
        if st.session_state.get(tracker_key) != edit_customer_id:
            default_ship_to_id = edit_customer_row.get('ship_to_master_id')
            if default_ship_to_id and int(default_ship_to_id) in ship_to_label_by_id:
                st.session_state[ship_to_key] = ship_to_label_by_id[int(default_ship_to_id)]
            st.session_state[tracker_key] = edit_customer_id

        if st.session_state.get(ship_to_key) not in ship_to_map:
            st.session_state[ship_to_key] = list(ship_to_map.keys())[0]
        edit_ship_to_label = st.selectbox('Edit Ship To *', list(ship_to_map.keys()), key=ship_to_key)
        edit_ship_to_row = ship_to_map[edit_ship_to_label]
        edit_ship_to_id = int(edit_ship_to_row['id'])

        bill_address = str(edit_customer_row.get('address') or '').strip() or '-'
        ship_address = ', '.join([
            str(edit_ship_to_row.get('addressline1') or '').strip(),
            str(edit_ship_to_row.get('addressline2') or '').strip(),
            str(edit_ship_to_row.get('addressline3') or '').strip(),
        ]).strip(', ') or '-'
        st.info(f'Bill To Address: {bill_address}')
        st.info(f'Ship To Address: {ship_address}')

        if first_product_relation.get('customer_id') and first_product_relation.get('ship_to_master_id'):
            if st.button('Load Header from First Product Master Relationship', key=f'load_product_relation_{suffix}'):
                st.session_state[f'edit_customer_sn2713_{suffix}'] = customer_label_by_id[int(first_product_relation['customer_id'])]
                st.session_state[ship_to_key] = ship_to_label_by_id[int(first_product_relation['ship_to_master_id'])]
                st.session_state[tracker_key] = int(first_product_relation['customer_id'])
                st.rerun()

    if st.button('SAVE - Update Shipment Header & Prepare PDF', type='primary', key=f'save_update_ship_header_{suffix}', width='stretch'):
        if not str(edit_customer_row.get('address') or '').strip():
            st.error('The selected Customer has no Bill To Address. Complete Customer Master before saving.')
            st.stop()
        if not edit_customer_row.get('ship_to_master_id'):
            st.error('The selected Customer has no required Ship To link in Customer Master.')
            st.stop()
        if edit_ship_to_row.get('is_active') is False:
            st.error('The selected Ship To is inactive. Select an active Ship To before saving.')
            st.stop()
        if not str(edit_ship_to_row.get('addressline1') or '').strip():
            st.error('The selected Ship To has no Address Line 1. Complete Ship To Master before saving.')
            st.stop()
        execute_query('''
            UPDATE shipments
            SET shipment_no=?, invoice_no=?, shipment_date=?, supplier_id=?, warehouse_id=?, customer_id=?, ship_to_master_id=?
            WHERE id=?
        ''', (
            edit_shipment_no.strip(), edit_invoice_no.strip(), edit_shipment_date.strip(),
            supplier_map[edit_supplier_label]['id'], warehouse_map[edit_warehouse_label]['id'],
            edit_customer_id, edit_ship_to_id, selected_ship_id,
        ))
        st.session_state['edit_shipment_last_print_id'] = selected_ship_id
        set_success_message('Shipment header updated successfully with Customer / Bill To and Ship To. PDF is ready.')
        clear_cache_after_write()
        st.rerun()

    st.divider()
    st.subheader('Edit Pallet / Product Row')
    rows = fetch_shipment_pallet_rows(selected_ship_id)
    if rows:
        row_map = {f"{r['id']} | Pallet {r['pallet_no']} | {r['product_code']} | Qty {r['original_qty']}": r for r in rows}
        selected_row_key = searchable_selectbox('Select Pallet / Product Row', list(row_map.keys()), key='edit_shipment_pallet_row')
        selected_row = row_map[selected_row_key]
        row_suffix = str(selected_row['id'])
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            fifo_id = st.number_input('FIFO ID', min_value=1, value=int(selected_row.get('fifo_row_id') or selected_row.get('id') or 1), step=1, key=f'edit_fifo_{row_suffix}')
            pallet_no = st.text_input('Pallet No', selected_row.get('pallet_no') or '', key=f'edit_pallet_{row_suffix}')
        with c2:
            box_no = st.text_input('Box No', selected_row.get('box_no') or '', key=f'edit_box_{row_suffix}')
            po_number = st.text_input('PO Number', selected_row.get('po_number') or '', key=f'edit_po_{row_suffix}')
        with c3:
            po_date = st.text_input('PO Date YYYY-MM-DD', str(selected_row.get('po_date') or ''), key=f'edit_po_date_{row_suffix}')
            qty = st.number_input('Quantity', min_value=0.0, value=float(selected_row.get('original_qty') or 0), step=1.0, key=f'edit_qty_{row_suffix}')
        with c4:
            price = st.number_input('Price', min_value=0.0, value=float(selected_row.get('unit_price') or 0), step=0.001, format='%.3f', key=f'edit_price_{row_suffix}')
            currency = st.selectbox('Currency', CURRENCIES, index=CURRENCIES.index(selected_row.get('currency')) if selected_row.get('currency') in CURRENCIES else 0, key=f'edit_currency_{row_suffix}')
        with c5:
            amount = qty * price
            st.metric('Amount', f'{amount:,.3f} {currency}')

        if st.button('SAVE - Update Pallet / Product Row & Prepare PDF', type='primary', key=f'save_update_pallet_row_{row_suffix}', width='stretch'):
            execute_query('''
                UPDATE shipment_boxes
                SET fifo_row_id=?, pallet_no=?, box_no=?, po_number=?, po_date=?, original_qty=?, unit_price=?, currency=?, amount=?
                WHERE id=?
            ''', (fifo_id, pallet_no.strip(), box_no.strip(), po_number.strip(), po_date.strip() or None, qty, price, currency, amount, selected_row['id']))
            st.session_state['edit_shipment_last_print_id'] = selected_ship_id
            set_success_message('Pallet / Product row updated successfully. PDF is ready.')
            clear_cache_after_write()
            st.rerun()
    else:
        st.info('No pallet rows available for selected shipment.')

render_slogan_footer()
