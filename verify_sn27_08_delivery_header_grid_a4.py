from pathlib import Path
import py_compile

VERSION = "SN 27.08"
common_path = Path("common.py")
delivery_path = Path("delivery_common.py")
common = common_path.read_text(encoding="utf-8", errors="ignore")
delivery = delivery_path.read_text(encoding="utf-8", errors="ignore")
pdf_start = delivery.index("def delivery_invoice_pdf_bytes")
pdf_end = delivery.index("def get_saved_delivery_invoice_for_pdf", pdf_start)
pdf_segment = delivery[pdf_start:pdf_end]
html_start = common.index("def delivery_note_html")
html_end = common.index("def build_delivery_invoice_print_data", html_start)
html_segment = common[html_start:html_end]
checks = {
    "version_file": Path("APP_VERSION.txt").read_text(encoding="utf-8").strip() == VERSION,
    "version_constant": f'APP_VERSION = "{VERSION}"' in common,
    "pdf_invoice_grid": "invoice_grid = Table" in pdf_segment and "Delivery Invoice No" in pdf_segment and "Delivery Date" in pdf_segment,
    "pdf_company_address_label": "Address:" in pdf_segment,
    "pdf_full_a4_margins": "rightMargin=10" in pdf_segment and "leftMargin=10" in pdf_segment,
    "pdf_footer_tuned": "footer_gap = max(10, min(88, 88 - ((item_count - 1) * 12)))" in pdf_segment,
    "html_invoice_flex_a4": "min-height:277mm" in html_segment and "invoice-tail" in html_segment,
    "html_invoice_grid": "invoice-meta-grid" in html_segment and "Delivery Invoice No" in html_segment and "Delivery Date" in html_segment,
    "html_company_address_label": "Address:" in html_segment,
    "body_grid_retained": all(token in (pdf_segment + html_segment) for token in ("PO NO.", "PO DATE", "PALLET", "BOX", "QTY", "AMOUNT")),
    "no_destructive_sql_in_print_update": "DELETE FROM" not in pdf_segment and "ALTER TABLE" not in pdf_segment,
}
for path in (common_path, delivery_path):
    py_compile.compile(str(path), doraise=True)
for name, result in checks.items():
    print(f"{name}: {result}")
assert all(checks.values()), "SN 27.08 verification failed"
print("OK: SN 27.08 Delivery Invoice header grid + A4 update is ready.")
