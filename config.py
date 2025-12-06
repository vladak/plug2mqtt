"""
config functions
"""

import argparse
import logging

from logutil import LogLevelAction

ON = "on"
CURRENT_POWER = "current_power"
NICKNAME = "nickname"
TODAY_ENERGY = "today_energy"
TODAY_RUNTIME = "today_runtime"


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


def check_reserved_keys(plug_data):
    """
    Check whether the dictionary has any reserved key.
    """
    if plug_data.get(ON):
        raise ValueError(f"data contains reserved key: {ON}")

    if plug_data.get(CURRENT_POWER):
        raise ValueError(f"data contains reserved key: {CURRENT_POWER}")

    if plug_data.get(TODAY_ENERGY):
        raise ValueError(f"data contains reserved key: {TODAY_ENERGY}")

    if plug_data.get(TODAY_RUNTIME):
        raise ValueError(f"data contains reserved key: {TODAY_RUNTIME}")


# pylint: disable=too-many-return-statements
def check_config(plugs):
    """
    Check config for missing keys, duplicate hostnames/topics.
    """
    logger = logging.getLogger("")

    logger.info("Checking configuration")
    for plug in plugs:
        if not plug.get("hostname"):
            raise ValueError("missing hostname")
        if not plug.get("username"):
            raise ValueError("missing username")
        if not plug.get("password"):
            raise ValueError("missing password")
        if not plug.get("topic"):
            raise ValueError("missing topic")

        plug_data = plug.get("data")
        if plug_data:
            if not isinstance(plug_data, dict):
                raise ValueError("data has to be a dictionary")

            check_reserved_keys(plug_data)

    # pylint: disable=consider-using-set-comprehension
    hostnames = set([plug["hostname"] for plug in plugs])
    if len(hostnames) != len(plugs):
        raise ValueError("duplicate hostnames in configuration")

    # pylint: disable=consider-using-set-comprehension
    topics = set([plug["topic"] for plug in plugs])
    if len(topics) != len(plugs):
        raise ValueError("duplicate topics in configuration")
