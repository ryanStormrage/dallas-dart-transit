"""
Dallas DART bus network analysis
--------------------------------
Downloads Dallas Area Rapid Transit's official GTFS schedule feed, loads it
into SQLite, measures every bus route on a typical weekday, and writes:

    data/dart.db          the full schedule + derived metric tables
    docs/index.html       an interactive map + dashboard (GitHub Pages ready)
    results/REPORT.md     answers to the questions in sql/analysis/*.sql

Standard library only.

    python build.py                    # download the latest feed and build everything
    python build.py --zip feed.zip     # use a GTFS zip you already have
    python build.py --date 2026-11-04  # analyze a specific service day
    python build.py --skip-load        # reuse data/dart.db, just rebuild outputs
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import io
import json
import math
import sqlite3
import statistics
import sys
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

FEED_URL = "https://www.dart.org/transitdata/latest/google_transit.zip"
ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "dart.db"
RAW_ZIP = ROOT / "data" / "google_transit.zip"
OUT_HTML = ROOT / "docs" / "index.html"
REPORT = ROOT / "results" / "REPORT.md"
BUS = 3

TIERS = ["Frequent (≤15 min)", "Every 16–30 min", "Every 31–60 min", "Limited (60+ min)", "Peak only"]


# =========================================================================== #
# 1. Load GTFS
# =========================================================================== #
def to_sec(t: str | None) -> int | None:
    if not t or not t.strip():
        return None
    h, m, s = (int(x) for x in t.strip().split(":"))
    return h * 3600 + m * 60 + s


def hhmm(sec: int | None) -> str:
    if sec is None:
        return "–"
    h, m = divmod(sec // 60, 60)
    suffix = " (+1)" if h >= 24 else ""
    return f"{h % 24:02d}:{m:02d}{suffix}"


def num(v):
    try:
        return float(v) if v not in (None, "") else None
    except ValueError:
        return None


def intval(v, default=None):
    try:
        return int(float(v)) if v not in (None, "") else default
    except ValueError:
        return default


def read_table(z: zipfile.ZipFile, name: str):
    match = [n for n in z.namelist() if n.split("/")[-1] == name]
    if not match:
        return
    with z.open(match[0]) as raw:
        reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
        for row in reader:
            yield {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items() if k}


def download() -> Path:
    RAW_ZIP.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {FEED_URL} …")
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": "dallas-dart-transit (student data project)"})
    with urllib.request.urlopen(req, timeout=180) as resp, open(RAW_ZIP, "wb") as f:
        f.write(resp.read())
    print(f"  {RAW_ZIP.stat().st_size / 1e6:.1f} MB")
    return RAW_ZIP


def load(con: sqlite3.Connection, zip_path: Path) -> None:
    con.executescript((ROOT / "sql" / "schema.sql").read_text(encoding="utf-8"))
    with zipfile.ZipFile(zip_path) as z:
        def ins(table, cols, rows):
            q = f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})"
            n = 0
            batch = []
            for r in rows:
                batch.append(r)
                if len(batch) >= 20000:
                    con.executemany(q, batch); n += len(batch); batch.clear()
            con.executemany(q, batch); n += len(batch)
            print(f"  {table:<15}{n:>10,} rows")

        ins("agency", ["agency_id", "agency_name", "agency_url", "agency_timezone"],
            ((r.get("agency_id"), r.get("agency_name"), r.get("agency_url"), r.get("agency_timezone"))
             for r in read_table(z, "agency.txt")))
        ins("routes", ["route_id", "route_short_name", "route_long_name", "route_type", "route_color"],
            ((r["route_id"], r.get("route_short_name"), r.get("route_long_name"), intval(r.get("route_type")),
              r.get("route_color")) for r in read_table(z, "routes.txt")))
        ins("trips", ["trip_id", "route_id", "service_id", "direction_id", "trip_headsign", "shape_id"],
            ((r["trip_id"], r["route_id"], r["service_id"], intval(r.get("direction_id"), 0),
              r.get("trip_headsign"), r.get("shape_id") or None) for r in read_table(z, "trips.txt")))
        ins("stops", ["stop_id", "stop_name", "stop_lat", "stop_lon"],
            ((r["stop_id"], r.get("stop_name"), num(r.get("stop_lat")), num(r.get("stop_lon")))
             for r in read_table(z, "stops.txt")))
        ins("stop_times", ["trip_id", "stop_sequence", "stop_id", "arrival_sec", "departure_sec"],
            ((r["trip_id"], intval(r["stop_sequence"]), r["stop_id"], to_sec(r.get("arrival_time")),
              to_sec(r.get("departure_time"))) for r in read_table(z, "stop_times.txt")))
        ins("calendar", ["service_id", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
                         "sunday", "start_date", "end_date"],
            ((r["service_id"], *(intval(r[d], 0) for d in
              ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")),
              r["start_date"], r["end_date"]) for r in read_table(z, "calendar.txt")))
        ins("calendar_dates", ["service_id", "date", "exception_type"],
            ((r["service_id"], r["date"], intval(r["exception_type"])) for r in read_table(z, "calendar_dates.txt")))
        ins("shapes", ["shape_id", "shape_pt_sequence", "shape_pt_lat", "shape_pt_lon"],
            ((r["shape_id"], intval(r["shape_pt_sequence"]), num(r["shape_pt_lat"]), num(r["shape_pt_lon"]))
             for r in read_table(z, "shapes.txt")))
    con.execute("CREATE INDEX IF NOT EXISTS ix_st_stop ON stop_times(stop_id)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_trips_route ON trips(route_id)")
    con.commit()


# =========================================================================== #
# 2. Which services run on a given day?
# =========================================================================== #
WEEKDAY_COLS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def feed_range(con) -> tuple[dt.date, dt.date]:
    lo, hi = con.execute("SELECT MIN(start_date), MAX(end_date) FROM calendar").fetchone()
    if not lo:
        lo, hi = con.execute("SELECT MIN(date), MAX(date) FROM calendar_dates").fetchone()
    p = lambda s: dt.datetime.strptime(s, "%Y%m%d").date()
    return p(lo), p(hi)


def active_services(con, day: dt.date) -> set[str]:
    ymd = day.strftime("%Y%m%d")
    col = WEEKDAY_COLS[day.weekday()]
    active = {r[0] for r in con.execute(
        f"SELECT service_id FROM calendar WHERE {col}=1 AND start_date<=? AND end_date>=?", (ymd, ymd))}
    for sid, ex in con.execute("SELECT service_id, exception_type FROM calendar_dates WHERE date=?", (ymd,)):
        if ex == 1:
            active.add(sid)
        elif ex == 2:
            active.discard(sid)
    return active


def pick_day(con, weekday: int, requested: dt.date | None = None) -> dt.date:
    """First date on/after today (or feed start) that falls on `weekday` and has service."""
    start, end = feed_range(con)
    d = max(requested or dt.date.today(), start)
    for _ in range(60):
        if d.weekday() == weekday and active_services(con, d):
            return d
        d += dt.timedelta(days=1)
        if d > end:
            d = start
    return start


# =========================================================================== #
# 3. Metrics
# =========================================================================== #
def haversine_mi(a, b) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))


def path_len(pts) -> float:
    return sum(haversine_mi(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def compute(con, wk: dt.date, sat: dt.date, sun: dt.date) -> dict:
    bus_routes = {r[0]: (r[1], r[2]) for r in con.execute(
        "SELECT route_id, route_short_name, route_long_name FROM routes WHERE route_type=?", (BUS,))}
    if not bus_routes:  # some feeds use extended route types (700 = bus service)
        bus_routes = {r[0]: (r[1], r[2]) for r in con.execute(
            "SELECT route_id, route_short_name, route_long_name FROM routes WHERE route_type BETWEEN 700 AND 799")}

    trips = {r[0]: {"route": r[1], "service": r[2], "dir": r[3], "shape": r[4]} for r in con.execute(
        "SELECT trip_id, route_id, service_id, direction_id, shape_id FROM trips")}
    trips = {k: v for k, v in trips.items() if v["route"] in bus_routes}

    svc = {"wk": active_services(con, wk), "sat": active_services(con, sat), "sun": active_services(con, sun)}

    # trip start / end / stop list for weekday trips
    wk_trips = {t for t, v in trips.items() if v["service"] in svc["wk"]}
    timing: dict[str, list] = {}
    stops_of: dict[str, list] = defaultdict(list)
    stop_deps = Counter()
    stop_routes = defaultdict(set)
    print("  scanning weekday stop_times …")
    for trip_id, seq, stop_id, arr, dep in con.execute(
            "SELECT trip_id, stop_sequence, stop_id, arrival_sec, departure_sec FROM stop_times ORDER BY trip_id, stop_sequence"):
        if trip_id not in wk_trips:
            continue
        t = arr if arr is not None else dep
        d = dep if dep is not None else arr
        rec = timing.setdefault(trip_id, [None, None])
        if d is not None and rec[0] is None:
            rec[0] = d
        if t is not None:
            rec[1] = t
        stops_of[trip_id].append(stop_id)
        stop_deps[stop_id] += 1
        stop_routes[stop_id].add(trips[trip_id]["route"])

    stop_xy = {r[0]: (r[1], r[2]) for r in con.execute("SELECT stop_id, stop_lat, stop_lon FROM stops")}

    # representative shape per route (most common weekday shape)
    shape_counts = defaultdict(Counter)
    for t in wk_trips:
        if trips[t]["shape"]:
            shape_counts[trips[t]["route"]][trips[t]["shape"]] += 1
    needed_shapes = {c.most_common(1)[0][0] for c in shape_counts.values()}
    shape_pts = defaultdict(list)
    for sid, lat, lon in con.execute(
            "SELECT shape_id, shape_pt_lat, shape_pt_lon FROM shapes ORDER BY shape_id, shape_pt_sequence"):
        if sid in needed_shapes:
            shape_pts[sid].append((lat, lon))

    def in_window(start, lo_h, hi_h):
        return start is not None and lo_h * 3600 <= start < hi_h * 3600

    rows, geo = [], []
    for rid, (short, long_) in bus_routes.items():
        r_trips = [t for t in trips if trips[t]["route"] == rid]
        wk_list = [t for t in r_trips if t in wk_trips and t in timing and timing[t][0] is not None]
        n_sat = sum(trips[t]["service"] in svc["sat"] for t in r_trips)
        n_sun = sum(trips[t]["service"] in svc["sun"] for t in r_trips)
        if not wk_list and not n_sat and not n_sun:
            continue

        starts = [timing[t][0] for t in wk_list]
        ends = [timing[t][1] for t in wk_list if timing[t][1] is not None]

        def headway(lo_h, hi_h):
            per_dir = Counter(trips[t]["dir"] for t in wk_list if in_window(timing[t][0], lo_h, hi_h))
            n = max(per_dir.values(), default=0)
            return round((hi_h - lo_h) * 60 / n, 1) if n else None

        peak, midday = headway(7, 9), headway(10, 14)
        if midday is None:
            tier = TIERS[4] if peak else TIERS[3]
        elif midday <= 15:
            tier = TIERS[0]
        elif midday <= 30:
            tier = TIERS[1]
        elif midday <= 60:
            tier = TIERS[2]
        else:
            tier = TIERS[3]

        # geometry: shape if available, else the longest trip's stop sequence
        shape = shape_counts[rid].most_common(1)[0][0] if shape_counts[rid] else None
        pts = shape_pts.get(shape) if shape else None
        longest = max(wk_list, key=lambda t: len(stops_of[t]), default=None)
        stop_pts = [stop_xy[s] for s in stops_of.get(longest, []) if stop_xy.get(s) and None not in stop_xy[s]]
        if not pts:
            pts = stop_pts
        length = path_len(pts) if pts and len(pts) > 1 else None

        rep_trips = [t for t in wk_list if (trips[t]["shape"] == shape if shape else True)
                     and timing[t][1] is not None]
        durations = [(timing[t][1] - timing[t][0]) / 60 for t in rep_trips if timing[t][1] > timing[t][0]]
        minutes = statistics.median(durations) if durations else None
        speed = round(length / (minutes / 60), 1) if length and minutes else None
        spacing = round(path_len(stop_pts) / (len(stop_pts) - 1) * 5280) if len(stop_pts) > 1 else None

        all_stops = {s for t in wk_list for s in stops_of[t]}
        row = {
            "route_id": rid, "route": short or rid, "name": long_ or "",
            "trips_weekday": len(wk_list), "trips_saturday": n_sat, "trips_sunday": n_sun,
            "first_trip": hhmm(min(starts)) if starts else "–", "last_trip_end": hhmm(max(ends)) if ends else "–",
            "span_hours": round((max(ends) - min(starts)) / 3600, 1) if starts and ends else None,
            "peak_headway_min": peak, "midday_headway_min": midday, "tier": tier,
            "stops_served": len(all_stops), "length_mi": round(length, 1) if length else None,
            "trip_minutes": round(minutes) if minutes else None, "avg_speed_mph": speed,
            "avg_stop_spacing_ft": spacing,
        }
        rows.append(row)
        if pts:
            step = max(1, len(pts) // 250)          # keep the page light
            simplified = pts[::step] + ([pts[-1]] if pts[-1] != pts[::step][-1] else [])
            geo.append({"route": row["route"], "name": row["name"], "tier": tier, "trips": row["trips_weekday"],
                        "midday": midday, "peak": peak,
                        "path": [[round(a, 5), round(b, 5)] for a, b in simplified]})

    # hourly profile
    hourly = []
    for h in range(4, 26):
        lo, hi = h * 3600, (h + 1) * 3600
        in_service = sum(1 for t in wk_list_all(timing) if timing[t][0] < hi and (timing[t][1] or timing[t][0]) >= lo)
        starting = sum(1 for t in timing if timing[t][0] is not None and lo <= timing[t][0] < hi)
        hourly.append((h, in_service, starting))

    stop_rows = []
    names = {r[0]: r[1] for r in con.execute("SELECT stop_id, stop_name FROM stops")}
    for sid, n in stop_deps.items():
        lat, lon = stop_xy.get(sid, (None, None))
        stop_rows.append((sid, names.get(sid), lat, lon, n, len(stop_routes[sid])))

    return {"routes": rows, "geo": geo, "hourly": hourly, "stops": stop_rows}


def wk_list_all(timing):
    return [t for t in timing if timing[t][0] is not None]


def save_metrics(con, m: dict, days: dict) -> None:
    cols = ["route_id", "route", "name", "trips_weekday", "trips_saturday", "trips_sunday", "first_trip",
            "last_trip_end", "span_hours", "peak_headway_min", "midday_headway_min", "tier", "stops_served",
            "length_mi", "trip_minutes", "avg_speed_mph", "avg_stop_spacing_ft"]
    con.execute("DELETE FROM route_metrics")
    con.executemany(f"INSERT INTO route_metrics VALUES ({','.join('?' * len(cols))})",
                    [tuple(r[c] for c in cols) for r in m["routes"]])
    con.execute("DELETE FROM stop_metrics")
    con.executemany("INSERT INTO stop_metrics VALUES (?,?,?,?,?,?)", m["stops"])
    con.execute("DELETE FROM hourly_service")
    con.executemany("INSERT INTO hourly_service VALUES (?,?,?)", m["hourly"])
    con.executemany("INSERT OR REPLACE INTO feed_meta VALUES (?,?)",
                    [(k, v.isoformat()) for k, v in days.items()] +
                    [("built_utc", dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M"))])
    con.commit()


# =========================================================================== #
# 4. SQL report
# =========================================================================== #
def nice(d: dt.date) -> str:
    return f"{d:%A}, {d:%B} {d.day}, {d.year}"   # portable (no %-d, which Windows lacks)


def fmt(v):
    if v is None:
        return "–"
    if isinstance(v, float):
        return f"{v:,.1f}"
    if isinstance(v, int):
        return f"{v:,}"
    return str(v).replace("|", "/")


def write_report(con, days) -> None:
    md = ["# DART bus network: SQL analysis", "",
          f"Weekday analyzed: **{nice(days['weekday'])}** · Saturday {days['saturday']} · Sunday {days['sunday']}  ",
          "Source: DART GTFS schedule feed. Each section is one file in `sql/analysis/`.", ""]
    for f in sorted((ROOT / "sql" / "analysis").glob("*.sql")):
        sql = f.read_text(encoding="utf-8")
        title = next((l.lstrip("- ").strip() for l in sql.splitlines() if l.startswith("--")), f.stem)
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        print(f"  {f.name}: {len(rows)} rows")
        md += [f"## {title}", "", f"[`{f.name}`](../sql/analysis/{f.name})", "",
               "| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|",
               *["| " + " | ".join(fmt(v) for v in r) + " |" for r in rows], ""]
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text("\n".join(md), encoding="utf-8")


# =========================================================================== #
# 5. Dashboard
# =========================================================================== #
def write_dashboard(con, m: dict, days: dict) -> None:
    e = html.escape
    routes = sorted(m["routes"], key=lambda r: (TIERS.index(r["tier"]), -(r["trips_weekday"] or 0)))
    total_trips = sum(r["trips_weekday"] for r in routes)
    tier_counts = Counter(r["tier"] for r in routes)
    frequent = tier_counts[TIERS[0]]
    top_stops = con.execute(
        "SELECT stop_name, weekday_departures, routes_served FROM stop_metrics ORDER BY weekday_departures DESC LIMIT 12"
    ).fetchall()
    agency = (con.execute("SELECT agency_name FROM agency LIMIT 1").fetchone() or ["DART"])[0]

    table = "".join(
        f'<tr><td><b>{e(r["route"])}</b></td><td class="nm">{e(r["name"])}</td>'
        f'<td><span class="tier t{TIERS.index(r["tier"])}"></span>{e(r["tier"])}</td>'
        f'<td data-v="{r["midday_headway_min"] or 999}">{fmt(r["midday_headway_min"])}</td>'
        f'<td data-v="{r["peak_headway_min"] or 999}">{fmt(r["peak_headway_min"])}</td>'
        f'<td data-v="{r["trips_weekday"]}">{r["trips_weekday"]}</td>'
        f'<td data-v="{r["span_hours"] or 0}">{e(r["first_trip"])}–{e(r["last_trip_end"])}</td>'
        f'<td data-v="{r["length_mi"] or 0}">{fmt(r["length_mi"])}</td>'
        f'<td data-v="{r["avg_speed_mph"] or 0}">{fmt(r["avg_speed_mph"])}</td>'
        f'<td data-v="{r["trips_sunday"]}">{r["trips_sunday"]}</td></tr>'
        for r in routes)

    stops_html = "".join(
        f'<li><span>{e(s[0] or "")}</span><b>{s[1]:,}</b><small>{s[2]} route{'s' if s[2] != 1 else ''}</small></li>' for s in top_stops)
    legend = "".join(f'<span><i class="tier t{i}"></i>{e(t)} · {tier_counts[t]}</span>' for i, t in enumerate(TIERS))

    page = TEMPLATE
    for k, v in {
        "%%AGENCY%%": e(agency), "%%DAY%%": nice(days['weekday']),
        "%%ROUTES%%": str(len(routes)), "%%TRIPS%%": f"{total_trips:,}",
        "%%FREQ%%": str(frequent), "%%FREQPCT%%": f"{100 * frequent / max(len(routes), 1):.0f}",
        "%%STOPS%%": f"{len(m['stops']):,}", "%%TABLE%%": table, "%%TOPSTOPS%%": stops_html, "%%LEGEND%%": legend,
        "%%GEO%%": json.dumps(m["geo"], separators=(",", ":")),
        "%%HOURLY%%": json.dumps([{"h": h, "n": n} for h, n, _ in m["hourly"]]),
        "%%TIERS%%": json.dumps(TIERS, ensure_ascii=False),
    }.items():
        page = page.replace(k, v)
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(page, encoding="utf-8")


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DART Bus Network</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
:root{--bg:#fcfcfb;--panel:#fff;--ink:#1d1d1b;--ink2:#55534e;--muted:#8a877f;--line:#e6e4df;--accent:#d97706;
--t0:#0d366b;--t1:#1c5cab;--t2:#3987e5;--t3:#86b6ef;--t4:#86b6ef}
@media (prefers-color-scheme:dark){:root{--bg:#1a1a19;--panel:#222220;--ink:#f1efe9;--ink2:#c9c6be;--muted:#8f8c84;--line:#34332f;
--t0:#cde2fb;--t1:#86b6ef;--t2:#3987e5;--t3:#1c5cab;--t4:#1c5cab}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 "Segoe UI",system-ui,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:32px 16px 60px}
.kicker{font:600 .75rem ui-monospace,Consolas,monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--accent)}
h1{margin:4px 0 4px;font-size:clamp(1.8rem,4.5vw,2.8rem);letter-spacing:-.03em;line-height:1.05}
.sub{color:var(--muted);margin:0 0 24px}
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}
.tile{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.tile b{display:block;font-size:1.9rem;letter-spacing:-.02em;font-variant-numeric:tabular-nums}.tile span{color:var(--ink2);font-size:.85rem}
.grid{display:grid;grid-template-columns:1.6fr 1fr;gap:16px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px;min-width:0}
h2{margin:0 0 4px;font-size:1rem}.note{color:var(--muted);font-size:.82rem;margin:0 0 10px}
#map{height:520px;border-radius:8px}
.legend{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:.82rem;color:var(--ink2);margin-top:10px}
.tier{display:inline-block;width:18px;height:4px;border-radius:2px;vertical-align:middle;margin-right:6px}
.t0{background:var(--t0)}.t1{background:var(--t1)}.t2{background:var(--t2)}.t3{background:var(--t3)}
.t4{background:repeating-linear-gradient(90deg,var(--t4) 0 4px,transparent 4px 7px)}
#hourly{position:relative}#hourly svg{display:block;width:100%;height:auto}
.tip{position:absolute;pointer-events:none;background:var(--ink);color:var(--bg);font-size:.78rem;padding:4px 8px;border-radius:6px;opacity:0;transition:opacity .1s;white-space:nowrap}
ol{margin:0;padding-left:20px}ol li{display:grid;grid-template-columns:1fr auto;column-gap:10px;padding:5px 0;border-bottom:1px solid var(--line)}
ol li:last-child{border-bottom:0}ol li span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
ol li b{font-variant-numeric:tabular-nums}ol li small{grid-column:1/-1;color:var(--muted);font-size:.75rem}
.stack{display:grid;gap:16px;align-content:start}
.tablewrap{overflow-x:auto;margin-top:16px}
table{width:100%;border-collapse:collapse;min-width:880px;font-size:.88rem}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}
th{font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);cursor:pointer;user-select:none}
td.nm{white-space:normal;color:var(--ink2);min-width:200px}
.controls{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:20px}
.controls input{font:inherit;padding:6px 10px;border:1px solid var(--line);border-radius:8px;background:var(--panel);color:var(--ink);min-width:220px}
footer{margin-top:24px;color:var(--muted);font-size:.82rem}a{color:var(--accent)}
@media(max-width:860px){.tiles{grid-template-columns:repeat(2,1fr)}.grid{grid-template-columns:1fr}#map{height:380px}}
</style></head><body><div class="wrap">
<div class="kicker">Dallas transit data project</div>
<h1>How often does the bus come?</h1>
<p class="sub">Every %%AGENCY%% bus route, measured from the published schedule for %%DAY%%.</p>

<div class="tiles">
  <div class="tile"><b>%%ROUTES%%</b><span>bus routes running</span></div>
  <div class="tile"><b>%%TRIPS%%</b><span>weekday bus trips</span></div>
  <div class="tile"><b>%%FREQ%%</b><span>routes every 15 min or better midday (%%FREQPCT%%%)</span></div>
  <div class="tile"><b>%%STOPS%%</b><span>stops served</span></div>
</div>

<div class="grid">
  <section class="panel"><h2>Route map by midday frequency</h2>
    <p class="note">Bolder, thicker lines = more frequent between 10 AM and 2 PM. Click a route for details.</p>
    <div id="map" role="img" aria-label="Map of DART bus routes colored by frequency"></div>
    <div class="legend">%%LEGEND%%</div>
  </section>
  <div class="stack">
    <section class="panel"><h2>Buses on the road, by hour</h2>
      <p class="note">Weekday trips in progress during each hour.</p>
      <div id="hourly"></div>
    </section>
    <section class="panel"><h2>Busiest stops</h2>
      <p class="note">Scheduled weekday bus departures.</p>
      <ol>%%TOPSTOPS%%</ol>
    </section>
  </div>
</div>

<div class="controls"><h2 style="margin:0 12px 0 0">Every route</h2>
  <input id="q" type="search" placeholder="Filter by route number or name…" aria-label="Filter routes"></div>
<div class="tablewrap panel"><table id="t"><thead><tr>
<th>Route</th><th>Name</th><th>Tier</th><th data-s>Midday every (min)</th><th data-s>Peak every (min)</th>
<th data-s>Weekday trips</th><th data-s>Service span</th><th data-s>Length (mi)</th><th data-s>Avg speed (mph)</th><th data-s>Sunday trips</th>
</tr></thead><tbody>%%TABLE%%</tbody></table></div>

<footer>Data: <a href="https://www.dart.org/about/about-dart/fixed-route-schedule">DART GTFS schedule feed</a>.
"Every N min" = window length ÷ trips starting in the busiest direction. Speeds are scheduled end-to-end averages.
Map tiles © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, © CARTO.
Built by <a href="https://github.com/ryanstormrage">ryanstormrage</a> · <a href="https://github.com/ryanstormrage/dallas-dart-transit">code</a>.</footer>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const GEO = %%GEO%%, HOURLY = %%HOURLY%%, TIERS = %%TIERS%%;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const dark = matchMedia('(prefers-color-scheme: dark)').matches;

// ---- map (skipped gracefully if the map library can't load)
if (window.L) {
const map = L.map('map', {scrollWheelZoom: false});
L.tileLayer(`https://{s}.basemaps.cartocdn.com/${dark ? 'dark_all' : 'light_all'}/{z}/{x}/{y}{r}.png`,
  {attribution: '© OpenStreetMap contributors © CARTO', maxZoom: 18}).addTo(map);
const bounds = [];
// draw least frequent first so frequent routes sit on top
[...GEO].sort((a, b) => TIERS.indexOf(b.tier) - TIERS.indexOf(a.tier)).forEach(r => {
  const i = TIERS.indexOf(r.tier);
  const line = L.polyline(r.path, {color: css('--t' + i), weight: i === 0 ? 4 : i === 1 ? 3 : 2,
    opacity: .9, dashArray: i === 4 ? '4 4' : null}).addTo(map);
  line.bindPopup(`<b>Route ${r.route}</b><br>${r.name}<br>${r.tier}<br>` +
    `Midday: ${r.midday ? 'every ' + r.midday + ' min' : 'no service'}<br>Weekday trips: ${r.trips}`);
  line.on('mouseover', () => line.setStyle({weight: 6})).on('mouseout', () => line.setStyle({weight: i === 0 ? 4 : i === 1 ? 3 : 2}));
  r.path.forEach(p => bounds.push(p));
});
if (bounds.length) map.fitBounds(bounds, {padding: [10, 10]});
} else { document.getElementById('map').innerHTML = '<p class="note" style="padding:20px">Map library could not load.</p>'; }

// ---- hourly bar chart (single series, one hue, hover tooltip)
(() => {
  const box = document.getElementById('hourly'), W = 420, H = 190, P = {l: 34, r: 6, t: 8, b: 24};
  const max = Math.max(...HOURLY.map(d => d.n), 1), bw = (W - P.l - P.r) / HOURLY.length;
  const y = v => H - P.b - v / max * (H - P.t - P.b);
  const tick = Math.pow(10, Math.floor(Math.log10(max))) * (max / Math.pow(10, Math.floor(Math.log10(max))) > 5 ? 2 : 1);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Buses in service by hour">`;
  for (let v = 0; v <= max; v += tick) s += `<line x1="${P.l}" x2="${W - P.r}" y1="${y(v)}" y2="${y(v)}" stroke="${css('--line')}"/>` +
    `<text x="${P.l - 6}" y="${y(v) + 4}" text-anchor="end" font-size="10" fill="${css('--muted')}">${v}</text>`;
  HOURLY.forEach((d, i) => {
    const x = P.l + i * bw + 1, h = H - P.b - y(d.n), lbl = `${(d.h % 24) % 12 || 12}${d.h % 24 < 12 ? 'a' : 'p'}`;
    s += `<rect class="b" data-i="${i}" x="${x}" y="${y(d.n)}" width="${bw - 2}" height="${Math.max(h, 0)}" rx="2" fill="${css('--t1')}"/>`;
    if (i % 3 === 0) s += `<text x="${x + bw / 2}" y="${H - 8}" text-anchor="middle" font-size="10" fill="${css('--muted')}">${lbl}</text>`;
    s += `<rect class="hit" data-i="${i}" x="${P.l + i * bw}" y="${P.t}" width="${bw}" height="${H - P.t - P.b}" fill="transparent"/>`;
  });
  box.innerHTML = s + '</svg><div class="tip"></div>';
  const tip = box.querySelector('.tip');
  box.querySelectorAll('.hit').forEach(el => {
    el.addEventListener('mousemove', ev => {
      const d = HOURLY[+el.dataset.i], hh = d.h % 24;
      tip.textContent = `${String(hh).padStart(2, '0')}:00–${String((hh + 1) % 24).padStart(2, '0')}:00 · ${d.n} trips in progress`;
      const r = box.getBoundingClientRect(); tip.style.left = Math.min(ev.clientX - r.left + 10, r.width - 190) + 'px';
      tip.style.top = (ev.clientY - r.top - 30) + 'px'; tip.style.opacity = 1;
      box.querySelectorAll('.b').forEach(b => b.style.opacity = b.dataset.i === el.dataset.i ? 1 : .55);
    });
    el.addEventListener('mouseleave', () => { tip.style.opacity = 0; box.querySelectorAll('.b').forEach(b => b.style.opacity = 1); });
  });
})();

// ---- table: filter + sort
const tb = document.querySelector('#t tbody');
document.getElementById('q').addEventListener('input', e => {
  const q = e.target.value.toLowerCase();
  [...tb.rows].forEach(r => r.style.display = r.textContent.toLowerCase().includes(q) ? '' : 'none');
});
document.querySelectorAll('#t th[data-s]').forEach(th => { let asc = true; th.onclick = () => {
  const i = th.cellIndex; [...tb.rows].sort((a, b) => (a.cells[i].dataset.v - b.cells[i].dataset.v) * (asc ? 1 : -1))
    .forEach(r => tb.appendChild(r)); asc = !asc; }; });
</script></body></html>"""


# =========================================================================== #
def main():
    ap = argparse.ArgumentParser(description="Analyze DART's bus network from its GTFS feed.")
    ap.add_argument("--zip", type=Path, help="use this GTFS zip instead of downloading")
    ap.add_argument("--date", type=dt.date.fromisoformat, help="weekday to analyze (YYYY-MM-DD)")
    ap.add_argument("--skip-load", action="store_true", help="reuse the existing database")
    args = ap.parse_args()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    if not args.skip_load:
        zip_path = args.zip or download()
        print("Loading GTFS into SQLite …")
        load(con, zip_path)

    base = args.date
    wk = base if base and base.weekday() < 5 and active_services(con, base) else pick_day(con, 2, base)
    days = {"weekday": wk, "saturday": pick_day(con, 5, wk), "sunday": pick_day(con, 6, wk)}
    print(f"Analyzing weekday {wk}, Saturday {days['saturday']}, Sunday {days['sunday']} …")

    m = compute(con, days["weekday"], days["saturday"], days["sunday"])
    if not m["routes"]:
        sys.exit("No bus routes found in this feed for that date.")
    save_metrics(con, m, days)
    write_report(con, days)
    write_dashboard(con, m, days)
    print(f"\n{len(m['routes'])} bus routes analyzed.")
    print(f"  dashboard → {OUT_HTML.relative_to(ROOT)}\n  report    → {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
