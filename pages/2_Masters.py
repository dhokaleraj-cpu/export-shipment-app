from common import *

page_setup()

require_page_view('masters')
show_edit_permission_status('masters')

show_header('Masters')
if not current_user_can_edit('masters'):
    st.info('You have View permission for Masters. Edit permission is disabled for this user.')
mtab = st.tabs(['Customer', 'Supplier', 'Warehouse', 'Product', 'Payment Terms', 'Incoterm', 'Forwarder', 'Ship To'])
with mtab[0]:
    customer_form()
with mtab[1]:
    master_form('Supplier Master', 'suppliers', ['supplier_name', 'contact_person', 'email', 'phone', 'address'])
with mtab[2]:
    master_form('Warehouse Master', 'warehouses', ['warehouse_name', 'location', 'contact_person', 'shipment_time_days'])
with mtab[3]:
    product_form()
with mtab[4]:
    master_form('Payment Term Master', 'payment_terms', ['term_name', 'days', 'remarks'])
with mtab[5]:
    master_form('Incoterm Master', 'incoterms', ['incoterm_name', 'remarks'])
with mtab[6]:
    master_form('Forwarder Master', 'forwarders', ['forwarder_name', 'contact_person', 'email', 'phone', 'remarks'])

render_slogan_footer()

with mtab[7]:
    ship_to_form()
