#!/usr/bin/env python3

# pylint: disable=logging-fstring-interpolation

"""
Gather state of P110 plugs specified in configuration file
and publish it to MQTT topics.
"""

import argparse
import base64
import json
import logging
import os
import socket
import ssl
import sys
import time

import adafruit_minimqtt.adafruit_minimqtt as MQTT
from PyP100 import PyP110

from logutil import LogLevelAction, get_log_level


def parse_args():
    """
    Parse command line arguments
    :return: arguments
    """
    parser = argparse.ArgumentParser(
        description="trun on/off a socket based on temperature difference",
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

        if plug.get("data") and not isinstance(plug["data"], dict):
            logger.error("data has to be a dictionary")
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
def main():
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
        # Make sure to stay connected to the broker e.g. in case of keep alive.
        mqtt.loop(1)

        for plug in plugs:
            hostname = plug["hostname"]
            logger.info(f"Connecting to the plug on {hostname}")
            try:
                p110 = PyP110.P110(hostname, plug["username"], plug["password"])
                p110.handshake()
                p110.login()
                logger.info("Connected to the plug")

                logger.debug(f"device info: {p110.getDeviceInfo()}")
                result = p110.getDeviceInfo()["result"]
                device_on = result["device_on"]
                logger.debug(f"device_on = {device_on}")

                try:
                    nickname = result["nickname"]
                except KeyError:
                    nickname = None

                energy_usage_dict = p110.getEnergyUsage()
                logger.debug(f"Got energy usage dictionary: {energy_usage_dict}")
                current_power = energy_usage_dict.get("result").get("current_power")
            # pylint: disable=broad-exception-caught
            except Exception as e:
                logger.error(f"Cannot get device state: {e}")
                continue

            payload = {"on": device_on, "current_power": current_power / 1000}
            if nickname:
                payload["nickname"] = base64.b64decode(nickname).decode("utf-8")

            if plug.get("data"):
                payload.update(plug["data"])

            # send the data to MQTT broker
            logger.info("Publishing to MQTT broker")
            logger.debug(f"Payload: {payload}")
            mqtt.publish(plug["topic"], json.dumps(payload))

        logger.debug(f"Sleeping for {args.sleep} seconds")
        time.sleep(args.sleep)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
