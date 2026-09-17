# BMS-EV MQTT Examples

Integration examples for [BMS-EV controllers](https://bms-ev.com/) — Node-RED flows, Grafana dashboards, InfluxDB scripts, Home Assistant automations, and MQTT client examples.

**Full documentation:** [docs.bms-ev.com](https://docs.bms-ev.com/)

## MQTT topic reference

BMS-EV controllers publish to `bms/{device_uid}/{topic}` where `device_uid` is printed on the controller label.

_Note: Topic pattern is `bms/{device_uid}` (**no wildcards or trailing /#**) — the controller publishes to specific sub-topics only._

| Topic | Frequency | Payload | Description |
|-------|-----------|---------|-------------|
| `bms/{uid}/info` | On connect + every 10 min | JSON | Firmware version, hardware revision, battery model, inverter model, device UID |
| `bms/{uid}/spec_data` | On connect | JSON | Nominal voltage, capacity kWh, chemistry, cell count, series/parallel topology |
| `bms/{uid}/balancing_data` | Every 5 sec | JSON | Array of per-cell voltages, min/max/delta, per-module temperatures |
| `bms/{uid}/status` | Every 1 sec | JSON | SOC, SOH, voltage, current, power, charge/discharge limits, contactor state, BMS state, error state |

## Example payloads

### /info

```json
{
  "device_uid": "bmev-a1b2c3d4",
  "firmware_version": "3.8.2",
  "hardware_revision": "HW3.1",
  "battery_model": "Tesla Model 3 LR 75 kWh",
  "inverter_model": "SOFAR HYD 10KTL-3PH",
  "protocol": "BYD Battery-Box HVS emulation"
}
```

### /spec_data

```json
{
  "chemistry": "NCA",
  "nominal_voltage": 355,
  "nominal_capacity_kwh": 75.0,
  "cell_count_series": 96,
  "cell_count_parallel": 46,
  "min_operating_voltage": 250,
  "max_operating_voltage": 410
}
```

### /balancing_data

```json
{
  "cell_voltages": [3.712, 3.714, 3.713],
  "min_cell_v": 3.708,
  "max_cell_v": 3.716,
  "delta_mv": 8,
  "module_temps": [28, 29, 30, 28, 27, 29, 28, 30]
}
```

### /status

```json
{
  "soc": 67.5,
  "soh": 94.2,
  "voltage": 356.8,
  "current": 15.3,
  "power": 5459,
  "charge_current_limit": 100,
  "discharge_current_limit": 200,
  "contactor": true,
  "bms_state": "discharging",
  "error_state": null,
  "timestamp": "2026-09-17T21:00:00Z"
}
```

## Examples in this repository

- [`node-red/`](node-red/) — Node-RED flows (SOC alerts, energy accounting, MQTT-to-Modbus bridge)
- [`grafana/`](grafana/) — Grafana dashboard JSON (SOC, cell voltage heatmap, power flow, cycle counter)
- [`influxdb/`](influxdb/) — InfluxDB retention policies, continuous queries, Python bridge script
- [`python/`](python/) — Python subscriber examples (paho-mqtt, asyncio-mqtt)
- [`mqtt-explorer/`](mqtt-explorer/) — MQTT Explorer session file

## Related

- [BMS-EV Home Assistant integration](https://github.com/BMS-EV/bms-ev-home-assistant) — HA custom component with auto-discovery
- [BMS-EV documentation](https://docs.bms-ev.com/) — full technical reference

## License

[MIT License](LICENSE)

## Contact

- Shop: https://bms-ev.com/
- Documentation: https://docs.bms-ev.com/
- Email: office@bms-ev.com
