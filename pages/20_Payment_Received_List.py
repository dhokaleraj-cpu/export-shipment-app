from payment_common import *

page_setup()
require_page_view("payment_list")
show_edit_permission_status("payment_list")
show_header("Payment Received List", "Payment receipt table grid")
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
if rows:
    df = pd.DataFrame(format_date_columns(rows))
    st.dataframe(df, width='stretch', hide_index=True)
    export_buttons(df, "payment_received_list")
else:
    st.info("No payment received records found for selected filters.")

render_slogan_footer()
