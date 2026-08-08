from common import *

page_setup()
require_page_view('masters')
show_edit_permission_status('masters')
show_header('Masters', 'SN 27.13 — Product Customer + Customer Ship To required links')
access_notice()

if not current_user_can_edit('masters'):
    st.info('You have View permission for Masters. Edit permission is disabled for this user.')

schema_ok = require_delivery_master_relationship_schema('Masters')


def _sn2713_customer_ship_to_link_panel():
    st.markdown(
        """
        <div style="border:2px solid #9FBAD0;border-radius:12px;padding:12px 14px;margin:8px 0 14px 0;background:#F7FAFC;">
          <div style="font-weight:900;font-size:16px;color:#1F2937;">REQUIRED FIELD — CUSTOMER MASTER → SHIP TO</div>
          <div style="font-size:13px;color:#475569;margin-top:4px;">Every Customer / Bill To must have one linked Ship To. Shipment Entry and Delivery Invoice use this link automatically.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    customer_rows = fetch_all('SELECT id, customer_name, company_code, ship_to_master_id FROM customers ORDER BY customer_name, id')
    ship_rows = fetch_all("""
        SELECT id, ship_to_name, ship_to_id, addressline1, addressline2, addressline3
        FROM ship_to_masters
        WHERE COALESCE(is_active, TRUE)=TRUE
        ORDER BY ship_to_name, ship_to_id, id
    """)
    if not customer_rows:
        st.info('Create a Customer record below first.')
        return
    if not ship_rows:
        st.warning('Create an active Ship To record with Address Line 1 before linking a Customer.')
        return

    customer_map = {
        f'{row.get("customer_name") or "-"} | {row.get("company_code") or "-"} | ID {row["id"]}': row
        for row in customer_rows
    }
    ship_map = {
        f'{row.get("ship_to_name") or "-"} | {row.get("ship_to_id") or "-"} | ID {row["id"]}': row
        for row in ship_rows
    }

    selected_customer_label = st.selectbox('Customer / Bill To', list(customer_map.keys()), key='sn2713_customer_link_customer')
    customer_row = customer_map[selected_customer_label]
    ship_labels = list(ship_map.keys())
    current_ship_id = customer_row.get('ship_to_master_id')
    current_ship_index = 0
    if current_ship_id:
        for idx, label in enumerate(ship_labels):
            if int(ship_map[label]['id']) == int(current_ship_id):
                current_ship_index = idx
                break
    selected_ship_label = st.selectbox('Ship To * (Required)', ship_labels, index=current_ship_index, key='sn2713_customer_link_ship_to')
    ship_row = ship_map[selected_ship_label]
    ship_address = ', '.join(
        str(ship_row.get(key) or '').strip()
        for key in ('addressline1', 'addressline2', 'addressline3')
        if str(ship_row.get(key) or '').strip()
    )
    st.caption(f'Selected Ship To Address: {ship_address or "-"}')

    if st.button('SAVE CUSTOMER → SHIP TO LINK', type='primary', key='sn2713_save_customer_ship_link', disabled=not current_user_can_edit('masters')):
        if not str(ship_row.get('addressline1') or '').strip():
            st.error('Selected Ship To must have Address Line 1.')
        else:
            execute_query('UPDATE customers SET ship_to_master_id=? WHERE id=?', (ship_row['id'], customer_row['id']))
            clear_cache_after_write()
            rerun_with_success('Customer Ship To link saved. Shipment and Delivery will use it automatically.')


def _sn2713_product_customer_link_panel():
    st.markdown(
        """
        <div style="border:2px solid #9FBAD0;border-radius:12px;padding:12px 14px;margin:8px 0 14px 0;background:#F7FAFC;">
          <div style="font-weight:900;font-size:16px;color:#1F2937;">REQUIRED FIELD — PRODUCT MASTER → CUSTOMER</div>
          <div style="font-size:13px;color:#475569;margin-top:4px;">Every Product must have a Customer. That Customer supplies the Bill To address and its linked Ship To for Shipment Entry and Delivery Invoice.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    product_rows = fetch_all('SELECT id, product_code, product_name, customer_id FROM products ORDER BY product_code, id')
    customer_rows = fetch_all("""
        SELECT c.id, c.customer_name, c.company_code, c.address, c.ship_to_master_id,
               stm.ship_to_name, stm.ship_to_id, stm.addressline1, stm.addressline2, stm.addressline3,
               stm.is_active
        FROM customers c
        LEFT JOIN ship_to_masters stm ON stm.id=c.ship_to_master_id
        ORDER BY c.customer_name, c.id
    """)
    if not product_rows:
        st.info('Create a Product record below first.')
        return
    if not customer_rows:
        st.warning('Create and complete a Customer record before linking a Product.')
        return

    product_map = {
        f'{row.get("product_code") or "-"} | {row.get("product_name") or ""} | ID {row["id"]}': row
        for row in product_rows
    }
    customer_map = {
        f'{row.get("customer_name") or "-"} | {row.get("company_code") or "-"} | ID {row["id"]}': row
        for row in customer_rows
    }

    selected_product_label = st.selectbox('Product', list(product_map.keys()), key='sn2713_product_link_product')
    product_row = product_map[selected_product_label]
    customer_labels = list(customer_map.keys())
    current_customer_id = product_row.get('customer_id')
    current_customer_index = 0
    if current_customer_id:
        for idx, label in enumerate(customer_labels):
            if int(customer_map[label]['id']) == int(current_customer_id):
                current_customer_index = idx
                break
    selected_customer_label = st.selectbox('Customer * (Required)', customer_labels, index=current_customer_index, key='sn2713_product_link_customer')
    customer_row = customer_map[selected_customer_label]
    st.caption(f'Bill To Address: {customer_row.get("address") or "-"}')
    ship_address = ', '.join(
        str(customer_row.get(key) or '').strip()
        for key in ('addressline1', 'addressline2', 'addressline3')
        if str(customer_row.get(key) or '').strip()
    )
    st.caption(
        f'Customer-linked Ship To: {customer_row.get("ship_to_name") or "-"} | '
        f'{customer_row.get("ship_to_id") or "-"} | {ship_address or "-"}'
    )

    if st.button('SAVE PRODUCT → CUSTOMER LINK', type='primary', key='sn2713_save_product_customer_link', disabled=not current_user_can_edit('masters')):
        if not str(customer_row.get('address') or '').strip():
            st.error('Selected Customer must have a Bill To Address.')
        elif not customer_row.get('ship_to_master_id'):
            st.error('Selected Customer must have a Ship To link first.')
        elif customer_row.get('is_active') is False or not str(customer_row.get('addressline1') or '').strip():
            st.error('Customer-linked Ship To must be active and have Address Line 1.')
        else:
            execute_query('UPDATE products SET customer_id=? WHERE id=?', (customer_row['id'], product_row['id']))
            clear_cache_after_write()
            rerun_with_success('Product Customer link saved. Shipment and Delivery will now load this Customer and its Ship To.')


st.success('SN 27.13 MASTER LINK FIELDS ACTIVE — Product Master has required Customer; Customer Master has required Ship To.')
st.markdown(
    """
    <div class="card" style="margin-bottom:14px;">
        <b>MASTER RELATIONSHIP — REQUIRED FOR SHIPMENT AND DELIVERY</b><br>
        1. Create Ship To. &nbsp; 2. Customer Master: select Ship To. &nbsp;
        3. Product Master: select Customer. &nbsp; 4. Shipment Entry and Delivery Invoice load Customer + Ship To from Product automatically.
    </div>
    """,
    unsafe_allow_html=True,
)

if schema_ok:
    health = fetch_master_relationship_health()
    h1, h2, h3, h4 = st.columns(4)
    h1.metric('Ship To Ready', f"{health.get('ship_to_ready', 0)} / {health.get('ship_to_total', 0)}")
    h2.metric('Customers with Ship To', f"{health.get('customer_linked', 0)} / {health.get('customer_total', 0)}")
    h3.metric('Products with Customer', f"{health.get('product_customer_linked', 0)} / {health.get('product_total', 0)}")
    h4.metric('Products with Complete Chain', f"{health.get('product_complete_chain', 0)} / {health.get('product_total', 0)}")

    missing_customers, missing_products = fetch_unlinked_master_relationships()
    if missing_customers or missing_products:
        with st.expander('Records requiring relationship mapping', expanded=True):
            if missing_customers:
                st.warning('Customers requiring Ship To / address completion:')
                st.dataframe(pd.DataFrame(missing_customers), width='stretch', hide_index=True)
            if missing_products:
                st.warning('Products requiring Customer / complete chain mapping:')
                st.dataframe(pd.DataFrame(missing_products), width='stretch', hide_index=True)
    else:
        st.success('All existing Products and Customers have the complete Product → Customer → Ship To relationship.')

mtab = st.tabs([
    '1. Ship To Master — Address Required',
    '2. Customer Master — Ship To * Required',
    '3. Product Master — Customer * Required',
    'Supplier',
    'Warehouse',
    'Payment Terms',
    'Incoterm',
    'Forwarder',
])

with mtab[0]:
    ship_to_form()
with mtab[1]:
    _sn2713_customer_ship_to_link_panel()
    st.divider()
    customer_form()
with mtab[2]:
    _sn2713_product_customer_link_panel()
    st.divider()
    product_form()
with mtab[3]:
    master_form('Supplier Master', 'suppliers', ['supplier_name', 'contact_person', 'email', 'phone', 'address'])
with mtab[4]:
    master_form('Warehouse Master', 'warehouses', ['warehouse_name', 'location', 'contact_person', 'shipment_time_days'])
with mtab[5]:
    master_form('Payment Term Master', 'payment_terms', ['term_name', 'days', 'remarks'])
with mtab[6]:
    master_form('Incoterm Master', 'incoterms', ['incoterm_name', 'remarks'])
with mtab[7]:
    master_form('Forwarder Master', 'forwarders', ['forwarder_name', 'contact_person', 'email', 'phone', 'remarks'])

render_slogan_footer()
st.markdown('<div class="footer">COPYRIGHT BY FOUR STAR INDUSTRIES PVT. LTD.</div>', unsafe_allow_html=True)
