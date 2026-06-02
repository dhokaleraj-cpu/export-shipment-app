from dotenv import load_dotenv
import os
import psycopg2

load_dotenv()

conn = psycopg2.connect(
    os.getenv("DATABASE_URL"),
    sslmode="require"
)

cur = conn.cursor()
cur.execute("SELECT NOW();")

print("Connected Successfully")
print(cur.fetchone())

cur.close()
conn.close()