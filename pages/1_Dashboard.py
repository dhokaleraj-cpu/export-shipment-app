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
        WITH delivered AS (
            SELECT date_trunc('week', d.delivery_date::date)::date AS week_start,
                   d.delivered_qty
            FROM customer_deliveries d
            JOIN shipment_boxes b ON d.box_id = b.id
            WHERE b.product_id=?
              AND d.delivery_date IS NOT NULL
        )
        SELECT week_start, COALESCE(SUM(delivered_qty),0) AS delivered_qty
        FROM delivered
        GROUP BY week_start
        ORDER BY week_start
    """, (product_id,))
    delivered_by_week = {}
    for rr in delivered_week_rows:
        wk = parse_db_date(rr.get("week_start"))
        if wk:
            delivered_by_week[wk.isoformat()] = dash_safe_float(rr.get("delivered_qty"))

    effective_days = int(shipment_time_days or 0)

    wh_rows = fetch_all("""
        WITH shipment_calc AS (
            SELECT date_trunc('week', s.warehouse_delivery_date::date)::date AS week_start,
                   b.original_qty
            FROM shipment_boxes b
            JOIN shipments s ON b.shipment_id = s.id
            WHERE b.product_id=?
              AND COALESCE(s.shipment_status,'In Transit') = 'Delivered'
              AND s.warehouse_delivery_date IS NOT NULL
        )
        SELECT week_start, COALESCE(SUM(original_qty),0) AS qty
        FROM shipment_calc
        GROUP BY week_start
    """, (product_id,))

    transit_rows = fetch_all("""
        WITH shipment_calc AS (
            SELECT date_trunc(
                       'week',
                       (
                           s.shipment_date::date
                           + (COALESCE(NULLIF(s.shipment_time_days,0), ?::int) * INTERVAL '1 day')
                       )
                   )::date AS week_start,
                   b.original_qty
            FROM shipment_boxes b
            JOIN shipments s ON b.shipment_id = s.id
            WHERE b.product_id=?
              AND s.shipment_date IS NOT NULL
              AND (
                    COALESCE(s.shipment_status,'In Transit') <> 'Delivered'
                    OR s.warehouse_delivery_date IS NULL
                  )
        )
        SELECT week_start, COALESCE(SUM(original_qty),0) AS qty
        FROM shipment_calc
        GROUP BY week_start
    """, (effective_days, product_id))

    shipment_by_week = {}
    for rows in (wh_rows, transit_rows):
        for rr in rows:
            wk = parse_db_date(rr.get("week_start"))
            if wk:
                key = wk.isoformat()
                shipment_by_week[key] = dash_safe_float(shipment_by_week.get(key, 0)) + dash_safe_float(rr.get("qty"))

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
require_page_view('dashboard')
access_notice()

# ---------------------------------------------------------------------------
# Dashboard filters: product, warehouse and period.
# Default = all products/warehouses available to the logged-in user.
# ---------------------------------------------------------------------------
st.markdown(
    '<div style="font-family:Aptos,Arial,sans-serif;font-size:26px;font-weight:900;color:#003B73;padding:8px 0 10px 0;">Dashboard Filters</div>',
    unsafe_allow_html=True
)

try:
    all_products_for_dash = filter_product_rows_for_current_user(fetch_all("""
        SELECT id, product_code, product_name, two_months_inventory, lcr_weekly, mcr_weekly
        FROM products
        ORDER BY product_code
    """))
except Exception:
    all_products_for_dash = []

try:
    all_warehouses_for_dash = filter_warehouse_rows_for_current_user(fetch_all("""
        SELECT id, warehouse_name, shipment_time_days
        FROM warehouses
        ORDER BY warehouse_name
    """))
except Exception:
    all_warehouses_for_dash = []

df1, df2, df3, df4 = st.columns([2.2, 2.0, 1.1, 1.1])

with df1:
    product_option_map = {
        f"{p.get('product_code','')} | {p.get('product_name','')} | {p.get('id')}": p
        for p in all_products_for_dash
    }
    selected_product_labels = st.multiselect(
        "Product / Part Number",
        list(product_option_map.keys()),
        default=list(product_option_map.keys()),
        key="dashboard_multi_product_filter",
        help="Default all allowed products. Select one or multiple products to filter dashboard."
    )
    selected_product_ids = [int(product_option_map[x]["id"]) for x in selected_product_labels if x in product_option_map]

with df2:
    warehouse_option_map = {
        f"{w.get('warehouse_name','')} | {w.get('id')}": w
        for w in all_warehouses_for_dash
    }
    selected_warehouse_labels = st.multiselect(
        "Warehouse",
        list(warehouse_option_map.keys()),
        default=list(warehouse_option_map.keys()),
        key="dashboard_multi_warehouse_filter",
        help="Default all allowed warehouses. Select one or multiple warehouses to filter dashboard."
    )
    selected_warehouse_ids = [int(warehouse_option_map[x]["id"]) for x in selected_warehouse_labels if x in warehouse_option_map]

with df3:
    dashboard_from_date = st.date_input("From Date", value=date(date.today().year, 1, 1), key="dashboard_from_date")

with df4:
    dashboard_to_date = st.date_input("To Date", value=date.today(), key="dashboard_to_date")

if dashboard_from_date > dashboard_to_date:
    st.warning("From Date is after To Date. Please correct the period.")
    dashboard_from_date, dashboard_to_date = dashboard_to_date, dashboard_from_date

def _dash_in_clause(column_name, values):
    values = [int(v) for v in (values or [])]
    if not values:
        return "", []
    return f" AND {column_name} IN ({','.join(['?'] * len(values))}) ", values

def _dash_date_clause(column_name):
    return f" AND {column_name} IS NOT NULL AND {column_name}::date BETWEEN ?::date AND ?::date ", [str(dashboard_from_date), str(dashboard_to_date)]

# Shared Dashboard SQL filters.
# These variables are required by the KPI queries below.
product_filter_clause, product_filter_params = _dash_in_clause("b.product_id", selected_product_ids)
warehouse_filter_clause, warehouse_filter_params = _dash_in_clause("s.warehouse_id", selected_warehouse_ids)
shipment_date_clause, shipment_date_params = _dash_date_clause("s.shipment_date")

delivery_product_clause, delivery_product_params = _dash_in_clause("b.product_id", selected_product_ids)
delivery_warehouse_clause, delivery_warehouse_params = _dash_in_clause("s.warehouse_id", selected_warehouse_ids)
delivery_date_clause, delivery_date_params = _dash_date_clause("d.delivery_date")

def _dash_fetch_one(query, params=()):
    rows = fetch_all(query, tuple(params))
    return rows[0] if rows else {}

def _dash_float(v):
    try:
        return float(v or 0)
    except Exception:
        return 0.0

# ---------------------------------------------------------------------------
# Main Dashboard KPIs filtered by selected products, warehouses and period.
# ---------------------------------------------------------------------------
try:
    total_shipments_row = _dash_fetch_one(f"""
        SELECT COUNT(DISTINCT s.id) AS c
        FROM shipments s
        LEFT JOIN shipment_boxes b ON b.shipment_id = s.id
        WHERE 1=1
        {product_filter_clause}
        {warehouse_filter_clause}
        {shipment_date_clause}
    """, product_filter_params + warehouse_filter_params + shipment_date_params)
    total_shipments = int(total_shipments_row.get("c") or 0)

    total_boxes_row = _dash_fetch_one(f"""
        SELECT COUNT(b.id) AS c
        FROM shipment_boxes b
        JOIN shipments s ON b.shipment_id = s.id
        WHERE 1=1
        {product_filter_clause}
        {warehouse_filter_clause}
        {shipment_date_clause}
    """, product_filter_params + warehouse_filter_params + shipment_date_params)
    total_boxes = int(total_boxes_row.get("c") or 0)

    total_customers = int((_dash_fetch_one("SELECT COUNT(*) AS c FROM customers").get("c") or 0))

    original_qty_row = _dash_fetch_one(f"""
        SELECT COALESCE(SUM(b.original_qty),0) AS original_qty
        FROM shipment_boxes b
        JOIN shipments s ON b.shipment_id = s.id
        WHERE 1=1
        {product_filter_clause}
        {warehouse_filter_clause}
        {shipment_date_clause}
    """, product_filter_params + warehouse_filter_params + shipment_date_params)
    original_qty = _dash_float(original_qty_row.get("original_qty"))

    delivery_summary_row = _dash_fetch_one(f"""
        SELECT COALESCE(SUM(d.delivered_qty),0) AS delivered_qty,
               COALESCE(SUM(d.sale_amount),0) AS total_sale
        FROM customer_deliveries d
        LEFT JOIN shipment_boxes b ON d.box_id = b.id
        LEFT JOIN shipments s ON d.shipment_id = s.id
        WHERE 1=1
        {delivery_product_clause}
        {delivery_warehouse_clause}
        {delivery_date_clause}
    """, delivery_product_params + delivery_warehouse_params + delivery_date_params)
    delivered_qty = _dash_float(delivery_summary_row.get("delivered_qty"))
    total_sale = _dash_float(delivery_summary_row.get("total_sale"))
    balance_qty = original_qty - delivered_qty

    stock_amount_row = _dash_fetch_one(f"""
        SELECT COALESCE(SUM(
            (COALESCE(b.original_qty,0) - COALESCE(d.delivered_qty,0)) * COALESCE(b.unit_price,0)
        ),0) AS total_stock_balance_amount
        FROM shipment_boxes b
        JOIN shipments s ON b.shipment_id = s.id
        LEFT JOIN (
            SELECT box_id, SUM(delivered_qty) AS delivered_qty
            FROM customer_deliveries
            GROUP BY box_id
        ) d ON b.id = d.box_id
        WHERE 1=1
        {product_filter_clause}
        {warehouse_filter_clause}
        {shipment_date_clause}
    """, product_filter_params + warehouse_filter_params + shipment_date_params)
    total_stock_balance_amount = _dash_float(stock_amount_row.get("total_stock_balance_amount"))

    overdue_row = _dash_fetch_one(f"""
        SELECT COUNT(*) AS overdue_count,
               COALESCE(SUM(pending_amount),0) AS overdue_amount
        FROM (
            SELECT d.delivery_invoice_no,
                   MAX(d.payment_due_date) AS payment_due_date,
                   COALESCE(SUM(d.sale_amount),0) - COALESCE((
                       SELECT SUM(p.payment_amount)
                       FROM payments p
                       JOIN customer_deliveries d2 ON p.delivery_id = d2.id
                       WHERE d2.delivery_invoice_no = d.delivery_invoice_no
                   ),0) AS pending_amount
            FROM customer_deliveries d
            LEFT JOIN shipment_boxes b ON d.box_id = b.id
            LEFT JOIN shipments s ON d.shipment_id = s.id
            WHERE 1=1
            {delivery_product_clause}
            {delivery_warehouse_clause}
            AND d.payment_due_date IS NOT NULL
            AND d.payment_due_date::date <= CURRENT_DATE
            AND d.payment_due_date::date BETWEEN ?::date AND ?::date
            GROUP BY d.delivery_invoice_no
        ) x
        WHERE pending_amount > 0
    """, delivery_product_params + delivery_warehouse_params + [str(dashboard_from_date), str(dashboard_to_date)])
    overdue_count = int(overdue_row.get("overdue_count") or 0)
    overdue_amount = _dash_float(overdue_row.get("overdue_amount"))

except Exception as dash_error:
    st.error(f"Dashboard KPI calculation failed: {dash_error}")
    total_shipments = total_boxes = total_customers = overdue_count = 0
    original_qty = delivered_qty = total_sale = balance_qty = total_stock_balance_amount = overdue_amount = 0.0

labels = [
    ('TOTAL SHIPMENTS', f"{total_shipments:,}", 'green'),
    ('TOTAL BOXES', f"{total_boxes:,}", 'teal'),
    ('DELIVERED QTY', f"{delivered_qty:,.0f}", 'orange'),
    ('BALANCE QTY', f"{balance_qty:,.0f}", 'blue'),
    ('TOTAL SALE', f"{total_sale:,.2f}", 'yellow'),
    ('WAREHOUSE STOCK AMOUNT', f'$ {total_stock_balance_amount:,.2f}', 'blue'),
    ('OVERDUE PAYMENTS', f"{overdue_count:,}", 'red'),
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

ui_spacer(38)

# ---------------------------------------------------------------------------
# Coverage Plan Dashboard KPIs filtered by multiple selected products/warehouses.
# ---------------------------------------------------------------------------
st.divider()
st.markdown(
    '<div style="font-family:Aptos,Arial,sans-serif;font-size:32px;font-weight:900;color:#003B73;padding:12px 0 14px 0;line-height:1.2;">Coverage Plan Dashboard</div>',
    unsafe_allow_html=True
)

try:
    selected_products_for_coverage = [p for p in all_products_for_dash if int(p.get("id")) in set(selected_product_ids)]
    selected_warehouses_for_coverage = [w for w in all_warehouses_for_dash if int(w.get("id")) in set(selected_warehouse_ids)]

    if not selected_products_for_coverage:
        st.info("No product available for your access/filter selection.")
    else:
        # Use max shipment time from selected warehouses. If no warehouse is selected, use 0/fallback.
        if selected_warehouses_for_coverage:
            dash_shipment_time_days = max([int(w.get("shipment_time_days") or 0) for w in selected_warehouses_for_coverage])
        else:
            dash_shipment_time_days = 0

        agg_next_dates = []
        agg_next_qty = 0.0
        agg_stock_at_wh = 0.0
        agg_wh_bank = 0.0
        agg_bank_status = 0.0
        agg_two_months_inventory = 0.0

        for prod in selected_products_for_coverage:
            prod_inventory = dash_safe_float(prod.get("two_months_inventory"))
            agg_two_months_inventory += prod_inventory
            kpi = dash_calculate_coverage_kpis(prod["id"], dash_shipment_time_days, prod_inventory)
            if kpi.get("next_shipment_date"):
                agg_next_dates.append(kpi.get("next_shipment_date"))
            agg_next_qty += dash_safe_float(kpi.get("next_shipment_qty"))
            agg_stock_at_wh += dash_safe_float(kpi.get("stock_at_wh"))
            agg_wh_bank += dash_safe_float(kpi.get("wh_bank"))
            agg_bank_status += dash_safe_float(kpi.get("bank_status"))

        next_date_value = min(agg_next_dates) if agg_next_dates else None
        product_value = "ALL" if len(selected_products_for_coverage) == len(all_products_for_dash) else f"{len(selected_products_for_coverage)} PRODUCTS"
        shipment_time_value = f"{dash_shipment_time_days} Days" if dash_shipment_time_days else "-"

        dk1, dk2, dk3, dk4 = st.columns(4)
        with dk1:
            dash_coverage_kpi_card(
                "NEXT SHIPMENT DATE",
                format_date_ddmmyyyy(next_date_value) if next_date_value else "-",
                "#B72C24",
                "#ffffff",
                "#B72C24"
            )
        with dk2:
            dash_coverage_kpi_card("NEXT SHIPMENT QTY", f"{agg_next_qty:,.0f}", "#EE9337", "#ffffff", "#EE9337")
        with dk3:
            dash_coverage_kpi_card("PRODUCT", product_value, "#1A5E99")
        with dk4:
            dash_coverage_kpi_card("SHIPMENT TIME", shipment_time_value, "#1A5E99")
        dk5, dk6, dk7, dk8 = st.columns(4)
        with dk5:
            dash_coverage_kpi_card("STOCK AT WH", f"{agg_stock_at_wh:,.0f}", "#1A5E99")
        with dk6:
            dash_coverage_kpi_card("WH BANK", f"{agg_wh_bank:,.0f}", "#1A5E99")
        with dk7:
            bank_color = "#B72C24" if agg_bank_status < 0 else "#15803D"
            dash_coverage_kpi_card("BANK STATUS", f"{agg_bank_status:,.0f}", bank_color, "#ffffff", bank_color)
        with dk8:
            dash_coverage_kpi_card("TWO MONTHS INVENTORY", f"{agg_two_months_inventory:,.0f}", "#1A5E99")

except Exception as coverage_dash_error:
    st.warning(f"Coverage Plan Dashboard could not load: {coverage_dash_error}")

render_slogan_footer()
