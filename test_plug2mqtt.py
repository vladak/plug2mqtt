"""
Test plug2mqtt
"""

import copy
from pprint import pprint

from plug2mqtt import is_config_ok

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
    assert not is_config_ok(plugs)


def test_config_check_dup_topic():
    """
    Test duplicate topic detection.
    """
    plugs = copy.deepcopy(PLUGS_BASE_CONFIG)
    plugs[0]["topic"] = plugs[1]["topic"]
    pprint(plugs)
    assert not is_config_ok(plugs)


def test_config_check_missing_hostname():
    """
    Test missing hostname detection.
    """
    plugs = [{"username": "foo", "password": "changeme", "topic": "foo/bar"}]
    assert not is_config_ok(plugs)


def test_config_check_missing_topic():
    """
    Test missing topic detection.
    """
    plugs = [{"username": "foo", "password": "changeme", "hostname": "foo"}]
    assert not is_config_ok(plugs)


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
    assert not is_config_ok(plugs)
