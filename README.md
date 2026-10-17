# How often does the bus come? A DART bus network analysis

A data project on **Dallas Area Rapid Transit (DART)** bus service. It downloads DART's official GTFS schedule feed,
loads it into SQLite, and measures every bus route on a typical weekday:

- **frequency**: how often a bus comes at rush hour (7–9 AM) and midday (10 AM–2 PM), sorted into tiers
- **span of service**: first departure to last arrival
- **length, run time, scheduled speed and stop spacing**, worked out from the route shapes and stop coordinates
- **weekend cuts**: Saturday and Sunday trips compared with weekdays
- **busiest stops** and **buses on the road by hour**

### Outputs

| | |
|---|---|
| [`docs/index.html`](docs/index.html) | interactive dashboard with a route map colored by frequency, an hourly chart, busiest stops and a sortable route table |
| [`results/REPORT.md`](results/REPORT.md) | answers to 10 questions, each one a SQL file in [`sql/analysis/`](sql/analysis) |
| `data/dart.db` | the full schedule plus the derived tables `route_metrics`, `stop_metrics` and `hourly_service` |

**Stack:** Python 3.10+ (standard library only), SQLite, SQL window functions and CTEs, HTML/CSS/JS, Leaflet,
GitHub Actions

## Run it

```bash
python build.py                     # downloads the latest DART feed (~20 MB) and builds everything
python build.py --date 2026-11-04   # analyze a specific weekday
python build.py --skip-load         # re-run the analysis on the existing database
```

Then open `docs/index.html`, or browse `data/dart.db` with the VS Code *SQLite Viewer* extension.

A GitHub Action re-runs the build every Monday against DART's latest feed and commits the refreshed dashboard and
report. To publish the dashboard, enable **Settings → Pages → `main` / `docs`**.

## The questions (in `sql/analysis/`)

1. How much bus service does DART run?
2. How many routes are "frequent" (every 15 min or better)?
3. Which routes come most often?
4. Which routes run the longest and shortest day?
5. Slowest and fastest routes by scheduled speed
6. Do routes with stops closer together run slower?
7. The busiest stops
8. Which routes lose the most service on Sundays?
9. How service changes through the day
10. Commuter-style, peak-only routes

## Method notes

- **Service day:** GTFS services are resolved for one real date (`calendar.txt` + `calendar_dates.txt` exceptions).
  By default that's the next Wednesday covered by the feed, plus the following Saturday and Sunday.
- **Headway** = window length ÷ trips *starting* in that window, in the busiest direction. That's a schedule-based
  average and doesn't reflect real-time reliability.
- **Length** uses each route's most common weekday shape, measured with the haversine formula. **Speed** =
  length ÷ median end-to-end scheduled run time.
- Bus routes only (`route_type = 3`). Light rail and streetcar are left out.

## Data

[DART GTFS schedule feed](https://www.dart.org/about/about-dart/fixed-route-schedule) (`google_transit.zip`),
published by Dallas Area Rapid Transit and also listed on the
[Mobility Database](https://mobilitydatabase.org/feeds/gtfs/mdb-152). GTFS format reference: [gtfs.org](https://gtfs.org).
