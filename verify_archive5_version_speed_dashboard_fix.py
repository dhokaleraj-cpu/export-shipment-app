from pathlib import Path
import sys

APP_VERSION = "Archive5-NoReports-v2026.07.18.02"
common = Path("common.py").read_text(encoding="utf-8", errors="ignore")
dash = Path("pages/1_Dashboard.py").read_text(encoding="utf-8", errors="ignore")

checks = {
    "app_version_file": Path("APP_VERSION.txt").exists() and Path("APP_VERSION.txt").read_text().strip() == APP_VERSION,
    "app_version_in_common": APP_VERSION in common,
    "reports_still_removed": not Path("pages/8_Reports.py").exists(),
    "auto_init_db_disabled": "Do not run init_db() automatically" in common,
    "dashboard_coverage_cte": "WITH shipment_calc AS" in dash,
    "dashboard_old_groupby_removed": "GROUP BY date_trunc('week', (s.shipment_date::date + (?::int * INTERVAL '1 day')))::date" not in dash,
    "password_eye_css": "Password eye icon fix" in common,
}
for key, value in checks.items():
    print(key, value)
if not all(checks.values()):
    sys.exit(1)
print("OK: " + APP_VERSION + " is ready.")
