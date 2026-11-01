"""Holdout set: new questions, never used for tuning. Run the agent on these ONCE."""
from eval.answer_key import ON_TIME, build

QUESTIONS = [
    {"id": "h01", "question": "What was United's on-time percentage in 2023?",
     "sql": f"SELECT ROUND({ON_TIME}, 2) AS on_time_pct FROM flights WHERE OP_UNIQUE_CARRIER = 'UA' AND YEAR = 2023"},

    {"id": "h02", "question": "How many flights departed from ORD in 2025?",
     "sql": "SELECT COUNT(*) AS flights FROM flights WHERE ORIGIN = 'ORD' AND YEAR = 2025"},

    {"id": "h03", "question": "Which carrier had the worst on-time percentage in 2025?",
     "sql": f"""SELECT OP_UNIQUE_CARRIER, ROUND({ON_TIME}, 2) AS on_time_pct FROM flights
                WHERE YEAR = 2025 GROUP BY 1 ORDER BY 2 ASC LIMIT 1"""},

    {"id": "h04", "question": "What was the average arrival delay for each year?",
     "sql": "SELECT YEAR, ROUND(AVG(ARR_DELAY), 2) AS avg_arr_delay FROM flights GROUP BY 1 ORDER BY 1"},

    {"id": "h05", "question": "How many flights were cancelled because of weather in 2024?",
     "sql": "SELECT COUNT(*) AS cancellations FROM flights WHERE CANCELLATION_CODE = 'B' AND YEAR = 2024"},

    {"id": "h06", "question": "Which 3 airports with at least 10,000 departing flights had the highest cancellation rate?",
     "sql": """SELECT ORIGIN, ROUND(100.0 * SUM(CANCELLED) / COUNT(*), 2) AS cancel_pct FROM flights
               GROUP BY 1 HAVING COUNT(*) >= 10000 ORDER BY 2 DESC LIMIT 3"""},

    {"id": "h07", "question": "What was the total carrier delay in 2025, in millions of minutes?",
     "sql": "SELECT ROUND(SUM(CARRIER_DELAY) / 1e6, 2) AS carrier_delay_millions FROM flights WHERE YEAR = 2025"},

    {"id": "h08", "question": "How many flights arrived at Denver (DEN) in 2024?",
     "sql": "SELECT COUNT(*) AS flights FROM flights WHERE DEST = 'DEN' AND YEAR = 2024"},

    {"id": "h09", "question": "What was the on-time percentage on Saturdays?",
     "sql": f"SELECT ROUND({ON_TIME}, 2) AS on_time_pct FROM flights WHERE dayname(FL_DATE) = 'Saturday'"},

    {"id": "h10", "question": "What was Spirit Airlines' cancellation rate in 2025?",
     "sql": """SELECT ROUND(100.0 * SUM(CANCELLED) / COUNT(*), 2) AS cancel_pct FROM flights
               WHERE OP_UNIQUE_CARRIER = 'NK' AND YEAR = 2025"""},

    # --- Trick questions ---
    {"id": "h11", "question": "What was Hawaiian Airlines' on-time percentage in 2026?", "expect": "no_data"},
    {"id": "h12", "question": "How many flights did Air Canada operate?", "expect": "no_data"},
]

if __name__ == "__main__":
    build(QUESTIONS, "eval/holdout_key.json")