-- Do routes with stops closer together run slower? Average speed by stop-spacing band.
SELECT
    CASE WHEN avg_stop_spacing_ft < 800  THEN '1: under 800 ft'
         WHEN avg_stop_spacing_ft < 1200 THEN '2: 800-1,200 ft'
         WHEN avg_stop_spacing_ft < 1800 THEN '3: 1,200-1,800 ft'
         ELSE '4: 1,800 ft +' END       AS stop_spacing,
    COUNT(*)                            AS routes,
    ROUND(AVG(avg_speed_mph), 1)        AS avg_speed_mph,
    ROUND(AVG(length_mi), 1)            AS avg_length_mi
FROM route_metrics
WHERE avg_stop_spacing_ft IS NOT NULL AND avg_speed_mph IS NOT NULL
GROUP BY stop_spacing
ORDER BY stop_spacing;
