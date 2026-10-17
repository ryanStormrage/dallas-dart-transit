-- The 15 most frequent bus routes at midday.
SELECT route, name, midday_headway_min, peak_headway_min, trips_weekday,
       first_trip || ' – ' || last_trip_end AS service_span
FROM route_metrics
WHERE midday_headway_min IS NOT NULL
ORDER BY midday_headway_min, trips_weekday DESC
LIMIT 15;
