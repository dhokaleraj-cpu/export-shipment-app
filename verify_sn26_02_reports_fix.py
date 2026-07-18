from pathlib import Path
import sys

APP_VERSION = "SN 26.02"
reports = Path("pages/8_Reports.py").read_text(encoding="utf-8", errors="ignore")
common = Path("common.py").read_text(encoding="utf-8", errors="ignore")

checks = {
    "version_file": Path("APP_VERSION.txt").read_text().strip() == APP_VERSION,
    "version_in_common": APP_VERSION in common,
    "version_in_reports": APP_VERSION in reports,
    "bl_number_column_removed": "s.bl_number" not in reports,
    "po_number_used_as_bl": "s.po_number AS bl_number" in reports,
    "default_start_2025": "date(2025, 1, 1)" in reports,
    "pdf_header_each_page": "onFirstPage=_draw_page_header_footer" in reports and "onLaterPages=_draw_page_header_footer" in reports,
    "pdf_page_number": "Page {doc_obj.page}" in reports or "Page " in reports,
    "excel_repeat_header": "ws.print_title_rows" in reports,
    "excel_page_footer": "Page &[Page] of &[Pages]" in reports,
}
for key, value in checks.items():
    print(key, value)
if not all(checks.values()):
    sys.exit(1)
print("OK: SN 26.02 report page/PDF/Excel fix is ready.")
