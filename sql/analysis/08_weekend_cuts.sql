-- Weekend service: which routes lose the most trips (or disappear) on Sunday?
SELECT route, name, trips_weekday, trips_saturday, trips_sunday,
       ROUND(100.0 * (trips_weekday - trips_sunday) / trips_weekday, 0) AS sunday_cut_pct,
       CASE WHEN trips_sunday = 0 THEN 'No Sunday service' ELSE '' END AS note
FROM route_metrics
WHERE trips_weekday >= 20
ORDER BY sunday_cut_pct DESC, trips_weekday DESC
LIMIT 15;
