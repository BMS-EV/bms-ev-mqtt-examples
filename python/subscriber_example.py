#!/usr/bin/env python3
"""
BMS-EV MQTT subscriber example
Subscribes to a specific BMS-EV controller and prints status updates.

Requires: pip install paho-mqtt
"""
import json
import paho.mqtt.client as mqtt

DEVICE_UID = 'bmev-XXXXXXXX'  # your controller ID from label
MQTT_HOST = 'localhost'
MQTT_PORT = 1883
MQTT_USER = None
MQTT_PASS = None

def on_message(client, userdata, msg):
    topic_parts = msg.topic.split('/')
    if len(topic_parts) < 3:
        return
    sub_topic = topic_parts[-1]
    payload = json.loads(msg.payload.decode())

    if sub_topic == 'status':
        print(f"SOC: {payload['soc']:.1f}% | V: {payload['voltage']:.1f}V | I: {payload['current']:+.1f}A | P: {payload['power']:+d}W | Contactor: {payload['contactor']}")
    elif sub_topic == 'balancing_data':
        print(f"Cells: min={payload['min_cell_v']:.3f}V max={payload['max_cell_v']:.3f}V delta={payload['delta_mv']}mV")

client = mqtt.Client()
if MQTT_USER: client.username_pw_set(MQTT_USER, MQTT_PASS)
client.on_message = on_message
client.connect(MQTT_HOST, MQTT_PORT)
client.subscribe(f'bms/{DEVICE_UID}/status')
client.subscribe(f'bms/{DEVICE_UID}/balancing_data')
print(f'Subscribed to bms/{DEVICE_UID}/status and /balancing_data')
client.loop_forever()
