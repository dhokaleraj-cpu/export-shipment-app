from pathlib import Path
import sys
APP_VERSION = "SN 26.05"
common = Path("common.py").read_text(encoding="utf-8", errors="ignore")
reports = Path("pages/8_Reports.py").read_text(encoding="utf-8", errors="ignore")
checks = {
    "version_file": Path("APP_VERSION.txt").read_text().strip() == APP_VERSION,
    "version_in_common": APP_VERSION in common,
    "version_in_reports": APP_VERSION in reports,
    "common_dataframe_patch": "_sn2605_patch_dataframe_3decimals" in common,
    "asn_filter_added": 'asn_filter = st.text_input("ASN Number"' in reports,
    "asn_filter_logic": '_like_clause("d.asn_number", asn_filter)' in reports,
    "pallet_report_option": '"Palletwise Pending Quantity",' in reports,
    "pallet_report_logic": 'if report_name == "Palletwise Pending Quantity":' in reports,
    "pallet_fields": "pallet_qty" in reports and "delivery_qty" in reports and "pending_qty" in reports,
    "removed_old_delivery_report": '"Delivery Invoice List with Original Invoice Number",' not in reports,
}
for k,v in checks.items(): print(k,v)
if not all(checks.values()): sys.exit(1)
print("OK: SN 26.05 module decimals, ASN filter and pallet pending report build is ready.")
