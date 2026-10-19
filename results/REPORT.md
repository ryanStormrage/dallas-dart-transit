# DART bus network: SQL analysis

Weekday analyzed: **Wednesday, October 21, 2026** · Saturday 2026-10-24 · Sunday 2026-10-25  
Source: DART GTFS schedule feed. Each section is one file in `sql/analysis/`.

## Network at a glance: how much bus service does DART run?

[`01_network_overview.sql`](../sql/analysis/01_network_overview.sql)

| bus_routes | weekday_trips | saturday_trips | sunday_trips | sunday_as_pct_of_weekday | total_route_miles_one_way | avg_scheduled_speed_mph |
|---|---|---|---|---|---|---|
| 84 | 6,729 | 5,155 | 4,995 | 74.2 | 890.0 | 15.5 |

## How many routes fall in each frequency tier (midday, weekday)?

[`02_frequency_tiers.sql`](../sql/analysis/02_frequency_tiers.sql)

| tier | routes | pct_of_routes | weekday_trips |
|---|---|---|---|
| Frequent (≤15 min) | 7 | 8.3 | 1,004 |
| Every 16–30 min | 29 | 34.5 | 2,824 |
| Every 31–60 min | 41 | 48.8 | 2,643 |
| Limited (60+ min) | 2 | 2.4 | 84 |
| Peak only | 5 | 6.0 | 174 |

## The 15 most frequent bus routes at midday.

[`03_most_frequent_routes.sql`](../sql/analysis/03_most_frequent_routes.sql)

| route | name | midday_headway_min | peak_headway_min | trips_weekday | service_span |
|---|---|---|---|---|---|
| 883W | UT DALLAS WEST | 12.0 | 10.9 | 164 | 07:00 – 23:29 |
| 005 | LOVE FIELD SHUTTLE | 15.0 | 15.0 | 154 | 04:14 – 01:23 (+1) |
| 001 | MALCOLM X/MAPLE | 15.0 | 15.0 | 148 | 03:50 – 00:52 (+1) |
| 003 | ROSS | 15.0 | 15.0 | 147 | 04:00 – 01:02 (+1) |
| 009 | JEFFERSON GASTON | 15.0 | 15.0 | 146 | 04:00 – 00:55 (+1) |
| 883E | UT DALLAS EAST | 15.0 | 15.0 | 130 | 07:00 – 23:25 |
| 440 | MUSTANG EXPRESS | 15.0 | 15.0 | 115 | 07:07 – 22:13 |
| 015 | BUCKNER | 20.0 | 20.0 | 122 | 04:00 – 01:43 (+1) |
| 017 | SKILLMAN | 20.0 | 20.0 | 121 | 04:00 – 01:55 (+1) |
| 023 | HASKELL | 20.0 | 20.0 | 121 | 04:06 – 01:41 (+1) |
| 025 | COCKRELL HILL NORTH | 20.0 | 20.0 | 121 | 04:00 – 01:38 (+1) |
| 022 | FOREST LANE | 20.0 | 20.0 | 120 | 03:55 – 01:30 (+1) |
| 027 | RIDGECREST | 20.0 | 20.0 | 119 | 04:15 – 01:00 (+1) |
| 030 | LAKE JUNE | 20.0 | 20.0 | 119 | 04:00 – 00:49 (+1) |
| 038 | LEDBETTER | 20.0 | 20.0 | 119 | 03:50 – 01:21 (+1) |

## Which routes run the longest day, and which barely run at all?

[`04_longest_service_day.sql`](../sql/analysis/04_longest_service_day.sql)

| list | route | name | span_hours | first_trip | last_trip_end | trips_weekday |
|---|---|---|---|---|---|---|
| Longest span | 017 | SKILLMAN | 21.9 | 04:00 | 01:55 (+1) | 121 |
| Longest span | 057 | WESTMORELAND | 21.9 | 03:55 | 01:46 (+1) | 117 |
| Longest span | 015 | BUCKNER | 21.7 | 04:00 | 01:43 (+1) | 122 |
| Longest span | 018 | SAMUELL | 21.7 | 04:05 | 01:47 (+1) | 117 |
| Longest span | 020 | NORTHWEST HWY | 21.7 | 04:00 | 01:41 (+1) | 118 |
| Longest span | 022 | FOREST LANE | 21.6 | 03:55 | 01:30 (+1) | 120 |
| Longest span | 023 | HASKELL | 21.6 | 04:06 | 01:41 (+1) | 121 |
| Longest span | 025 | COCKRELL HILL NORTH | 21.6 | 04:00 | 01:38 (+1) | 121 |
| Shortest span | 408 | PALISADES E-SHUTTLE | 12.4 | 06:18 | 18:45 | 42 |
| Shortest span | 422 | UT SOUTHWESTERN SOUTH | 13.3 | 05:42 | 19:00 | 40 |
| Shortest span | 423 | UT SOUTHWESTERN NORTH | 13.4 | 05:52 | 19:16 | 27 |
| Shortest span | 421 | BAYLOR BRYAN TOWER | 13.9 | 05:30 | 19:25 | 42 |
| Shortest span | 306 | GLENN HEIGHTS EXPRESS | 14.2 | 05:15 | 19:30 | 42 |
| Shortest span | 413 | TI SHUTTLE - FOREST LANE CAMPUS | 14.4 | 05:40 | 20:02 | 26 |
| Shortest span | 417 | TI SHUTTLE- MAIN CAMPUS NORTH ROUTE | 14.5 | 05:30 | 19:58 | 28 |
| Shortest span | 419 | TI SHUTTLE- MAIN CAMPUS SOUTH ROUTE | 14.5 | 05:40 | 20:08 | 27 |

## Slowest and fastest routes by scheduled speed (routes at least 3 miles long).

[`05_speed_and_length.sql`](../sql/analysis/05_speed_and_length.sql)

| list | route | name | length_mi | trip_minutes | avg_speed_mph | avg_stop_spacing_ft |
|---|---|---|---|---|---|---|
| Slowest | 442 | BUSH/ MEADOWS-MOCKINGBIRD STA. | 3.2 | 23.0 | 8.2 | 984.0 |
| Slowest | 423 | UT SOUTHWESTERN NORTH | 3.3 | 24.0 | 8.3 | 2,079.0 |
| Slowest | 419 | TI SHUTTLE- MAIN CAMPUS SOUTH ROUTE | 3.0 | 18.0 | 10.1 | 3,282.0 |
| Slowest | 023 | HASKELL | 7.0 | 37.0 | 11.3 | 888.0 |
| Slowest | 103 | CEDAR SPRINGS | 4.5 | 23.0 | 11.7 | 851.0 |
| Slowest | 003 | ROSS | 6.6 | 33.0 | 12.0 | 814.0 |
| Slowest | 001 | MALCOLM X/MAPLE | 8.7 | 43.0 | 12.1 | 934.0 |
| Slowest | 205 | HENDERSON | 6.6 | 32.0 | 12.3 | 825.0 |
| Fastest | 213 | HARRY HINES | 4.6 | 15.0 | 18.3 | 1,038.0 |
| Fastest | 235 | TIMBERGLEN/MIDWAY | 8.2 | 27.0 | 18.3 | 999.0 |
| Fastest | 243 | PLANO RD | 7.2 | 22.0 | 19.8 | 893.0 |
| Fastest | 308 | NORTHWEST PLANO EXPRESS | 23.3 | 64.0 | 21.7 | 4,633.0 |
| Fastest | 244 | UTD RICHARDSON | 6.5 | 17.0 | 22.9 | 1,203.0 |
| Fastest | 224 | I-30 BROADWAY | 21.0 | 53.0 | 23.7 | 1,848.0 |
| Fastest | 306 | GLENN HEIGHTS EXPRESS | 20.6 | 46.0 | 26.6 | 4,178.0 |
| Fastest | 223 | CLARK | 9.9 | 22.0 | 27.1 | 1,528.0 |

## Do routes with stops closer together run slower? Average speed by stop-spacing band.

[`06_stop_spacing_vs_speed.sql`](../sql/analysis/06_stop_spacing_vs_speed.sql)

| stop_spacing | routes | avg_speed_mph | avg_length_mi |
|---|---|---|---|
| 1: under 800 ft | 7 | 14.3 | 6.9 |
| 2: 800-1,200 ft | 63 | 15.2 | 10.9 |
| 3: 1,200-1,800 ft | 6 | 18.2 | 12.3 |
| 4: 1,800 ft + | 8 | 16.5 | 10.0 |

## The 15 busiest bus stops by scheduled weekday departures.

[`07_busiest_stops.sql`](../sql/analysis/07_busiest_stops.sql)

| stop_name | weekday_departures | routes_served | avg_buses_per_hour_5am_to_midnight |
|---|---|---|---|
| SOUTH GARLAND TC | 1,000 | 12 | 52.6 |
| CBD WEST TC | 899 | 10 | 47.3 |
| SOUTHWEST MEDICAL DISTRICT/PARKLAND | 852 | 10 | 44.8 |
| ADDISON TRANSIT CENTER | 775 | 11 | 40.8 |
| ELM @ AKARD - W - NS | 757 | 17 | 39.8 |
| ELM @ GRIFFIN - W - MB | 757 | 17 | 39.8 |
| CBD EAST TC | 714 | 10 | 37.6 |
| ELM @ LAMAR - W - NS | 699 | 15 | 36.8 |
| ELM @ ERVAY - W - NS | 698 | 16 | 36.7 |
| COMMERCE @ FIELD - E - FS | 695 | 15 | 36.6 |
| COMMERCE @ LANE - E - NS | 669 | 14 | 35.2 |
| COMMERCE @ ERVAY - E - MB | 669 | 14 | 35.2 |
| ELM @ HARWOOD - W - NS | 646 | 14 | 34.0 |
| DOWNTOWN GARLAND STATION | 581 | 8 | 30.6 |
| WESTMORELAND STATION | 538 | 6 | 28.3 |

## Weekend service: which routes lose the most trips (or disappear) on Sunday?

[`08_weekend_cuts.sql`](../sql/analysis/08_weekend_cuts.sql)

| route | name | trips_weekday | trips_saturday | trips_sunday | sunday_cut_pct | note |
|---|---|---|---|---|---|---|
| 440 | MUSTANG EXPRESS | 115 | 80 | 0 | 100.0 | No Sunday service |
| 308 | NORTHWEST PLANO EXPRESS | 51 | 0 | 0 | 100.0 | No Sunday service |
| 306 | GLENN HEIGHTS EXPRESS | 42 | 0 | 0 | 100.0 | No Sunday service |
| 408 | PALISADES E-SHUTTLE | 42 | 0 | 0 | 100.0 | No Sunday service |
| 421 | BAYLOR BRYAN TOWER | 42 | 0 | 0 | 100.0 | No Sunday service |
| 422 | UT SOUTHWESTERN SOUTH | 40 | 0 | 0 | 100.0 | No Sunday service |
| 442 | BUSH/ MEADOWS-MOCKINGBIRD STA. | 36 | 0 | 0 | 100.0 | No Sunday service |
| 417 | TI SHUTTLE- MAIN CAMPUS NORTH ROUTE | 28 | 0 | 0 | 100.0 | No Sunday service |
| 419 | TI SHUTTLE- MAIN CAMPUS SOUTH ROUTE | 27 | 0 | 0 | 100.0 | No Sunday service |
| 423 | UT SOUTHWESTERN NORTH | 27 | 0 | 0 | 100.0 | No Sunday service |
| 413 | TI SHUTTLE - FOREST LANE CAMPUS | 26 | 0 | 0 | 100.0 | No Sunday service |
| 883E | UT DALLAS EAST | 130 | 66 | 34 | 74.0 |  |
| 883W | UT DALLAS WEST | 164 | 100 | 52 | 68.0 |  |
| 221 | MERRIFIELD | 59 | 40 | 40 | 32.0 |  |
| 226 | CLARENDON | 56 | 40 | 40 | 29.0 |  |

## Service through the day: buses in progress each hour, with share of the peak.

[`09_service_by_hour.sql`](../sql/analysis/09_service_by_hour.sql)

| hour | buses_in_service | trips_starting | pct_of_peak |
|---|---|---|---|
| 00:00 (+1) | 270 | 168 | 40.0 |
| 01:00 (+1) | 75 | 11 | 11.0 |
| 04:00 | 166 | 157 | 25.0 |
| 05:00 | 428 | 326 | 63.0 |
| 06:00 | 552 | 378 | 82.0 |
| 07:00 | 648 | 412 | 96.0 |
| 08:00 | 665 | 406 | 99.0 |
| 09:00 | 604 | 352 | 89.0 |
| 10:00 | 500 | 303 | 74.0 |
| 11:00 | 496 | 320 | 73.0 |
| 12:00 | 490 | 301 | 73.0 |
| 13:00 | 498 | 322 | 74.0 |
| 14:00 | 504 | 312 | 75.0 |
| 15:00 | 576 | 394 | 85.0 |
| 16:00 | 660 | 413 | 98.0 |
| 17:00 | 675 | 409 | 100.0 |
| 18:00 | 637 | 375 | 94.0 |
| 19:00 | 535 | 314 | 79.0 |
| 20:00 | 481 | 310 | 71.0 |
| 21:00 | 468 | 292 | 69.0 |
| 22:00 | 395 | 233 | 59.0 |
| 23:00 | 323 | 212 | 48.0 |

## Commuter-style routes: service at rush hour but little or none midday.

[`10_peak_only_routes.sql`](../sql/analysis/10_peak_only_routes.sql)

| route | name | peak_headway_min | midday_headway_min | trips_weekday | first_trip | last_trip_end |
|---|---|---|---|---|---|---|
| 308 | NORTHWEST PLANO EXPRESS | 20.0 | – | 51 | 05:06 | 20:24 |
| 306 | GLENN HEIGHTS EXPRESS | 30.0 | 120.0 | 42 | 05:15 | 19:30 |
| 408 | PALISADES E-SHUTTLE | 20.0 | – | 42 | 06:18 | 18:45 |
| 421 | BAYLOR BRYAN TOWER | 30.0 | 240.0 | 42 | 05:30 | 19:25 |
| 417 | TI SHUTTLE- MAIN CAMPUS NORTH ROUTE | 20.0 | – | 28 | 05:30 | 19:58 |
| 419 | TI SHUTTLE- MAIN CAMPUS SOUTH ROUTE | 20.0 | – | 27 | 05:40 | 20:08 |
| 413 | TI SHUTTLE - FOREST LANE CAMPUS | 20.0 | – | 26 | 05:40 | 20:02 |
