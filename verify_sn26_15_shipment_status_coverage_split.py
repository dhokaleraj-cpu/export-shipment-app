from pathlib import Path
import sys

APP_VERSION = "SN 26.15"
common = Path("common.py").read_text(encoding="utf-8", errors="ignore")
db = Path("db.py").read_text(encoding="utf-8", errors="ignore")
shipment = Path("pages/3_Shipment_Entry.py").read_text(encoding="utf-8", errors="ignore")
coverage = Path("pages/6_Coverage_Plan.py").read_text(encoding="utf-8", errors="ignore")
dashboard = Path("pages/1_Dashboard.py").read_text(encoding="utf-8", errors="ignore")
shipcommon = Path("shipment_common.py").read_text(encoding="utf-8", errors="ignore")

checks = {
    "version_file": Path("APP_VERSION.txt").read_text().strip() == APP_VERSION,
    "status_migrations": "shipment_status" in db and "warehouse_delivery_date" in db,
    "common_helpers": "ensure_shipment_status_columns" in common and "render_tuesday_shipment_status_popup" in common,
    "shipment_entry_status_fields": "Shipment Status" in shipment and "Delivered to WH Date" in shipment,
    "shipment_update_panel": "Update Shipment Delivered to WH / In Transit Status" in shipment,
    "coverage_split_columns": "Shipment Delivered to WH" in coverage and "Shipment in Transit" in coverage,
    "coverage_logic_delivered_date": "warehouse_delivery_date" in coverage and "shipment_in_transit_qty" in coverage,
    "dashboard_status_logic": "warehouse_delivery_date" in dashboard and "shipment_status" in dashboard,
    "tuesday_popup": "Tuesday Reminder" in common,
    "shipment_print_status": "Delivered to WH Date" in shipcommon and "logo_cell" in shipcommon,
}
for key, value in checks.items():
    print(key, value)
if not all(checks.values()):
    sys.exit(1)
print("OK: SN 26.15 shipment status and coverage split build is ready.")
