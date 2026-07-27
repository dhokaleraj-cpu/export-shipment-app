from common import *

page_setup()
require_page_view("shipment_status")
show_edit_permission_status("shipment_status")

show_header("Shipment Status", "Delivered to WH / In Transit status update")
access_notice()
render_shipment_subnav("shipment_status")
ensure_shipment_status_columns()
render_tuesday_shipment_status_popup()

can_edit_status = current_user_can_edit("shipment_status") or current_user_can_edit("shipment") or st.session_state.get("user", {}).get("role") == "super_admin"
if not can_edit_status:
    st.info("You have View permission only. Status update is disabled for this user.")

st.caption("Delivered shipments use Delivered to WH Date in Coverage Plan. In Transit shipments use Shipment Date + Shipment Time Days.")

filter_c1, filter_c2, filter_c3 = st.columns([1, 1, 2])
with filter_c1:
    status_filter = st.selectbox("Status Filter", ["All", "In Transit", "Delivered"], index=0, key="shipment_status_page_filter")
with filter_c2:
    row_limit = st.selectbox("Rows", [50, 100, 150, 300, 500], index=2, key="shipment_status_page_rows")
with filter_c3:
    text_filter = st.text_input("Search Shipment / Original Invoice / Customer / Warehouse", key="shipment_status_page_search")

where_sql = ""
params = []
if status_filter != "All":
    where_sql += " AND COALESCE(s.shipment_status,'In Transit')=? "
    params.append(status_filter)
if text_filter.strip():
    like = "%" + text_filter.strip().lower() + "%"
    where_sql += """
        AND (
            LOWER(COALESCE(s.shipment_no,'')) LIKE ?
            OR LOWER(COALESCE(s.invoice_no,'')) LIKE ?
            OR LOWER(COALESCE(c.customer_name,'')) LIKE ?
            OR LOWER(COALESCE(w.warehouse_name,'')) LIKE ?
        )
    """
    params.extend([like, like, like, like])

status_rows = fetch_all(f"""
    SELECT s.id, s.shipment_no, s.invoice_no, s.shipment_date,
           COALESCE(s.shipment_status,'In Transit') AS shipment_status,
           s.warehouse_delivery_date,
           s.shipment_time_days,
           w.warehouse_name,
           c.customer_name,
           s.shipment_status_updated_at
    FROM shipments s
    LEFT JOIN warehouses w ON w.id = s.warehouse_id
    LEFT JOIN customers c ON c.id = s.customer_id
    WHERE 1=1
    {where_sql}
    ORDER BY s.id DESC
    LIMIT {int(row_limit)}
""", tuple(params))

if not status_rows:
    st.info("No shipments found for selected filters.")
    render_slogan_footer()
    st.stop()

st.subheader("Shipment Status Update")
status_map = {
    f"{r.get('id')} | {r.get('shipment_no')} | {r.get('invoice_no')} | {r.get('shipment_status')} | WH Date {format_date_ddmmyyyy(r.get('warehouse_delivery_date')) if r.get('warehouse_delivery_date') else '-'}": r
    for r in status_rows
}
selected_status_key = st.selectbox("Select Shipment to Update Status", list(status_map.keys()), key="shipment_status_subpage_select")
selected_status_row = status_map[selected_status_key]

su1, su2, su3 = st.columns([1, 1, 1])
with su1:
    updated_status = st.selectbox(
        "Update Status",
        ["In Transit", "Delivered"],
        index=1 if selected_status_row.get("shipment_status") == "Delivered" else 0,
        key=f"shipment_status_subpage_status_{selected_status_row.get('id')}"
    )
with su2:
    if updated_status == "Delivered":
        updated_wh_date = st.date_input(
            "Delivered to WH Date",
            value=parse_date_for_input(selected_status_row.get("warehouse_delivery_date")),
            key=f"shipment_status_subpage_wh_date_{selected_status_row.get('id')}"
        )
    else:
        updated_wh_date = None
        st.info("No Delivered to WH Date applicable for In Transit.")
with su3:
    st.write("")
    st.write("")
    if st.button("Save Shipment Status", type="primary", key=f"shipment_status_subpage_save_{selected_status_row.get('id')}", disabled=not can_edit_status):
        execute_query("""
            UPDATE shipments
            SET shipment_status=?, warehouse_delivery_date=?, shipment_status_updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        """, (updated_status, str(updated_wh_date) if updated_wh_date else None, selected_status_row.get("id")))
        clear_cache_after_write()
        st.success("Shipment status updated successfully.")
        st.rerun()

st.subheader("Shipment Status List")
status_df = pd.DataFrame(format_date_columns(status_rows))
st.dataframe(status_df, width="stretch", hide_index=True)
try:
    export_buttons(status_df, "shipment_status_list")
except Exception:
    pass

render_slogan_footer()
