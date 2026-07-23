from pathlib import Path
import sys

APP_VERSION = "SN 26.13"
files = {
    "common": Path("common.py").read_text(encoding="utf-8", errors="ignore"),
    "shipment_page": Path("pages/3_Shipment_Entry.py").read_text(encoding="utf-8", errors="ignore"),
    "delivery_page": Path("pages/4_Delivery_to_Customer.py").read_text(encoding="utf-8", errors="ignore"),
    "shipment_common": Path("shipment_common.py").read_text(encoding="utf-8", errors="ignore"),
    "delivery_common": Path("delivery_common.py").read_text(encoding="utf-8", errors="ignore"),
    "payment_page": Path("pages/5_Payment_Entry.py").read_text(encoding="utf-8", errors="ignore"),
    "reports": Path("pages/8_Reports.py").read_text(encoding="utf-8", errors="ignore") if Path("pages/8_Reports.py").exists() else "",
}
checks = {
    "version": Path("APP_VERSION.txt").read_text().strip() == APP_VERSION and APP_VERSION in files["common"],
    "effective_common": "def get_effective_product_price" in files["common"] and "product_price_history" in files["common"],
    "shipment_effective": "get_effective_product_price" in files["shipment_page"] and "shipment_date" in files["shipment_page"],
    "delivery_effective": "effective_delivery_price" in files["delivery_page"] and "get_effective_product_price" in files["delivery_page"] and "delivery_date" in files["delivery_page"],
    "shipment_print_decimals": ":,.2f" not in files["shipment_common"] and ":.2f" not in files["shipment_common"] and ":,.3f" in files["shipment_common"],
    "delivery_print_decimals": ":,.2f" not in files["delivery_common"] and ":.2f" not in files["delivery_common"] and ":,.3f" in files["delivery_common"],
    "shipment_page_decimals": ":,.2f" not in files["shipment_page"] and "format='%.3f'" in files["shipment_page"],
    "delivery_page_decimals": ":,.2f" not in files["delivery_page"] and "format='%.3f'" in files["delivery_page"],
    "payment_page_decimals": ":,.2f" not in files["payment_page"],
    "reports_decimals": ":,.2f" not in files["reports"] and ".3f" in files["reports"],
}
for k, v in checks.items():
    print(k, v)
if not all(checks.values()):
    sys.exit(1)
print("OK: SN 26.13 effective price and decimal verification build is ready.")
