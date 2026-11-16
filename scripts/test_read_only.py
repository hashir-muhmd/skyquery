"""Prove layer 2: harmful SQL sent straight to DuckDB (skipping layer 1's checks) is refused."""
import tempfile
from pathlib import Path

from src.semantic import connect

# A real "secret" file outside the project, so a read attempt has something to find
secret = Path(tempfile.gettempdir()) / "skyquery_secret_test.csv"
secret.write_text("password\nhunter2\n")
s = secret.as_posix()

SHOULD_RUN = {
    "normal query":       "SELECT COUNT(*) FROM flights",
}
SHOULD_FAIL = {
    "drop a view":        "DROP VIEW flights",
    "create table":       "CREATE TABLE hack AS SELECT 1",
    "replace view":       "CREATE OR REPLACE VIEW flights AS SELECT 1 AS x",
    "read_csv":           f"SELECT * FROM read_csv('{s}')",
    "single-quoted path": f"SELECT * FROM '{s}'",
    "double-quoted path": f'SELECT * FROM "{s}"',
    "query() trick":      f"SELECT * FROM query('SELECT * FROM read_' || 'csv(''{s}'')')",
    "unlock settings":    "SET enable_external_access = true",
}

con = connect()
failures = 0
for label, handle in [("connection", con), ("cursor (what the app uses)", con.cursor())]:
    print(f"\n--- {label} ---")
    for name, sql in {**SHOULD_RUN, **SHOULD_FAIL}.items():
        try:
            handle.execute(sql).fetchall()
            ran, err = True, ""
        except Exception as e:
            ran, err = False, str(e).splitlines()[0]
        ok = ran == (name in SHOULD_RUN)
        failures += not ok
        print(f"{'✅' if ok else '❌'} {'ran    ' if ran else 'refused'} {name}"
              + (f": {err[:70]}" if err else ""))

secret.unlink()  # clean up the fake secret file
print("\nAll checks passed" if failures == 0 else f"\n{failures} CHECK(S) FAILED")