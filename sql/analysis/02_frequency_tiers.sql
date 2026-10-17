-- How many routes fall in each frequency tier (midday, weekday)?
SELECT
    tier,
    COUNT(*)                                          AS routes,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_routes,
    SUM(trips_weekday)                                AS weekday_trips
FROM route_metrics
GROUP BY tier
ORDER BY MIN(COALESCE(midday_headway_min, 999));
