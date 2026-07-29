from delivery_common import *
import zipfile

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
        STRING_AGG(DISTINCT s.invoice_no, ', ' ORDER BY s.invoice_no) AS original_invoice_no,
        STRING_AGG(DISTINCT s.shipment_no, ', ' ORDER BY s.shipment_no) AS shipment_no,
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
    GROUP BY d.delivery_invoice_no, c.customer_name
    ORDER BY MIN(d.id) DESC
    LIMIT 500
""", reprint_access_params)

if saved_delivery_invoices_for_reprint:
    reprint_options = [
        f"{r['delivery_invoice_no']} | Original Inv {r.get('original_invoice_no') or '-'} | {r['customer_name']} | {float(r.get('total_qty') or 0):,.3f} Qty | {float(r.get('total_amount') or 0):,.3f} {r.get('currency') or ''}"
        for r in saved_delivery_invoices_for_reprint
    ]
    selected_reprint_keys = st.multiselect(
        "Select one or more Delivery Invoices for PDF Reprint",
        reprint_options,
        key="delivery_invoice_pdf_reprint_multi_select"
    )

    if selected_reprint_keys:
        selected_invoice_numbers = [x.split(" | ")[0].strip() for x in selected_reprint_keys]

        st.caption(f"Selected Delivery Invoices: {len(selected_invoice_numbers)}")

        generated = []
        failed = []
        for inv_no in selected_invoice_numbers:
            try:
                invoice_for_reprint, line_items_for_reprint = get_saved_delivery_invoice_for_pdf(inv_no)
                if invoice_for_reprint and line_items_for_reprint:
                    pdf_bytes_reprint = delivery_invoice_pdf_bytes(invoice_for_reprint, line_items_for_reprint)
                    generated.append((inv_no, pdf_bytes_reprint))
                else:
                    failed.append((inv_no, "No saved line items found"))
            except Exception as pdf_error:
                failed.append((inv_no, str(pdf_error)))

        if generated:
            if len(generated) == 1:
                inv_no, pdf_bytes = generated[0]
                st.download_button(
                    "Reprint Delivery Invoice PDF",
                    data=pdf_bytes,
                    file_name=f"delivery_invoice_reprint_{inv_no}.pdf",
                    mime="application/pdf",
                    key="reprint_delivery_invoice_pdf_button_single"
                )
            else:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for inv_no, pdf_bytes in generated:
                        safe_name = str(inv_no).replace("/", "_").replace("\\", "_")
                        zip_file.writestr(f"delivery_invoice_reprint_{safe_name}.pdf", pdf_bytes)
                st.download_button(
                    "Download Selected Delivery Invoice PDFs as ZIP",
                    data=zip_buffer.getvalue(),
                    file_name=f"delivery_invoice_reprints_{len(generated)}_invoices.zip",
                    mime="application/zip",
                    key="reprint_delivery_invoice_pdf_zip_button"
                )

            with st.expander("Generated PDF List", expanded=False):
                st.write([x[0] for x in generated])

        if failed:
            st.warning("Some invoices could not be generated.")
            st.dataframe(pd.DataFrame([{"delivery_invoice_no": x[0], "error": x[1]} for x in failed]), width="stretch", hide_index=True)
    else:
        st.info("Select one or more delivery invoices to generate PDF.")
else:
    st.info("No saved Delivery Invoices available for reprint.")

render_slogan_footer()
