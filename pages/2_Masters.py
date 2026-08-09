from common import *

page_setup()
require_page_view('masters')
show_edit_permission_status('masters')
show_header('Masters', 'SN 27.14 — Simple and fast Master setup')
access_notice()

if not current_user_can_edit('masters'):
    st.info('You have View permission for Masters. Edit permission is disabled for this user.')

# Lightweight once-per-session additive columns only; no health scans, no mapping panels.
ensure_delivery_master_link_columns(show_errors=False)

master_name = st.selectbox(
    'Select Master',
    ['Customer', 'Supplier', 'Warehouse', 'Product', 'Payment Terms', 'Incoterm', 'Forwarder', 'Ship To'],
    key='masters_active_section_sn2714',
)

if master_name == 'Customer':
    customer_form()
elif master_name == 'Supplier':
    master_form('Supplier Master', 'suppliers', ['supplier_name', 'contact_person', 'email', 'phone', 'address'])
elif master_name == 'Warehouse':
    master_form('Warehouse Master', 'warehouses', ['warehouse_name', 'location', 'contact_person', 'shipment_time_days'])
elif master_name == 'Product':
    product_form()
elif master_name == 'Payment Terms':
    master_form('Payment Term Master', 'payment_terms', ['term_name', 'days', 'remarks'])
elif master_name == 'Incoterm':
    master_form('Incoterm Master', 'incoterms', ['incoterm_name', 'remarks'])
elif master_name == 'Forwarder':
    master_form('Forwarder Master', 'forwarders', ['forwarder_name', 'contact_person', 'email', 'phone', 'remarks'])
elif master_name == 'Ship To':
    ship_to_form()

render_slogan_footer()
st.markdown('<div class="footer">COPYRIGHT BY FOUR STAR INDUSTRIES PVT. LTD.</div>', unsafe_allow_html=True)
