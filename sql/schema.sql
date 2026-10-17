-- DART GTFS schedule data (a subset of the GTFS spec) + derived analysis tables.
-- GTFS reference: https://gtfs.org/documentation/schedule/reference/

DROP TABLE IF EXISTS agency;
DROP TABLE IF EXISTS routes;
DROP TABLE IF EXISTS trips;
DROP TABLE IF EXISTS stops;
DROP TABLE IF EXISTS stop_times;
DROP TABLE IF EXISTS calendar;
DROP TABLE IF EXISTS calendar_dates;
DROP TABLE IF EXISTS shapes;
DROP TABLE IF EXISTS route_metrics;
DROP TABLE IF EXISTS stop_metrics;
DROP TABLE IF EXISTS hourly_service;
DROP TABLE IF EXISTS feed_meta;

CREATE TABLE agency (agency_id TEXT, agency_name TEXT, agency_url TEXT, agency_timezone TEXT);

CREATE TABLE routes (
    route_id         TEXT PRIMARY KEY,
    route_short_name TEXT,
    route_long_name  TEXT,
    route_type       INTEGER,          -- 3 = bus, 0 = light rail, 2 = rail
    route_color      TEXT
);

CREATE TABLE trips (
    trip_id       TEXT PRIMARY KEY,
    route_id      TEXT REFERENCES routes(route_id),
    service_id    TEXT,
    direction_id  INTEGER,
    trip_headsign TEXT,
    shape_id      TEXT
);

CREATE TABLE stops (
    stop_id   TEXT PRIMARY KEY,
    stop_name TEXT,
    stop_lat  REAL,
    stop_lon  REAL
);

CREATE TABLE stop_times (
    trip_id        TEXT,
    stop_sequence  INTEGER,
    stop_id        TEXT,
    arrival_sec    INTEGER,   -- seconds after midnight of the service day (can exceed 86400)
    departure_sec  INTEGER,   -- NULL at stops that aren't timepoints
    PRIMARY KEY (trip_id, stop_sequence)
) WITHOUT ROWID;

CREATE TABLE calendar (
    service_id TEXT PRIMARY KEY,
    monday INTEGER, tuesday INTEGER, wednesday INTEGER, thursday INTEGER,
    friday INTEGER, saturday INTEGER, sunday INTEGER,
    start_date TEXT, end_date TEXT          -- YYYYMMDD
);

CREATE TABLE calendar_dates (service_id TEXT, date TEXT, exception_type INTEGER);  -- 1 added, 2 removed

CREATE TABLE shapes (
    shape_id TEXT, shape_pt_sequence INTEGER, shape_pt_lat REAL, shape_pt_lon REAL,
    PRIMARY KEY (shape_id, shape_pt_sequence)
) WITHOUT ROWID;

-- ----------------------------------------------------------- derived tables
CREATE TABLE feed_meta (key TEXT PRIMARY KEY, value TEXT);

-- one row per bus route, measured on a typical weekday (plus Sat/Sun trip counts)
CREATE TABLE route_metrics (
    route_id            TEXT PRIMARY KEY,
    route               TEXT,     -- short name, e.g. '21'
    name                TEXT,     -- long name
    trips_weekday       INTEGER,
    trips_saturday      INTEGER,
    trips_sunday        INTEGER,
    first_trip          TEXT,     -- HH:MM
    last_trip_end       TEXT,
    span_hours          REAL,
    peak_headway_min    REAL,     -- 7-9 AM, busiest direction
    midday_headway_min  REAL,     -- 10 AM-2 PM, busiest direction
    tier                TEXT,     -- Frequent / 30-min / Hourly / Limited / Peak only
    stops_served        INTEGER,
    length_mi           REAL,     -- one-way, representative trip
    trip_minutes        REAL,     -- median weekday end-to-end run time
    avg_speed_mph       REAL,
    avg_stop_spacing_ft REAL
);

CREATE TABLE stop_metrics (
    stop_id            TEXT PRIMARY KEY,
    stop_name          TEXT,
    stop_lat           REAL,
    stop_lon           REAL,
    weekday_departures INTEGER,
    routes_served      INTEGER
);

CREATE TABLE hourly_service (hour INTEGER PRIMARY KEY, buses_in_service INTEGER, trips_starting INTEGER);
