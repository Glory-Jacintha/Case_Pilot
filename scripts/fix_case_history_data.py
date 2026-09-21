import os
import csv
import psycopg
from dotenv import load_dotenv

load_dotenv()

conn = psycopg.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT", "5432"),
    dbname=os.getenv("DB_NAME", "postgres"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
)

DATA_FILE = "data/case_history_examples.csv"

try:
    with conn.cursor() as cur:

        print("Adding ID column...")

        cur.execute("""
            ALTER TABLE case_history_examples
            ADD COLUMN IF NOT EXISTS id BIGSERIAL;
        """)

        print("Removing case_id primary key...")

        cur.execute("""
            ALTER TABLE case_history_examples
            DROP CONSTRAINT IF EXISTS case_history_examples_pkey;
        """)

        print("Making ID the primary key...")

        cur.execute("""
            ALTER TABLE case_history_examples
            ADD CONSTRAINT case_history_examples_pkey PRIMARY KEY (id);
        """)

        print("Reading source data...")

        with open(DATA_FILE, "r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))

        print(f"Source rows: {len(rows)}")

        # Insert all source rows that are not already present.
        #
        # We identify an existing history record using all
        # source fields because case_id can legitimately repeat.
        inserted = 0

        for row in rows:
            cur.execute("""
                SELECT 1
                FROM case_history_examples
                WHERE case_id = %s
                  AND scenario = %s
                  AND domain = %s
                  AND case_description = %s
                  AND attempt = %s
                  AND result = %s
                  AND reason_or_next_step = %s
                LIMIT 1;
            """, (
                row["case_id"],
                row["scenario"],
                row["domain"],
                row["case_description"],
                row["attempt"],
                row["result"],
                row["reason_or_next_step"],
            ))

            if cur.fetchone():
                continue

            cur.execute("""
                INSERT INTO case_history_examples (
                    case_id,
                    scenario,
                    domain,
                    case_description,
                    attempt,
                    result,
                    reason_or_next_step
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, (
                row["case_id"],
                row["scenario"],
                row["domain"],
                row["case_description"],
                row["attempt"],
                row["result"],
                row["reason_or_next_step"],
            ))

            inserted += 1

        conn.commit()

        print(f"Inserted missing rows: {inserted}")

        cur.execute("""
            SELECT COUNT(*)
            FROM case_history_examples;
        """)

        count = cur.fetchone()[0]

        print(f"Final row count: {count}/15")

        if count != 15:
            raise RuntimeError(
                f"Expected 15 case history rows, found {count}"
            )

        print("case_history_examples repaired successfully.")

finally:
    conn.close()
    