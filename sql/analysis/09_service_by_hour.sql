-- Service through the day: buses in progress each hour, with share of the peak.
SELECT printf('%02d:00', hour % 24) || CASE WHEN hour >= 24 THEN ' (+1)' ELSE '' END AS hour,
       buses_in_service,
       trips_starting,
       ROUND(100.0 * buses_in_service / MAX(buses_in_service) OVER (), 0) AS pct_of_peak
FROM hourly_service
ORDER BY hour;
