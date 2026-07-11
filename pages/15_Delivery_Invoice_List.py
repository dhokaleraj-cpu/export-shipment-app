from delivery_common import *

page_setup()
require_page_view("delivery_list")
show_edit_permission_status("delivery_list")
show_header("Delivery Invoice List", "Delivery invoice table grid")
access_notice()
render_delivery_subnav("delivery_list")

part_options = fetch_delivery_part_options()
part_label = delivery_part_selectbox("Part Number", part_options, key="delivery_list_part", include_all=True)
selected_product_id = None if part_label == "ALL PARTS" else part_options.get(part_label, {}).get("id")

c1, c2, c3, c4 = st.columns(4)
with c1:
    date_from = st.date_input("Delivery From", value=date(date.today().year, 1, 1), key="delivery_list_from")
with c2:
    date_to = st.date_input("Delivery To", value=date.today(), key="delivery_list_to")
with c3:
    original_invoice_search = st.text_input("Original Invoice Number", key="delivery_list_original_invoice")
with c4:
    delivery_invoice_search = st.text_input("Delivery Invoice Number", key="delivery_list_delivery_invoice")

rows = fetch_delivery_invoice_headers_for_edit(selected_product_id=selected_product_id, date_from=date_from, date_to=date_to)
filtered = []
for r in rows:
    if original_invoice_search and original_invoice_search.lower() not in str(r.get("original_invoice_no") or "").lower():
        continue
    if delivery_invoice_search and delivery_invoice_search.lower() not in str(r.get("delivery_invoice_no") or "").lower():
        continue
    filtered.append(r)

st.caption(f"Showing {len(filtered)} delivery invoices.")
if filtered:
    df = pd.DataFrame(format_date_columns(filtered))
    st.dataframe(df, use_container_width=True, hide_index=True)
    export_buttons(df, "delivery_invoice_list")
else:
    st.info("No delivery invoices found for selected filters.")

render_slogan_footer()
