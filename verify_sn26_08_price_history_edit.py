from pathlib import Path
import sys
APP_VERSION = "SN 26.08"
common = Path("common.py").read_text(encoding="utf-8", errors="ignore")
db = Path("db.py").read_text(encoding="utf-8", errors="ignore")
checks = {
    "version_file": Path("APP_VERSION.txt").read_text().strip() == APP_VERSION,
    "version_in_common": APP_VERSION in common,
    "po_columns_exist": "po_number" in db and "po_date" in db and "po_copy_path" in db,
    "edit_panel": "Edit Product Effective Price History" in common,
    "select_record": "Select Price History Record to Edit" in common,
    "update_button": "Update Selected Price History Record" in common,
    "update_sql_only_price_history": "UPDATE product_price_history" in common,
    "po_replace_upload": "Replace / Attach PO Copy PDF" in common,
    "download_current_po": "Download Current PO Copy" in common,
    "no_transaction_update_message": "Existing shipment/delivery/payment transactions are unchanged" in common,
}
for key, value in checks.items():
    print(key, value)
if not all(checks.values()): sys.exit(1)
print("OK: SN 26.08 price history edit build is ready.")
