#!/usr/bin/env python3

# pylint: disable=logging-fstring-interpolation

"""
Gather state of P110 plugs specified in configuration file
and publish it to MQTT topics.
"""

import asyncio
import json
import logging
import os
import socket
import ssl
import sys

import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_minimqtt.adafruit_minimqtt import MMQTTException

# pylint: disable=no-name-in-module
from tapo import ApiClient

from config import (
    CURRENT_POWER,
    NICKNAME,
    ON,
    TODAY_ENERGY,
    TODAY_RUNTIME,
    is_config_ok,
    parse_args,
)
from logutil import get_log_level


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

                payload = {
                    ON: device_on,
                    CURRENT_POWER: current_power / 1000,
                    TODAY_ENERGY: energy_usage_dict.get("today_energy"),
                    TODAY_RUNTIME: energy_usage_dict.get("today_runtime"),
                }
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
        await asyncio.sleep(args.sleep)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
