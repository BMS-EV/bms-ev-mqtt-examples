# BMS-EV MQTT Examples

MQTT topic reference and integration examples for [BMS-EV controllers](https://bms-ev.com/) — Home Assistant, Node-RED, Grafana, InfluxDB.

**Full documentation:** [docs.bms-ev.com](https://docs.bms-ev.com/)

---

## Home Assistant users: you probably don't need this

The controller publishes **native Home Assistant MQTT auto-discovery**. Point it at your
broker and the battery appears under Settings → Devices & Services with 25 entities
already configured. See [bms-ev-home-assistant](https://github.com/BMS-EV/bms-ev-home-assistant).

This repository is for everything else — Node-RED, Grafana, InfluxDB, your own client.

---

## Topics

Controllers publish to `bms/{device_uid}/…`, where `device_uid` is shown in the
controller's web interface and in your account panel.

Use the exact sub-topics. `bms/{uid}/#` is not needed and the broker's ACL may reject it.

| Topic | Frequency | Contents |
|---|---|---|
| `bms/{uid}/info` | ~2 s | **All measurements** — SoC, voltage, current, power, temperatures, limits, status |
| `bms/{uid}/spec_data` | ~2 s | `cell_voltages` — one entry per cell |
| `bms/{uid}/balancing_data` | ~2 s | `cell_balancing` — one boolean per cell |
| `bms/{uid}/status` | on change | `online` / `offline` only (MQTT last will) |

> **Note on naming:** `/info` carries the live measurements despite its name, and
> `/status` is only the availability flag. Historic naming — kept stable so existing
> integrations keep working.

---

## Payloads

Captured from a running controller (Kia EV6 77 kWh pack, firmware 16.5.0).

### `/info` — measurements

```json
{
  "bms_status": "ACTIVE",
  "pause_status": "RUNNING",
  "SOC": 88.64,
  "SOC_real": 82.62,
  "state_of_health": 100,
  "temperature_min": 17,
  "temperature_max": 20,
  "cpu_temp": 58.88889,
  "stat_batt_power": -375,
  "battery_current": -0.5,
  "battery_voltage": 754.4,
  "cell_max_voltage": 3.92,
  "cell_min_voltage": 3.92,
  "cell_voltage_delta": 0,
  "total_capacity": 77400,
  "remaining_capacity_real": 63947,
  "remaining_capacity": 44594,
  "max_discharge_power": 20000,
  "max_charge_power": 20000,
  "balancing_active_cells": 0,
  "balancing_status": "Unknown",
  "event_level": "EVENT_LEVEL_DEBUG",
  "emulator_status": "OK"
}
```

| Field | Unit | Meaning |
|---|---|---|
| `SOC` | % | State of charge **after** the configured usable window |
| `SOC_real` | % | Raw value from the vehicle BMS |
| `state_of_health` | % | As reported by the pack |
| `battery_voltage` | V | Pack terminal voltage |
| `battery_current` | A | Negative = discharging |
| `stat_batt_power` | W | Negative = discharging |
| `cell_min_voltage` / `cell_max_voltage` | V | Extremes across the pack |
| `cell_voltage_delta` | V | Spread — **the number to watch**; a widening delta means a cell is ageing faster than the rest |
| `total_capacity` | Wh | Nameplate |
| `remaining_capacity_real` | Wh | From the pack |
| `remaining_capacity` | Wh | Scaled to the usable window |
| `max_charge_power` / `max_discharge_power` | W | Limits the BMS currently allows |
| `temperature_min` / `temperature_max` | °C | Coldest and hottest cell |
| `balancing_active_cells` | count | Cells balancing right now |

`SOC` and `SOC_real` differ because the controller applies a usable window — the pack
above reports 82.62 % raw and 88.64 % scaled.

### `/spec_data` — per-cell voltages

```json
{ "cell_voltages": [3.92, 3.92, 3.92, "… one entry per cell"] }
```

Array length equals the pack's series count — 96 for a Tesla Model 3 NCA pack,
192 for a Hyundai/Kia E-GMP pack.

### `/balancing_data` — per-cell balancing

```json
{ "cell_balancing": [false, false, true, "… one entry per cell"] }
```

Same index order as `cell_voltages`, so the two line up cell by cell.

### `/status` — availability

Plain text, `online` or `offline`. Published as the MQTT last will, so `offline`
arrives automatically if the controller loses power or network.

---

## Node-RED

Minimal flow: subscribe, parse, alert when the cell spread widens.

```json
[
  {
    "id": "bmsev_in", "type": "mqtt in",
    "topic": "bms/YOUR_DEVICE_UID/info",
    "qos": "0", "broker": "your_broker", "x": 140, "y": 100,
    "wires": [["bmsev_parse"]]
  },
  {
    "id": "bmsev_parse", "type": "json",
    "property": "payload", "action": "obj",
    "x": 310, "y": 100, "wires": [["bmsev_delta"]]
  },
  {
    "id": "bmsev_delta", "type": "switch",
    "property": "payload.cell_voltage_delta", "propertyType": "msg",
    "rules": [{ "t": "gt", "v": "0.1", "vt": "num" }],
    "outputs": 1, "x": 480, "y": 100, "wires": [["bmsev_alert"]]
  },
  {
    "id": "bmsev_alert", "type": "debug",
    "name": "cell imbalance", "active": true,
    "complete": "payload.cell_voltage_delta",
    "x": 660, "y": 100, "wires": []
  }
]
```

---

## InfluxDB + Grafana

```python
import json
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

DEVICE = "YOUR_DEVICE_UID"
influx = InfluxDBClient(url="http://localhost:8086", token="TOKEN", org="ORG")
write = influx.write_api(write_options=SYNCHRONOUS)

# Only numeric fields — the text ones would break the schema
NUMERIC = (
    "SOC", "SOC_real", "state_of_health", "battery_voltage", "battery_current",
    "stat_batt_power", "cell_min_voltage", "cell_max_voltage", "cell_voltage_delta",
    "temperature_min", "temperature_max", "cpu_temp", "total_capacity",
    "remaining_capacity", "remaining_capacity_real",
    "max_charge_power", "max_discharge_power", "balancing_active_cells",
)


def on_message(client, userdata, msg):
    data = json.loads(msg.payload)
    point = Point("battery").tag("device", DEVICE)
    for key in NUMERIC:
        if key in data and isinstance(data[key], (int, float)):
            point = point.field(key, float(data[key]))
    write.write(bucket="bms_ev", record=point)


client = mqtt.Client()
client.username_pw_set("YOUR_MQTT_USER", "YOUR_MQTT_PASSWORD")
client.on_message = on_message
client.connect("your.broker", 1883)
client.subscribe(f"bms/{DEVICE}/info")
client.loop_forever()
```

Useful Grafana queries once data is flowing:

```flux
// Cell spread over time — the clearest early warning of a failing cell
from(bucket: "bms_ev")
  |> range(start: -30d)
  |> filter(fn: (r) => r._measurement == "battery" and r._field == "cell_voltage_delta")
  |> aggregateWindow(every: 1h, fn: max)

// Charge vs discharge power
from(bucket: "bms_ev")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "battery" and r._field == "stat_batt_power")
```

---

## Python client

[`python/subscriber_example.py`](python/subscriber_example.py) — a complete subscriber
that prints decoded values, with reconnect handling.

---

## Related

- [bms-ev-home-assistant](https://github.com/BMS-EV/bms-ev-home-assistant) — native auto-discovery, 25 entities
- [bms-ev-docs](https://github.com/BMS-EV/bms-ev-docs) — compatibility dataset: 70 battery profiles × 56 inverters
- [docs.bms-ev.com](https://docs.bms-ev.com/) — full technical documentation

Built on [dalathegreat/Battery-Emulator](https://github.com/dalathegreat/Battery-Emulator).
