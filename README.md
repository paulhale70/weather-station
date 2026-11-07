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

## Plan

1. Buy the parts. Start with ESP32 + BME280 only.
2. Firmware: read the BME280 and POST JSON to the PC (`firmware/`).
3. Receiver: a small Python server that stores the readings in SQLite (`server/`).
4. Dashboard: current conditions plus history charts.
5. Add wind and rain once the kit arrives.
6. Optional: alerts (frost, high wind, heavy rain) and a Tool Launcher entry.
