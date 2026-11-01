"""Run the eval questions in a given mode and report accuracy.

Modes:
    raw       one model call, raw columns only
    semantic  one model call, semantic view + schema guide
    agent     full agent: semantic layer + retry on error

Usage:
    python -m eval.run_eval --mode agent
"""
import argparse
import json
import math
import time
from pathlib import Path

import duckdb
import ollama

from src.agent import MODEL, answer, extract_sql
from src.prompt import SCHEMA_DOC, build_prompt
from src.semantic import connect as connect_semantic
from src.sql_tool import run_sql

LABEL_COLUMNS = {"year", "month", "quarter"}  # labels, not answers


def connect_raw():
    """Raw Parquet columns, with only names and types as the schema."""
    con = duckdb.connect()
    con.execute("CREATE VIEW flights AS SELECT * FROM 'data/flights.parquet'")
    cols = con.execute("DESCRIBE flights").fetchall()
    schema = "Table: flights\nColumns: " + ", ".join(f"{name} {dtype}" for name, dtype, *_ in cols)
    return con, schema


def single_call(question, con, schema):
    """One model call, no retry."""
    reply = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": build_prompt(question, schema, examples="")}],
        options={"temperature": 0},
    )["message"]["content"]
    result = run_sql(con, extract_sql(reply))
    result["attempts"] = 1
    return result


def numeric(values):
    """Keep real numbers only (skip text, booleans, nulls and NaN)."""
    out = []
    for v in values:
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            continue
        if isinstance(v, float) and math.isnan(v):
            continue
        out.append(float(v))
    return out


def expected_values(q):
    """Numbers the answer must contain (label columns like YEAR are skipped)."""
    keep = [i for i, col in enumerate(q["columns"]) if col.lower() not in LABEL_COLUMNS]
    return numeric(row[i] for row in q["rows"] for i in keep)


def close(actual, expected):
    return abs(actual - expected) <= max(0.11, 0.001 * abs(expected))


def is_correct(q, result):
    # Trick questions: nothing, zeros/nulls, or an honest give-up all count as correct
    if q.get("expect") == "no_data" or not q["rows"]:
        if not result["ok"]:
            return True
        return all(v == 0 for v in numeric(v for row in result["rows"] for v in row))

    if not result["ok"]:
        return False

    pool = numeric(v for row in result["rows"] for v in row)
    expected = expected_values(q)
    # Same rows, OR same amount of numbers in a different layout (wide vs long)
    if len(result["rows"]) != len(q["rows"]) and len(pool) != len(expected):
        return False
    for e in expected:
        match = next((i for i, a in enumerate(pool) if close(a, e)), None)
        if match is None:
            return False
        pool.pop(match)  # each number can only be used once
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["raw", "semantic", "agent"], required=True)
    parser.add_argument("--set", dest="qset", choices=["dev", "holdout"], default="dev")
    args = parser.parse_args()
    mode = args.mode

    if mode == "raw":
        con, schema = connect_raw()
    else:
        con, schema = connect_semantic(), SCHEMA_DOC

    key_file = "eval/answer_key.json" if args.qset == "dev" else "eval/holdout_key.json"
    questions = json.loads(Path(key_file).read_text())
    results, correct = [], 0

    for q in questions:
        start = time.time()
        if mode == "agent":
            result = answer(q["question"], con, verbose=False)
        else:
            result = single_call(q["question"], con, schema)

        ok = is_correct(q, result)
        correct += ok
        retries = f", {result['attempts']} attempts" if result["attempts"] > 1 else ""
        print(f"{'✅' if ok else '❌'} {q['id']}: {q['question']}  ({time.time() - start:.1f}s{retries})")
        if not ok:
            print(f"     SQL: {' '.join(result['sql'].split())}")
            if not result["ok"]:
                print(f"     ERROR: {result['error']}")

        results.append({"id": q["id"], "question": q["question"], "sql": result["sql"],
                        "correct": ok, "attempts": result["attempts"], "error": result.get("error")})

    print(f"\n[{mode} / {args.qset}] Score: {correct}/{len(questions)} ({100 * correct / len(questions):.0f}%)")
    Path(f"eval/results_{mode}_{args.qset}.json").write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()