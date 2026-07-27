
from common import *
from datetime import date, datetime, timedelta

# ---------------------------------------------------------------------
# Coverage Plan page
# Calculation logic follows attached Excel sheet:
#   WH Bank = Shipment Delivery to Warehouse + Stock at WH - Delivered to Customer - Customer Forecast
#   Bank Status = WH Bank - Two Months Inventory
# Stock at WH:
#   First week = stored/imported opening stock.
#   Next weeks = previous week WH Bank unless a non-zero Stock at WH is specifically entered/imported.
# ---------------------------------------------------------------------

def local_coverage_card(title, value, header_bg="#1A5E99", value_bg="#ffffff", value_color="#111827", compact=True):
    """Compact top KPI/filter card. Used for all cards EXCEPT the final four KPI cards."""
    head_h = 34 if compact else 48
    value_h = 40 if compact else 56
    head_fs = 14 if compact else 19
    value_fs = 18 if compact else 26
    margin = 6 if compact else 10
    st.markdown(
        f"""
        <div style="width:100%;border:1px solid #cbd5e1;border-radius:4px;overflow:hidden;background:white;margin-bottom:{margin}px;box-shadow:none;">
            <div style="height:{head_h}px;background:{header_bg};color:white;display:flex;align-items:center;justify-content:center;text-align:center;font-family:Aptos,Arial,sans-serif;font-size:{head_fs}px;font-weight:900;line-height:1.08;text-transform:uppercase;padding:4px;">
                {title}
            </div>
            <div style="height:{value_h}px;background:{value_bg};color:{value_color};display:flex;align-items:center;justify-content:center;text-align:center;font-family:Aptos,Arial,sans-serif;font-size:{value_fs}px;font-weight:900;line-height:1.10;padding:4px;">
                {value}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def local_final_kpi_card(title, value, header_bg="#1A5E99", value_bg="#ffffff", value_color="#111827"):
    """Final four KPI cards. Size intentionally NOT reduced per user instruction."""
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
    """Compact input card header for product/warehouse/past/future/safety cards."""
    st.markdown(
        f"""
        <div class="coverage-input-card-header compact-coverage-input-card" style="width:100%;border:1px solid #cbd5e1;border-bottom:0;border-radius:4px 4px 0 0;overflow:hidden;background:white;margin-bottom:0;box-shadow:none;">
            <div style="height:34px;background:{header_bg};color:white;display:flex;align-items:center;justify-content:center;text-align:center;font-family:Aptos,Arial,sans-serif;font-size:14px;font-weight:900;line-height:1.08;text-transform:uppercase;padding:4px;">
                {title}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def local_coverage_input_end():
    pass

def local_filter_start(title, header_bg="#1A5E99"):
    local_coverage_input_start(title, header_bg)

def local_filter_end():
    pass

def local_table_title(title="Coverage Plan Table"):
    st.markdown(
        f'<div style="font-family:Aptos,Arial,sans-serif;font-size:32px;font-weight:900;color:#003B73;padding:12px 0 14px 0;line-height:1.2;">{title}</div>',
        unsafe_allow_html=True
    )

def normalize_product_code_for_import(value):
    if value is None:
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text

def safe_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def ensure_coverage_rows(product_id, start_week, weeks_count, two_months_inventory=0):
    """Ensure weekly rows exist for selected product using one PostgreSQL bulk insert.

    This is much faster than row-by-row SELECT/INSERT and avoids duplicate row errors.
    """
    if not product_id or not start_week or not weeks_count:
        return

    try:
        start_date = start_week if isinstance(start_week, date) else parse_db_date(start_week)
    except Exception:
        start_date = None
    if not start_date:
        return

    try:
        start_date = datetime.strptime(monday_of_date(start_date), "%Y-%m-%d").date()
    except Exception:
        start_date = start_date - timedelta(days=start_date.weekday())

    execute_query(
        """
        INSERT INTO coverage_plan_lines
        (product_id, week_no, plan_date, stock_at_wh, customer_forecast,
         shipment_delivery_qty, delivered_to_customer, wh_bank,
         two_months_inventory, bank_status, suggested_shipment_qty, next_shipment_date)
        SELECT
            ? AS product_id,
            EXTRACT(WEEK FROM gs.plan_date)::int AS week_no,
            gs.plan_date::date AS plan_date,
            0 AS stock_at_wh,
            0 AS customer_forecast,
            0 AS shipment_delivery_qty,
            0 AS delivered_to_customer,
            0 AS wh_bank,
            ? AS two_months_inventory,
            0 AS bank_status,
            0 AS suggested_shipment_qty,
            NULL AS next_shipment_date
        FROM generate_series(?::date, (?::date + ((?::int - 1) * INTERVAL '7 days')), INTERVAL '7 days') AS gs(plan_date)
        WHERE NOT EXISTS (
            SELECT 1
            FROM coverage_plan_lines c
            WHERE c.product_id = ?
              AND c.plan_date::date = gs.plan_date::date
        )
        ON CONFLICT DO NOTHING
        """,
        (
            product_id,
            two_months_inventory,
            start_date.isoformat(),
            start_date.isoformat(),
            int(weeks_count),
            product_id,
        ),
    )


def get_product_shipment_time_info(product_id, fallback_days=0):
    """Return latest warehouse and shipment days linked to selected product from Shipment Entry.

    Priority:
    1. Latest shipment.shipment_time_days for this product, if available/non-zero.
    2. Latest shipment warehouse master shipment_time_days for this product.
    3. Fallback days.
    """
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


def get_week_qty_maps(product_id, shipment_time_days):
    """Weekly quantity maps for Coverage Plan.

    SN 26.15 split:
    - Shipment Delivered to WH: status Delivered and week is warehouse_delivery_date.
    - Shipment in Transit: status not Delivered / no warehouse delivery date and week is shipment_date + shipment_time_days.
    """
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
            delivered_by_week[wk.isoformat()] = safe_float(rr.get("delivered_qty"))

    effective_days = int(shipment_time_days or 0)

    wh_delivered_rows = fetch_all("""
        WITH shipment_calc AS (
            SELECT date_trunc('week', s.warehouse_delivery_date::date)::date AS week_start,
                   b.original_qty
            FROM shipment_boxes b
            JOIN shipments s ON b.shipment_id = s.id
            WHERE b.product_id=?
              AND COALESCE(s.shipment_status,'In Transit') = 'Delivered'
              AND s.warehouse_delivery_date IS NOT NULL
        )
        SELECT week_start, COALESCE(SUM(original_qty),0) AS shipment_delivered_to_wh_qty
        FROM shipment_calc
        GROUP BY week_start
        ORDER BY week_start
    """, (product_id,))

    in_transit_rows = fetch_all("""
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
        SELECT week_start, COALESCE(SUM(original_qty),0) AS shipment_in_transit_qty
        FROM shipment_calc
        GROUP BY week_start
        ORDER BY week_start
    """, (effective_days, product_id))

    delivered_to_wh_by_week = {}
    for rr in wh_delivered_rows:
        wk = parse_db_date(rr.get("week_start"))
        if wk:
            delivered_to_wh_by_week[wk.isoformat()] = safe_float(rr.get("shipment_delivered_to_wh_qty"))

    in_transit_by_week = {}
    for rr in in_transit_rows:
        wk = parse_db_date(rr.get("week_start"))
        if wk:
            in_transit_by_week[wk.isoformat()] = safe_float(rr.get("shipment_in_transit_qty"))

    shipment_by_week = {}
    for wk in set(list(delivered_to_wh_by_week.keys()) + list(in_transit_by_week.keys())):
        shipment_by_week[wk] = safe_float(delivered_to_wh_by_week.get(wk, 0)) + safe_float(in_transit_by_week.get(wk, 0))

    invoice_week_rows = fetch_all("""
        WITH invoice_calc AS (
            SELECT DISTINCT
                   CASE
                       WHEN COALESCE(s.shipment_status,'In Transit') = 'Delivered'
                            AND s.warehouse_delivery_date IS NOT NULL
                       THEN date_trunc('week', s.warehouse_delivery_date::date)::date
                       ELSE date_trunc(
                                'week',
                                (
                                    s.shipment_date::date
                                    + (COALESCE(NULLIF(s.shipment_time_days,0), ?::int) * INTERVAL '1 day')
                                )
                            )::date
                   END AS week_start,
                   s.invoice_no
            FROM shipment_boxes b
            JOIN shipments s ON b.shipment_id = s.id
            WHERE b.product_id=?
              AND s.shipment_date IS NOT NULL
              AND COALESCE(s.invoice_no,'') <> ''
        )
        SELECT week_start,
               STRING_AGG(invoice_no, ', ' ORDER BY invoice_no) AS original_invoice_numbers
        FROM invoice_calc
        GROUP BY week_start
        ORDER BY week_start
    """, (effective_days, product_id))

    original_invoice_by_week = {}
    for rr in invoice_week_rows:
        wk = parse_db_date(rr.get("week_start"))
        if wk:
            original_invoice_by_week[wk.isoformat()] = rr.get("original_invoice_numbers") or ""

    return shipment_by_week, delivered_by_week, original_invoice_by_week, delivered_to_wh_by_week, in_transit_by_week

def calculate_coverage_rows(raw_rows, product_id, shipment_time_days, two_months_inventory, visible_start_week=None, max_rows=None):
    """Coverage Plan calculation.

    - Old/passed weeks: Customer Forecast is treated as 0.
    - Stock at WH = previous week's WH Bank. First row uses opening Stock at WH if entered/imported.
    - WH Bank = Shipment Delivery to Warehouse + Stock at WH - Delivered to Customer - Customer Forecast.
    - Suggested Shipment Qty is shown in the shortage week.
    - KPI Next Shipment Date/Qty ignores past shipment dates and uses only today/future dates.
    """
    shipment_by_week, delivered_by_week, original_invoice_by_week, delivered_to_wh_by_week, in_transit_by_week = get_week_qty_maps(product_id, shipment_time_days)

    calculated = []
    update_params = []
    previous_wh_bank = None
    demand_started = False
    next_shipment_date = ""
    next_shipment_qty = 0.0

    today_date = date.today()
    current_week_start = datetime.strptime(monday_of_date(today_date), "%Y-%m-%d").date()

    for r in raw_rows:
        week_start = parse_db_date(r.get("plan_date"))
        if not week_start:
            continue
        week_key = week_start.isoformat()

        shipment_delivery_qty = safe_float(delivered_to_wh_by_week.get(week_key, 0))
        shipment_in_transit_qty = safe_float(in_transit_by_week.get(week_key, 0))
        shipment_total_inbound_qty = shipment_delivery_qty + shipment_in_transit_qty
        original_invoice_numbers = original_invoice_by_week.get(week_key, "")
        raw_customer_forecast = safe_float(r.get("customer_forecast"))
        delivered_to_customer = safe_float(delivered_by_week.get(week_key, 0))
        stored_stock = safe_float(r.get("stock_at_wh"))

        customer_forecast = 0.0 if week_start < current_week_start else raw_customer_forecast

        if previous_wh_bank is None:
            stock_at_wh = stored_stock if abs(stored_stock) > 0.000001 else 0.0
        else:
            stock_at_wh = previous_wh_bank

        wh_bank = shipment_total_inbound_qty + stock_at_wh - delivered_to_customer - customer_forecast
        bank_status = wh_bank - two_months_inventory

        if customer_forecast > 0 or delivered_to_customer > 0:
            demand_started = True

        suggested_qty = 0.0
        suggested_date = ""
        if demand_started and bank_status < 0:
            suggested_qty = abs(bank_status)
            candidate_date_obj = week_start - timedelta(days=int(shipment_time_days or 0))
            # Table keeps suggested qty/date by shortage week; KPI ignores past dates.
            suggested_date = candidate_date_obj.isoformat()
            if candidate_date_obj >= today_date and not next_shipment_date:
                next_shipment_date = suggested_date
                next_shipment_qty = suggested_qty

        previous_wh_bank = wh_bank

        out = {
            "id": r["id"],
            "week_no": r.get("week_no"),
            "plan_date": week_key,
            "original_invoice_numbers": original_invoice_numbers,
            "shipment_delivery_qty": round(shipment_delivery_qty, 2),
            "shipment_in_transit_qty": round(shipment_in_transit_qty, 2),
            "stock_at_wh": round(stock_at_wh, 2),
            "customer_forecast": round(customer_forecast, 2),
            "delivered_to_customer": round(delivered_to_customer, 2),
            "wh_bank": round(wh_bank, 2),
            "two_months_inventory": round(two_months_inventory, 2),
            "bank_status": round(bank_status, 2),
            "suggested_shipment_qty": round(suggested_qty, 2),
            "next_shipment_date": suggested_date,
        }
        calculated.append(out)
        update_params.append((
            shipment_delivery_qty,
            delivered_to_customer,
            stock_at_wh,
            customer_forecast,
            wh_bank,
            bank_status,
            suggested_qty,
            suggested_date or None,
            two_months_inventory,
            r["id"]
        ))

    visible = []
    for row in calculated:
        wk = parse_db_date(row.get("plan_date"))
        if visible_start_week is None or (wk and wk >= visible_start_week):
            visible.append(row)
        if max_rows and len(visible) >= max_rows:
            break

    return calculated, visible, update_params, next_shipment_date, next_shipment_qty


def save_calculated_coverage(update_params):
    for item in update_params:
        execute_query("""
            UPDATE coverage_plan_lines
            SET shipment_delivery_qty=?, delivered_to_customer=?, stock_at_wh=?, customer_forecast=?,
                wh_bank=?, bank_status=?, suggested_shipment_qty=?, next_shipment_date=?, two_months_inventory=?
            WHERE id=?
        """, item)
    clear_cache_after_write()

def recalculate_coverage_for_product(product_id, shipment_time_days=0):
    product_rows = fetch_all("SELECT id, two_months_inventory FROM products WHERE id=?", (product_id,))
    if not product_rows:
        return
    two_months_inventory = safe_float(product_rows[0].get("two_months_inventory"))
    raw_rows = fetch_all("""
        SELECT id, week_no, plan_date, customer_forecast, stock_at_wh,
               shipment_delivery_qty, delivered_to_customer, wh_bank, bank_status,
               suggested_shipment_qty, next_shipment_date
        FROM coverage_plan_lines
        WHERE product_id=?
        ORDER BY date(plan_date), week_no, id
    """, (product_id,))
    if not raw_rows:
        return
    _, _, update_params, _, _ = calculate_coverage_rows(raw_rows, product_id, shipment_time_days, two_months_inventory)
    save_calculated_coverage(update_params)

def style_vertical_coverage_grid(df):
    def style_cell(value, column_name):
        col = str(column_name)
        base = "font-weight:800; text-align:center;"
        if col in ("Week No", "Week Start From"):
            return base + "background-color:#eaf3fc; color:#0a3f7a;"
        if col in ("Shipment Delivery to Warehouse", "Shipment in Transit"):
            return base + "background-color:#dcfce7; color:#166534;"
        if col == "Stock at WH":
            return base + "background-color:#e8f5e9; color:#166534;"
        if col == "Customer Forecast":
            return base + "background-color:#fef9c3; color:#854d0e;"
        if col == "Delivered to Customer":
            return base + "background-color:#e0f2fe; color:#075985;"
        if col == "WH Bank":
            return base + "background-color:#f3f4f6; color:#374151;"
        if col == "Bank Status":
            try:
                val = float(value or 0)
                if val < 0:
                    return base + "background-color:#fee2e2; color:#991b1b;"
                return base + "background-color:#d1fae5; color:#065f46;"
            except Exception:
                return base
        if col == "Suggested Shipment Qty":
            return base + "background-color:#ffedd5; color:#9a3412;"
        if col == "Next Shipment Date":
            return base + ("background-color:#fde047; color:#b91c1c;" if str(value).strip() else "")
        return base
    return df.style.apply(lambda row: [style_cell(row[col], col) for col in df.columns], axis=1)

page_setup()
ensure_shipment_status_columns()

require_page_view('coverage')
show_edit_permission_status('coverage')

st.markdown("""
<style>
/* COVERAGE PAGE UI UPDATE */
@media (min-width: 1400px) {
    .block-container {
        max-width: 1720px !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }
}
@media (max-width: 900px) {
    .coverage-input-card-header div {
        font-size: 13px !important;
    }
}
/* Compact top input cards only. Final four KPI cards are not affected. */
.compact-coverage-input-card + div[data-testid="stSelectbox"],
.compact-coverage-input-card + div[data-testid="stNumberInput"] {
    margin-top:0 !important;
    margin-bottom:6px !important;
}
.compact-coverage-input-card + div[data-testid="stSelectbox"] label,
.compact-coverage-input-card + div[data-testid="stNumberInput"] label,
.compact-coverage-input-card + div[data-testid="stSelectbox"] div[data-testid="InputInstructions"],
.compact-coverage-input-card + div[data-testid="stNumberInput"] div[data-testid="InputInstructions"] {
    display:none !important;
}
.compact-coverage-input-card + div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
.compact-coverage-input-card + div[data-testid="stNumberInput"] div[data-baseweb="input"] > div,
.compact-coverage-input-card + div[data-testid="stNumberInput"] input {
    height:40px !important;
    min-height:40px !important;
    border:1px solid #cbd5e1 !important;
    border-top:0 !important;
    border-radius:0 0 4px 4px !important;
    background:#EEF2F7 !important;
    box-shadow:none !important;
    font-family:Aptos, Arial, sans-serif !important;
    font-size:15px !important;
    font-weight:900 !important;
    color:#111827 !important;
}
.compact-coverage-input-card + div[data-testid="stSelectbox"] div[data-baseweb="select"] span {
    font-size:15px !important;
    font-weight:900 !important;
    color:#111827 !important;
}
.compact-coverage-input-card + div[data-testid="stNumberInput"] input {
    text-align:center !important;
    padding-left:4px !important;
}
</style>
""", unsafe_allow_html=True)

show_header("Coverage Plan", "Weekly customer forecast, warehouse stock and shipment planning")
access_notice()

@st.cache_data(ttl=1800, show_spinner=False)
def load_coverage_products():
    return fetch_all("""
        SELECT id, product_code, product_name, lcr_weekly, mcr_weekly, two_months_inventory
        FROM products
        ORDER BY product_code
    """)

@st.cache_data(ttl=1800, show_spinner=False)
def load_coverage_warehouses():
    return fetch_all("""
        SELECT id, warehouse_name, shipment_time_days
        FROM warehouses
        ORDER BY warehouse_name
    """)

refresh_col, _ = st.columns([1, 5])
with refresh_col:
    if st.button("Refresh Coverage Data", key="coverage_refresh_master_cache"):
        load_coverage_products.clear()
        load_coverage_warehouses.clear()
        clear_app_cache()
        st.rerun()

products = filter_product_rows_for_current_user(load_coverage_products())
warehouses = filter_warehouse_rows_for_current_user(load_coverage_warehouses())

if not products:
    st.warning("No Coverage Plan product is available for your user access. Ask Super Admin to allot the required Part Number, or leave Product Access blank for all parts.")
else:
    product_map = {f"{p['product_code']} | {p['product_name']}": p for p in products}
    product_labels = list(product_map.keys())
    default_product_index = 0
    for i, label in enumerate(product_labels):
        if str(product_map[label].get("product_code") or "") == "40257237":
            default_product_index = i
            break

    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([1.10, 0.95, 0.62, 0.62])
    with filter_col1:
        local_filter_start("PRODUCT", "#1A5E99")
        selected_product_label = st.selectbox("Product", product_labels, index=default_product_index, key="coverage_product_select", label_visibility="collapsed")
        local_filter_end()

    selected_product = product_map[selected_product_label]
    selected_product_id = selected_product["id"]

    with filter_col2:
        local_filter_start("WAREHOUSE", "#1A5E99")
        if warehouses:
            warehouse_map = {w["warehouse_name"]: w for w in warehouses}
            product_wh_name, product_ship_days = get_product_shipment_time_info(selected_product_id, 0)
            warehouse_names = list(warehouse_map.keys())
            default_wh_index = warehouse_names.index(product_wh_name) if product_wh_name in warehouse_names else 0
            selected_warehouse_name = st.selectbox("Warehouse", warehouse_names, index=default_wh_index, key="coverage_warehouse_select", label_visibility="collapsed")
            master_days = int(warehouse_map[selected_warehouse_name].get("shipment_time_days") or 0)
            shipment_time_days = int(product_ship_days or master_days or 0)
            st.caption(f"Shipment time linked from Shipment Entry/Product: {shipment_time_days} Days")
        else:
            selected_warehouse_name = ""
            product_wh_name, shipment_time_days = get_product_shipment_time_info(selected_product_id, 0)
            st.info("Create Warehouse Master and enter Shipment Time Days.")
        local_filter_end()

    with filter_col3:
        local_filter_start("PAST WEEKS", "#1A5E99")
        past_weeks = int(st.selectbox("Past Weeks", [0, 4, 8, 12, 26, 52], index=1, key="coverage_past_weeks", label_visibility="collapsed"))
        local_filter_end()

    with filter_col4:
        local_filter_start("FUTURE WEEKS", "#1A5E99")
        visible_weeks = int(st.selectbox("Future Weeks", [16, 26, 52, 78, 104], index=0, key="coverage_visible_weeks", label_visibility="collapsed"))
        local_filter_end()

    c0, c1, c2 = st.columns([0.72, 0.72, 0.72])
    with c0:
        local_coverage_card("SHIPMENT TIME DAYS", f"{shipment_time_days}", "#1A5E99", compact=True)
    with c1:
        lcr_weekly = safe_float(selected_product.get("lcr_weekly"))
        local_coverage_card("LCR WEEKLY", f"{lcr_weekly:,.0f}", "#1A5E99", compact=True)
    with c2:
        mcr_weekly = safe_float(selected_product.get("mcr_weekly"))
        local_coverage_card("MCR WEEKLY", f"{mcr_weekly:,.0f}", "#1A5E99", compact=True)

    current_week_start = datetime.strptime(monday_of_date(date.today()), "%Y-%m-%d").date()
    visible_start_week = current_week_start - timedelta(days=7 * int(past_weeks))
    total_table_weeks = int(past_weeks) + int(visible_weeks)
    required_seed_weeks = int(past_weeks) + max(52, int(visible_weeks))
    product_two_months_inventory = safe_float(selected_product.get("two_months_inventory"))

    try:
        deduplicate_coverage_plan_dates(selected_product_id)
    except Exception:
        pass

    product_linked_warehouse_name, product_linked_shipment_time_days = get_product_shipment_time_info(selected_product_id, shipment_time_days)
    if product_linked_shipment_time_days:
        shipment_time_days = int(product_linked_shipment_time_days)
    ensure_coverage_rows(selected_product_id, visible_start_week, required_seed_weeks, product_two_months_inventory)
    execute_query("UPDATE coverage_plan_lines SET two_months_inventory=? WHERE product_id=?", (product_two_months_inventory, selected_product_id))

    raw_rows = fetch_all("""
        SELECT id, week_no, plan_date, customer_forecast, stock_at_wh,
               shipment_delivery_qty, delivered_to_customer, wh_bank, bank_status,
               suggested_shipment_qty, next_shipment_date
        FROM coverage_plan_lines
        WHERE product_id=?
        ORDER BY date(plan_date), week_no, id
    """, (selected_product_id,))

    calculated_rows, visible_rows, rows_to_update, next_shipment_date, next_shipment_qty = calculate_coverage_rows(
        raw_rows,
        selected_product_id,
        shipment_time_days,
        product_two_months_inventory,
        visible_start_week,
        total_table_weeks
    )

    st.divider()

    # User requested this title above NEXT SHIPMENT DATE KPI card.
    local_table_title("Coverage Plan Table")
    st.caption("SN 26.16 note: Shipment Delivery to Warehouse means Delivered to WH qty. Shipment in Transit is shown separately.")

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        local_final_kpi_card("NEXT SHIPMENT DATE", format_date_ddmmyyyy(next_shipment_date) if next_shipment_date else "-", "#B72C24", "#ffffff", "#B72C24")
    with k2:
        local_final_kpi_card("NEXT SHIPMENT QTY", f"{next_shipment_qty:,.0f}", "#EE9337", "#ffffff", "#EE9337")
    with k3:
        local_final_kpi_card("PRODUCT", selected_product["product_code"], "#1A5E99")
    with k4:
        local_final_kpi_card("SHIPMENT TIME", f"{shipment_time_days} Days", "#1A5E99")

    vertical_rows = []
    for source_row in visible_rows:
        vertical_rows.append({
            "Week No": source_row.get("week_no"),
            "Week Start From": format_date_ddmmyyyy(source_row.get("plan_date")),
            "Original Invoice Number": source_row.get("original_invoice_numbers") or "",
            "Shipment Delivery to Warehouse": source_row.get("shipment_delivery_qty"),
            "Shipment in Transit": source_row.get("shipment_in_transit_qty"),
            "Stock at WH": source_row.get("stock_at_wh"),
            "Customer Forecast": source_row.get("customer_forecast"),
            "Delivered to Customer": source_row.get("delivered_to_customer"),
            "WH Bank": source_row.get("wh_bank"),
            "Two Months Inventory": source_row.get("two_months_inventory"),
            "Bank Status": source_row.get("bank_status"),
            "Suggested Shipment Qty": source_row.get("suggested_shipment_qty"),
            "Next Shipment Date": format_date_ddmmyyyy(source_row.get("next_shipment_date")) if source_row.get("next_shipment_date") else "",
        })

    vertical_df = pd.DataFrame(vertical_rows)

    if vertical_df.empty:
        st.info("No coverage plan data available.")
    else:
        st.markdown('<div class="sap-grid-card"><div class="sap-grid-card-title">Weekly Calculation Data</div>', unsafe_allow_html=True)
        try:
            st.dataframe(style_vertical_coverage_grid(vertical_df), width='stretch', hide_index=True)
        except Exception as table_error:
            st.warning(f"Coverage table style failed, showing plain table: {table_error}")
            st.dataframe(vertical_df, width='stretch', hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
        try:
            export_buttons(vertical_df, "coverage_plan_vertical_grid")
        except Exception as export_error:
            st.info(f"Export unavailable: {export_error}")

    recalc_col1, recalc_col2 = st.columns([1, 3])
    with recalc_col1:
        if st.button("Recalculate & Save Coverage", type="primary", key="coverage_recalculate_save"):
            save_calculated_coverage(rows_to_update)
            st.success("Coverage values recalculated and saved.")
            st.rerun()
    with recalc_col2:
        st.info(
            "Formula: WH Bank = Shipment Delivery to Warehouse + Shipment in Transit + Stock at WH - Delivered to Customer - Customer Forecast. "
            "Bank Status = WH Bank - Two Months Inventory."
        )

    st.divider()
    # SN 26.09 removed Customer Forecast / Stock at WH Input Grid section.
    st.info('Customer Forecast / Stock at WH Input Grid removed in SN 26.09. Existing coverage data is retained.')

    st.markdown('<div class="sap-subtitle">Import Customer Forecast / Stock at WH</div>', unsafe_allow_html=True)
    forecast_template_df = pd.DataFrame({
        "product_code": [selected_product["product_code"]],
        "plan_date": [date.today().isoformat()],
        "stock_at_wh": [0],
        "customer_forecast": [0],
    })
    st.download_button(
        "Download Customer Forecast Template",
        to_excel_bytes(forecast_template_df),
        "customer_forecast_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_customer_forecast_template"
    )

    st.info("Import matches PRODUCT CODE from Excel with Product Master. It is not dependent on the Product card selection. After import, select that product in the Product card to view KPI and table values.")
    forecast_file = st.file_uploader("Import Customer Forecast Excel", type=["xlsx"], key="coverage_import_forecast_excel")
    if forecast_file is not None:
        try:
            forecast_df = pd.read_excel(forecast_file)
            forecast_df.columns = [str(c).strip().lower().replace(" ", "_") for c in forecast_df.columns]
            required_cols = {"product_code", "plan_date", "customer_forecast"}
            if not required_cols.issubset(set(forecast_df.columns)):
                st.error("Excel must have columns: product_code, plan_date, customer_forecast. Optional column: stock_at_wh")
            else:
                st.dataframe(forecast_df, width='stretch', hide_index=True)
                if st.button("Update Customer Forecast / Stock at WH from Excel", type="primary", key="coverage_import_forecast_btn"):
                    product_lookup = {normalize_product_code_for_import(p.get("product_code")): p for p in products}
                    updated = inserted = skipped = 0
                    affected_product_ids = set()
                    for _, row in forecast_df.iterrows():
                        product_code = normalize_product_code_for_import(row.get("product_code"))
                        if not product_code or product_code not in product_lookup:
                            skipped += 1
                            continue
                        try:
                            plan_date_text = monday_of_date(pd.to_datetime(row.get("plan_date")).date())
                        except Exception:
                            skipped += 1
                            continue
                        product_row = product_lookup[product_code]
                        pid = product_row["id"]
                        p_two_months = safe_float(product_row.get("two_months_inventory"))
                        forecast = safe_float(row.get("customer_forecast"))
                        stock_at_wh_import = None
                        if "stock_at_wh" in forecast_df.columns and not pd.isna(row.get("stock_at_wh")):
                            stock_at_wh_import = safe_float(row.get("stock_at_wh"))

                        existing = fetch_all("SELECT id FROM coverage_plan_lines WHERE product_id=? AND plan_date=? LIMIT 1", (pid, plan_date_text))
                        if existing:
                            if stock_at_wh_import is None:
                                execute_query("UPDATE coverage_plan_lines SET customer_forecast=?, two_months_inventory=? WHERE id=?", (forecast, p_two_months, existing[0]["id"]))
                            else:
                                execute_query("UPDATE coverage_plan_lines SET customer_forecast=?, stock_at_wh=?, two_months_inventory=? WHERE id=?", (forecast, stock_at_wh_import, p_two_months, existing[0]["id"]))
                            updated += 1
                        else:
                            max_week = fetch_all("SELECT COALESCE(MAX(week_no),0) AS max_week FROM coverage_plan_lines WHERE product_id=?", (pid,))[0]["max_week"] or 0
                            execute_query("""
                                INSERT INTO coverage_plan_lines
                                (product_id, week_no, plan_date, customer_forecast, stock_at_wh,
                                 shipment_delivery_qty, delivered_to_customer, wh_bank, two_months_inventory,
                                 bank_status, suggested_shipment_qty, next_shipment_date)
                                VALUES (?, ?, ?, ?, ?, 0, 0, 0, ?, 0, 0, NULL)
                                ON CONFLICT DO NOTHING
                            """, (pid, int(max_week) + 1, plan_date_text, forecast, safe_float(stock_at_wh_import), p_two_months))
                            inserted += 1
                        affected_product_ids.add(pid)

                    for pid in affected_product_ids:
                        recalculate_coverage_for_product(pid, shipment_time_days)

                    clear_cache_after_write()
                    st.success(f"Customer Forecast / Stock at WH Import Complete. Updated: {updated}, Inserted: {inserted}, Skipped: {skipped}. Affected products recalculated: {len(affected_product_ids)}")
                    st.rerun()
        except Exception as e:
            st.error(f"Forecast import failed: {e}")

render_slogan_footer()
st.markdown('<div class="footer">COPYRIGHT BY FOUR STAR INDUSTRIES PVT. LTD.</div>', unsafe_allow_html=True)


# Safety no-op marker: suggested_shipment_qty and next_shipment_date are calculated and saved above.
