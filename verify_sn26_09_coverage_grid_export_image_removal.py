from pathlib import Path
import sys

APP_VERSION = "SN 26.09"
common = Path("common.py").read_text(encoding="utf-8", errors="ignore")
coverage = Path("pages/6_Coverage_Plan.py").read_text(encoding="utf-8", errors="ignore")
reports = Path("pages/8_Reports.py").read_text(encoding="utf-8", errors="ignore") if Path("pages/8_Reports.py").exists() else ""

checks = {
    "version_file": Path("APP_VERSION.txt").read_text().strip() == APP_VERSION,
    "version_in_common": APP_VERSION in common,
    "coverage_grid_removed": "SN 26.09 removed Customer Forecast / Stock at WH Input Grid section" in coverage,
    "input_grid_old_subtitle_removed": "sap-subtitle\">Customer Forecast / Stock at WH Input Grid" not in coverage,
    "import_section_retained": "Import Customer Forecast / Stock at WH" in coverage,
    "main_coverage_table_retained": "Coverage Plan Table" in coverage,
    "past_weeks_default_4": 'st.selectbox("Past Weeks", [0, 4, 8, 12, 26, 52], index=1' in coverage,
    "export_image_button_removed_common": 'download_button("Export Image"' not in common,
    "export_image_button_removed_reports": 'download_button("Export Image"' not in reports,
}
for key, value in checks.items():
    print(key, value)
if not all(checks.values()):
    sys.exit(1)
print("OK: SN 26.09 coverage grid and image export button removal build is ready.")
