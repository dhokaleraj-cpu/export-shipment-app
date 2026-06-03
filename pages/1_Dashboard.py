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

show_header('Dashboard')
total_shipments = fetch_all('SELECT COUNT(*) c FROM shipments')[0]['c']
total_boxes = fetch_all('SELECT COUNT(*) c FROM shipment_boxes')[0]['c']
total_customers = fetch_all('SELECT COUNT(*) c FROM customers')[0]['c']
qty = fetch_all('\n        SELECT IFNULL((SELECT SUM(original_qty) FROM shipment_boxes),0) original_qty,\n               IFNULL((SELECT SUM(delivered_qty) FROM customer_deliveries),0) delivered_qty,\n               IFNULL((SELECT SUM(sale_amount) FROM customer_deliveries),0) total_sale\n    ')[0]
balance_qty = qty['original_qty'] - qty['delivered_qty']
try:
    overdue_count = len(overdue_rows())
    overdue_amount = sum((float(r.get('pending_amount') or 0) for r in overdue_rows()))
except Exception:
    overdue_count = 0
    overdue_amount = 0
labels = [('TOTAL SHIPMENTS', total_shipments, 'green'), ('TOTAL BOXES', total_boxes, 'teal'), ('DELIVERED QTY', qty['delivered_qty'], 'orange'), ('BALANCE QTY', balance_qty, 'blue'), ('TOTAL SALE', round(qty['total_sale'], 2), 'yellow'), ('OVERDUE PAYMENTS', overdue_count, 'red'), ('OVERDUE PAYMENT AMOUNT', f'{overdue_amount:,.2f}', 'red')]
cols = st.columns(7)
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
st.markdown('<div class="coverage-dashboard-title">Coverage Plan Dashboard</div>', unsafe_allow_html=True)
try:
    dashboard_products = cached_fetch_all('\n            SELECT id, product_code, product_name\n            FROM products\n            ORDER BY product_code\n        ')
    if dashboard_products:
        product_options = [p['product_code'] for p in dashboard_products]
        default_index = product_options.index('40257237') if '40257237' in product_options else 0
        cov_cols = st.columns([1.05, 1, 1, 1, 1])
        with cov_cols[0]:
            local_dashboard_filter_header('PRODUCT', '#FF8C00')
            dashboard_product_code = st.selectbox('Product', product_options, index=default_index, key='dashboard_coverage_product_filter', label_visibility='collapsed')
        dashboard_product = next((p for p in dashboard_products if p['product_code'] == dashboard_product_code))
        coverage_kpi = fetch_all('\n                SELECT next_shipment_date, suggested_shipment_qty\n                FROM coverage_plan_lines\n                WHERE product_id = ?\n                  AND suggested_shipment_qty > 0\n                  AND (COALESCE(customer_forecast,0) > 0 OR COALESCE(delivered_to_customer,0) > 0)\n                ORDER BY date(next_shipment_date), date(plan_date), week_no\n                LIMIT 1\n            ', (dashboard_product['id'],))
        shipment_time_row = cached_fetch_all('\n                SELECT IFNULL(MAX(shipment_time_days),0) AS shipment_time_days\n                FROM warehouses\n            ')[0]
        next_date = coverage_kpi[0]['next_shipment_date'] if coverage_kpi else ''
        next_qty = float(coverage_kpi[0]['suggested_shipment_qty'] or 0) if coverage_kpi else 0
        shipment_time_days = int(shipment_time_row['shipment_time_days'] or 0)
        next_date_display = format_date_ddmmyyyy(next_date) if next_date else '-'
        with cov_cols[1]:
            local_coverage_card('NEXT SHIPMENT DATE', next_date_display, '#B72C24', '#ffffff', '#B72C24')
        with cov_cols[2]:
            local_coverage_card('NEXT SHIPMENT QTY', f'{next_qty:,.0f}', '#EE9337', '#ffffff', '#EE9337')
        with cov_cols[3]:
            local_coverage_card('PRODUCT', dashboard_product_code, '#1A5E99')
        with cov_cols[4]:
            local_coverage_card('SHIPMENT TIME', f'{shipment_time_days} Days', '#1A5E99')
    else:
        st.info('Coverage dashboard will appear after product master is available.')
except Exception:
    st.info('Coverage Plan dashboard will appear after coverage data is available.')
st.divider()
st.subheader('Recent Shipments')
show_filtered_df(fetch_all('\n        SELECT s.shipment_no, s.invoice_no, s.shipment_date, sup.supplier_name, w.warehouse_name, s.currency, s.invoice_amount\n        FROM shipments s\n        LEFT JOIN suppliers sup ON s.supplier_id = sup.id\n        LEFT JOIN warehouses w ON s.warehouse_id = w.id\n        ORDER BY s.id DESC LIMIT 10\n    '), 'dashboard_recent_shipments', total=True)

st.markdown('<div class="footer">COPYRIGHT BY FOUR STAR INDUSTRIES PVT. LTD.</div>', unsafe_allow_html=True)
