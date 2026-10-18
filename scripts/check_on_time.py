"""Test three on-time definitions to find which one matches SkyMetrics (79.1%)."""
import duckdb

con = duckdb.connect()
con.execute("CREATE VIEW flights AS SELECT * FROM 'data/flights.parquet'")

print(con.sql("""
    SELECT
        -- A: on-time / ALL flights (what the handoff says)
        ROUND(100.0 * COUNT(*) FILTER (WHERE ARR_DEL15 = 0) / COUNT(*), 1)
            AS a_all_flights,
        -- B: on-time / flights that have an arrival result (no cancelled or diverted)
        ROUND(100.0 * COUNT(*) FILTER (WHERE ARR_DEL15 = 0) / COUNT(ARR_DEL15), 1)
            AS b_completed_only,
        -- C: on-time / non-cancelled flights
        ROUND(100.0 * COUNT(*) FILTER (WHERE ARR_DEL15 = 0)
              / COUNT(*) FILTER (WHERE CANCELLED = 0), 1)
            AS c_not_cancelled,
        -- D: NOT delayed / ALL flights (blanks counted as on-time, like DAX "<> 1")
        ROUND(100.0 * COUNT(*) FILTER (WHERE ARR_DEL15 IS DISTINCT FROM 1) / COUNT(*), 1)
            AS d_not_delayed
    FROM flights
"""))