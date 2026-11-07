# weather-station

A DIY home weather station. An ESP32 outside reads the sensors and sends readings over Wi-Fi to the PC, which logs them and shows a local dashboard.

Status: started 6 Nov 2026. Hardware chosen (ESP32); parts not bought yet.

## Hardware (draft parts list)

Prices are rough estimates. Check them before buying.

| Part | Purpose | Notes | Rough cost |
|---|---|---|---|
| ESP32 dev board (e.g. ESP32-DevKitC) | Reads the sensors, sends data over Wi-Fi | Any ESP32 with a USB port is fine | ~$10 |
| BME280 breakout (I2C) | Temperature, humidity, pressure | Many cheap boards are really a **BMP280**, which has no humidity sensor. Check the listing | ~$10 |
| Weather meter kit (anemometer, wind vane, rain gauge) | Wind speed, direction, rainfall | Optional, can be added later. The SparkFun-style kit uses simple reed switches | ~$80 |
| Radiation shield | Stops sun and rain from skewing the temperature | Buy one or 3D-print one; needed for accurate temperatures | ~$15-30 |
| Weatherproof box, cable glands, wire | Housing | | ~$15 |
| Power | | USB power supply if there's an outdoor outlet; otherwise a small solar panel + 18650 battery + charger, with deep sleep in the firmware | $10-40 |

## Architecture

```
ESP32 (outside) --Wi-Fi, HTTP POST JSON every ~60 s--> PC receiver (Python) --> SQLite --> web dashboard
```

## Setup

### 1. Receiver (on the PC)

Needs Python 3 only, no extra packages.

```powershell
$env:WS_TOKEN = "pick-a-long-random-string"
python server\receiver.py
```

Readings go into `data\weather.db` (git-ignored). Check it from a browser:

- `http://localhost:8080/api/latest` shows the newest reading
- `http://localhost:8080/api/history?hours=24` shows the last 24 hours

To test without the ESP32, run `python server\fake_station.py` in a second window with the same `WS_TOKEN`.

The first time, Windows Firewall asks whether to allow Python. Allow it on **private** networks, or the ESP32 can't reach the PC. Port 8080 isn't secured with HTTPS, so keep it on the home network only.

### 2. Firmware (on the ESP32)

1. Install the Arduino IDE, then add the **esp32** board package by Espressif (Boards Manager).
2. Install **Adafruit BME280 Library** (Library Manager). Say yes to its dependencies.
3. Wire the BME280: VIN to 3V3, GND to GND, SDA to GPIO21, SCL to GPIO22.
4. Copy `firmware/weather_station/secrets.h.example` to `secrets.h` in the same folder. Fill in your Wi-Fi details (2.4 GHz only), the PC's IP, and the same token as `WS_TOKEN`. `secrets.h` is git-ignored.
5. Open `firmware/weather_station/weather_station.ino`, choose board **ESP32 Dev Module**, and upload.
6. Open Serial Monitor at 115200 baud. You should see `POST ... -> 201` every 60 seconds.

The PC's IP address can change. Give it a DHCP reservation in the router so `RECEIVER_URL` stays correct.

Pressure is station pressure, not sea-level pressure, so it reads lower than the weather forecast. The dashboard can correct for altitude later.

## Plan

1. Buy the parts. Start with ESP32 + BME280 only.
2. Firmware: read the BME280 and POST JSON to the PC (`firmware/`).
3. Receiver: a small Python server that stores the readings in SQLite (`server/`).
4. Dashboard: current conditions plus history charts.
5. Add wind and rain once the kit arrives.
6. Optional: alerts (frost, high wind, heavy rain) and a Tool Launcher entry.
