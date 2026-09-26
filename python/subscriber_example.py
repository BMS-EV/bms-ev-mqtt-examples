#!/usr/bin/env python3
"""
Subscribe to a BMS-EV controller and print decoded battery data.

Field names and topics below were captured from a running controller
(firmware 16.5.0), not written from documentation:

    bms/{uid}/info           all measurements
    bms/{uid}/spec_data      cell_voltages, one entry per cell
    bms/{uid}/balancing_data cell_balancing, one boolean per cell
    bms/{uid}/status         "online" / "offline" only

Note that /info carries the measurements despite its name, and /status is only
the availability flag published as the MQTT last will.

    pip install paho-mqtt
    python subscriber_example.py
"""

import json
import ssl
import sys

import paho.mqtt.client as mqtt

# --- settings -------------------------------------------------------------
BROKER = "your.broker.address"
PORT = 1883          # 8883 for TLS; see USE_TLS below
USERNAME = "your_mqtt_username"
PASSWORD = "your_mqtt_password"
DEVICE_UID = "YOUR_DEVICE_UID"   # controller web interface / account panel
USE_TLS = False
# --------------------------------------------------------------------------

TOPICS = [
    (f"bms/{DEVICE_UID}/info", 0),
    (f"bms/{DEVICE_UID}/spec_data", 0),
    (f"bms/{DEVICE_UID}/balancing_data", 0),
    (f"bms/{DEVICE_UID}/status", 0),
]


def on_connect(client, userdata, flags, rc, properties=None):
    if rc != 0:
        print(f"Connection refused, code {rc}", file=sys.stderr)
        if rc == 5:
            print("  Check the username and password.", file=sys.stderr)
        return
    print(f"Connected. Subscribing to bms/{DEVICE_UID}/…")
    client.subscribe(TOPICS)


def on_disconnect(client, userdata, rc, properties=None):
    # paho retries on its own when loop_forever() is running
    if rc != 0:
        print(f"Disconnected unexpectedly (code {rc}), reconnecting…", file=sys.stderr)


def show_measurements(d):
    """Print the /info payload in a readable form."""
    power = d.get("stat_batt_power", 0)
    flow = "discharging" if power < 0 else ("charging" if power > 0 else "idle")

    print(f"  State of charge   {d.get('SOC', '?'):>8} %   "
          f"(raw from BMS: {d.get('SOC_real', '?')} %)")
    print(f"  State of health   {d.get('state_of_health', '?'):>8} %")
    print(f"  Pack voltage      {d.get('battery_voltage', '?'):>8} V")
    print(f"  Current           {d.get('battery_current', '?'):>8} A")
    print(f"  Power             {power:>8} W   {flow}")

    lo = d.get("cell_min_voltage")
    hi = d.get("cell_max_voltage")
    delta = d.get("cell_voltage_delta")
    if lo is not None and hi is not None:
        print(f"  Cells             {lo} – {hi} V, spread {delta} V")
        # A widening spread is the clearest early sign of a cell going bad.
        if isinstance(delta, (int, float)) and delta > 0.1:
            print("    ^ spread above 0.1 V — worth investigating")

    print(f"  Temperature       {d.get('temperature_min', '?')} – "
          f"{d.get('temperature_max', '?')} °C")
    print(f"  Limits            charge {d.get('max_charge_power', '?')} W, "
          f"discharge {d.get('max_discharge_power', '?')} W")
    print(f"  Energy            {d.get('remaining_capacity_real', '?')} of "
          f"{d.get('total_capacity', '?')} Wh")
    print(f"  BMS               {d.get('bms_status', '?')}, "
          f"controller {d.get('emulator_status', '?')}")

    balancing = d.get("balancing_active_cells", 0)
    if balancing:
        print(f"  Balancing         {balancing} cells active")


def on_message(client, userdata, msg):
    topic = msg.topic.rsplit("/", 1)[-1]
    raw = msg.payload.decode(errors="replace")

    if topic == "status":
        # plain text, not JSON
        print(f"\n[status] controller is {raw}")
        return

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(f"\n[{topic}] not JSON: {raw[:80]}", file=sys.stderr)
        return

    if topic == "info":
        print("\n[measurements]")
        show_measurements(data)

    elif topic == "spec_data":
        cells = data.get("cell_voltages", [])
        if cells:
            print(f"\n[cells] {len(cells)} cells, "
                  f"{min(cells)} – {max(cells)} V")

    elif topic == "balancing_data":
        flags = data.get("cell_balancing", [])
        active = [i for i, on in enumerate(flags) if on]
        if active:
            print(f"\n[balancing] cells {active}")


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(USERNAME, PASSWORD)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    if USE_TLS:
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

    try:
        client.connect(BROKER, PORT, keepalive=60)
    except OSError as e:
        print(f"Cannot reach {BROKER}:{PORT} — {e}", file=sys.stderr)
        return 1

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nStopping.")
        client.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
