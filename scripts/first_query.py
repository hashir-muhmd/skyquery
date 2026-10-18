"""First queries on flights.parquet: check types and match SkyMetrics numbers."""
import duckdb

con = duckdb.connect()
con.execute("CREATE VIEW flights AS SELECT * FROM 'data/flights.parquet'")

# 1. Column names and types
print(con.sql("DESCRIBE flights"))

# 2. Three SkyMetrics numbers to match
print(con.sql("""
    SELECT
        COUNT(*)                                          AS total_flights,
        ROUND(100.0 * COUNT(*) FILTER (WHERE ARR_DEL15 = 0) / COUNT(*), 1)
                                                          AS on_time_pct,      -- expect 79.1
        ROUND(AVG(ARR_DELAY), 2)                          AS avg_arr_delay,    -- expect 7.41
        ROUND(100.0 * SUM(CANCELLED) / COUNT(*), 2)       AS cancel_rate_pct   -- expect ~1.4
    FROM flights
"""))