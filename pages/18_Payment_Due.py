from payment_common import *

page_setup()
require_page_view('payment_due')
show_edit_permission_status('payment_due')
show_header("Payment Due", "Pending delivery invoices and balances")
access_notice()
render_payment_subnav('payment_due')

rows = fetch_payment_due_rows()
if not rows:
    st.info("No pending payment invoices as per product/warehouse access.")
else:
    df = pd.DataFrame(rows)
    st.dataframe(style_total_row(df), width='stretch', hide_index=True)
    export_buttons(add_total_row(df), "payment_due_rows")

render_slogan_footer()
