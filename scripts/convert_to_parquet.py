"""Convert the 36 SkyMetrics CSV files into one Parquet file."""
import time
from pathlib import Path

import duckdb

# Where the raw CSVs live (from the SkyMetrics project)
RAW_DIR = Path(r"C:\Users\hashi\Documents\Programming\Projects\skymetrics\data\raw")

# Where the Parquet file goes (skyquery/data/flights.parquet)
OUT_FILE = Path(__file__).resolve().parent.parent / "data" / "flights.parquet"

EXPECTED_ROWS = 20_928_599


def main():
    # 1. Check the input files exist
    csv_files = sorted(RAW_DIR.glob("*.csv"))
    print(f"Found {len(csv_files)} CSV files")
    if len(csv_files) != 36:
        raise SystemExit("Expected 36 files. Check RAW_DIR.")

    OUT_FILE.parent.mkdir(exist_ok=True)
    con = duckdb.connect()

    # 2. Read all CSVs at once and write one Parquet file
    print("Converting... (this can take a few minutes)")
    start = time.time()
    con.execute(f"""
        COPY (
            SELECT * REPLACE (make_date(YEAR, MONTH, DAY_OF_MONTH) AS FL_DATE)
            FROM read_csv('{RAW_DIR.as_posix()}/*.csv',
                          types = {{'CANCELLATION_CODE': 'VARCHAR'}})
        )
        TO '{OUT_FILE.as_posix()}' (FORMAT parquet, COMPRESSION zstd)
    """)
    print(f"Done in {time.time() - start:.0f} seconds")

    # 3. Verify the result
    rows, first_day, last_day = con.execute(f"""
        SELECT COUNT(*), MIN(FL_DATE), MAX(FL_DATE)
        FROM '{OUT_FILE.as_posix()}'
    """).fetchone()

    size_mb = OUT_FILE.stat().st_size / 1_000_000
    print(f"Rows:       {rows:,}")
    print(f"Date range: {first_day} to {last_day}")
    print(f"File size:  {size_mb:.0f} MB")
    print("Row count matches SkyMetrics ✅" if rows == EXPECTED_ROWS
          else f"Row count MISMATCH ❌ (expected {EXPECTED_ROWS:,})")


if __name__ == "__main__":
    main()