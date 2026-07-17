from pathlib import Path
import sys

app = Path("app.py").read_text(encoding="utf-8", errors="ignore")
checks = {
    "safe_start_version": "CLOUD-SAFE-START-NO-COMMON-IMPORT" in app,
    "no_common_import_in_app": "from common import" not in app and "import common" not in app,
    "system_check_page": Path("pages/99_System_Check.py").exists(),
    "streamlit_config": Path(".streamlit/config.toml").exists(),
    "reports_file": Path("pages/8_Reports.py").exists(),
}
for k, v in checks.items():
    print(k, v)
if not all(checks.values()):
    sys.exit(1)
print("OK: Cloud safe-start deployment files are ready.")
