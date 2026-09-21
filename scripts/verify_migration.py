import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

EXPECTED_COUNTS = {
    "customers": 100000,
    "products": 50,
    "orders": 100000,
    "payments": 100000,
    "deliveries": 100000,
    "returns": 3054,
    "refunds": 6083,
    "support_cases": 80093,
    "resolution_strategies": 8,
    "case_history_examples": 15,
    "data_dictionary": 12,
}

conn = psycopg.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT", "5432"),
    dbname=os.getenv("DB_NAME", "postgres"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
)

all_ok = True

try:
    with conn.cursor() as cur:
        print("=" * 60)
        print("CASEPILOT RDS MIGRATION VERIFICATION")
        print("=" * 60)

        for table, expected in EXPECTED_COUNTS.items():
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            actual = cur.fetchone()[0]

            status = "OK" if actual == expected else "CHECK"

            print(
                f"{table:<30} "
                f"{actual:>8,} / {expected:>8,} [{status}]"
            )

            if actual != expected:
                all_ok = False

finally:
    conn.close()

print("=" * 60)

if all_ok:
    print("ALL MIGRATED DATA VERIFIED SUCCESSFULLY.")
else:
    print("ONE OR MORE TABLE COUNTS DO NOT MATCH.")