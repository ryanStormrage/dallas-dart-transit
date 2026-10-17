-- Which routes run the longest day, and which barely run at all?
SELECT * FROM (
    SELECT 'Longest span' AS list, route, name, span_hours, first_trip, last_trip_end, trips_weekday
    FROM route_metrics ORDER BY span_hours DESC LIMIT 8
)
UNION ALL
SELECT * FROM (
    SELECT 'Shortest span', route, name, span_hours, first_trip, last_trip_end, trips_weekday
    FROM route_metrics WHERE span_hours IS NOT NULL ORDER BY span_hours ASC LIMIT 8
);
