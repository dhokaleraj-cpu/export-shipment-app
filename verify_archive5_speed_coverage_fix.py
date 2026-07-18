from pathlib import Path
import sys

common = Path("common.py").read_text(encoding="utf-8", errors="ignore")
coverage = Path("pages/6_Coverage_Plan.py").read_text(encoding="utf-8", errors="ignore")

checks = {
    "reports_page_removed": not Path("pages/8_Reports.py").exists(),
    "init_db_not_at_import": "init_db()\n\n\nst.markdown" not in common,
    "init_db_delayed_in_page_setup": "_db_initialized_once" in common,
    "coverage_uses_cte": "WITH shipment_calc AS" in coverage and "WITH invoice_calc AS" in coverage,
    "coverage_old_duplicate_groupby_removed": "GROUP BY date_trunc('week', (s.shipment_date::date + (?::int * INTERVAL '1 day')))::date" not in coverage,
    "coverage_fallback_removed": "except Exception:\n        shipment_week_rows = fetch_all" not in coverage,
}
for k, v in checks.items():
    print(k, v)
if not all(checks.values()):
    sys.exit(1)
print("OK: Archive(5) speed and Coverage Plan fix is ready.")
