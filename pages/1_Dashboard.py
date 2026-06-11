from common import *

def local_dash_card(title, value, header_bg):
    st.markdown(
        f"""
        <div style="width:100%;height:118px;border:0;border-radius:0;overflow:hidden;background:white;margin-bottom:8px;box-shadow:none;">
            <div style="height:58px;background:{header_bg};color:white;display:flex;align-items:center;justify-content:center;text-align:center;font-family:Aptos,Arial,sans-serif;font-size:19px;font-weight:900;line-height:1.10;text-transform:uppercase;padding:5px;">
                {title}
            </div>
            <div style="height:60px;background:white;color:#111827;display:flex;align-items:center;justify-content:center;text-align:center;font-family:Aptos,Arial,sans-serif;font-size:24px;font-weight:900;line-height:1.1;padding:5px;">
                {value}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def local_coverage_card(title, value, header_bg="#1A5E99", value_bg="#ffffff", value_color="#111827"):
    st.markdown(
        f"""
        <div style="width:100%;border:1px solid #cbd5e1;border-radius:4px;overflow:hidden;background:white;margin-bottom:10px;box-shadow:none;">
            <div style="height:48px;background:{header_bg};color:white;display:flex;align-items:center;justify-content:center;text-align:center;font-family:Aptos,Arial,sans-serif;font-size:19px;font-weight:900;line-height:1.12;text-transform:uppercase;padding:6px;">
                {title}
            </div>
            <div style="height:56px;background:{value_bg};color:{value_color};display:flex;align-items:center;justify-content:center;text-align:center;font-family:Aptos,Arial,sans-serif;font-size:26px;font-weight:900;line-height:1.12;padding:6px;">
                {value}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def local_coverage_input_start(title, header_bg="#1A5E99"):
    st.markdown(
        f"""
        <div style="width:100%;border:1px solid #cbd5e1;border-bottom:0;border-radius:4px 4px 0 0;overflow:hidden;background:white;margin-bottom:0;box-shadow:none;">
            <div style="height:48px;background:{header_bg};color:white;display:flex;align-items:center;justify-content:center;text-align:center;font-family:Aptos,Arial,sans-serif;font-size:19px;font-weight:900;line-height:1.12;text-transform:uppercase;padding:6px;">
                {title}
            </div>
        </div>
        <div class="embedded-card-input-body" style="min-height:56px;border-left:1px solid #cbd5e1;border-right:1px solid #cbd5e1;border-bottom:1px solid #cbd5e1;border-radius:0 0 4px 4px;background:white;padding:6px;margin-bottom:10px;">
        """,
        unsafe_allow_html=True
    )

def local_coverage_input_end():
    st.markdown("</div>", unsafe_allow_html=True)

def local_filter_start(title, header_bg="#1A5E99"):
    local_coverage_input_start(title, header_bg)

def local_filter_end():
    local_coverage_input_end()

def local_dashboard_filter_header(title, header_bg="#FF8C00"):
    st.markdown(
        f"""
        <div class="dashboard-product-card-header" style="width:100%;border:1px solid #cbd5e1;border-bottom:0;border-radius:8px 8px 0 0;overflow:hidden;background:white;margin-bottom:0;box-shadow:none;">
            <div style="height:74px;background:{header_bg};color:white;display:flex;align-items:center;justify-content:center;text-align:center;font-family:Aptos,Arial,sans-serif;font-size:32px;font-weight:900;line-height:1.12;text-transform:uppercase;padding:8px;">
                {title}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def local_table_title(title="Coverage Plan Table"):
    st.markdown(
        f'<div style="font-family:Aptos,Arial,sans-serif;font-size:32px;font-weight:900;color:#003B73;padding:4px 0 18px 0;line-height:1.2;">{title}</div>',
        unsafe_allow_html=True
    )

page_setup(cleanup=False)

require_page_view('dashboard')


# --- Dashboard Coverage Cards: same calculation concept as Coverage Plan module ---
def dash_safe_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default

def dash_coverage_kpi_card(title, value, header_bg="#1A5E99", value_bg="#ffffff", value_color="#111827"):
    """Same size/style as final Coverage Plan KPI cards."""
    st.markdown(
        f"""
        <div style="width:100%;border:1px solid #cbd5e1;border-radius:4px;overflow:hidden;background:white;margin-bottom:10px;box-shadow:none;">
            <div style="height:48px;background:{header_bg};color:white;display:flex;align-items:center;justify-content:center;text-align:center;font-family:Aptos,Arial,sans-serif;font-size:19px;font-weight:900;line-height:1.12;text-transform:uppercase;padding:6px;">
                {title}
            </div>
            <div style="height:56px;background:{value_bg};color:{value_color};display:flex;align-items:center;justify-content:center;text-align:center;font-family:Aptos,Arial,sans-serif;font-size:26px;font-weight:900;line-height:1.12;padding:6px;">
                {value}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def dash_get_product_shipment_time_info(product_id, fallback_days=0):
    try:
        rows = fetch_all("""
            SELECT w.warehouse_name,
                   COALESCE(NULLIF(s.shipment_time_days,0), NULLIF(w.shipment_time_days,0), ?::int) AS shipment_time_days
            FROM shipment_boxes b
            JOIN shipments s ON b.shipment_id = s.id
            LEFT JOIN warehouses w ON s.warehouse_id = w.id
            WHERE b.product_id=?
            ORDER BY s.shipment_date DESC NULLS LAST, s.id DESC, b.id DESC
            LIMIT 1
        """, (int(fallback_days or 0), product_id))
        if rows:
            return rows[0].get("warehouse_name") or "", int(rows[0].get("shipment_time_days") or fallback_days or 0)
    except Exception:
        pass
    return "", int(fallback_days or 0)

def dash_get_week_qty_maps(product_id, shipment_time_days):
    delivered_week_rows = fetch_all("""
        SELECT date_trunc('week', d.delivery_date::date)::date AS week_start,
               COALESCE(SUM(d.delivered_qty),0) AS delivered_qty
        FROM customer_deliveries d
        JOIN shipment_boxes b ON d.box_id = b.id
        WHERE b.product_id=?
          AND d.delivery_date IS NOT NULL
        GROUP BY date_trunc('week', d.delivery_date::date)::date
    """, (product_id,))
    delivered_by_week = {}
    for rr in delivered_week_rows:
        wk = parse_db_date(rr.get("week_start"))
        if wk:
            delivered_by_week[wk.isoformat()] = dash_safe_float(rr.get("delivered_qty"))

    shipment_week_rows = fetch_all("""
        SELECT date_trunc('week', (s.shipment_date::date + (?::int * INTERVAL '1 day')))::date AS week_start,
               COALESCE(SUM(b.original_qty),0) AS shipment_delivery_qty
        FROM shipment_boxes b
        JOIN shipments s ON b.shipment_id = s.id
        WHERE b.product_id=?
          AND s.shipment_date IS NOT NULL
        GROUP BY date_trunc('week', (s.shipment_date::date + (?::int * INTERVAL '1 day')))::date
    """, (int(shipment_time_days), product_id, int(shipment_time_days)))
    shipment_by_week = {}
    for rr in shipment_week_rows:
        wk = parse_db_date(rr.get("week_start"))
        if wk:
            shipment_by_week[wk.isoformat()] = dash_safe_float(rr.get("shipment_delivery_qty"))

    return shipment_by_week, delivered_by_week

def dash_calculate_coverage_kpis(product_id, shipment_time_days, two_months_inventory):
    """Dashboard Coverage KPIs aligned with Coverage Plan page calculation."""
    _, product_ship_days = dash_get_product_shipment_time_info(product_id, shipment_time_days)
    if product_ship_days:
        shipment_time_days = int(product_ship_days)

    raw_rows = fetch_all("""
        SELECT id, week_no, plan_date, customer_forecast, stock_at_wh,
               shipment_delivery_qty, delivered_to_customer, wh_bank, bank_status,
               suggested_shipment_qty, next_shipment_date
        FROM coverage_plan_lines
        WHERE product_id=?
        ORDER BY date(plan_date), week_no, id
    """, (product_id,))

    shipment_by_week, delivered_by_week = dash_get_week_qty_maps(product_id, shipment_time_days)

    today_date = date.today()
    current_week_start = datetime.strptime(monday_of_date(today_date), "%Y-%m-%d").date()

    previous_wh_bank = None
    demand_started = False
    next_shipment_date = ""
    next_shipment_qty = 0.0
    current_week_found = False
    current_stock_at_wh = 0.0
    current_wh_bank = 0.0
    current_bank_status = 0.0

    for r in raw_rows:
        week_start = parse_db_date(r.get("plan_date"))
        if not week_start:
            continue
        week_key = week_start.isoformat()

        shipment_delivery_qty = dash_safe_float(shipment_by_week.get(week_key, 0))
        raw_customer_forecast = dash_safe_float(r.get("customer_forecast"))
        customer_forecast = 0.0 if week_start < current_week_start else raw_customer_forecast
        delivered_to_customer = dash_safe_float(delivered_by_week.get(week_key, 0))
        stored_stock = dash_safe_float(r.get("stock_at_wh"))

        if previous_wh_bank is None:
            stock_at_wh = stored_stock if abs(stored_stock) > 0.000001 else 0.0
        else:
            stock_at_wh = previous_wh_bank

        wh_bank = shipment_delivery_qty + stock_at_wh - delivered_to_customer - customer_forecast
        bank_status = wh_bank - two_months_inventory

        if customer_forecast > 0 or delivered_to_customer > 0:
            demand_started = True

        if demand_started and bank_status < 0:
            candidate_date_obj = week_start - timedelta(days=int(shipment_time_days or 0))
            if candidate_date_obj >= today_date and not next_shipment_date:
                next_shipment_date = candidate_date_obj.isoformat()
                next_shipment_qty = abs(bank_status)

        if week_start == current_week_start:
            current_week_found = True
            current_stock_at_wh = stock_at_wh
            current_wh_bank = wh_bank
            current_bank_status = bank_status

        previous_wh_bank = wh_bank

    if not current_week_found:
        current_stock_at_wh = 0.0
        current_wh_bank = 0.0
        current_bank_status = 0.0

    return {
        "next_shipment_date": next_shipment_date,
        "next_shipment_qty": next_shipment_qty,
        "stock_at_wh": current_stock_at_wh,
        "wh_bank": current_wh_bank,
        "bank_status": current_bank_status,
    }

show_header('Dashboard')
total_shipments = fetch_all('SELECT COUNT(*) c FROM shipments')[0]['c']
total_boxes = fetch_all('SELECT COUNT(*) c FROM shipment_boxes')[0]['c']
total_customers = fetch_all('SELECT COUNT(*) c FROM customers')[0]['c']
qty = fetch_all('\n        SELECT IFNULL((SELECT SUM(original_qty) FROM shipment_boxes),0) original_qty,\n               IFNULL((SELECT SUM(delivered_qty) FROM customer_deliveries),0) delivered_qty,\n               IFNULL((SELECT SUM(sale_amount) FROM customer_deliveries),0) total_sale\n    ')[0]
balance_qty = qty['original_qty'] - qty['delivered_qty']
stock_amount_row = fetch_all("""
    SELECT COALESCE(SUM(
        CASE
            WHEN UPPER(COALESCE(b.currency,'USD')) = 'USD'
            THEN (b.original_qty - COALESCE(d.delivered_qty,0)) * COALESCE(b.unit_price,0)
            ELSE (b.original_qty - COALESCE(d.delivered_qty,0)) * COALESCE(b.unit_price,0)
        END
    ),0) AS total_stock_balance_amount
    FROM shipment_boxes b
    LEFT JOIN (
        SELECT box_id, SUM(delivered_qty) AS delivered_qty
        FROM customer_deliveries
        GROUP BY box_id
    ) d ON b.id = d.box_id
""")[0]
total_stock_balance_amount = float(stock_amount_row.get('total_stock_balance_amount') or 0)
try:
    overdue_count = len(overdue_rows())
    overdue_amount = sum((float(r.get('pending_amount') or 0) for r in overdue_rows()))
except Exception:
    overdue_count = 0
    overdue_amount = 0
labels = [
    ('TOTAL SHIPMENTS', total_shipments, 'green'),
    ('TOTAL BOXES', total_boxes, 'teal'),
    ('DELIVERED QTY', qty['delivered_qty'], 'orange'),
    ('BALANCE QTY', balance_qty, 'blue'),
    ('TOTAL SALE', round(qty['total_sale'], 2), 'yellow'),
    ('WAREHOUSE STOCK AMOUNT', f'$ {total_stock_balance_amount:,.2f}', 'blue'),
    ('OVERDUE PAYMENTS', overdue_count, 'red'),
    ('OVERDUE PAYMENT AMOUNT', f'{overdue_amount:,.2f}', 'red'),
]
cols = st.columns(len(labels))
for col, (lab, val, cls) in zip(cols, labels):
    with col:
        card_color = (
            '#008A00' if cls == 'green'
            else '#1A5E99' if cls in ('blue', 'teal')
            else '#FF8C00' if cls in ('orange', 'yellow')
            else '#B00020'
        )
        local_dash_card(lab, val, card_color)
ui_spacer(60)

st.divider()
st.markdown(
    '<div style="font-family:Aptos,Arial,sans-serif;font-size:32px;font-weight:900;color:#003B73;padding:12px 0 14px 0;line-height:1.2;">Coverage Plan Dashboard</div>',
    unsafe_allow_html=True
)

try:
    dash_products = fetch_all("""
        SELECT id, product_code, product_name, lcr_weekly, mcr_weekly, two_months_inventory
        FROM products
        ORDER BY product_code
    """)
    dash_warehouses = fetch_all("""
        SELECT id, warehouse_name, shipment_time_days
        FROM warehouses
        ORDER BY warehouse_name
    """)

    if not dash_products:
        st.info("Create Product Master to view Coverage Plan Dashboard.")
    else:
        dash_product_map = {f"{p['product_code']} | {p['product_name']}": p for p in dash_products}
        dash_product_labels = list(dash_product_map.keys())
        dash_default_index = 0
        for i, label in enumerate(dash_product_labels):
            if str(dash_product_map[label].get("product_code") or "") == "40257237":
                dash_default_index = i
                break

        dfilter1, dfilter2 = st.columns([1.4, 0.9])
        with dfilter1:
            selected_dash_product_label = st.selectbox(
                "Coverage Product",
                dash_product_labels,
                index=dash_default_index,
                key="dashboard_coverage_product_select"
            )
        selected_dash_product = dash_product_map[selected_dash_product_label]

        with dfilter2:
            if dash_warehouses:
                dash_warehouse_map = {w["warehouse_name"]: w for w in dash_warehouses}
                selected_dash_wh = st.selectbox(
                    "Coverage Warehouse",
                    list(dash_warehouse_map.keys()),
                    key="dashboard_coverage_warehouse_select"
                )
                dash_shipment_time_days = int(dash_warehouse_map[selected_dash_wh].get("shipment_time_days") or 0)
            else:
                dash_shipment_time_days = 0
                st.warning("Create Warehouse Master to show Shipment Time.")

        dash_two_months_inventory = dash_safe_float(selected_dash_product.get("two_months_inventory"))
        dash_kpis = dash_calculate_coverage_kpis(
            selected_dash_product["id"],
            dash_shipment_time_days,
            dash_two_months_inventory
        )

        dk1, dk2, dk3, dk4 = st.columns(4)
        with dk1:
            dash_coverage_kpi_card(
                "NEXT SHIPMENT DATE",
                format_date_ddmmyyyy(dash_kpis["next_shipment_date"]) if dash_kpis["next_shipment_date"] else "-",
                "#B72C24",
                "#ffffff",
                "#B72C24"
            )
        with dk2:
            dash_coverage_kpi_card(
                "NEXT SHIPMENT QTY",
                f"{dash_kpis['next_shipment_qty']:,.0f}",
                "#EE9337",
                "#ffffff",
                "#EE9337"
            )
        with dk3:
            dash_coverage_kpi_card("PRODUCT", selected_dash_product["product_code"], "#1A5E99")
        with dk4:
            dash_coverage_kpi_card("SHIPMENT TIME", f"{dash_shipment_time_days} Days", "#1A5E99")

        dk5, dk6, dk7, dk8 = st.columns(4)
        with dk5:
            dash_coverage_kpi_card("STOCK AT WH", f"{dash_kpis['stock_at_wh']:,.0f}", "#1A5E99")
        with dk6:
            dash_coverage_kpi_card("WH BANK", f"{dash_kpis['wh_bank']:,.0f}", "#1A5E99")
        with dk7:
            bank_color = "#B72C24" if dash_kpis["bank_status"] < 0 else "#15803D"
            dash_coverage_kpi_card("BANK STATUS", f"{dash_kpis['bank_status']:,.0f}", bank_color, "#ffffff", bank_color)
        with dk8:
            dash_coverage_kpi_card("TWO MONTHS INVENTORY", f"{dash_two_months_inventory:,.0f}", "#1A5E99")

except Exception as coverage_dash_error:
    st.warning(f"Coverage Plan Dashboard could not load: {coverage_dash_error}")


render_slogan_footer()
st.markdown('<div class="footer">COPYRIGHT BY FOUR STAR INDUSTRIES PVT. LTD.</div>', unsafe_allow_html=True)
