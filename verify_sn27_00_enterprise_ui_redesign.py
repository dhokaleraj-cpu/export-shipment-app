from pathlib import Path
import sys

APP_VERSION = "SN 27.00"
common = Path("common.py").read_text(encoding="utf-8", errors="ignore")

checks = {
    "version_file": Path("APP_VERSION.txt").read_text().strip() == APP_VERSION,
    "version_in_common": APP_VERSION in common,
    "sn27_block_exists": "SN 27.00 - Enterprise UI Redesign" in common,
    "sn27_header": "sn27-shell" in common and "Four Star Industries" in common,
    "sn27_nav": "sn27-nav-card" in common and "sn27-nav-active" in common,
    "sn27_page_title": "sn27-page-title" in common,
    "sn27_kpi": "sn27-kpi-card" in common,
    "overrides_exported": common.rfind("__all__") > common.rfind("SN 27.00 - Enterprise UI Redesign"),
}
for key, value in checks.items():
    print(key, value)
if not all(checks.values()):
    sys.exit(1)
print("OK: SN 27.00 Enterprise UI redesign build is ready.")
