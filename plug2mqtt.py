#!/usr/bin/env python3

"""
Gather state of P110 plugs specified in configuration file
and publish it to MQTT topics.
"""

import json
import argparse
import logging
import os
import sys
import ssl
import socket
import time

from PyP100 import PyP110
import adafruit_minimqtt.adafruit_minimqtt as MQTT

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


def config_check(plugs):
    """
    check config for missing keys, duplicate hostnames/topics

    Will exit the program on error.
    """
    logger = logging.getLogger(__name__)

    logger.info("Checking configuration")
    for plug in plugs:
        if not plug.get("hostname"):
            logger.error("missing hostname")
            sys.exit(1)
        if not plug.get("username"):
            logger.error("missing username")
            sys.exit(1)
        if not plug.get("password"):
            logger.error("missing password")
            sys.exit(1)
        if not plug.get("topic"):
            logger.error("missing topic")
            sys.exit(1)

    hostnames = (plug["hostname"] for plug in plugs)
    if len(hostnames) != len(plugs):
        logger.error("duplicate hostnames in configuration")
        sys.exit(1)

    hostnames = (plug["topic"] for plug in plugs)
    if len(hostnames) != len(plugs):
        logger.error("duplicate topics in configuration")
        sys.exit(1)


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
            # The output of this statement will contain passwords, so leave it out:
            # logger.debug(f"{plugs}")
        except json.decoder.JSONDecodeError as e:
            logger.error(f"failed to load config: {e}")
            sys.exit(1)

    config_check(plugs)

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
                device_on = p110.getDeviceInfo()["result"]["device_on"]
                logger.debug(f"device_on = {device_on}")
	    # pylint: disable=broad-exception-caught
            except Exception as e:
                logger.error(f"Cannot get device state: {e}")
                continue

            # send the state to MQTT broker
            logger.debug("Publishing to MQTT broker")
            mqtt.publish(plug["topic"], json.dumps({"on": device_on}))

        logger.debug(f"Sleeping for {args.sleep} seconds")
        time.sleep(args.sleep)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
