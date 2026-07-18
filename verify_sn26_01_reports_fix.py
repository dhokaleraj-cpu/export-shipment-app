from pathlib import Path
import sys

APP_VERSION = "SN 26.01"
reports = Path("pages/8_Reports.py").read_text(encoding="utf-8", errors="ignore")
common = Path("common.py").read_text(encoding="utf-8", errors="ignore")

checks = {
    "version_file": Path("APP_VERSION.txt").exists() and Path("APP_VERSION.txt").read_text().strip() == APP_VERSION,
    "version_in_common": APP_VERSION in common,
    "version_in_reports": APP_VERSION in reports,
    "w_customer_id_removed": "w.customer_id" not in reports,
    "logo_file_present": Path("FSI_LOGO_new.png").exists(),
    "uploaded_logo_copy_present": Path("Four Star Industries - Logo.png").exists(),
    "report_header_width_full": "width:100%" in reports and "grid-template-columns:1.2fr 2.2fr 1.2fr" in reports,
    "report_side_version_removed": "Version {REPORTS_VERSION}" not in reports and "Version SN 26.01" not in reports,
    "four_star_text_removed_from_excel": "Four Star Industries Pvt. Ltd." not in reports,
    "footer_color_highlight": "Report Footer Totals" in reports and "#EAF3FC" in reports,
}
for key, value in checks.items():
    print(key, value)
if not all(checks.values()):
    sys.exit(1)
print("OK: SN 26.01 reports fix build is ready.")
