from pathlib import Path
import sys

checks = {}
req = Path("requirements.txt").read_text(encoding="utf-8", errors="ignore")
db = Path("db.py").read_text(encoding="utf-8", errors="ignore")
reports = Path("pages/8_Reports.py").read_text(encoding="utf-8", errors="ignore")
app = Path("app.py").read_text(encoding="utf-8", errors="ignore")

checks["no_psycopg2_binary"] = "psycopg2-binary" not in req
checks["psycopg3_binary"] = "psycopg[binary]" in req
checks["no_old_pandas_pin"] = "pandas==2.2.3" not in req
checks["db_uses_psycopg3"] = "import psycopg" in db
checks["reports_marker"] = "2026-07-17-POSTGRESQL-SAFE-PSYCOPG3" in reports
checks["reports_no_old_tuple"] = "(invoice_filter, invoice_filter, delivery_invoice_filter" not in reports
checks["reports_no_question_placeholder"] = "?" not in reports
checks["app_marker"] = "2026-07-17-PSYCOPG3-CLEAN" in app
checks["no_dist"] = not Path("dist").exists()
checks["no_local_db"] = not Path("shipment_app.db").exists()

for k, v in checks.items():
    print(k, v)

if not all(checks.values()):
    sys.exit(1)
print("OK: clean Cloud build is ready.")
