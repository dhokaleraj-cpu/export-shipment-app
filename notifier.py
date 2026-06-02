from app import overdue_rows, send_email
from db import init_db
init_db()

for row in overdue_rows():
    body = f"Dear {row['customer_name']}, payment is overdue for invoice {row['delivery_invoice_no']}. Due date: {row['payment_due_date']}. Pending amount: {row['pending_amount']}."
    if row.get("email"):
        ok, msg = send_email(row["email"], f"Overdue Payment - {row['delivery_invoice_no']}", body)
        print(row["delivery_invoice_no"], msg)
