from pathlib import Path
import sys

APP_VERSION = "SN 26.11"
reports = Path("pages/8_Reports.py").read_text(encoding="utf-8", errors="ignore")
common = Path("common.py").read_text(encoding="utf-8", errors="ignore")

checks = {
    "version_file": Path("APP_VERSION.txt").read_text().strip() == APP_VERSION,
    "version_in_common": APP_VERSION in common,
    "version_in_reports": APP_VERSION in reports,
    "no_report_footer_html_function": "def _report_footer_html" not in reports,
    "kpi_renderer_exists": "def _render_report_footer_kpis" in reports,
    "display_uses_kpi_renderer": "_render_report_footer_kpis(df)" in reports,
    "pallet_qty_kpi_exists": "Total Pallet Qty" in reports,
    "delivery_pending_kpis_exist": "Total Delivery Qty" in reports and "Total Pending Qty" in reports,
}
for key, value in checks.items():
    print(key, value)
if not all(checks.values()):
    sys.exit(1)
print("OK: SN 26.11 report footer HTML rendering fix is ready.")
