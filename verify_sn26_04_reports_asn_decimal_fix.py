from pathlib import Path
import sys

APP_VERSION = "SN 26.04"
reports = Path("pages/8_Reports.py").read_text(encoding="utf-8", errors="ignore")
common = Path("common.py").read_text(encoding="utf-8", errors="ignore")

checks = {
    "version_file": Path("APP_VERSION.txt").read_text().strip() == APP_VERSION,
    "version_in_common": APP_VERSION in common,
    "version_in_reports": APP_VERSION in reports,
    "removed_delivery_invoice_with_original_report": '"Delivery Invoice List with Original Invoice Number",' not in reports,
    "asn_added": reports.count("d.asn_number") >= 8,
    "report_decimal_helper": "def _format_rate_price_amount_3decimals" in reports and ".3f" in reports,
    "common_decimal_helper": "def format_rate_price_amount_3decimals" in common,
    "excel_pdf_grid_decimal": "_format_rate_price_amount_3decimals(_add_total_footer" in reports,
}
for key, value in checks.items():
    print(key, value)
if not all(checks.values()):
    sys.exit(1)
print("OK: SN 26.04 ASN and 3-decimal report build is ready.")
