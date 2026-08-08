"""Apply and verify the additive SN 27.13 Product -> Customer -> Ship To schema."""

from __future__ import annotations

import json
import sys
import db


def main() -> int:
    if not db.DATABASE_URL:
        print("SN 27.13 database migration was not run locally: DATABASE_URL is not configured.")
        print("The deployed Streamlit pages will apply the same additive migration using Streamlit secrets.")
        return 2

    status = db.ensure_master_relationship_schema()
    print(json.dumps(status, indent=2, default=str))
    if status.get("ok"):
        print("OK: Product.customer_id and Customer.ship_to_master_id schema is ready.")
        return 0

    print("ERROR: SN 27.13 master relationship schema verification failed.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
