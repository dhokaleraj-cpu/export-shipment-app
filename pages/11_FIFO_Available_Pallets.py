from delivery_common import *

page_setup()
require_page_view('delivery_fifo')
show_edit_permission_status('delivery_fifo')
ensure_delivery_columns()

show_header("FIFO Available Pallets", "Pending FIFO pallet/product rows with balance quantity")
render_delivery_subnav('delivery_fifo')
access_notice()

selected_product_id, selected_product_label, part_rows_for_fifo = delivery_part_selectbox(
    key="fifo_page_part_filter",
    label="Select Part Number"
)

invoice_shipments = fetch_available_invoice_shipments(selected_product_id)
if not invoice_shipments:
    st.info("No FIFO pallet balance available for the selected Part / user access.")
else:
    invoice_options = ["All Original Invoices / Shipments"] + [
        f"{s['invoice_no']} | Shipment {s['shipment_no']} | Balance {float(s.get('balance_qty') or 0):,.0f} | Date {s.get('shipment_date')}"
        for s in invoice_shipments
    ]
    invoice_map = {
        f"{s['invoice_no']} | Shipment {s['shipment_no']} | Balance {float(s.get('balance_qty') or 0):,.0f} | Date {s.get('shipment_date')}": s
        for s in invoice_shipments
    }
    selected_invoice_key = searchable_selectbox(
        "Filter Original Invoice / Shipment",
        invoice_options,
        key="fifo_invoice_filter",
        default_index=0
    )
    selected_ship_id = None
    if selected_invoice_key and selected_invoice_key != "All Original Invoices / Shipments":
        selected_ship_id = invoice_map[selected_invoice_key]["id"]

    sort_mode = st.radio("Sort FIFO Rows", ["FIFO ID", "Pallet Number", "Original Invoice"], horizontal=True, key="fifo_page_sort_mode")
    rows = fetch_fifo_available_rows(selected_ship_id, selected_product_id)

    if sort_mode == "Pallet Number":
        rows = sorted(rows, key=lambda x: str(x.get("pallet_no") or ""))
    elif sort_mode == "Original Invoice":
        rows = sorted(rows, key=lambda x: (str(x.get("invoice_no") or ""), int(x.get("fifo_row_id") or x.get("id") or 0)))
    else:
        rows = sorted(rows, key=lambda x: (int(x.get("fifo_row_id") or x.get("id") or 0), str(x.get("pallet_no") or "")))

    fifo_display_rows = []
    for r in rows:
        fifo_display_rows.append({
            "fifo_row_id": r.get("fifo_row_id") or r.get("id"),
            "shipment_no": r.get("shipment_no"),
            "original_invoice_no": r.get("invoice_no"),
            "warehouse_name": r.get("warehouse_name"),
            "po_number": r.get("po_number", ""),
            "po_date": r.get("po_date", ""),
            "shipment_date": r.get("shipment_date"),
            "pallet_no": r.get("pallet_no"),
            "box_no": r.get("box_no") or "-",
            "product_code": r.get("product_code"),
            "product_name": r.get("product_name"),
            "original_qty": r.get("original_qty"),
            "delivered_qty": r.get("delivered_qty"),
            "balance_qty": r.get("balance_qty"),
            "unit_price": r.get("unit_price"),
            "currency": r.get("currency"),
        })

    if fifo_display_rows:
        show_fifo_df(fifo_display_rows, "fifo_available_pallets_page")
        export_buttons(add_total_row(pd.DataFrame(fifo_display_rows)), "fifo_available_pallets")
    else:
        st.info("No FIFO available pallets found.")

render_slogan_footer()
