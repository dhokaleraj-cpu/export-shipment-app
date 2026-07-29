from pathlib import Path
import sys
APP_VERSION = "SN 27.03"
dc = Path("delivery_common.py").read_text(encoding="utf-8", errors="ignore")
pd = Path("pages/4_Delivery_to_Customer.py").read_text(encoding="utf-8", errors="ignore")
common = Path("common.py").read_text(encoding="utf-8", errors="ignore")
checks = {
    "version_file": Path("APP_VERSION.txt").read_text().strip() == APP_VERSION,
    "version_in_common": APP_VERSION in common,
    "pdf_header_original_invoice": "Original Invoice No" in dc,
    "pdf_row_uses_original_invoice": 'item.get("original_invoice_no") or invoice.get("original_invoice_no")' in dc,
    "excel_original_invoice_added": '"Original Invoice No": item.get("original_invoice_no"' in dc,
    "excel_box_removed": '"Box No": item.get("box_no"' not in dc,
    "fallback_print_original_invoice": "'original_invoice_no': row.get('invoice_no')" in pd or "original_invoice_no" in pd,
}
for k, v in checks.items():
    print(k, v)
if not all(checks.values()):
    sys.exit(1)
print("OK: SN 27.03 delivery invoice original invoice column build is ready.")
