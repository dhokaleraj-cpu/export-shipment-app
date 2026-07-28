from pathlib import Path
import sys
APP_VERSION = "SN 26.17"
page = Path("pages/4_Delivery_to_Customer.py").read_text(encoding="utf-8", errors="ignore")
common = Path("common.py").read_text(encoding="utf-8", errors="ignore")
dc = Path("delivery_common.py").read_text(encoding="utf-8", errors="ignore")
checks = {
    "version_file": Path("APP_VERSION.txt").read_text().strip() == APP_VERSION,
    "multi_invoice_select": "selected_invoice_labels = st.multiselect" in page,
    "selected_ships_list": "selected_ships = [inv_map[x]" in page,
    "multi_available_rows": "for _ship in selected_ships" in page and "fetch_fifo_available_rows(_ship" in page,
    "pallet_label_original_invoice": "Orig Inv" in page and "selected_original_invoices_summary" in page,
    "notification_multiple_invoices": "Original Invoices:" in page,
    "pdf_header_aggregates_invoices": "STRING_AGG(DISTINCT s.invoice_no" in dc,
    "html_print_aggregates_invoices": "original_invoice_numbers =" in common and "shipment_numbers =" in common,
}
for k,v in checks.items(): print(k, v)
if not all(checks.values()): sys.exit(1)
print("OK: SN 26.17 multi original invoice delivery build is ready.")
