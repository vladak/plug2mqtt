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


def has_reserved_keys(plug_data):
    """
    Check whether the dictionary has any reserved key.
    """
    logger = logging.getLogger(__name__)

    if plug_data.get(ON):
        logger.error(f"data contains reserved key: {ON}")
        return True

    if plug_data.get(CURRENT_POWER):
        logger.error(f"data contains reserved key: {CURRENT_POWER}")
        return True

    if plug_data.get(TODAY_ENERGY):
        logger.error(f"data contains reserved key: {TODAY_ENERGY}")
        return True

    if plug_data.get(TODAY_RUNTIME):
        logger.error(f"data contains reserved key: {TODAY_RUNTIME}")
        return True

    return False


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

            if has_reserved_keys(plug_data):
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
