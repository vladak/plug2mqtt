"""
Test plug2mqtt
"""

import copy
from pprint import pprint

import pytest

from config import (
    CURRENT_POWER,
    NICKNAME,
    ON,
    TODAY_ENERGY,
    TODAY_RUNTIME,
    check_config,
)

PLUGS_BASE_CONFIG = [
    {
        "topic": "devices/plug/kitchen",
        "username": "foo@bar",
        "password": "Changeme",
        "hostname": "foo.iot",
    },
    {
        "topic": "devices/plug/cellar",
        "username": "foo@bar",
        "password": "Changeme",
        "hostname": "bar.iot",
    },
]


def test_config_check_dup_hostname():
    """
    Test duplicate hostname detection.
    """
    plugs = copy.deepcopy(PLUGS_BASE_CONFIG)
    plugs[0]["hostname"] = plugs[1]["hostname"]
    pprint(plugs)
    with pytest.raises(ValueError):
        check_config(plugs)


def test_config_check_dup_topic():
    """
    Test duplicate topic detection.
    """
    plugs = copy.deepcopy(PLUGS_BASE_CONFIG)
    plugs[0]["topic"] = plugs[1]["topic"]
    pprint(plugs)
    with pytest.raises(ValueError):
        check_config(plugs)


def test_config_check_missing_hostname():
    """
    Test missing hostname detection.
    """
    plugs = [{"username": "foo", "password": "changeme", "topic": "foo/bar"}]
    with pytest.raises(ValueError):
        check_config(plugs)


def test_config_check_missing_topic():
    """
    Test missing topic detection.
    """
    plugs = [{"username": "foo", "password": "changeme", "hostname": "foo"}]
    with pytest.raises(ValueError):
        check_config(plugs)


def test_config_check_data_not_dict():
    """
    Test missing topic detection.
    """
    plugs = [
        {
            "username": "foo",
            "password": "changeme",
            "hostname": "foo",
            "topic": "xxx",
            "data": ["foo", "bar"],
        }
    ]
    with pytest.raises(ValueError):
        check_config(plugs)


@pytest.mark.parametrize(
    "key", [ON, CURRENT_POWER, NICKNAME, TODAY_ENERGY, TODAY_RUNTIME]
)
def test_config_check_data_reserved_key(key):
    """
    Test reserved key detection.
    """
    plugs = [
        {
            "username": "foo",
            "password": "changeme",
            "hostname": "foo",
            "topic": "xxx",
            "data": {key, "huh"},
        }
    ]
    with pytest.raises(ValueError):
        check_config(plugs)
