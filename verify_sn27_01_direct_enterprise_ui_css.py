from pathlib import Path
import sys

APP_VERSION = "SN 27.01"
common = Path("common.py").read_text(encoding="utf-8", errors="ignore")
config = Path(".streamlit/config.toml").read_text(encoding="utf-8", errors="ignore")

checks = {
    "version_file": Path("APP_VERSION.txt").read_text().strip() == APP_VERSION,
    "version_in_common": APP_VERSION in common,
    "direct_css_function": "def inject_enterprise_ui_css" in common and "sn27-enterprise-ui-v2" in common,
    "old_header_forced_hidden": ".exact-app-header, .exact-nav-card, .exact-page-title-card" in common,
    "direct_top_layout_override": common.rfind("def top_layout") > common.rfind("SN 27.01 direct CSS injection"),
    "direct_show_header_override": common.rfind("def show_header") > common.rfind("SN 27.01 direct CSS injection"),
    "direct_nav_override": common.rfind("def render_top_navigation") > common.rfind("SN 27.01 direct CSS injection"),
    "sn27_shell": "sn27-shell" in common and "sn27-brand" in common,
    "theme_config": "[theme]" in config and "#0F6CBD" in config,
    "final_export_refresh": "SN 27.01 final direct export refresh" in common,
}
for key, value in checks.items():
    print(key, value)
if not all(checks.values()):
    sys.exit(1)
print("OK: SN 27.01 direct enterprise UI CSS build is ready.")
