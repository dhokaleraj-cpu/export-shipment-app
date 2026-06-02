import sqlite3
from pathlib import Path

DB_NAME = "shipment_app.db"

print("Checking SQLite database...")
conn = sqlite3.connect(DB_NAME, timeout=30)
try:
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.execute("PRAGMA optimize")
    conn.commit()
    print("Database checkpoint completed.")
finally:
    conn.close()

for suffix in ["-wal", "-shm"]:
    p = Path(DB_NAME + suffix)
    if p.exists():
        try:
            p.unlink()
            print(f"Removed {p.name}")
        except Exception as e:
            print(f"Could not remove {p.name}: {e}")

print("Done. Now run: streamlit run app.py")
