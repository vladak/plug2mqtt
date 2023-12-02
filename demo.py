#!/usr/bin/env python3

# pylint: disable=logging-fstring-interpolation

"""
Gather state of P110 plugs from MQTT.
"""

import argparse
import json
import logging
import socket
import ssl
import sys
import time

import adafruit_minimqtt.adafruit_minimqtt as MQTT

from logutil import LogLevelAction


# pylint: disable=too-few-public-methods
class Device:
    """
    represents a plug device
    """

    def __init__(self, name, power):
        self.name = name
        self.power = power
        self.last_time = time.monotonic()

    def __str__(self):
        return f"{self.name}: {self.power} {self.last_time}"

    def update(self, power):
        """
        update last power state.
        """
        self.last_time = time.monotonic()
        self.power = power


def parse_args():
    """
    Parse command line arguments
    :return: arguments
    """
    parser = argparse.ArgumentParser(
        description="get P110 plug state from MQTT",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-l",
        "--loglevel",
        action=LogLevelAction,
        help='Set log level (e.g. "ERROR")',
        default=logging.INFO,
    )
    parser.add_argument(
        "--hostname",
        help="MQTT broker hostname",
        default="localhost",
    )
    parser.add_argument(
        "--port",
        help="MQTT broker port",
        default=1883,
    )
    parser.add_argument(
        "--sleep",
        help="Sleep time in seconds between getting device state",
        default=30,
    )
    parser.add_argument(
        "--topic",
        help="MQTT topic",
        required=True,
    )
    parser.add_argument(
        "--threshold",
        help='minimal value in Watts recognized as "on" state',
        default=10,
        type=int,
    )
    parser.add_argument(
        "--timeout",
        help="if device state was last read earlier than this, "
        "consider the state unknown, in seconds",
        default=60,
        type=int,
    )

    return parser.parse_args()


# pylint: disable=unused-argument, redefined-outer-name
def connect(mqtt_client, userdata, flags, rc):
    """
    connect callback
    """
    logger = logging.getLogger(__name__)
    logger.debug("Connected to MQTT Broker!")
    logger.debug(f"Flags: {flags}\n RC: {rc}")


def subscribe(mqtt_client, userdata, topic, granted_qos):
    """
    subscribe callback
    """
    logger = logging.getLogger(__name__)
    logger.debug(f"Subscribed to {topic} with QOS level {granted_qos}")


def message(client, topic, message):
    """
    received message callback
    """
    logger = logging.getLogger(__name__)
    logger.debug(f"New message on topic {topic}: {message}")

    device_name = None
    try:
        idx = topic.rindex("/")
        device_name = topic[idx + 1 :]
    except ValueError as e:
        logger.error(f"not a valid topic: {topic}", e)

    if device_name:
        try:
            d = json.loads(message)
            on = d.get("on")
        except json.decoder.JSONDecodeError as e:
            logger.error(f"cannot parse JSON: {e}")
            return

        if on:
            power = d.get("current_power")
            logger.debug(f"updating {device_name} with {power}")
            # The "on_message" callback does not get user data directly like other callbacks,
            # so one has to use the MQTT object.
            devices = client.user_data
            if not devices.get(device_name):
                devices[device_name] = Device(device_name, power)
            else:
                devices[device_name].update(power)


def get_device_state(device_info, args):
    """
    return device state based on power consumption
    """
    state = "N/A"
    # if not updated for X seconds, consider the state as unknown.
    if time.monotonic() - device_info.last_time < args.timeout:
        if device_info.power > args.threshold:
            state = "on"
        else:
            state = "off"

    return state


# pylint: disable=too-many-statements,too-many-locals
def main():
    """
    Main loop. Acquire state from plugs using MQTT and use a threshold to determine
    if the plugged device is on or off.
    """
    args = parse_args()

    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel(args.loglevel)

    # map of device name to Devices instance
    devices = {}

    # connect to MQTT broker
    mqtt = MQTT.MQTT(
        broker=args.hostname,
        port=args.port,
        socket_pool=socket,
        ssl_context=ssl.create_default_context(),
        user_data=devices,
    )

    mqtt.on_connect = connect
    mqtt.on_subscribe = subscribe
    mqtt.on_message = message

    logger.info(f"Connecting to MQTT broker {args.hostname} on port {args.port}")
    mqtt.connect()
    mqtt.subscribe(args.topic, qos=0)

    i = 0
    while True:
        # Make sure to stay connected to the broker e.g. in case of keep alive.
        i += 1
        logger.debug(f"Loop {i}")
        mqtt.loop(1)

        for device_name, device_info in devices.items():
            logger.debug(f"{device_info}")
            logger.info(f"{device_name} = {get_device_state(device_info, args)}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
