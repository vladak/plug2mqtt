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
from datetime import datetime

import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_minimqtt.adafruit_minimqtt import MMQTTException

from config import (
    check_config,
    parse_args,
)
from logutil import get_log_level
from plug import Plug


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
            plugs_config = json.load(config_fp)
            # The output of this statement will contain passwords,
            # so leave it out:
            # logger.debug(f"{plugs}")
        except json.decoder.JSONDecodeError as e:
            logger.error(f"failed to load config: {e}")
            sys.exit(1)

    check_config(plugs_config)

    # connect to MQTT broker
    mqtt = MQTT.MQTT(
        broker=args.hostname,
        port=args.port,
        socket_pool=socket,
        ssl_context=ssl.create_default_context(),
    )
    logger.info(f"Connecting to MQTT broker {args.hostname} on port {args.port}")
    mqtt.connect()

    plugs = []
    for plug_config in plugs_config:
        plug = Plug(plug_config)
        plugs.append(plug)

    before = datetime.now()
    logger.info("Connecting to the plugs")
    res = await asyncio.gather(
        *[plug.connect() for plug in plugs], return_exceptions=True
    )
    logger.info(f"Handled connect to all plugs in {datetime.now() - before}")
    for r in res:
        if isinstance(r, Exception):
            logger.error(r)

    while True:
        try:
            # Make sure to stay connected to the broker e.g. in case of keep alive.
            mqtt.loop(1)

            before = datetime.now()
            plug_data = await asyncio.gather(
                *[plug.get_device_info() for plug in plugs], return_exceptions=True
            )
            logger.info(f"Got data from all plugs in {datetime.now() - before}")
            for r in plug_data:
                if isinstance(r, Exception):
                    logger.error(r)
                else:
                    (topic, payload) = r
                    if payload is not None:
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
