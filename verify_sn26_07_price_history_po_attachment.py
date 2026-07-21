from pathlib import Path
import sys
APP_VERSION = "SN 26.07"
common = Path("common.py").read_text(encoding="utf-8", errors="ignore")
db = Path("db.py").read_text(encoding="utf-8", errors="ignore")
checks = {
    "version_file": Path("APP_VERSION.txt").read_text().strip() == APP_VERSION,
    "version_in_common": APP_VERSION in common,
    "db_po_columns": "product_price_history ADD COLUMN IF NOT EXISTS po_number" in db and "po_copy_path" in db,
    "common_po_migrations": "ADD COLUMN IF NOT EXISTS po_number" in common and "ADD COLUMN IF NOT EXISTS po_copy_path" in common,
    "po_number_input": 'ph_po_number = st.text_input("PO Number"' in common,
    "po_date_input": 'ph_po_date = st.date_input("PO Date"' in common,
    "po_pdf_upload": 'Attach PO Copy PDF' in common and 'type=["pdf"]' in common,
    "insert_po_fields": "po_number, po_date, po_copy_path" in common,
    "price_history_grid_po_fields": "h.po_number, h.po_date, h.po_copy_path" in common,
    "download_po_copies": "Download PO Copies" in common and "st.download_button" in common,
}
for key, value in checks.items(): print(key, value)
if not all(checks.values()): sys.exit(1)
print("OK: SN 26.07 price history PO attachment build is ready.")
