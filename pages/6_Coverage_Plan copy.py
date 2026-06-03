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
        <div class="coverage-input-card-header" style="width:100%;border:1px solid #cbd5e1;border-bottom:0;border-radius:4px 4px 0 0;overflow:hidden;background:white;margin-bottom:0;box-shadow:none;">
            <div style="height:48px;background:{header_bg};color:white;display:flex;align-items:center;justify-content:center;text-align:center;font-family:Aptos,Arial,sans-serif;font-size:19px;font-weight:900;line-height:1.12;text-transform:uppercase;padding:6px;">
                {title}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def local_coverage_input_end():
    # No closing div needed. The Streamlit widget directly below is styled as the card body.
    pass

def local_filter_start(title, header_bg="#1A5E99"):
    local_coverage_input_start(title, header_bg)

def local_filter_end():
    pass

def local_dashboard_filter_header(title, header_bg="#FF8C00"):
    local_coverage_input_start(title, header_bg)

def local_table_title(title="Coverage Plan Table"):
    st.markdown(
        f'<div style="font-family:Aptos,Arial,sans-serif;font-size:32px;font-weight:900;color:#003B73;padding:4px 0 18px 0;line-height:1.2;">{title}</div>',
        unsafe_allow_html=True
    )

page_setup()

show_header('Coverage Plan', 'Weekly customer forecast, warehouse stock and shipment planning')

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
    st.warning('Please create Product Master first.')
else:
    product_map = {f"{p['product_code']} | {p['product_name']}": p for p in products}
    product_labels = list(product_map.keys())
    default_product_index = 0
    for i, label in enumerate(product_labels):
        if str(product_map[label].get('product_code') or '') == '40257237':
            default_product_index = i
            break

    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([1.35, 1.05, 0.85, 0.85])
    with filter_col1:
        local_filter_start('PRODUCT', '#1A5E99')
        selected_product_label = st.selectbox(
            'Product',
            product_labels,
            index=default_product_index,
            key='coverage_product_select',
            label_visibility='collapsed'
        )
        local_filter_end()
    selected_product = product_map[selected_product_label]

    with filter_col2:
        local_filter_start('WAREHOUSE', '#1A5E99')
        if warehouses:
            warehouse_map = {w['warehouse_name']: w for w in warehouses}
            selected_warehouse_name = st.selectbox(
                'Warehouse',
                list(warehouse_map.keys()),
                key='coverage_warehouse_select',
                label_visibility='collapsed'
            )
            shipment_time_days = int(warehouse_map[selected_warehouse_name].get('shipment_time_days') or 0)
        else:
            shipment_time_days = 0
            st.info('Create Warehouse Master and enter Shipment Time Days.')
        local_filter_end()

    with filter_col3:
        local_filter_start('PAST WEEKS', '#1A5E99')
        past_weeks = int(st.selectbox('Past Weeks', [0, 4, 8, 12, 26, 52], index=3, key='coverage_past_weeks', label_visibility='collapsed'))
        local_filter_end()

    with filter_col4:
        local_filter_start('FUTURE WEEKS', '#1A5E99')
        visible_weeks = int(st.selectbox('Future Weeks', [16, 26, 52, 78, 104], index=0, key='coverage_visible_weeks', label_visibility='collapsed'))
        local_filter_end()


    c0, c1, c2, c3 = st.columns(4)
    with c0:
        local_coverage_card('SHIPMENT TIME DAYS', f'{shipment_time_days}', '#1A5E99')
    with c1:
        local_coverage_input_start('SAFETY STOCK DAYS', '#1A5E99')
        safety_stock_days = st.number_input('Safety Stock Days', min_value=0, value=60, step=1, key='coverage_safety_days', label_visibility='collapsed')
        local_coverage_input_end()
    with c2:
        lcr_weekly = float(selected_product.get('lcr_weekly') or 0)
        local_coverage_card('LCR WEEKLY', f'{lcr_weekly:,.0f}', '#1A5E99')
    with c3:
        mcr_weekly = float(selected_product.get('mcr_weekly') or 0)
        local_coverage_card('MCR WEEKLY', f'{mcr_weekly:,.0f}', '#1A5E99')

    current_week_start = datetime.strptime(monday_of_date(date.today()), '%Y-%m-%d').date()
    visible_start_week = current_week_start - timedelta(days=7 * int(past_weeks))
    product_two_months_inventory = float(selected_product.get('two_months_inventory') or 0)

    try:
        deduplicate_coverage_plan_dates(selected_product['id'])
    except Exception:
        pass

    existing_any = fetch_all('SELECT COUNT(*) AS c FROM coverage_plan_lines WHERE product_id=?', (selected_product['id'],))[0]['c'] or 0
    if existing_any == 0:
        for i in range(52):
            new_date = current_week_start + timedelta(days=7 * i)
            execute_query('''
                INSERT INTO coverage_plan_lines
                (product_id, week_no, plan_date, customer_forecast, stock_at_wh,
                 shipment_delivery_qty, delivered_to_customer, wh_bank, two_months_inventory,
                 bank_status, suggested_shipment_qty, next_shipment_date)
                VALUES (?, ?, ?, 0, 0, 0, 0, 0, ?, 0, 0, NULL)
            ''', (selected_product['id'], i + 1, new_date.isoformat(), product_two_months_inventory))

    date_rows = fetch_all('''
        SELECT plan_date
        FROM coverage_plan_lines
        WHERE product_id=?
        ORDER BY date(plan_date)
    ''', (selected_product['id'],))
    existing_future_dates = {str(r.get('plan_date'))[:10] for r in date_rows if r.get('plan_date')}
    required_dates = [(visible_start_week + timedelta(days=7 * i)).isoformat() for i in range(int(past_weeks) + max(52, visible_weeks))]
    max_week_seed = int(fetch_all('SELECT COALESCE(MAX(week_no),0) AS max_week FROM coverage_plan_lines WHERE product_id=?', (selected_product['id'],))[0]['max_week'] or 0)
    inserted_missing = 0
    for plan_date_text in required_dates:
        if plan_date_text in existing_future_dates:
            continue
        max_week_seed += 1
        execute_query('''
            INSERT INTO coverage_plan_lines
            (product_id, week_no, plan_date, customer_forecast, stock_at_wh,
             shipment_delivery_qty, delivered_to_customer, wh_bank, two_months_inventory,
             bank_status, suggested_shipment_qty, next_shipment_date)
            VALUES (?, ?, ?, 0, 0, 0, 0, 0, ?, 0, 0, NULL)
            ON CONFLICT DO NOTHING
        ''', (selected_product['id'], max_week_seed, plan_date_text, product_two_months_inventory))
        inserted_missing += 1
    if inserted_missing:
        clear_cache_after_write()

    execute_query('UPDATE coverage_plan_lines SET two_months_inventory=? WHERE product_id=?', (product_two_months_inventory, selected_product['id']))
    ui_spacer(60)
    st.divider()
    local_table_title('Coverage Plan Table')

    raw_rows = fetch_all('''
        SELECT id, week_no, plan_date, customer_forecast, stock_at_wh, two_months_inventory,
               shipment_delivery_qty, delivered_to_customer, wh_bank, bank_status,
               suggested_shipment_qty, next_shipment_date
        FROM coverage_plan_lines
        WHERE product_id=?
        ORDER BY date(plan_date), week_no, id
    ''', (selected_product['id'],))

    delivered_week_rows = fetch_all('''
        SELECT date_trunc('week', d.delivery_date::date)::date AS week_start,
               COALESCE(SUM(d.delivered_qty),0) AS delivered_qty
        FROM customer_deliveries d
        JOIN shipment_boxes b ON d.box_id = b.id
        WHERE b.product_id=?
          AND d.delivery_date IS NOT NULL
        GROUP BY date_trunc('week', d.delivery_date::date)::date
    ''', (selected_product['id'],))
    delivered_by_week = {}
    for rr in delivered_week_rows:
        wk = parse_db_date(rr.get('week_start'))
        if wk:
            delivered_by_week[wk.isoformat()] = float(rr.get('delivered_qty') or 0)

    shipment_week_rows = fetch_all('''
        SELECT date_trunc('week', (s.shipment_date::date + (?::int * INTERVAL '1 day')))::date AS week_start,
               COALESCE(SUM(b.original_qty),0) AS shipment_delivery_qty
        FROM shipment_boxes b
        JOIN shipments s ON b.shipment_id = s.id
        WHERE b.product_id=?
          AND s.shipment_date IS NOT NULL
        GROUP BY date_trunc('week', (s.shipment_date::date + (?::int * INTERVAL '1 day')))::date
    ''', (int(shipment_time_days), selected_product['id'], int(shipment_time_days)))
    shipment_by_week = {}
    for rr in shipment_week_rows:
        wk = parse_db_date(rr.get('week_start'))
        if wk:
            shipment_by_week[wk.isoformat()] = float(rr.get('shipment_delivery_qty') or 0)

    calculated_rows = []
    rows_to_update = []
    previous_wh_bank = None
    coverage_activity_started = False
    next_shipment_date = ''
    next_shipment_qty = 0.0

    for r in raw_rows:
        week_start = parse_db_date(r.get('plan_date'))
        week_key = week_start.isoformat() if week_start else ''
        customer_forecast = float(r.get('customer_forecast') or 0)
        shipment_delivery_qty = float(shipment_by_week.get(week_key, 0))
        delivered_to_customer = float(delivered_by_week.get(week_key, 0))

        # Excel concept from Coverage Plan sheet:
        # Stock at WH is opening stock for the week. In Excel, next week's Stock at WH
        # normally comes from previous week's WH Bank. If the user has manually entered
        # Stock at WH, that value is respected; otherwise previous WH Bank is used.
        stored_stock_at_wh = float(r.get('stock_at_wh') or 0)
        if previous_wh_bank is None:
            stock_at_wh = stored_stock_at_wh
        else:
            stock_at_wh = stored_stock_at_wh if abs(stored_stock_at_wh) > 0.000001 else previous_wh_bank

        wh_bank = stock_at_wh + shipment_delivery_qty - customer_forecast - delivered_to_customer
        previous_wh_bank = wh_bank
        two_months_inventory = product_two_months_inventory
        bank_status = wh_bank - two_months_inventory

        if customer_forecast > 0 or delivered_to_customer > 0:
            coverage_activity_started = True

        suggested_qty = 0.0
        suggested_date = None
        if coverage_activity_started and bank_status < 0:
            suggested_qty = abs(bank_status)
            if week_start:
                suggested_date = (week_start - timedelta(days=int(shipment_time_days))).isoformat()

        if suggested_qty > 0 and not next_shipment_date:
            next_shipment_date = suggested_date or ''
            next_shipment_qty = suggested_qty

        row_out = {
            'id': r['id'],
            'week_no': r.get('week_no'),
            'plan_date': week_key,
            'shipment_delivery_qty': round(shipment_delivery_qty, 2),
            'stock_at_wh': round(stock_at_wh, 2),
            'customer_forecast': round(customer_forecast, 2),
            'delivered_to_customer': round(delivered_to_customer, 2),
            'wh_bank': round(wh_bank, 2),
            'two_months_inventory': round(two_months_inventory, 2),
            'bank_status': round(bank_status, 2),
            'suggested_shipment_qty': round(suggested_qty, 2),
            'next_shipment_date': suggested_date or ''
        }
        calculated_rows.append(row_out)
        rows_to_update.append((
            shipment_delivery_qty, delivered_to_customer, stock_at_wh, wh_bank, bank_status,
            suggested_qty, suggested_date, two_months_inventory, r['id']
        ))

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        local_coverage_card('NEXT SHIPMENT DATE', (format_date_ddmmyyyy(next_shipment_date) if next_shipment_date else '-'), '#1A5E99', '#ffffff', '#B91C1C')
    with k2:
        local_coverage_card('NEXT SHIPMENT QTY', f'{next_shipment_qty:,.0f}', '#1A5E99', '#ffffff', '#FF8C00')
    with k3:
        local_coverage_card('PRODUCT', selected_product['product_code'], '#1A5E99')
    with k4:
        local_coverage_card('SHIPMENT TIME', f'{shipment_time_days} Days', '#1A5E99')

    visible_rows = []
    total_table_weeks = int(past_weeks) + int(visible_weeks)
    for row in calculated_rows:
        wk = parse_db_date(row.get('plan_date'))
        if wk and wk >= visible_start_week:
            visible_rows.append(row)
        if len(visible_rows) >= total_table_weeks:
            break

    # Vertical coverage grid: each week is a row and each calculation is a column.
    # This keeps the Excel concept but makes the table easier and faster to read online.
    vertical_rows = []
    for source_row in visible_rows:
        dt = parse_db_date(source_row.get('plan_date'))
        vertical_rows.append({
            'Week No': source_row.get('week_no'),
            'Week Start From': format_date_ddmmyyyy(source_row.get('plan_date')),
            'Shipment Delivery to Warehouse': source_row.get('shipment_delivery_qty'),
            'Stock at WH': source_row.get('stock_at_wh'),
            'Customer Forecast': source_row.get('customer_forecast'),
            'Delivered to Customer': source_row.get('delivered_to_customer'),
            'WH Bank': source_row.get('wh_bank'),
            'Two Months Inventory': source_row.get('two_months_inventory'),
            'Bank Status': source_row.get('bank_status'),
            'Suggested Shipment Qty': source_row.get('suggested_shipment_qty'),
            'Next Shipment Date': format_date_ddmmyyyy(source_row.get('next_shipment_date')) if source_row.get('next_shipment_date') else '',
        })

    vertical_df = pd.DataFrame(vertical_rows)

    def style_vertical_coverage_grid(df):
        def style_cell(value, column_name):
            col = str(column_name)
            base = 'font-weight:800; text-align:center;'
            if col in ('Week No', 'Week Start From'):
                return base + 'background-color:#eaf3fc; color:#0a3f7a;'
            if col == 'Shipment Delivery to Warehouse':
                return base + 'background-color:#dcfce7; color:#166534;'
            if col == 'Stock at WH':
                return base + 'background-color:#e8f5e9; color:#1b5e20;'
            if col == 'Customer Forecast':
                return base + 'background-color:#fef3c7; color:#92400e;'
            if col == 'Delivered to Customer':
                return base + 'background-color:#dbeafe; color:#1e3a8a;'
            if col == 'WH Bank':
                return base + 'background-color:#eef6ff; color:#0a3f7a;'
            if col == 'Two Months Inventory':
                return base + 'background-color:#f3f4f6; color:#374151;'
            if col == 'Bank Status':
                try:
                    val = float(value or 0)
                    if val < 0:
                        return base + 'background-color:#fee2e2; color:#991b1b;'
                    return base + 'background-color:#d1fae5; color:#065f46;'
                except Exception:
                    return base
            if col == 'Suggested Shipment Qty':
                return base + 'background-color:#ffedd5; color:#9a3412;'
            if col == 'Next Shipment Date':
                return base + ('background-color:#fde047; color:#b91c1c;' if str(value).strip() else '')
            return base

        return df.style.apply(lambda row: [style_cell(row[col], col) for col in df.columns], axis=1)

    if vertical_df.empty:
        st.info('No coverage plan data available.')
    else:
        st.markdown('<div class="sap-grid-card"><div class="sap-grid-card-title">Coverage Plan Vertical Grid</div>', unsafe_allow_html=True)
        st.dataframe(style_vertical_coverage_grid(vertical_df), use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)
        export_buttons(vertical_df, 'coverage_plan_vertical_grid')

    recalc_col1, recalc_col2 = st.columns([1, 3])
    with recalc_col1:
        if st.button('Recalculate & Save Coverage', type='primary', key='coverage_recalculate_save'):
            for item in rows_to_update:
                execute_query('''                    UPDATE coverage_plan_lines
                    SET shipment_delivery_qty=?, delivered_to_customer=?, stock_at_wh=?, wh_bank=?, bank_status=?,
                        suggested_shipment_qty=?, next_shipment_date=?, two_months_inventory=?
                    WHERE id=?
                ''', item)
            clear_cache_after_write()
            st.success('Coverage values recalculated and saved.')
            st.rerun()
    with recalc_col2:
        st.info('Fast mode: transaction quantities are grouped once, then the Excel-style vertical table is calculated in memory.')

    st.divider()
    st.markdown('<div class="sap-subtitle">Customer Forecast / Stock at WH Input Grid</div>', unsafe_allow_html=True)
    st.markdown('<div class="sap-grid-note">Edit Customer Forecast and Stock at WH by Week Start. These values are linked directly to the Coverage Plan table.</div>', unsafe_allow_html=True)

    forecast_rows = [r for r in visible_rows]
    if forecast_rows:
        grid_values = {}
        id_by_label = {}
        for r in forecast_rows:
            dt = parse_db_date(r.get('plan_date'))
            label = f"W{r.get('week_no')} | Week Start {dt.strftime('%d-%m-%Y')}" if dt else f"W{r.get('week_no')}"
            grid_values[label] = {
                'Stock at WH': float(r.get('stock_at_wh') or 0),
                'Customer Forecast': float(r.get('customer_forecast') or 0),
            }
            id_by_label[label] = r['id']
        input_grid = pd.DataFrame(grid_values)
        edited_input_grid = st.data_editor(
            input_grid,
            use_container_width=True,
            key='coverage_forecast_stock_horizontal_grid',
            num_rows='fixed'
        )
        if st.button('Save Forecast / Stock at WH Grid', type='primary', key='coverage_save_forecast_stock_grid'):
            for label, record_id in id_by_label.items():
                new_stock = float(edited_input_grid.loc['Stock at WH', label] or 0)
                new_forecast = float(edited_input_grid.loc['Customer Forecast', label] or 0)
                execute_query(
                    'UPDATE coverage_plan_lines SET stock_at_wh=?, customer_forecast=? WHERE id=?',
                    (new_stock, new_forecast, record_id)
                )
            clear_cache_after_write()
            st.success('Customer Forecast and Stock at WH updated successfully. Click Recalculate & Save Coverage to store updated WH Bank and Bank Status.')
            st.rerun()

    with st.expander('Detailed vertical coverage rows', expanded=False):
        detail_rows = []
        total_table_weeks = int(past_weeks) + int(visible_weeks)
        for r in calculated_rows:
            wk = parse_db_date(r.get('plan_date'))
            if wk and wk >= visible_start_week:
                detail_rows.append(r)
            if len(detail_rows) >= total_table_weeks:
                break
        detail_df = pd.DataFrame(format_date_columns(detail_rows))
        if not detail_df.empty and 'id' in detail_df.columns:
            detail_df = detail_df.drop(columns=['id'])
        if detail_df.empty:
            st.info('No detailed data available.')
        else:
            st.dataframe(detail_df, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown('<div class="sap-subtitle">Import Customer Forecast / Stock at WH</div>', unsafe_allow_html=True)
    forecast_template_df = pd.DataFrame({'product_code': [selected_product['product_code']], 'plan_date': [date.today().isoformat()], 'stock_at_wh': [0], 'customer_forecast': [0]})
    st.download_button('Download Customer Forecast Template', to_excel_bytes(forecast_template_df), 'customer_forecast_template.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', key='download_customer_forecast_template')
    forecast_file = st.file_uploader('Import Customer Forecast Excel', type=['xlsx'], key='coverage_import_forecast_excel')
    if forecast_file is not None:
        try:
            forecast_df = pd.read_excel(forecast_file)
            forecast_df.columns = [str(c).strip().lower().replace(' ', '_') for c in forecast_df.columns]
            required_cols = {'product_code', 'plan_date', 'customer_forecast'}
            if not required_cols.issubset(set(forecast_df.columns)):
                st.error('Excel must have columns: product_code, plan_date, customer_forecast. Optional column: stock_at_wh')
            else:
                st.dataframe(forecast_df, use_container_width=True, hide_index=True)
                if st.button('Update Customer Forecast from Excel', type='primary', key='coverage_import_forecast_btn'):
                    updated = 0
                    inserted = 0
                    skipped = 0
                    for _, row in forecast_df.iterrows():
                        product_code = str(row.get('product_code') or '').strip()
                        try:
                            plan_date_text = monday_of_date(pd.to_datetime(row.get('plan_date')).date())
                        except Exception:
                            plan_date_text = str(row.get('plan_date'))[:10]
                        product_rows = fetch_all('SELECT id, two_months_inventory FROM products WHERE product_code=?', (product_code,))
                        if not product_rows:
                            skipped += 1
                            continue
                        pid = product_rows[0]['id']
                        p_two_months = float(product_rows[0].get('two_months_inventory') or 0)
                        forecast = float(row.get('customer_forecast') or 0)
                        stock_at_wh_import = float(row.get('stock_at_wh') or 0) if 'stock_at_wh' in forecast_df.columns else None
                        existing = fetch_all('SELECT id FROM coverage_plan_lines WHERE product_id=? AND plan_date=? LIMIT 1', (pid, plan_date_text))
                        if existing:
                            
                            if stock_at_wh_import is None:
                                execute_query('UPDATE coverage_plan_lines SET customer_forecast=? WHERE id=?', (forecast, existing[0]['id']))
                            else:
                                execute_query('UPDATE coverage_plan_lines SET customer_forecast=?, stock_at_wh=? WHERE id=?', (forecast, stock_at_wh_import, existing[0]['id']))
                            updated += 1
                        else:
                            max_week = fetch_all('SELECT COALESCE(MAX(week_no),0) AS max_week FROM coverage_plan_lines WHERE product_id=?', (pid,))[0]['max_week'] or 0
                            execute_query('''
                                INSERT INTO coverage_plan_lines
                                (product_id, week_no, plan_date, customer_forecast, stock_at_wh,
                                 shipment_delivery_qty, delivered_to_customer, wh_bank, two_months_inventory,
                                 bank_status, suggested_shipment_qty, next_shipment_date)
                                VALUES (?, ?, ?, ?, ?, 0, 0, 0, ?, 0, 0, NULL)
                                ON CONFLICT DO NOTHING
                            ''', (pid, int(max_week) + 1, plan_date_text, forecast, float(stock_at_wh_import or 0), p_two_months))
                            inserted += 1
                    clear_cache_after_write()
                    st.success(f'Customer Forecast Import Complete. Updated: {updated}, Inserted: {inserted}, Skipped: {skipped}')
                    st.rerun()
        except Exception as e:
            st.error(f'Forecast import failed: {e}')



st.markdown('<div class="footer">COPYRIGHT BY FOUR STAR INDUSTRIES PVT. LTD.</div>', unsafe_allow_html=True)
