-- The 15 busiest bus stops by scheduled weekday departures.
SELECT stop_name, weekday_departures, routes_served,
       ROUND(weekday_departures / 19.0, 1) AS avg_buses_per_hour_5am_to_midnight
FROM stop_metrics
ORDER BY weekday_departures DESC
LIMIT 15;
