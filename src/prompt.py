"""Prompt for the SQL agent: schema guide + business rules."""

SCHEMA_DOC = """Table: flights (one row per scheduled US domestic flight, 2023-2025)

Columns:
- flight_date DATE
- year, quarter, month INTEGER; month_name TEXT ('January', ...)
- weekday TEXT ('Monday', ...); weekday_num INTEGER (1 = Monday ... 7 = Sunday)
- carrier_code TEXT, carrier_name TEXT. The 15 carriers in the data:
  9E Endeavor Air, AA American Airlines, AS Alaska Airlines, B6 JetBlue, DL Delta Air Lines,
  F9 Frontier Airlines, G4 Allegiant Air, HA Hawaiian Airlines, MQ Envoy Air, NK Spirit Airlines,
  OH PSA Airlines, OO SkyWest Airlines, UA United Airlines, WN Southwest Airlines, YX Republic Airways
- origin, dest TEXT: airport codes (e.g. 'JFK'); origin_city, dest_city, origin_state, dest_state TEXT
- dep_delay_min, arr_delay_min DOUBLE: delay in minutes, negative = early, NULL if cancelled
- is_on_time BOOLEAN: arrived less than 15 min late. Cancelled and diverted flights = false
- is_delayed BOOLEAN: arrived 15+ min late
- is_cancelled, is_diverted BOOLEAN
- cancellation_reason TEXT: 'Carrier', 'Weather', 'National Air System', 'Security'; NULL if not cancelled
- distance_miles DOUBLE
- carrier_delay_min, weather_delay_min, nas_delay_min, security_delay_min, late_aircraft_delay_min DOUBLE:
  delay minutes by cause. NULL means not applicable (only filled for flights 15+ min late)

Table: delay_causes (one row per delayed flight per cause; only flights 15+ min late)
- flight_date, year, month, carrier_code, carrier_name, origin, dest (same as flights)
- cause TEXT: 'Carrier', 'Weather', 'National Air System', 'Security', 'Late aircraft'
- minutes DOUBLE: delay minutes from that cause (can be 0)

Rules:
- On-time percentage = ROUND(100 * AVG(is_on_time::INT), 2), over ALL flights.
- Cancellation rate = ROUND(100 * AVG(is_cancelled::INT), 2).
- "Best to worst" means ORDER BY the metric DESC.
- When ranking airports, only include airports with at least 10,000 flights.
- "Airport" means the departure airport (origin), unless the question mentions arrivals or destinations (then use dest).
- If no year is given, include all years 2023-2025 combined.
- If the question names a carrier, airport or year that is not in the data, still filter for exactly what was asked (the result will be empty). Never substitute a different one.
- For questions that compare delay causes (which cause, minutes by cause), use delay_causes and GROUP BY cause."""

PROMPT_TEMPLATE = """You write DuckDB SQL for the table below.

{schema}

Question: {question}

Return only one SQL query, no explanation."""


def build_prompt(question, schema=SCHEMA_DOC):
    """Fill the template with a schema guide and the user's question."""
    return PROMPT_TEMPLATE.format(schema=schema, question=question)