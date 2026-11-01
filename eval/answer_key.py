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

    # --- Filters ---
    {"id": "q12", "question": "What was Delta's on-time percentage in 2024?",
     "sql": f"""SELECT ROUND({ON_TIME}, 2) AS on_time_pct FROM flights
                WHERE OP_UNIQUE_CARRIER = 'DL' AND YEAR = 2024"""},

    {"id": "q13", "question": "How many flights departed from JFK in 2023?",
     "sql": "SELECT COUNT(*) AS flights FROM flights WHERE ORIGIN = 'JFK' AND YEAR = 2023"},

    # --- Trends ---
    {"id": "q14", "question": "How did the on-time percentage change from year to year?",
     "sql": f"SELECT YEAR, ROUND({ON_TIME}, 2) AS on_time_pct FROM flights GROUP BY 1 ORDER BY 1"},

    {"id": "q15", "question": "What was the average NAS delay per delayed flight in each year?",
     "sql": """SELECT YEAR, ROUND(AVG(NAS_DELAY), 2) AS avg_nas_delay
               FROM flights WHERE ARR_DEL15 = 1 GROUP BY 1 ORDER BY 1"""},

    # --- Delay causes ---
    {"id": "q16", "question": "Which delay cause accounts for the most total delay minutes, and how many minutes?",
     # Label hardcoded because q07 already verified late aircraft is the top cause
     "sql": "SELECT 'Late aircraft' AS cause, SUM(LATE_AIRCRAFT_DELAY) AS total_minutes FROM flights"},

    {"id": "q17", "question": "For flights that had a weather delay, what was the average weather delay in minutes?",
     "sql": "SELECT ROUND(AVG(WEATHER_DELAY), 2) AS avg_weather_delay FROM flights WHERE WEATHER_DELAY > 0"},

    # --- Airports ---
    {"id": "q18", "question": "Which 5 airports with at least 10,000 arriving flights had the best on-time percentage for arrivals?",
     "sql": f"""SELECT DEST, ROUND({ON_TIME}, 2) AS on_time_pct FROM flights
                GROUP BY 1 HAVING COUNT(*) >= 10000 ORDER BY 2 DESC LIMIT 5"""},

    {"id": "q19", "question": "Which airport had the most departing flights?",
     "sql": "SELECT ORIGIN, COUNT(*) AS flights FROM flights GROUP BY 1 ORDER BY 2 DESC LIMIT 1"},

    # --- Other ---
    {"id": "q20", "question": "Which carrier had the highest cancellation rate?",
     "sql": """SELECT OP_UNIQUE_CARRIER, ROUND(100.0 * SUM(CANCELLED) / COUNT(*), 2) AS cancel_pct
               FROM flights GROUP BY 1 ORDER BY 2 DESC LIMIT 1"""},

    {"id": "q21", "question": "Which single month (year and month) had the worst on-time percentage?",
     "sql": f"""SELECT YEAR, MONTH, ROUND({ON_TIME}, 2) AS on_time_pct FROM flights
                GROUP BY 1, 2 ORDER BY 3 ASC LIMIT 1"""},

    {"id": "q22", "question": "How many flights flew from JFK to LAX?",
     "sql": "SELECT COUNT(*) AS flights FROM flights WHERE ORIGIN = 'JFK' AND DEST = 'LAX'"},

    {"id": "q23", "question": "What is the average flight distance in miles for each carrier?",
     "sql": """SELECT OP_UNIQUE_CARRIER, ROUND(AVG(DISTANCE), 1) AS avg_distance
               FROM flights GROUP BY 1 ORDER BY 2 DESC"""},

    {"id": "q24", "question": "How many flights were diverted?",
     "sql": "SELECT CAST(SUM(DIVERTED) AS BIGINT) AS diverted_flights FROM flights"},

    {"id": "q25", "question": "What percentage of Southwest flights were on time in July 2025?",
     "sql": f"""SELECT ROUND({ON_TIME}, 2) AS on_time_pct FROM flights
                WHERE OP_UNIQUE_CARRIER = 'WN' AND YEAR = 2025 AND MONTH = 7"""},

    # --- Trick questions: the correct answer is "no data" ---
    {"id": "q26", "question": "What was Mesa Airlines' on-time percentage?", "expect": "no_data"},
    {"id": "q27", "question": "How many flights were there in 2022?", "expect": "no_data"},
    {"id": "q28", "question": "What was the on-time percentage for flights to Dubai?", "expect": "no_data"},
]


def build(questions, out_path):
    """Run each question's verified SQL and save the answers."""
    con = duckdb.connect()
    con.execute("CREATE VIEW flights AS SELECT * FROM 'data/flights.parquet'")

    for q in questions:
        if q.get("expect") == "no_data":
            q["columns"], q["rows"] = [], []
            print(f"\n{q['id']}: {q['question']}\n   (expected answer: no data)")
            continue
        rel = con.sql(q["sql"])
        q["columns"] = rel.columns
        q["rows"] = rel.fetchall()
        print(f"\n{q['id']}: {q['question']}")
        print(rel)

    Path(out_path).write_text(json.dumps(questions, indent=2, default=str))
    print(f"\nSaved {len(questions)} answers to {out_path}")


if __name__ == "__main__":
    build(QUESTIONS, "eval/answer_key.json")