from delivery_common import *

page_setup()
require_page_view('delivery_reprint')
show_edit_permission_status('delivery_reprint')
ensure_delivery_columns()

show_header("Reprint Invoice", "Generate saved Delivery Invoice again in the approved PDF format")
render_delivery_subnav('delivery_reprint')

reprint_access_sql, reprint_access_params = _delivery_access_filter_sql("b", "s")
saved_delivery_invoices_for_reprint = fetch_all(f"""
    SELECT
        d.delivery_invoice_no,
        MIN(d.delivery_date) AS delivery_date,
        c.customer_name,
        s.invoice_no AS original_invoice_no,
        MAX(s.warehouse_id) AS warehouse_id,
        MAX(w.warehouse_name) AS warehouse_name,
        SUM(d.delivered_qty) AS total_qty,
        SUM(d.sale_amount) AS total_amount,
        MAX(d.currency) AS currency
    FROM customer_deliveries d
    JOIN customers c ON d.customer_id = c.id
    JOIN shipments s ON d.shipment_id = s.id
    JOIN shipment_boxes b ON d.box_id = b.id
    JOIN products p ON b.product_id = p.id
    LEFT JOIN warehouses w ON s.warehouse_id = w.id
    WHERE 1=1
    {reprint_access_sql}
    GROUP BY d.delivery_invoice_no, c.customer_name, s.invoice_no
    ORDER BY MIN(d.id) DESC
    LIMIT 200
""", reprint_access_params)

if saved_delivery_invoices_for_reprint:
    reprint_options = [
        f"{r['delivery_invoice_no']} | Original Inv {r['original_invoice_no']} | {r['customer_name']} | {r['total_qty']:,.0f} Qty | {r['total_amount']:,.2f} {r['currency']}"
        for r in saved_delivery_invoices_for_reprint
    ]
    selected_reprint_key = searchable_selectbox(
        "Select Delivery Invoice for PDF Reprint",
        reprint_options,
        key="delivery_invoice_pdf_reprint_select"
    )
    selected_reprint_invoice_no = selected_reprint_key.split(" | ")[0].strip()

    invoice_for_reprint, line_items_for_reprint = get_saved_delivery_invoice_for_pdf(selected_reprint_invoice_no)
    if invoice_for_reprint and line_items_for_reprint:
        pdf_bytes_reprint = delivery_invoice_pdf_bytes(invoice_for_reprint, line_items_for_reprint)
        st.download_button(
            "Reprint Delivery Invoice PDF",
            data=pdf_bytes_reprint,
            file_name=f"delivery_invoice_reprint_{selected_reprint_invoice_no}.pdf",
            mime="application/pdf",
            key="reprint_delivery_invoice_pdf_button"
        )
    else:
        st.warning("No saved line items found for selected Delivery Invoice.")
else:
    st.info("No saved Delivery Invoices available for reprint.")

render_slogan_footer()
