"""weather-station receiver.

Accepts readings from the ESP32 and stores them in SQLite. Standard library only.

Endpoints
  POST /api/readings           JSON body from the station; needs header X-Station-Token
  GET  /api/latest             newest reading per device
  GET  /api/history?hours=24   readings from the last N hours (optional &device=name)
  GET  /health                 "ok"

Settings (environment variables)
  WS_TOKEN  shared secret, must match STATION_TOKEN in the firmware (required)
  WS_PORT   port to listen on (default 8080)
  WS_HOST   address to bind (default 0.0.0.0, so the ESP32 can reach it)
  WS_DB     SQLite file (default ../data/weather.db next to this folder)

Run:  set WS_TOKEN=... then  python server/receiver.py
"""

import hmac
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("WS_DB", ROOT / "data" / "weather.db"))
TOKEN = os.environ.get("WS_TOKEN", "")
HOST = os.environ.get("WS_HOST", "0.0.0.0")
PORT = int(os.environ.get("WS_PORT", "8080"))
MAX_BODY = 4096

# field -> (min, max). Values outside these ranges are rejected as sensor errors.
FIELDS = {
    "temp_c": (-60.0, 70.0),
    "humidity": (0.0, 100.0),
    "pressure_hpa": (300.0, 1100.0),
}
OPTIONAL_INTS = ("rssi", "uptime_s")

SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    received_at  TEXT    NOT NULL,   -- UTC ISO 8601, set by the receiver
    device       TEXT    NOT NULL,
    temp_c       REAL    NOT NULL,
    humidity     REAL    NOT NULL,
    pressure_hpa REAL    NOT NULL,
    rssi         INTEGER,
    uptime_s     INTEGER
);
CREATE INDEX IF NOT EXISTS idx_readings_device_time ON readings(device, received_at);
"""


def connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA)


def validate(payload):
    """Return a clean row dict, or raise ValueError with a reason."""
    if not isinstance(payload, dict):
        raise ValueError("body must be a JSON object")
    device = payload.get("device")
    if not isinstance(device, str) or not 1 <= len(device) <= 64:
        raise ValueError("device must be a string of 1-64 characters")
    row = {"device": device}
    for name, (lo, hi) in FIELDS.items():
        value = payload.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be a number")
        if not lo <= value <= hi:
            raise ValueError(f"{name}={value} is outside {lo}..{hi}")
        row[name] = float(value)
    for name in OPTIONAL_INTS:
        value = payload.get(name)
        row[name] = int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None
    return row


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0)


class Handler(BaseHTTPRequestHandler):
    server_version = "weather-station/0.1"

    def send_json(self, status, obj):
        data = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if urlparse(self.path).path != "/api/readings":
            return self.send_json(404, {"error": "not found"})
        given = self.headers.get("X-Station-Token", "")
        if not hmac.compare_digest(given.encode(), TOKEN.encode()):
            return self.send_json(401, {"error": "bad token"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self.send_json(400, {"error": "bad Content-Length"})
        if not 0 < length <= MAX_BODY:
            return self.send_json(400, {"error": "body missing or too large"})
        try:
            row = validate(json.loads(self.rfile.read(length)))
        except (ValueError, json.JSONDecodeError) as exc:
            return self.send_json(400, {"error": str(exc)})
        row["received_at"] = utc_now().isoformat()
        with connect() as conn:
            conn.execute(
                "INSERT INTO readings (received_at, device, temp_c, humidity, pressure_hpa, rssi, uptime_s) "
                "VALUES (:received_at, :device, :temp_c, :humidity, :pressure_hpa, :rssi, :uptime_s)",
                row,
            )
        self.send_json(201, {"ok": True, "received_at": row["received_at"]})

    def do_GET(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        if url.path == "/health":
            return self.send_json(200, {"ok": True})
        if url.path == "/api/latest":
            with connect() as conn:
                rows = conn.execute(
                    "SELECT r.* FROM readings r JOIN ("
                    "  SELECT device, MAX(id) AS id FROM readings GROUP BY device"
                    ") last ON r.id = last.id ORDER BY r.device"
                ).fetchall()
            return self.send_json(200, [dict(r) for r in rows])
        if url.path == "/api/history":
            try:
                hours = float(query.get("hours", ["24"])[0])
            except ValueError:
                return self.send_json(400, {"error": "hours must be a number"})
            hours = max(0.0, min(hours, 24 * 366))
            since = (utc_now() - timedelta(hours=hours)).isoformat()
            sql = "SELECT * FROM readings WHERE received_at >= ?"
            args = [since]
            if "device" in query:
                sql += " AND device = ?"
                args.append(query["device"][0])
            with connect() as conn:
                rows = conn.execute(sql + " ORDER BY received_at", args).fetchall()
            return self.send_json(200, [dict(r) for r in rows])
        self.send_json(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        sys.stderr.write(f"{utc_now().isoformat()} {self.address_string()} {fmt % args}\n")


def main():
    if not TOKEN:
        sys.exit("WS_TOKEN is not set. Set it to the same value as STATION_TOKEN in the firmware.")
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"weather-station receiver on http://{HOST}:{PORT}  db={DB_PATH}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
