"""Run eval questions in a given mode and report accuracy.

Usage:
    python -m eval.run_eval --mode raw
    python -m eval.run_eval --mode semantic
"""
import argparse
import json
import re
import time
from pathlib import Path

import duckdb
import ollama

from src.prompt import SCHEMA_DOC, build_prompt
from src.semantic import connect as connect_semantic

MODEL = "qwen2.5-coder:7b"
QUESTION_IDS = ["q01", "q02", "q05", "q08", "q10"]


def connect_raw():
    """Raw Parquet columns, with only names and types as the schema."""
    con = duckdb.connect()
    con.execute("CREATE VIEW flights AS SELECT * FROM 'data/flights.parquet'")
    cols = con.execute("DESCRIBE flights").fetchall()
    schema = "Table: flights\nColumns: " + ", ".join(f"{name} {dtype}" for name, dtype, *_ in cols)
    return con, schema


def extract_sql(text):
    """Pull the SQL out of the reply, even if it's wrapped in ```sql ... ```."""
    match = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    return (match.group(1) if match else text).strip().rstrip(";")


def numbers(rows):
    """All numeric values in a result, sorted. Text labels are ignored."""
    return sorted(float(v) for row in rows for v in row
                  if isinstance(v, (int, float)) and not isinstance(v, bool))


def matches(actual, expected, tol=0.11):
    """Same numbers (within rounding tolerance), regardless of labels or column order."""
    a, e = numbers(actual), numbers(expected)
    return len(a) == len(e) and all(abs(x - y) <= tol for x, y in zip(a, e))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["raw", "semantic"], required=True)
    mode = parser.parse_args().mode

    if mode == "raw":
        con, schema = connect_raw()
    else:
        con, schema = connect_semantic(), SCHEMA_DOC

    key = {q["id"]: q for q in json.loads(Path("eval/answer_key.json").read_text())}
    results, correct = [], 0

    for qid in QUESTION_IDS:
        q = key[qid]
        start = time.time()
        reply = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": build_prompt(q["question"], schema)}],
            options={"temperature": 0},
        )["message"]["content"]
        sql = extract_sql(reply)

        try:
            rows = con.execute(sql).fetchall()
            ok, error = matches(rows, q["rows"]), None
        except Exception as e:
            ok, error = False, str(e).splitlines()[0]

        correct += ok
        results.append({"id": qid, "question": q["question"], "sql": sql, "correct": ok, "error": error})
        print(f"\n{'✅' if ok else '❌'} {qid}: {q['question']}  ({time.time() - start:.1f}s)")
        print(f"   SQL: {' '.join(sql.split())}")
        if error:
            print(f"   ERROR: {error}")

    print(f"\n[{mode}] Score: {correct}/{len(QUESTION_IDS)}")
    Path(f"eval/results_{mode}.json").write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()