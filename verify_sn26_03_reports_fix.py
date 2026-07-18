from pathlib import Path
import sys

APP_VERSION = "SN 26.03"
reports = Path("pages/8_Reports.py").read_text(encoding="utf-8", errors="ignore")
common = Path("common.py").read_text(encoding="utf-8", errors="ignore")

checks = {
    "version_file": Path("APP_VERSION.txt").read_text().strip() == APP_VERSION,
    "version_in_common": APP_VERSION in common,
    "version_in_reports": APP_VERSION in reports,
    "no_bl_column": "s.bl_number" not in reports,
    "no_alias_in_group_by": "GROUP BY s.shipment_no, s.shipment_date, s.po_number AS bl_number" not in reports,
    "po_number_alias_select": "s.po_number AS bl_number" in reports,
    "pdf_table_full_width": "available_width = landscape(A4)[0] - doc.leftMargin - doc.rightMargin" in reports and "colWidths=col_widths" in reports,
    "excel_landscape": "ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE" in reports,
    "ui_full_width_css": "SN2603 full width report table" in reports,
}
for key, value in checks.items():
    print(key, value)
if not all(checks.values()):
    sys.exit(1)
print("OK: SN 26.03 report table width and SQL fix is ready.")
