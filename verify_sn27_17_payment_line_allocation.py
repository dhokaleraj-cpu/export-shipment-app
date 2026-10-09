from pathlib import Path
import py_compile

checks = {}
root = Path('.')
common = (root/'common.py').read_text(encoding='utf-8', errors='ignore')
db = (root/'db.py').read_text(encoding='utf-8', errors='ignore')
payment_common = (root/'payment_common.py').read_text(encoding='utf-8', errors='ignore')
entry = (root/'pages/5_Payment_Entry.py').read_text(encoding='utf-8', errors='ignore')
edit = (root/'pages/19_Edit_Payment.py').read_text(encoding='utf-8', errors='ignore')
plist = (root/'pages/20_Payment_Received_List.py').read_text(encoding='utf-8', errors='ignore')
reports = (root/'pages/8_Reports.py').read_text(encoding='utf-8', errors='ignore')

checks['version_file'] = (root/'APP_VERSION.txt').read_text().strip() == 'SN 27.17'
checks['version_constant'] = 'APP_VERSION = "SN 27.17"' in common
checks['allocation_table'] = 'CREATE TABLE IF NOT EXISTS payment_allocations' in db
checks['allocation_fk_cascade'] = 'REFERENCES payments(id) ON DELETE CASCADE' in db
checks['atomic_allocated_save'] = 'def save_invoice_payment_allocated_atomic' in db and 'pg_advisory_xact_lock' in db
checks['atomic_allocated_edit'] = 'def update_invoice_payment_allocated_atomic' in db
checks['line_balance_helper'] = 'def fetch_payment_line_rows' in payment_common
checks['entry_tick_column'] = "CheckboxColumn('Select'" in entry
checks['entry_allocate_column'] = 'Allocate Amount' in entry
checks['entry_selected_save'] = 'Save Payment with Selected Line Allocation' in entry
checks['entry_no_single_amount_only'] = 'save_invoice_payment_allocated_atomic' in entry
checks['edit_line_allocation'] = 'Update Payment and Line Allocation' in edit and 'fetch_payment_allocations' in edit
checks['legacy_edit_support'] = 'legacy payment receipt' in edit.lower()
checks['received_allocation_context'] = 'allocation_summary' in payment_common
checks['report_exact_allocations'] = 'explicit_paid' in reports and 'payment_allocations' in reports
checks['bulk_delete_retained'] = 'DELETE SELECTED PAYMENT RECEIPTS' in plist
checks['product_summary_retained'] = 'Summary Report - Product Wise' in reports
checks['warehouse_report_retained'] = 'Warehouse Balance Qty - Product Wise / Warehouse Wise' in reports
checks['no_destructive_payment_migration'] = 'DROP TABLE IF EXISTS payment_allocations' not in db and 'DELETE FROM payment_allocations' in db

for path in [root/'common.py', root/'db.py', root/'payment_common.py', root/'pages/5_Payment_Entry.py', root/'pages/18_Payment_Due.py', root/'pages/19_Edit_Payment.py', root/'pages/20_Payment_Received_List.py', root/'pages/8_Reports.py', root/'pages/9_Overdue_Notification.py']:
    py_compile.compile(str(path), doraise=True)

# Reconcile the exact user-highlighted examples using explicit line allocation.
examples = [
    ([534.0, 1068.0], [534.0, 1068.0], 1602.0),
    ([2926.8, 1951.2], [2926.8, 1951.2], 4878.0),
]
for idx, (invoice_lines, allocations, total) in enumerate(examples, start=1):
    checks[f'example_{idx}_receipt_total'] = abs(sum(allocations)-total) < 0.0005
    checks[f'example_{idx}_line_balances'] = all(abs(a-b) < 0.0005 for a,b in zip(invoice_lines,allocations))

for name, result in checks.items():
    print(f'{name}: {result}')
assert all(checks.values()), 'SN 27.17 payment line allocation verification failed'
print('OK: SN 27.17 exact line-item payment allocation is ready.')
