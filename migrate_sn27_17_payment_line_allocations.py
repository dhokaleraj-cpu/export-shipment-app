from db import ensure_payment_allocation_schema, DATABASE_URL

if not DATABASE_URL:
    print('DATABASE_URL is not configured locally; runtime page will apply the same additive migration from Streamlit secrets.')
    raise SystemExit(2)

ensure_payment_allocation_schema()
print('SN 27.17 payment_allocations schema: APPLIED / VERIFIED')
