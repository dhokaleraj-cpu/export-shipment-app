from pathlib import Path
import sys

APP_VERSION = "SN 26.14"
common = Path("common.py").read_text(encoding="utf-8", errors="ignore")
shipment = Path("shipment_common.py").read_text(encoding="utf-8", errors="ignore")
delivery = Path("delivery_common.py").read_text(encoding="utf-8", errors="ignore")
reports = Path("pages/8_Reports.py").read_text(encoding="utf-8", errors="ignore")
shipment_entry = Path("pages/3_Shipment_Entry.py").read_text(encoding="utf-8", errors="ignore")
delivery_entry = Path("pages/4_Delivery_to_Customer.py").read_text(encoding="utf-8", errors="ignore")

checks = {
    "version_file": Path("APP_VERSION.txt").read_text().strip() == APP_VERSION,
    "version_in_common": APP_VERSION in common,
    "effective_helper_exported": "get_effective_product_price" in common and common.rfind("__all__") > common.rfind("get_effective_product_price"),
    "shipment_fallback": "_local_effective_product_price" in shipment_entry,
    "delivery_fallback": "_local_effective_product_price" in delivery_entry,
    "common_pdf_wrap": "_pdf_wrap_cell" in common and "wordWrap" in common,
    "shipment_pdf_wrap": "_shipment_pdf_p" in shipment and "wordWrap" in shipment,
    "delivery_pdf_wrap": "_p(f\"{item.get('product_code'" in delivery or "Paragraph(str(value" in delivery,
    "reports_pdf_wrap": "_wrap_pdf_cell" in reports and "wordWrap" in reports,
    "three_decimal_qty_print": 'f"{qty:,.3f}"' in shipment and 'f"{qty:,.3f}"' in delivery,
}
for key, value in checks.items():
    print(key, value)
if not all(checks.values()):
    sys.exit(1)
print("OK: SN 26.14 effective price export and PDF wrap build is ready.")
