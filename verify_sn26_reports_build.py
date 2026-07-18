from pathlib import Path
import sys

APP_VERSION = "SN 26.00"
common = Path("common.py").read_text(encoding="utf-8", errors="ignore")
reports = Path("pages/8_Reports.py").read_text(encoding="utf-8", errors="ignore")

required_reports = [
    "Shipment List",
    "Shipment List with Part Number",
    "Shipment List with Pallet Numbers",
    "Delivery Invoice List with Original Invoice Number",
    "Delivery Invoice List against Original Invoice Number",
    "Payment Report with Original Invoice Number",
    "Payment Due Invoice List",
    "Payment Received Report",
    "Customer Wise Shipment Report",
    "Customer Wise Delivery Report",
]

checks = {
    "stable_version_file": Path("APP_VERSION.txt").exists() and Path("APP_VERSION.txt").read_text().strip() == APP_VERSION,
    "version_in_common": APP_VERSION in common,
    "reports_page_exists": Path("pages/8_Reports.py").exists(),
    "reports_nav_exists": "pages/8_Reports.py" in common and '"key": "reports"' in common,
    "all_requested_reports": all(r in reports for r in required_reports),
    "excel_export": "_excel_bytes" in reports and "download_button" in reports,
    "pdf_export": "_pdf_bytes" in reports and "SimpleDocTemplate" in reports,
    "header_footer_logic": "_report_header_html" in reports and "_report_footer_html" in reports,
    "filters_present": "Original Invoice Number" in reports and "Part Number" in reports and "Customer" in reports and "From Date" in reports and "To Date" in reports,
}
for key, value in checks.items():
    print(key, value)
if not all(checks.values()):
    sys.exit(1)
print("OK: SN 26.00 stable reports build is ready.")
