from pathlib import Path
import sys

APP_VERSION = "SN 27.04"
delivery_common = Path("delivery_common.py").read_text(encoding="utf-8", errors="ignore")
reprint = Path("pages/10_Reprint_Invoice.py").read_text(encoding="utf-8", errors="ignore")
common = Path("common.py").read_text(encoding="utf-8", errors="ignore")

checks = {
    "version_file": Path("APP_VERSION.txt").read_text().strip() == APP_VERSION,
    "version_in_common": APP_VERSION in common,
    "company_master_helper": "_delivery_company_master" in delivery_common,
    "bank_from_master": "_company_bank_text(company)" in delivery_common and "004330150000003" not in delivery_common,
    "original_invoice_removed_from_header": '"Original Invoice:"' not in delivery_common and "Original invoice intentionally excluded from header" in delivery_common,
    "invoice_no_date_top_grid": "Delivery Invoice No." in delivery_common and "Delivery Date" in delivery_common and "invoice_grid" in delivery_common,
    "item_table_original_invoice": "Original Invoice No" in delivery_common,
    "multi_reprint": "st.multiselect" in reprint and "selected_invoice_numbers" in reprint,
    "zip_reprint": "zipfile.ZipFile" in reprint and "application/zip" in reprint,
}
for key, value in checks.items():
    print(key, value)
if not all(checks.values()):
    sys.exit(1)
print("OK: SN 27.04 delivery print layout and multi reprint build is ready.")
