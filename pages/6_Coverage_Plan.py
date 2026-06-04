
from common import *

# ---------------------------------------------------------------------
# Coverage Plan page
# Calculation logic follows attached Excel sheet:
#   WH Bank = Stock at WH + Shipment Delivery to Warehouse - Customer Forecast - Delivered to Customer
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

def get_week_qty_maps(product_id, shipment_time_days):
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
            delivered_by_week[wk.isoformat()] = safe_float(rr.get("delivered_qty"))

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
            shipment_by_week[wk.isoformat()] = safe_float(rr.get("shipment_delivery_qty"))

    return shipment_by_week, delivered_by_week

def ensure_coverage_rows(product_id, visible_start_week, total_weeks, two_months_inventory):
    date_rows = fetch_all("""
        SELECT plan_date
        FROM coverage_plan_lines
        WHERE product_id=?
        ORDER BY date(plan_date)
    """, (product_id,))
    existing_dates = {str(r.get("plan_date"))[:10] for r in date_rows if r.get("plan_date")}
    max_week_seed = int(fetch_all(
        "SELECT COALESCE(MAX(week_no),0) AS max_week FROM coverage_plan_lines WHERE product_id=?",
        (product_id,)
    )[0]["max_week"] or 0)

    inserted = 0
    for i in range(total_weeks):
        plan_date_text = (visible_start_week + timedelta(days=7 * i)).isoformat()
        if plan_date_text in existing_dates:
            continue
        max_week_seed += 1
        execute_query("""
            INSERT INTO coverage_plan_lines
            (product_id, week_no, plan_date, customer_forecast, stock_at_wh,
             shipment_delivery_qty, delivered_to_customer, wh_bank, two_months_inventory,
             bank_status, suggested_shipment_qty, next_shipment_date)
            VALUES (?, ?, ?, 0, 0, 0, 0, 0, ?, 0, 0, NULL)
            ON CONFLICT DO NOTHING
        """, (product_id, max_week_seed, plan_date_text, two_months_inventory))
        inserted += 1
    if inserted:
        clear_cache_after_write()


def calculate_coverage_rows(raw_rows, product_id, shipment_time_days, two_months_inventory, visible_start_week=None, max_rows=None):
    """Excel-style weekly running calculation.

    Corrected rules:
    1. Stock at WH remains ZERO until the first automatic Shipment Delivery
       to Warehouse quantity appears for the selected product.
    2. Stock at WH never rolls forward as a negative value.
       If previous week's WH Bank is negative, next week's Stock at WH becomes 0.
    3. After first shipment receipt, Stock at WH rolls from previous week's
       positive WH Bank unless a non-zero manual/imported Stock at WH is entered.
    4. Suggested Shipment Qty and Next Shipment Date start only from the first
       week where Customer Forecast or Delivered to Customer has quantity.
    """
    shipment_by_week, delivered_by_week = get_week_qty_maps(product_id, shipment_time_days)

    calculated = []
    update_params = []
    previous_wh_bank = 0.0
    shipment_receipt_started = False
    demand_started = False
    next_shipment_date = ""
    next_shipment_qty = 0.0

    for r in raw_rows:
        week_start = parse_db_date(r.get("plan_date"))
        if not week_start:
            continue
        week_key = week_start.isoformat()

        shipment_delivery_qty = safe_float(shipment_by_week.get(week_key, 0))
        customer_forecast = safe_float(r.get("customer_forecast"))
        delivered_to_customer = safe_float(delivered_by_week.get(week_key, 0))
        stored_stock = safe_float(r.get("stock_at_wh"))

        if shipment_delivery_qty > 0:
            shipment_receipt_started = True

        if customer_forecast > 0 or delivered_to_customer > 0:
            demand_started = True

        # Stock at WH:
        # Before first automatic shipment receipt, keep zero.
        # After receipt starts:
        #   - manual/imported positive stock overrides,
        #   - otherwise roll forward previous WH Bank,
        #   - but never below zero.
        if not shipment_receipt_started:
            stock_at_wh = 0.0
        else:
            if stored_stock > 0:
                stock_at_wh = stored_stock
            else:
                stock_at_wh = max(previous_wh_bank, 0.0)

        # Formula:
        # WH Bank = Stock at WH + Shipment Delivery to Warehouse - Customer Forecast - Delivered to Customer
        wh_bank = stock_at_wh + shipment_delivery_qty - customer_forecast - delivered_to_customer

        # Bank Status = WH Bank - Two Months Inventory
        bank_status = wh_bank - two_months_inventory

        # Suggested shipment starts only from first demand week.
        if demand_started and bank_status < 0:
            suggested_qty = abs(bank_status)
            suggested_date = (week_start - timedelta(days=int(shipment_time_days))).isoformat()
        else:
            suggested_qty = 0.0
            suggested_date = ""

        if demand_started and suggested_qty > 0 and not next_shipment_date:
            next_shipment_date = suggested_date
            next_shipment_qty = suggested_qty

        # Roll forward WH Bank, but Stock at WH will use max(previous_wh_bank, 0)
        # in the next week, so negative WH Bank will not become negative stock.
        previous_wh_bank = wh_bank if shipment_receipt_started else 0.0

        out = {
            "id": r["id"],
            "week_no": r.get("week_no"),
            "plan_date": week_key,
            "shipment_delivery_qty": round(shipment_delivery_qty, 2),
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
            SET shipment_delivery_qty=?, delivered_to_customer=?, stock_at_wh=?, wh_bank=?, bank_status=?,
                suggested_shipment_qty=?, next_shipment_date=?, two_months_inventory=?
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
        if col == "Shipment Delivery to Warehouse":
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

products = load_coverage_products()
warehouses = load_coverage_warehouses()

if not products:
    st.warning("Please create Product Master first.")
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
            selected_warehouse_name = st.selectbox("Warehouse", list(warehouse_map.keys()), key="coverage_warehouse_select", label_visibility="collapsed")
            shipment_time_days = int(warehouse_map[selected_warehouse_name].get("shipment_time_days") or 0)
        else:
            selected_warehouse_name = ""
            shipment_time_days = 0
            st.info("Create Warehouse Master and enter Shipment Time Days.")
        local_filter_end()

    with filter_col3:
        local_filter_start("PAST WEEKS", "#1A5E99")
        past_weeks = int(st.selectbox("Past Weeks", [0, 4, 8, 12, 26, 52], index=0, key="coverage_past_weeks", label_visibility="collapsed"))
        local_filter_end()

    with filter_col4:
        local_filter_start("FUTURE WEEKS", "#1A5E99")
        visible_weeks = int(st.selectbox("Future Weeks", [16, 26, 52, 78, 104], index=0, key="coverage_visible_weeks", label_visibility="collapsed"))
        local_filter_end()

    c0, c1, c2, c3 = st.columns([0.72, 0.72, 0.72, 0.72])
    with c0:
        local_coverage_card("SHIPMENT TIME DAYS", f"{shipment_time_days}", "#1A5E99", compact=True)
    with c1:
        local_coverage_input_start("SAFETY STOCK DAYS", "#1A5E99")
        safety_stock_days = st.number_input("Safety Stock Days", min_value=0, value=60, step=1, key="coverage_safety_days", label_visibility="collapsed")
        local_coverage_input_end()
    with c2:
        lcr_weekly = safe_float(selected_product.get("lcr_weekly"))
        local_coverage_card("LCR WEEKLY", f"{lcr_weekly:,.0f}", "#1A5E99", compact=True)
    with c3:
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
            "Shipment Delivery to Warehouse": source_row.get("shipment_delivery_qty"),
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
            st.dataframe(style_vertical_coverage_grid(vertical_df), use_container_width=True, hide_index=True)
        except Exception as table_error:
            st.warning(f"Coverage table style failed, showing plain table: {table_error}")
            st.dataframe(vertical_df, use_container_width=True, hide_index=True)
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
            "Formula: WH Bank = Stock at WH + Shipment Delivery to Warehouse - Customer Forecast - Delivered to Customer. "
            "Bank Status = WH Bank - Two Months Inventory."
        )

    st.divider()
    st.markdown('<div class="sap-subtitle">Customer Forecast / Stock at WH Input Grid</div>', unsafe_allow_html=True)
    st.markdown('<div class="sap-grid-note">Edit Customer Forecast and Stock at WH by Week Start. Values update the Coverage Plan table calculation.</div>', unsafe_allow_html=True)

    forecast_rows = [r for r in visible_rows]
    if forecast_rows:
        grid_values = {}
        id_by_label = {}
        for r in forecast_rows:
            dt = parse_db_date(r.get("plan_date"))
            label = f"W{r.get('week_no')} | Week Start {dt.strftime('%d-%m-%Y')}" if dt else f"W{r.get('week_no')}"
            grid_values[label] = {
                "Stock at WH": safe_float(r.get("stock_at_wh")),
                "Customer Forecast": safe_float(r.get("customer_forecast")),
            }
            id_by_label[label] = r["id"]
        input_grid = pd.DataFrame(grid_values)
        try:
            edited_input_grid = st.data_editor(input_grid, use_container_width=True, key="coverage_forecast_stock_horizontal_grid", num_rows="fixed")
        except Exception as editor_error:
            st.warning(f"Forecast / Stock input grid could not load as editor: {editor_error}")
            st.dataframe(input_grid, use_container_width=True)
            edited_input_grid = input_grid

        if st.button("Save Forecast / Stock at WH Grid", type="primary", key="coverage_save_forecast_stock_grid"):
            for label, record_id in id_by_label.items():
                new_stock = safe_float(edited_input_grid.loc["Stock at WH", label])
                new_forecast = safe_float(edited_input_grid.loc["Customer Forecast", label])
                execute_query("UPDATE coverage_plan_lines SET stock_at_wh=?, customer_forecast=? WHERE id=?", (new_stock, new_forecast, record_id))
            clear_cache_after_write()
            st.success("Customer Forecast and Stock at WH updated. Coverage table will recalculate immediately.")
            st.rerun()

    with st.expander("Detailed calculated rows", expanded=False):
        detail_df = pd.DataFrame(format_date_columns(visible_rows))
        if not detail_df.empty and "id" in detail_df.columns:
            detail_df = detail_df.drop(columns=["id"])
        if detail_df.empty:
            st.info("No detailed data available.")
        else:
            st.dataframe(detail_df, use_container_width=True, hide_index=True)

    st.divider()
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
                st.dataframe(forecast_df, use_container_width=True, hide_index=True)
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

st.markdown('<div class="footer">COPYRIGHT BY FOUR STAR INDUSTRIES PVT. LTD.</div>', unsafe_allow_html=True)
