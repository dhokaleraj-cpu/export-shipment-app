from pathlib import Path
import sys
files = {
    "common": Path("common.py").read_text(encoding="utf-8", errors="ignore"),
    "shipment_page": Path("pages/3_Shipment_Entry.py").read_text(encoding="utf-8", errors="ignore"),
    "delivery_page": Path("pages/4_Delivery_to_Customer.py").read_text(encoding="utf-8", errors="ignore"),
    "shipment_common": Path("shipment_common.py").read_text(encoding="utf-8", errors="ignore"),
    "delivery_common": Path("delivery_common.py").read_text(encoding="utf-8", errors="ignore"),
}
checks={
"version": Path("APP_VERSION.txt").exists(),
"effective": "def get_effective_product_price" in files["common"] and "get_effective_product_price" in files["shipment_page"] and "get_effective_product_price" in files["delivery_page"],
"decimal": ":,.2f" not in files["shipment_common"] and ":,.2f" not in files["delivery_common"] and ":,.3f" in files["shipment_common"] and ":,.3f" in files["delivery_common"]
}
for k,v in checks.items(): print(k,v)
assert all(checks.values())
