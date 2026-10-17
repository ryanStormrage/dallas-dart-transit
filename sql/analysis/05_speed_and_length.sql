-- Slowest and fastest routes by scheduled speed (routes at least 3 miles long).
WITH ranked AS (
    SELECT route, name, length_mi, trip_minutes, avg_speed_mph, avg_stop_spacing_ft,
           RANK() OVER (ORDER BY avg_speed_mph ASC)  AS slow_rank,
           RANK() OVER (ORDER BY avg_speed_mph DESC) AS fast_rank
    FROM route_metrics
    WHERE avg_speed_mph IS NOT NULL AND length_mi >= 3
)
SELECT CASE WHEN slow_rank <= 8 THEN 'Slowest' ELSE 'Fastest' END AS list,
       route, name, length_mi, trip_minutes, avg_speed_mph, avg_stop_spacing_ft
FROM ranked
WHERE slow_rank <= 8 OR fast_rank <= 8
ORDER BY avg_speed_mph;
