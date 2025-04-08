#!/usr/bin/env python3

# pylint: disable=logging-fstring-interpolation

"""
Gather state of P110 plugs specified in configuration file
and publish it to MQTT topics.
"""

import argparse
import asyncio
import json
import logging
import os
import socket
import ssl
import sys
import time

import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_minimqtt.adafruit_minimqtt import MMQTTException

# pylint: disable=no-name-in-module
from tapo import ApiClient

from logutil import LogLevelAction, get_log_level


ON = "on"
CURRENT_POWER = "current_power"
NICKNAME = "nickname"


def parse_args():
    """
    Parse command line arguments
    :return: arguments
    """
    parser = argparse.ArgumentParser(
        description="publish P110 plug state to MQTT",
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
        "--config",
        help="Configuration file ",
        default="plugs.json",
    )

    return parser.parse_args()


# pylint: disable=too-many-return-statements
def is_config_ok(plugs):
    """
    Check config for missing keys, duplicate hostnames/topics.

    Return True on success, False on failure.
    """
    logger = logging.getLogger(__name__)

    logger.info("Checking configuration")
    for plug in plugs:
        if not plug.get("hostname"):
            logger.error("missing hostname")
            return False
        if not plug.get("username"):
            logger.error("missing username")
            return False
        if not plug.get("password"):
            logger.error("missing password")
            return False
        if not plug.get("topic"):
            logger.error("missing topic")
            return False

        plug_data = plug.get("data")
        if plug_data:
            if not isinstance(plug_data, dict):
                logger.error("data has to be a dictionary")
                return False

            if plug_data.get(ON):
                logger.error(f"data contains reserved key: {ON}")
                return False

            if plug_data.get(CURRENT_POWER):
                logger.error(f"data contains reserved key: {CURRENT_POWER}")
                return False

    # pylint: disable=consider-using-set-comprehension
    hostnames = set([plug["hostname"] for plug in plugs])
    if len(hostnames) != len(plugs):
        logger.error("duplicate hostnames in configuration")
        return False

    # pylint: disable=consider-using-set-comprehension
    topics = set([plug["topic"] for plug in plugs])
    if len(topics) != len(plugs):
        logger.error("duplicate topics in configuration")
        return False

    return True


# pylint: disable=too-many-statements,too-many-locals
async def main():
    """
    Main loop. Acquire state from all plugs, publish it to MQTT, sleep, repeat.
    """
    args = parse_args()

    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel(args.loglevel)

    # To support relative paths.
    os.chdir(os.path.dirname(__file__))

    config_log_level = get_log_level(args.loglevel)
    if config_log_level:
        logger.setLevel(config_log_level)

    # load config from file
    with open(args.config, encoding="UTF-8") as config_fp:
        try:
            plugs = json.load(config_fp)
            # The output of this statement will contain passwords,
            # so leave it out:
            # logger.debug(f"{plugs}")
        except json.decoder.JSONDecodeError as e:
            logger.error(f"failed to load config: {e}")
            sys.exit(1)

    if not is_config_ok(plugs):
        sys.exit(1)

    # connect to MQTT broker
    mqtt = MQTT.MQTT(
        broker=args.hostname,
        port=args.port,
        socket_pool=socket,
        ssl_context=ssl.create_default_context(),
    )
    logger.info(f"Connecting to MQTT broker {args.hostname} on port {args.port}")
    mqtt.connect()

    while True:
        try:
            # Make sure to stay connected to the broker e.g. in case of keep alive.
            mqtt.loop(1)

            for plug in plugs:
                hostname = plug["hostname"]
                logger.info(f"Connecting to the plug on {hostname}")
                try:
                    client = ApiClient(plug["username"], plug["password"])
                    p110 = await client.p110(hostname)
                    logger.info(f"Connected to the plug on {hostname}")

                    logger.debug("Getting device info")
                    device_info = await p110.get_device_info()
                    logger.debug("Got device info")
                    device_info_dict = device_info.to_dict()
                    logger.debug(f"device info: {device_info_dict}")
                    device_on = device_info_dict["device_on"]
                    logger.debug(f"device_on = {device_on}")

                    try:
                        nickname = device_info_dict["nickname"]
                    except KeyError:
                        nickname = None

                    energy_usage = await p110.get_energy_usage()
                    energy_usage_dict = energy_usage.to_dict()
                    logger.debug(f"Got energy usage dictionary: {energy_usage_dict}")
                    current_power = energy_usage_dict.get("current_power")
                # pylint: disable=broad-exception-caught
                except Exception as e:
                    logger.error(f"Cannot get device state: {e}")
                    continue

                payload = {ON: device_on, CURRENT_POWER: current_power / 1000}
                if nickname:
                    payload[NICKNAME] = nickname

                if plug.get("data"):
                    payload.update(plug["data"])

                # send the data to MQTT broker
                topic = plug["topic"]
                logger.info(f"Publishing to MQTT topic {topic}")
                logger.debug(f"Payload: {payload}")
                mqtt.publish(topic, json.dumps(payload))
        except MMQTTException as e:
            logger.warning(f"Got MQTT exception: {e}")
            mqtt.reconnect()

        logger.info(f"Sleeping for {args.sleep} seconds")
        time.sleep(args.sleep)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
