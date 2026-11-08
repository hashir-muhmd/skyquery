"""Prove layer 2 works: send harmful SQL straight to DuckDB, skipping our keyword checks."""
from src.semantic import connect

con = connect()

tests = {
    "normal query":  "SELECT COUNT(*) FROM flights",
    "drop a view":   "DROP VIEW flights",
    "create table":  "CREATE TABLE hack AS SELECT 1",
    "replace view":  "CREATE OR REPLACE VIEW flights AS SELECT 1 AS x",
}

for name, sql in tests.items():
    try:
        con.execute(sql)
        print(f"⚠️  RAN       {name}")
    except Exception as e:
        print(f"✅ refused   {name}: {str(e).splitlines()[0]}")