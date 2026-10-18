"""Build the answer key: questions + verified SQL + correct results."""
import json
from pathlib import Path

import duckdb

ON_TIME = "100.0 * COUNT(*) FILTER (WHERE ARR_DEL15 = 0) / COUNT(*)"  # agreed definition (A)

QUESTIONS = [
    {"id": "q01", "question": "How many flights are in the dataset?",
     "sql": "SELECT COUNT(*) AS total_flights FROM flights"},

    {"id": "q02", "question": "What is the overall on-time percentage?",
     "sql": f"SELECT ROUND({ON_TIME}, 2) AS on_time_pct FROM flights"},

    {"id": "q03", "question": "What is the average arrival delay in minutes?",
     "sql": "SELECT ROUND(AVG(ARR_DELAY), 2) AS avg_arr_delay FROM flights"},

    {"id": "q04", "question": "What is the average departure delay in minutes?",
     "sql": "SELECT ROUND(AVG(DEP_DELAY), 2) AS avg_dep_delay FROM flights"},

    {"id": "q05", "question": "What percentage of flights were cancelled?",
     "sql": "SELECT ROUND(100.0 * SUM(CANCELLED) / COUNT(*), 2) AS cancel_pct FROM flights"},

    {"id": "q06", "question": "How many cancellations were there for each reason?",
     "sql": """SELECT CANCELLATION_CODE, COUNT(*) AS cancellations
               FROM flights WHERE CANCELLED = 1
               GROUP BY 1 ORDER BY 2 DESC"""},

    {"id": "q07", "question": "What are the total delay minutes by cause, in millions?",
     "sql": """SELECT ROUND(SUM(LATE_AIRCRAFT_DELAY) / 1e6, 2) AS late_aircraft,
                      ROUND(SUM(CARRIER_DELAY) / 1e6, 2)       AS carrier,
                      ROUND(SUM(NAS_DELAY) / 1e6, 2)           AS nas,
                      ROUND(SUM(WEATHER_DELAY) / 1e6, 2)       AS weather,
                      ROUND(SUM(SECURITY_DELAY) / 1e6, 2)      AS security
               FROM flights"""},

    {"id": "q08", "question": "What is the on-time percentage for each carrier, best to worst?",
     "sql": f"""SELECT OP_UNIQUE_CARRIER, ROUND({ON_TIME}, 2) AS on_time_pct
                FROM flights GROUP BY 1 ORDER BY 2 DESC"""},

    {"id": "q09", "question": "What is the on-time percentage for each month?",
     "sql": f"""SELECT MONTH, ROUND({ON_TIME}, 2) AS on_time_pct
                FROM flights GROUP BY 1 ORDER BY 1"""},

    {"id": "q10", "question": "What is the on-time percentage for each day of the week?",
     "sql": f"""SELECT dayname(FL_DATE) AS weekday, ROUND({ON_TIME}, 2) AS on_time_pct
                FROM flights GROUP BY 1 ORDER BY 2 DESC"""},

    {"id": "q11", "question": "How many flights did Mesa Airlines (YV) operate each year?",
     "sql": """SELECT YEAR, COUNT(*) AS flights
               FROM flights WHERE OP_UNIQUE_CARRIER = 'YV'
               GROUP BY 1 ORDER BY 1"""},
]


def main():
    con = duckdb.connect()
    con.execute("CREATE VIEW flights AS SELECT * FROM 'data/flights.parquet'")

    for q in QUESTIONS:
        rel = con.sql(q["sql"])
        q["columns"] = rel.columns
        q["rows"] = rel.fetchall()
        print(f"\n{q['id']}: {q['question']}")
        print(rel)

    out = Path("eval/answer_key.json")
    out.write_text(json.dumps(QUESTIONS, indent=2, default=str))
    print(f"\nSaved {len(QUESTIONS)} answers to {out}")


if __name__ == "__main__":
    main()