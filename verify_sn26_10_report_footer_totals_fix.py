from pathlib import Path
import sys
APP_VERSION = "SN 26.10"
reports = Path("pages/8_Reports.py").read_text(encoding="utf-8", errors="ignore")
common = Path("common.py").read_text(encoding="utf-8", errors="ignore")
checks = {
    "version_file": Path("APP_VERSION.txt").read_text().strip() == APP_VERSION,
    "version_in_common": APP_VERSION in common,
    "version_in_reports": APP_VERSION in reports,
    "pallet_qty_specific_kpi": '("pallet_qty", "Pallet Qty")' in reports,
    "delivery_pending_qty_kpis": '("delivery_qty", "Delivery Qty")' in reports and '("pending_qty", "Pending Qty")' in reports,
    "pallet_count_only_identifier": 'cl in ("pallet_no", "pallet_number", "pallet", "pallet id", "pallet_id")' in reports,
    "qty_columns_summed": 'if "qty" in cl or "quantity" in cl:' in reports,
}
for key, value in checks.items():
    print(key, value)
if not all(checks.values()):
    sys.exit(1)
print("OK: SN 26.10 report footer totals fix is ready.")
