"""Semantic layer: clean, well-named views over the raw flight data.

Usage:
    python -m src.semantic             # self-check
    python -m src.semantic --rebuild   # rebuild the views after editing them
"""
import sys
from pathlib import Path

import duckdb

# Absolute paths, so it works no matter which folder you run it from
ROOT = Path(__file__).resolve().parent.parent  # the skyquery folder
PARQUET = (ROOT / "data" / "flights.parquet").as_posix()
DB_PATH = (ROOT / "data" / "skyquery.duckdb").as_posix()

CARRIER_NAMES = {
    "9E": "Endeavor Air", "AA": "American Airlines", "AS": "Alaska Airlines",
    "B6": "JetBlue", "DL": "Delta Air Lines", "F9": "Frontier Airlines",
    "G4": "Allegiant Air", "HA": "Hawaiian Airlines", "MQ": "Envoy Air",
    "NK": "Spirit Airlines", "OH": "PSA Airlines", "OO": "SkyWest Airlines",
    "UA": "United Airlines", "WN": "Southwest Airlines",
    "YV": "Mesa Airlines",  # not in the 2023-2025 data; kept so the trick question returns nothing
    "YX": "Republic Airways",
}

_carrier_case = "CASE OP_UNIQUE_CARRIER " + " ".join(
    f"WHEN '{code}' THEN '{name}'" for code, name in CARRIER_NAMES.items()
) + " ELSE OP_UNIQUE_CARRIER END"

VIEW_SQL = f"""
CREATE OR REPLACE VIEW flights AS
SELECT
    -- Time
    FL_DATE                 AS flight_date,
    YEAR                    AS year,
    QUARTER                 AS quarter,
    MONTH                   AS month,
    monthname(FL_DATE)      AS month_name,
    dayname(FL_DATE)        AS weekday,
    isodow(FL_DATE)         AS weekday_num,      -- 1 = Monday ... 7 = Sunday

    -- Carrier
    OP_UNIQUE_CARRIER       AS carrier_code,
    {_carrier_case}         AS carrier_name,

    -- Airports
    ORIGIN AS origin, ORIGIN_CITY_NAME AS origin_city, ORIGIN_STATE_ABR AS origin_state,
    DEST   AS dest,   DEST_CITY_NAME   AS dest_city,   DEST_STATE_ABR   AS dest_state,

    -- Delays (minutes; negative = early)
    DEP_DELAY               AS dep_delay_min,
    ARR_DELAY               AS arr_delay_min,

    -- Outcomes (cancelled and diverted flights are NOT on time)
    coalesce(ARR_DEL15 = 0, false) AS is_on_time,
    coalesce(ARR_DEL15 = 1, false) AS is_delayed,
    CANCELLED = 1                  AS is_cancelled,
    DIVERTED = 1                   AS is_diverted,
    CASE CANCELLATION_CODE
        WHEN 'A' THEN 'Carrier'  WHEN 'B' THEN 'Weather'
        WHEN 'C' THEN 'National Air System'  WHEN 'D' THEN 'Security'
    END                            AS cancellation_reason,

    -- Distance
    DISTANCE                AS distance_miles,

    -- Delay causes (minutes; only filled when arrival delay >= 15 min, else NULL)
    CARRIER_DELAY           AS carrier_delay_min,
    WEATHER_DELAY           AS weather_delay_min,
    NAS_DELAY               AS nas_delay_min,
    SECURITY_DELAY          AS security_delay_min,
    LATE_AIRCRAFT_DELAY     AS late_aircraft_delay_min
FROM '{PARQUET}'
"""

CAUSES_VIEW_SQL = """
CREATE OR REPLACE VIEW delay_causes AS
SELECT * FROM (
    UNPIVOT (
        SELECT flight_date, year, month, carrier_code, carrier_name, origin, dest,
               carrier_delay_min       AS "Carrier",
               weather_delay_min       AS "Weather",
               nas_delay_min           AS "National Air System",
               security_delay_min      AS "Security",
               late_aircraft_delay_min AS "Late aircraft"
        FROM flights
    )
    ON "Carrier", "Weather", "National Air System", "Security", "Late aircraft"
    INTO NAME cause VALUE minutes
)
WHERE minutes > 0
"""


def build_db():
    """Save the views into a small database file. This is the only write connection."""
    Path(DB_PATH).parent.mkdir(exist_ok=True)
    con = duckdb.connect(DB_PATH)
    con.execute(VIEW_SQL)
    con.execute(CAUSES_VIEW_SQL)
    con.close()


def connect():
    """Open the database READ-ONLY, allowed to read only flights.parquet."""
    if not Path(DB_PATH).exists():
        build_db()
    con = duckdb.connect(DB_PATH, read_only=True)

    # Layer 2: DuckDB itself enforces these, however the SQL is written
    con.execute(f"SET allowed_paths = ['{PARQUET}']")
    con.execute("SET enable_external_access = false")
    con.execute("SET autoload_known_extensions = false")
    con.execute("SET memory_limit = '4GB'")
    con.execute("SET lock_configuration = true")  # must be last: locks everything above
    return con


if __name__ == "__main__":
    if "--rebuild" in sys.argv:
        build_db()
        print(f"Rebuilt views in {DB_PATH}")

    # Quick self-check against the answer key
    con = connect()
    print(con.sql("""
        SELECT COUNT(*)                                  AS flights,        -- expect 20,928,599
               ROUND(100 * AVG(is_on_time::INT), 2)      AS on_time_pct,    -- expect 77.49
               COUNT(DISTINCT carrier_name)              AS carriers        -- expect 15
        FROM flights
    """))