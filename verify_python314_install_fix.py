from pathlib import Path
import sys

req = Path("requirements.txt").read_text(encoding="utf-8", errors="ignore")
db = Path("db.py").read_text(encoding="utf-8", errors="ignore")

checks = {
    "no_psycopg2_binary_pin": "psycopg2-binary" not in req,
    "psycopg3_binary_present": "psycopg[binary]" in req,
    "pandas_not_old_pinned": "pandas==2.2.3" not in req,
    "numpy_not_old_pinned": "numpy==2.1.3" not in req,
    "db_py_exists": Path("db.py").exists(),
    "db_uses_psycopg3": "import psycopg" in db and "dict_row" in db,
    "db_fallback_psycopg2": "psycopg2" in db,
}
for k, v in checks.items():
    print(k, v)
if not all(checks.values()):
    sys.exit(1)
print("OK: Python 3.14 installation fix is ready.")
