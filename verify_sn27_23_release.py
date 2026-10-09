"""SN 27.23 release verification (static, no database writes).

Run from the project folder:  python3 verify_sn27_23_release.py
"""
from pathlib import Path
import py_compile
import re
import sys

root = Path(__file__).resolve().parent


def read(rel):
    return (root / rel).read_text(encoding="utf-8", errors="ignore")


checks = {}
common = read("common.py")
db = read("db.py")
pc = read("payment_common.py")
ship = read("pages/3_Shipment_Entry.py")
entry = read("pages/5_Payment_Entry.py")
edit = read("pages/19_Edit_Payment.py")
plist = read("pages/20_Payment_Received_List.py")
reports = read("pages/8_Reports.py")

checks["version_file"] = read("APP_VERSION.txt").strip() == "SN 27.23"
checks["version_constant"] = 'APP_VERSION = "SN 27.23"' in common

# Navigation must point at the pages edited in this release.
for key, target in [
    ("shipment", "pages/3_Shipment_Entry.py"),
    ("payment", "pages/5_Payment_Entry.py"),
    ("payment_edit", "pages/19_Edit_Payment.py"),
    ("payment_list", "pages/20_Payment_Received_List.py"),
    ("reports", "pages/8_Reports.py"),
]:
    checks[f"nav_{key}"] = bool(re.search(r'"target":\s*"' + re.escape(target) + r'",\s*"key":\s*"' + key + '"', common))

# Shipment Entry: Customer + Ship To header, Product only per row.
checks["ship_marker"] = "SN 27.23 SIMPLE SHIPMENT HEADER ACTIVE" in ship
checks["ship_customer_header"] = "'Customer / Bill To *'" in ship
checks["ship_ship_to_header"] = "'Ship To *'" in ship
checks["ship_product_row_only"] = "'Product / Part for This Row *'" in ship and "WHERE customer_id=?" in ship
checks["ship_customer_guard"] = "product_customer_id != selected_customer_id" in ship
checks["ship_atomic_save"] = "save_shipment_atomic(header, st.session_state.shipment_temp_rows)" in ship
checks["ship_row_remove"] = "Remove Ticked Rows" in ship
checks["db_atomic_shipment"] = "def save_shipment_atomic" in db

# Payment: explicit line allocation in Entry and Edit.
for name, src in (("entry", entry), ("edit", edit)):
    for col in ["Select", "Original Invoice", "Invoice Amount", "Already Paid", "Pending", "Allocate Amount"]:
        checks[f"{name}_col_{col.replace(' ', '_').lower()}"] = f"'{col}'" in src
checks["entry_marker"] = "SN 27.23 EXPLICIT LINE-ITEM PAYMENT ACTIVE" in entry
checks["entry_allocated_save"] = "save_invoice_payment_allocated_atomic(" in entry
checks["entry_fill_pending"] = "Fill Full Pending for Ticked Lines" in entry
checks["edit_marker"] = "SN 27.23 EDIT PAYMENT LINE ALLOCATION ACTIVE" in edit
checks["edit_allocated_update"] = "update_invoice_payment_allocated_atomic(" in edit
checks["edit_no_raw_amount_update"] = "UPDATE payments" not in edit
checks["edit_legacy_support"] = "legacy payment receipt" in edit.lower()
checks["line_balance_helper"] = "def fetch_payment_line_rows" in pc and "def fetch_payment_allocations" in pc
checks["bulk_delete_retained"] = "DELETE SELECTED PAYMENT RECEIPTS" in plist and "check_delete_password" in plist
checks["report_exact_allocations"] = "explicit_paid" in reports and "payment_allocations" in reports
checks["product_summary_retained"] = "Summary Report - Product Wise" in reports
checks["warehouse_report_retained"] = "Warehouse Balance Qty - Product Wise / Warehouse Wise" in reports

# Database safety: no destructive statements introduced.
all_src = "\n".join([common, db, pc, ship, entry, edit, plist, reports])
checks["no_drop_table"] = not re.search(r"DROP\s+TABLE", all_src, re.I)
checks["no_truncate"] = not re.search(r"\bTRUNCATE\b", all_src, re.I)
checks["allocation_table_additive"] = "CREATE TABLE IF NOT EXISTS payment_allocations" in db

compile_targets = ["app.py", "common.py", "db.py", "payment_common.py", "shipment_common.py", "delivery_common.py"]
compile_targets += sorted(str(p.relative_to(root)) for p in (root / "pages").glob("*.py"))
for rel in compile_targets:
    try:
        py_compile.compile(str(root / rel), doraise=True)
        checks[f"compile_{rel}"] = True
    except Exception as exc:
        print(f"COMPILE ERROR {rel}: {exc}")
        checks[f"compile_{rel}"] = False

failed = [k for k, v in checks.items() if not v]
for k, v in checks.items():
    print(f"{'PASS' if v else 'FAIL'}  {k}")
if failed:
    print(f"\nSN 27.23 verification FAILED: {len(failed)} check(s): {', '.join(failed)}")
    sys.exit(1)
print(f"\nOK: SN 27.23 verified ({len(checks)} checks).")
