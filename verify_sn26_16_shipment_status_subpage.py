from pathlib import Path
import sys
APP_VERSION = "SN 26.16"
common = Path("common.py").read_text(encoding="utf-8", errors="ignore")
shipment = Path("pages/3_Shipment_Entry.py").read_text(encoding="utf-8", errors="ignore")
status = Path("pages/16_Shipment_Status.py").read_text(encoding="utf-8", errors="ignore")
coverage = Path("pages/6_Coverage_Plan.py").read_text(encoding="utf-8", errors="ignore")
checks = {
    "version_file": Path("APP_VERSION.txt").read_text().strip() == APP_VERSION,
    "status_page_exists": Path("pages/16_Shipment_Status.py").exists(),
    "status_page_nav_def": '"key": "shipment_status"' in common and 'pages/16_Shipment_Status.py' in common,
    "subnav_has_status": '("shipment_status", "Shipment Status", "pages/16_Shipment_Status.py")' in common,
    "entry_update_panel_removed": "Update Shipment Delivered to WH / In Transit Status" not in shipment,
    "entry_points_to_status_page": "pages/16_Shipment_Status.py" in shipment,
    "status_page_has_update_panel": "Shipment Status Update" in status and "Save Shipment Status" in status,
    "no_duplicate_delivered_column_label": '"Shipment Delivered to WH"' not in coverage and "'Shipment Delivered to WH'" not in coverage,
    "coverage_existing_column_retained": '"Shipment Delivery to Warehouse"' in coverage,
    "coverage_transit_retained": '"Shipment in Transit"' in coverage,
    "wh_bank_uses_total_inbound": "shipment_total_inbound_qty + stock_at_wh" in coverage,
}
for k, v in checks.items(): print(k, v)
if not all(checks.values()): sys.exit(1)
print("OK: SN 26.16 shipment status subpage and coverage column fix is ready.")
