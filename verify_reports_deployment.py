from pathlib import Path
import sys

report_path = Path("pages/8_Reports.py")
if not report_path.exists():
    print("ERROR: pages/8_Reports.py not found")
    sys.exit(1)

txt = report_path.read_text(encoding="utf-8", errors="ignore")

bad_patterns = [
    "return fetch_all(sql, tuple(base_params) + tuple(access_params))",
    "elif report == 'Original Invoice Number Wise Payment Due':",
    "(invoice_filter, invoice_filter, delivery_invoice_filter, delivery_invoice_filter, customer_filter, customer_filter, product_filter, product_filter)",
    "? = '' OR",
]

failed = False
for pattern in bad_patterns:
    if pattern in txt:
        print("FAILED: old bad Reports code still exists:", pattern)
        failed = True

required = [
    "REPORTS_DEPLOY_VERSION",
    "POSTGRESQL SAFE",
    "expected_params = final_sql.count(\"%s\")",
]
for pattern in required:
    if pattern not in txt:
        print("FAILED: required new Reports marker missing:", pattern)
        failed = True

if failed:
    sys.exit(1)

print("OK: Reports file is the new PostgreSQL-safe version.")
print("OK: Old line 293 payment-due code is removed.")
print("OK: Ready to commit and push.")
