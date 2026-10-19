"""Guarded SQL tool: the only way the agent touches the data."""
import re
import threading

import duckdb

MAX_ROWS = 1000
TIMEOUT_SECONDS = 30

# Words that change data, change settings, or read files
BLOCKED = re.compile(
    r"\b(insert|update|delete|drop|create|alter|attach|detach|copy|export|import|"
    r"install|load|pragma|set|reset|call|checkpoint|vacuum|"
    r"read_csv\w*|read_parquet|read_json\w*|read_text|read_blob|parquet_scan|glob)\b",
    re.IGNORECASE,
)
# File paths in quotes, e.g. FROM 'C:/secrets.csv'
FILE_LITERAL = re.compile(r"'[^']*\.(csv|tsv|parquet|json|txt|xlsx|duckdb|db)'", re.IGNORECASE)


def clean(sql):
    """Remove comments and a trailing semicolon."""
    sql = re.sub(r"--[^\n]*", "", sql)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return sql.strip().rstrip(";").strip()


def check_sql(sql):
    """Return the reason a query is not allowed, or None if it's safe."""
    if not sql:
        return "Empty query."
    if ";" in sql:
        return "Only one statement is allowed."
    if not re.match(r"(select|with)\b", sql, re.IGNORECASE):
        return "Only SELECT queries are allowed."
    match = BLOCKED.search(sql)
    if match:
        return f"Keyword not allowed: {match.group(0)}"
    if FILE_LITERAL.search(sql):
        return "Reading files directly is not allowed."
    return None


def run_sql(con, sql):
    """Check, run with a timeout, and return at most MAX_ROWS rows."""
    sql = clean(sql)
    problem = check_sql(sql)
    if problem:
        return {"ok": False, "sql": sql, "error": f"Blocked: {problem}"}

    timer = threading.Timer(TIMEOUT_SECONDS, con.interrupt)  # stops the query if too slow
    timer.start()
    try:
        cursor = con.execute(sql)
        columns = [d[0] for d in cursor.description]
        rows = cursor.fetchmany(MAX_ROWS + 1)  # one extra row tells us if it was cut off
    except duckdb.InterruptException:
        return {"ok": False, "sql": sql, "error": f"Query took over {TIMEOUT_SECONDS}s and was stopped."}
    except duckdb.Error as e:
        return {"ok": False, "sql": sql, "error": str(e).splitlines()[0]}
    finally:
        timer.cancel()

    return {"ok": True, "sql": sql, "columns": columns,
            "rows": rows[:MAX_ROWS], "truncated": len(rows) > MAX_ROWS}


if __name__ == "__main__":
    from src.semantic import connect

    con = connect()
    tests = {
        "normal query":    "SELECT carrier_name, COUNT(*) AS flights FROM flights GROUP BY 1 ORDER BY 2 DESC LIMIT 3",
        "delete attempt":  "DELETE FROM flights",
        "hidden 2nd step": "SELECT 1; DROP VIEW flights",
        "read a file":     "SELECT * FROM read_csv('C:/Users/hashi/secrets.csv')",
        "file shortcut":   "SELECT * FROM 'data/flights.parquet'",
        "bad column":      "SELECT made_up_column FROM flights",
        "too many rows":   "SELECT flight_date FROM flights",
    }
    for name, sql in tests.items():
        r = run_sql(con, sql)
        if r["ok"]:
            print(f"✅ ran     {name}: {len(r['rows'])} rows, truncated={r['truncated']}")
        else:
            print(f"🛑 stopped {name}: {r['error']}")