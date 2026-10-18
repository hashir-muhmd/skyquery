"""Baseline: ask the model 5 questions with only the raw schema, no extra help."""
import json
import re
import time
from pathlib import Path

import duckdb
import ollama

MODEL = "qwen2.5-coder:7b"
BASELINE_IDS = ["q01", "q02", "q05", "q08", "q10"]

PROMPT = """You write DuckDB SQL.
Table: flights
Columns: {schema}

Question: {question}

Return only one SQL query, no explanation."""


def extract_sql(text):
    """Pull the SQL out of the reply, even if it's wrapped in ```sql ... ```."""
    match = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    return (match.group(1) if match else text).strip().rstrip(";")


def normalise(rows):
    """Turn a result into a sorted list of values so different layouts compare fairly."""
    values = []
    for row in rows:
        for v in row:
            values.append(str(round(float(v), 1)) if isinstance(v, (int, float)) else str(v))
    return sorted(values)


def main():
    key = {q["id"]: q for q in json.loads(Path("eval/answer_key.json").read_text())}
    con = duckdb.connect()
    con.execute("CREATE VIEW flights AS SELECT * FROM 'data/flights.parquet'")
    schema = ", ".join(f"{name} {dtype}" for name, dtype, *_ in con.execute("DESCRIBE flights").fetchall())

    results, correct = [], 0
    for qid in BASELINE_IDS:
        q = key[qid]
        start = time.time()
        reply = ollama.chat(model=MODEL, messages=[
            {"role": "user", "content": PROMPT.format(schema=schema, question=q["question"])}
        ])["message"]["content"]
        sql = extract_sql(reply)

        try:
            rows = con.execute(sql).fetchall()
            ok = normalise(rows) == normalise(q["rows"])
            error = None
        except Exception as e:
            rows, ok, error = None, False, str(e).splitlines()[0]

        correct += ok
        results.append({"id": qid, "question": q["question"], "sql": sql, "correct": ok, "error": error})
        print(f"\n{'✅' if ok else '❌'} {qid}: {q['question']}  ({time.time() - start:.1f}s)")
        print(f"   SQL: {' '.join(sql.split())}")
        if error:
            print(f"   ERROR: {error}")

    print(f"\nBaseline score: {correct}/{len(BASELINE_IDS)}")
    Path("eval/baseline_results.json").write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()