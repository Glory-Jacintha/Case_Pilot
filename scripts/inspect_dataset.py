from pathlib import Path
import csv


DATA_DIR = Path("data")

csv_files = sorted(DATA_DIR.glob("*.csv"))

if not csv_files:
    print("No CSV files found in data/")
    raise SystemExit(1)

for file_path in csv_files:
    print("\n" + "=" * 80)
    print(f"FILE: {file_path.name}")
    print("=" * 80)

    with file_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.reader(file)

        headers = next(reader, [])
        print(f"Columns ({len(headers)}):")
        for index, header in enumerate(headers, start=1):
            print(f"  {index}. {header}")

        row_count = sum(1 for _ in reader)
        print(f"Rows: {row_count}")
        