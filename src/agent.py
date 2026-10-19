"""SkyQuery agent: question -> SQL -> guarded run -> retry on error.

Usage:
    python -m src.agent "your question"
"""
import re
import sys

import ollama

from src.prompt import build_prompt
from src.semantic import connect
from src.sql_tool import run_sql

MODEL = "qwen2.5-coder:7b"
MAX_RETRIES = 2

RETRY_MESSAGE = """That query failed with this error:
{error}

Fix the query. Return only the corrected SQL, no explanation."""

SUMMARY_PROMPT = """Question: {question}

SQL used:
{sql}

Result ({count} rows):
{table}

Answer the question in 1-3 sentences using ONLY the numbers in the result.
Then add one line starting with "Note:" saying how the question was interpreted
(say whether airports are departures (origin) or arrivals (dest), and which years were included)."""


def extract_sql(text):
    """Pull the SQL out of the reply, even if it's wrapped in ```sql ... ```."""
    match = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    return (match.group(1) if match else text).strip()


def ask_model(messages):
    reply = ollama.chat(model=MODEL, messages=messages, options={"temperature": 0})
    return reply["message"]["content"]


def answer(question, con, verbose=True):
    """Run the agent loop and return the final result."""
    messages = [{"role": "user", "content": build_prompt(question)}]

    for attempt in range(1, MAX_RETRIES + 2):        # 1 try + 2 retries = 3 attempts max
        reply = ask_model(messages)
        result = run_sql(con, extract_sql(reply))
        result["attempts"] = attempt

        if verbose:
            print(f"\nAttempt {attempt}: {' '.join(result['sql'].split())}")
            if not result["ok"]:
                print(f"   ❌ {result['error']}")

        if result["ok"]:
            return result

        # Show the model its own SQL and the error, then let it try again
        messages += [
            {"role": "assistant", "content": reply},
            {"role": "user", "content": RETRY_MESSAGE.format(error=result["error"])},
        ]

    return result


def summarize(question, result, limit=20):
    """Second model call: turn the result table into a short, grounded answer."""
    lines = [" | ".join(result["columns"])]
    lines += [" | ".join(str(v) for v in row) for row in result["rows"][:limit]]
    prompt = SUMMARY_PROMPT.format(
        question=question,
        sql=result["sql"],
        count=len(result["rows"]),
        table="\n".join(lines),
    )
    return ask_model([{"role": "user", "content": prompt}])


def print_table(result, limit=20):
    cols, rows = result["columns"], result["rows"]
    print("\n" + " | ".join(cols))
    for row in rows[:limit]:
        print(" | ".join(f"{v:,.2f}" if isinstance(v, float) else str(v) for v in row))
    if len(rows) > limit or result["truncated"]:
        total = f"{len(rows)}+" if result["truncated"] else str(len(rows))
        print(f"... showing {min(limit, len(rows))} of {total} rows")


def main():
    if len(sys.argv) < 2:
        print('Usage: python -m src.agent "your question"')
        return

    question = " ".join(sys.argv[1:])
    result = answer(question, connect())

    if result["ok"]:
        print_table(result)
        print("\n" + summarize(question, result))
    else:
        print(f"\nSorry, I couldn't answer that after {result['attempts']} attempts.")


if __name__ == "__main__":
    main()