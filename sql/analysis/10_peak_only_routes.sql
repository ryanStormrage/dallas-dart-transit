-- Commuter-style routes: service at rush hour but little or none midday.
SELECT route, name, peak_headway_min, midday_headway_min, trips_weekday, first_trip, last_trip_end
FROM route_metrics
WHERE tier IN ('Peak only', 'Limited (60+ min)')
ORDER BY trips_weekday DESC;
