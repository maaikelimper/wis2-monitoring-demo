import os
import requests
import boto3
import csv
import ssl
import logging
import random
import paho.mqtt.client as mqtt
import re
import json
import sys

MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PWD = os.getenv("MQTT_PWD")
MQTT_HOST = os.getenv("MQTT_HOST")
MQTT_PORT = os.getenv("MQTT_PORT", 8883)

DATA_MAPPING = {}

LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING")
LOGGER = logging.getLogger('mqtt-subscriber')
LOGGER.setLevel(LOG_LEVEL)
logging.basicConfig(stream=sys.stdout)

def sub_connect(client, userdata, flags, rc, properties=None):
    LOGGER.info(f"on connection to subscribe: {mqtt.connack_string(rc)}")
    for topic in DATA_MAPPING:
        LOGGER.info(f'subscribing to topic: {topic}')
        client.subscribe(topic, qos=1)

def sub_on_message(client, userdata, msg):
    """
      do something with the message
    """
    # use regex to match msg.topic with subscribed-topic  
    subscription = ''
    for topic in DATA_MAPPING:
        pattern = topic.replace('+', '[^/]*').replace('/#', '(|/.*)')
        if re.match(pattern, msg.topic):
            subscription=topic
    if subscription == '':
        LOGGER.warning(f"failed to find subscription for msg.topic={msg.topic}")
        return
    try:
        message = json.loads(msg.payload.decode('utf-8'))
        data_url = message["links"][0]["href"]
        data_type = message["links"][0]["type"]
        LOGGER.info(f"New MQTT-message received on topic={topic}")
        LOGGER.info(f"subscription={subscription}, data_type={data_type}")
        LOGGER.info(f"message-content={message}")
    except Exception as e:
        LOGGER.error(f'Exception: {e}')


def run_mqtt_subscriber():
    r = random.Random()
    client_id = f"{__name__}_{r.randint(1,1000):04d}"
    client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv5)
    if MQTT_PORT == 8883:
        client.tls_set(
            certfile=None,
            keyfile=None,
            cert_reqs=ssl.CERT_REQUIRED
        )
    client.username_pw_set(MQTT_USERNAME, MQTT_PWD)
    client.on_connect = sub_connect
    client.on_message = sub_on_message
    client.connect(MQTT_HOST, port=int(MQTT_PORT))
    client.loop_forever()


def main():
    print(f'Starting mqtt-subscriber with LOG_LEVEL={LOG_LEVEL}')
    LOGGER.info("run mqtt-subscriber")
    LOGGER.info(f'MQTT_HOST={MQTT_HOST}')
    LOGGER.info(f'MQTT_USERNAME={MQTT_USERNAME}')
    LOGGER.info(f'MQTT_PASSWORD={MQTT_PWD}')
    LOGGER.info(f'MQTT_PORT={MQTT_PORT}')

    if not MQTT_HOST:
        LOGGER.error('MQTT_HOST is not defined')
        return
    data_mapping_file = '/tmp/topics.csv'
    print(f"Read configuration from {data_mapping_file}: ")
    with open(data_mapping_file) as file:
        reader = csv.reader(file)
        next(reader, None)
        for data in reader:
            topic = data[0].rstrip()
            if topic == 'mqtt_topic':
                continue
            print(f' * topic={topic}')
            DATA_MAPPING[topic] = {}
    if len(DATA_MAPPING.keys()) > 0:
        print(f'Configuration provided {len(DATA_MAPPING.keys())} mqtt-topics')
        run_mqtt_subscriber()
    else:
        print('0 topics defined, exiting')


if __name__ == "__main__":
    main()
