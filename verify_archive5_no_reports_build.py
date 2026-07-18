from pathlib import Path
import sys

req = Path("requirements.txt").read_text(encoding="utf-8", errors="ignore")
common = Path("common.py").read_text(encoding="utf-8", errors="ignore")
db = Path("db.py").read_text(encoding="utf-8", errors="ignore")
admin = Path("pages/7_Admin.py").read_text(encoding="utf-8", errors="ignore") if Path("pages/7_Admin.py").exists() else ""

checks = {
    "reports_page_removed": not Path("pages/8_Reports.py").exists(),
    "reports_removed_from_common": "pages/8_Reports.py" not in common and '"key": "reports"' not in common and "'reports'" not in common and '"reports"' not in common,
    "reports_removed_from_admin_defaults": "'reports'" not in admin and '"reports"' not in admin,
    "psycopg2_binary_removed": "psycopg2-binary" not in req,
    "psycopg3_binary_added": "psycopg[binary]" in req,
    "db_uses_psycopg3": "import psycopg" in db and "dict_row" in db,
    "streamlit_config_exists": Path(".streamlit/config.toml").exists(),
}
for key, value in checks.items():
    print(key, value)
if not all(checks.values()):
    sys.exit(1)
print("OK: Archive(5) based build is ready with Reports module removed.")
