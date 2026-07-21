from pathlib import Path
import sys

APP_VERSION = "SN 26.06"
common = Path("common.py").read_text(encoding="utf-8", errors="ignore")
db = Path("db.py").read_text(encoding="utf-8", errors="ignore")
reports = Path("pages/8_Reports.py").read_text(encoding="utf-8", errors="ignore")
shipment = Path("pages/3_Shipment_Entry.py").read_text(encoding="utf-8", errors="ignore")
delivery = Path("pages/4_Delivery_to_Customer.py").read_text(encoding="utf-8", errors="ignore")
payment = Path("pages/5_Payment_Entry.py").read_text(encoding="utf-8", errors="ignore")

checks = {
    "version_file": Path("APP_VERSION.txt").read_text().strip() == APP_VERSION,
    "version_in_common": APP_VERSION in common,
    "product_price_history_table": "CREATE TABLE IF NOT EXISTS product_price_history" in db and "idx_product_price_history_product_dates" in db,
    "effective_price_helpers": "get_effective_product_price" in common and "ensure_product_price_history_table" in common,
    "product_price_history_ui": "Product Effective Price History" in common and "Save Effective Price Period" in common,
    "number_input_patch": "_patched_number_input" in common and "%.3f" in common,
    "shipment_3_decimals": "format='%.3f'" in shipment and ":,.2f" not in shipment and "get_effective_product_price" in shipment,
    "delivery_3_decimals": "format='%.3f'" in delivery and ":,.2f" not in delivery,
    "payment_3_decimals": ":,.2f" not in payment,
    "reports_asn_filter": 'asn_filter = st.text_input("ASN Number"' in reports,
    "reports_pallet_pending": "Palletwise Pending Quantity" in reports,
}
for key, value in checks.items():
    print(key, value)
if not all(checks.values()):
    sys.exit(1)
print("OK: SN 26.06 full app 3-decimal and effective price build is ready.")
