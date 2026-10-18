"""Semantic layer: a clean, well-named view over the raw flight data."""
import duckdb

PARQUET = "data/flights.parquet"

CARRIER_NAMES = {
    "9E": "Endeavor Air", "AA": "American Airlines", "AS": "Alaska Airlines",
    "B6": "JetBlue", "DL": "Delta Air Lines", "F9": "Frontier Airlines",
    "G4": "Allegiant Air", "HA": "Hawaiian Airlines", "MQ": "Envoy Air",
    "NK": "Spirit Airlines", "OH": "PSA Airlines", "OO": "SkyWest Airlines",
    "UA": "United Airlines", "WN": "Southwest Airlines", "YV": "Mesa Airlines",
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


def connect():
    """Open DuckDB with the semantic view ready to query."""
    con = duckdb.connect()
    con.execute(VIEW_SQL)
    return con


if __name__ == "__main__":
    # Quick self-check against the answer key
    con = connect()
    print(con.sql("""
        SELECT COUNT(*)                                  AS flights,        -- expect 20,928,599
               ROUND(100 * AVG(is_on_time::INT), 2)      AS on_time_pct,    -- expect 77.49
               COUNT(DISTINCT carrier_name)              AS carriers        -- expect 15
        FROM flights
    """))
    print(con.sql("SELECT weekday, ROUND(100 * AVG(is_on_time::INT), 2) AS on_time_pct "
                  "FROM flights GROUP BY 1 ORDER BY 2 DESC LIMIT 2"))  # expect Tuesday 80.83 first``