-- Network at a glance: how much bus service does DART run?
SELECT
    COUNT(*)                                      AS bus_routes,
    SUM(trips_weekday)                            AS weekday_trips,
    SUM(trips_saturday)                           AS saturday_trips,
    SUM(trips_sunday)                             AS sunday_trips,
    ROUND(100.0 * SUM(trips_sunday) / SUM(trips_weekday), 1) AS sunday_as_pct_of_weekday,
    ROUND(SUM(length_mi), 0)                      AS total_route_miles_one_way,
    ROUND(AVG(avg_speed_mph), 1)                  AS avg_scheduled_speed_mph
FROM route_metrics;
