// weather-station firmware for ESP32 + BME280.
//
// Every SEND_INTERVAL_MS it reads the BME280 and POSTs JSON to the PC receiver:
//   {"device":"...","temp_c":..,"humidity":..,"pressure_hpa":..,"rssi":..,"uptime_s":..}
//
// Wiring (I2C): BME280 VIN -> 3V3, GND -> GND, SDA -> GPIO21, SCL -> GPIO22.
// Libraries (Arduino Library Manager): "Adafruit BME280 Library" (pulls in Adafruit Unified Sensor).
// Board: "ESP32 Dev Module" from the esp32 board package by Espressif.
//
// Copy secrets.h.example to secrets.h and fill it in. secrets.h is git-ignored.

#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_BME280.h>
#include "secrets.h"

static const unsigned long SEND_INTERVAL_MS = 60UL * 1000UL;
static const unsigned long WIFI_TIMEOUT_MS  = 20UL * 1000UL;
static const int I2C_SDA = 21;
static const int I2C_SCL = 22;

Adafruit_BME280 bme;
bool sensorOk = false;
unsigned long lastSend = 0;

bool startSensor() {
  // Breakouts use address 0x76 or 0x77 depending on the board.
  if (bme.begin(0x76, &Wire) || bme.begin(0x77, &Wire)) {
    // Weather-station mode from the BME280 datasheet: forced mode, 1x oversampling, no filter.
    bme.setSampling(Adafruit_BME280::MODE_FORCED,
                    Adafruit_BME280::SAMPLING_X1,   // temperature
                    Adafruit_BME280::SAMPLING_X1,   // pressure
                    Adafruit_BME280::SAMPLING_X1,   // humidity
                    Adafruit_BME280::FILTER_OFF);
    Serial.println("BME280 found");
    return true;
  }
  // begin() also fails on a BMP280 (no humidity), a common mislabelled part.
  Serial.println("BME280 not found. Check wiring, or the board may be a BMP280 (no humidity).");
  return false;
}

bool ensureWifi() {
  if (WiFi.status() == WL_CONNECTED) return true;
  Serial.printf("Connecting to Wi-Fi \"%s\"", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < WIFI_TIMEOUT_MS) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wi-Fi connect failed, will retry next cycle");
    return false;
  }
  Serial.print("Wi-Fi connected, IP ");
  Serial.println(WiFi.localIP());
  return true;
}

void sendReading() {
  if (!sensorOk) {
    sensorOk = startSensor();
    if (!sensorOk) return;
  }
  if (!bme.takeForcedMeasurement()) {
    Serial.println("Measurement failed, resetting sensor");
    sensorOk = false;
    return;
  }
  float t = bme.readTemperature();        // deg C
  float h = bme.readHumidity();           // %
  float p = bme.readPressure() / 100.0F;  // Pa -> hPa (station pressure, not sea-level)
  if (isnan(t) || isnan(h) || isnan(p)) {
    Serial.println("Got NaN from sensor, skipping");
    sensorOk = false;
    return;
  }

  if (!ensureWifi()) return;

  char body[256];
  snprintf(body, sizeof(body),
           "{\"device\":\"%s\",\"temp_c\":%.2f,\"humidity\":%.2f,\"pressure_hpa\":%.2f,"
           "\"rssi\":%d,\"uptime_s\":%lu}",
           DEVICE_ID, t, h, p, WiFi.RSSI(), millis() / 1000UL);

  HTTPClient http;
  http.setTimeout(10000);
  http.begin(RECEIVER_URL);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Station-Token", STATION_TOKEN);
  int code = http.POST(body);
  Serial.printf("POST %s -> %d\n", body, code);
  http.end();
}

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("\nweather-station starting");
  Wire.begin(I2C_SDA, I2C_SCL);
  sensorOk = startSensor();
  ensureWifi();
  sendReading();
  lastSend = millis();
}

void loop() {
  if (millis() - lastSend >= SEND_INTERVAL_MS) {
    lastSend = millis();
    sendReading();
  }
  delay(100);
}
