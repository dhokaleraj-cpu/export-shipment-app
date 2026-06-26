from delivery_common import *

page_setup()
require_page_view('delivery_edit')
show_edit_permission_status('delivery_edit')
ensure_delivery_columns()

show_header("Edit Delivery Invoice", "Modify saved delivery invoice records")
render_delivery_subnav('delivery_edit')
access_notice()

if not current_user_can_edit("delivery_edit"):
    st.error("You have View permission but not Edit permission for Edit Delivery Invoice page. Contact Super Admin.")
    st.stop()

cleanup_orphan_transactions()

edit_access_sql, edit_access_params = _delivery_access_filter_sql("b", "s")
old_deliveries = fetch_all(f"""
    SELECT
        d.*,
        c.customer_name,
        s.invoice_no AS original_invoice_no,
        s.shipment_no,
        s.warehouse_id,
        w.warehouse_name,
        b.product_id,
        p.product_code,
        p.product_name,
        b.pallet_no,
        b.box_no
    FROM customer_deliveries d
    JOIN customers c ON d.customer_id = c.id
    JOIN shipments s ON d.shipment_id = s.id
    JOIN shipment_boxes b ON d.box_id = b.id
    JOIN products p ON b.product_id = p.id
    LEFT JOIN warehouses w ON s.warehouse_id = w.id
    WHERE 1=1
    {edit_access_sql}
    ORDER BY d.id DESC
    LIMIT 500
""", edit_access_params)

if not old_deliveries:
    st.info("No delivery invoices available for edit as per your product/warehouse access.")
else:
    dmap = {
        f"{d['id']} | {d['delivery_invoice_no']} | {d['customer_name']} | {d['product_code']} | Qty {d['delivered_qty']}": d
        for d in old_deliveries
    }
    selected_key = searchable_selectbox("Select Delivery Invoice Row to Edit", list(dmap.keys()), key="edit_delivery_invoice_row_select")
    ed = dmap[selected_key]

    st.info(
        f"Loaded Delivery ID {ed.get('id')} | Delivery Invoice {ed.get('delivery_invoice_no')} | "
        f"Original Invoice {ed.get('original_invoice_no')} | Product {ed.get('product_code')}"
    )

    edit_suffix = str(ed.get("id"))
    dc1, dc2 = st.columns(2)
    with dc1:
        ed_inv = st.text_input("Edit Delivery Invoice No", ed.get("delivery_invoice_no") or "", key=f"edit_delivery_inv_{edit_suffix}")
        ed_date = st.text_input("Edit Delivery Date YYYY-MM-DD", str(ed.get("delivery_date") or ""), key=f"edit_delivery_date_{edit_suffix}")
        ed_qty = st.number_input("Edit Delivered Qty", min_value=0.0, value=float(ed.get("delivered_qty") or 0), step=1.0, key=f"edit_delivery_qty_{edit_suffix}")
        ed_vehicle = st.text_input("Edit Vehicle Number", ed.get("vehicle_number") or "", key=f"edit_delivery_vehicle_{edit_suffix}")
        ed_asn_no = st.text_input("Edit ASN Number", ed.get("asn_number") or "", key=f"edit_delivery_asn_no_{edit_suffix}")
    with dc2:
        ed_price = st.number_input("Edit Unit Price", min_value=0.0, value=float(ed.get("unit_price") or 0), step=1.0, key=f"edit_delivery_price_{edit_suffix}")
        ed_currency = st.selectbox("Edit Currency", CURRENCIES, index=CURRENCIES.index(ed.get("currency")) if ed.get("currency") in CURRENCIES else 0, key=f"edit_delivery_currency_{edit_suffix}")
        ed_due = st.text_input("Edit Payment Due Date YYYY-MM-DD", str(ed.get("payment_due_date") or ""), key=f"edit_delivery_due_{edit_suffix}")
        ed_asn_date = st.text_input("Edit ASN Date YYYY-MM-DD", str(ed.get("asn_date") or ""), key=f"edit_delivery_asn_date_{edit_suffix}")
        ed_packaging = st.text_input("Edit Packaging Details", ed.get("packaging_details") or "", key=f"edit_delivery_packaging_{edit_suffix}")
        ed_packaging_remark = st.text_input("Edit Remarks", ed.get("packaging_remark") or "", key=f"edit_delivery_remarks_{edit_suffix}")

    ed_amount = float(ed_qty or 0) * float(ed_price or 0)
    st.markdown(f'<div class="total-box">New Sale Amount: {ed_amount:,.2f} {ed_currency}</div>', unsafe_allow_html=True)

    if st.button("Update Delivery Invoice Row", type="primary", key=f"update_delivery_invoice_{edit_suffix}"):
        execute_query("""
            UPDATE customer_deliveries
            SET delivery_invoice_no=?,
                delivery_date=?,
                delivered_qty=?,
                unit_price=?,
                currency=?,
                sale_amount=?,
                payment_due_date=?,
                vehicle_number=?,
                asn_number=?,
                asn_date=?,
                packaging_details=?,
                packaging_remark=?
            WHERE id=?
        """, (
            ed_inv.strip(),
            ed_date.strip(),
            ed_qty,
            ed_price,
            ed_currency,
            ed_amount,
            ed_due.strip(),
            ed_vehicle.strip(),
            ed_asn_no.strip(),
            ed_asn_date.strip() or None,
            ed_packaging.strip(),
            ed_packaging_remark.strip(),
            ed["id"],
        ))
        st.success("Delivery invoice row updated successfully.")
        clear_cache_after_write()
        st.rerun()

render_slogan_footer()
