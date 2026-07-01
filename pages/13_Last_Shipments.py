from shipment_common import *

page_setup()
require_page_view('shipment_last')
show_edit_permission_status('shipment_last')
show_header("Last Shipments", "Shipment headers, pallet rows and Shipment Invoice PDF reprint")
access_notice()
render_shipment_subnav('shipment_last')

shipments = fetch_shipment_headers(limit=300)
if not shipments:
    st.info("No shipments available as per your product/warehouse access.")
    render_slogan_footer()
    st.stop()

ship_map = {f"{s['id']} | {s['shipment_no']} | Invoice {s['invoice_no']} | {s.get('warehouse_name') or ''}": s for s in shipments}
selected_key = searchable_selectbox("Select Shipment", list(ship_map.keys()), key="last_shipments_select")
selected_shipment = ship_map[selected_key]
rows = fetch_shipment_pallet_rows(selected_shipment["id"])

st.subheader("Shipment Header")
st.dataframe(pd.DataFrame([selected_shipment]), use_container_width=True, hide_index=True)

st.subheader("Pallet / Product Rows")
if rows:
    df = pd.DataFrame(rows)
    st.dataframe(style_total_row(df), use_container_width=True, hide_index=True)
    export_buttons(add_total_row(df), "shipment_pallet_rows")
    pdf_bytes = shipment_pdf_bytes(selected_shipment, rows)
    st.download_button(
        "Print / Download Shipment Details PDF",
        pdf_bytes,
        file_name=f"shipment_details_{selected_shipment.get('shipment_no')}.pdf",
        mime="application/pdf",
        key="shipment_pdf_print_download"
    )

    shipment_invoice_pdf = shipment_invoice_pdf_bytes(selected_shipment, rows)
    st.download_button(
        "Reprint Shipment Invoice PDF",
        shipment_invoice_pdf,
        file_name=f"shipment_invoice_{selected_shipment.get('invoice_no') or selected_shipment.get('shipment_no')}.pdf",
        mime="application/pdf",
        key="shipment_invoice_reprint_pdf_download"
    )
else:
    st.info("No pallet rows found for selected shipment.")

render_slogan_footer()
