"""Send fake readings to the receiver, to test it without the ESP32.

Usage: python server/fake_station.py [count] [url]
Uses WS_TOKEN from the environment. Defaults: 5 readings to http://127.0.0.1:8080/api/readings
"""

import json
import math
import os
import random
import sys
import time
import urllib.error
import urllib.request

count = int(sys.argv[1]) if len(sys.argv) > 1 else 5
url = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8080/api/readings"
token = os.environ.get("WS_TOKEN", "")

for i in range(count):
    body = {
        "device": "fake",
        "temp_c": round(10 + 5 * math.sin(i / 3) + random.uniform(-0.3, 0.3), 2),
        "humidity": round(random.uniform(60, 90), 2),
        "pressure_hpa": round(random.uniform(1005, 1020), 2),
        "rssi": random.randint(-80, -50),
        "uptime_s": i * 60,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "X-Station-Token": token},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(resp.status, resp.read().decode())
    except urllib.error.HTTPError as exc:
        print(exc.code, exc.read().decode())
    time.sleep(0.2)
