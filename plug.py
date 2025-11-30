"""
plug class
"""

import logging

# pylint: disable=no-name-in-module
from tapo import ApiClient

from config import CURRENT_POWER, NICKNAME, ON, TODAY_ENERGY, TODAY_RUNTIME


class Plug:
    """
    encapsulates a plug
    """

    def __init__(self, plug_config):
        """
        assumes the plug configuration has been already validated
        """
        self._plug_config = plug_config
        self._p110 = None

        self.logger = logging.getLogger(__name__)

    async def connect(self):
        """
        connect to the plug using the configuration
        """
        hostname = self._plug_config["hostname"]
        self.logger.info(f"Connecting to {hostname}")

        try:
            client = ApiClient(
                self._plug_config["username"], self._plug_config["password"]
            )
            self._p110 = await client.p110(hostname)
            self.logger.info(f"Connected to {hostname}")
        except Exception as e:
            # pylint: disable=broad-exception-raised
            raise Exception(f"Cannot connect to plug {self.hostname}: {e}") from e

    @property
    def hostname(self):
        """
        returns the hostname
        """
        return self._plug_config["hostname"]

    @property
    def topic(self):
        """
        returns the topic
        """
        return self._plug_config["topic"]

    async def get_device_info(self):
        """
        get the device info
        """
        if self._p110 is None:
            self.logger.error(f"Not connected to plug {self.hostname}, reconnecting")
            await self.connect()

        self.logger.debug("Getting device info")
        device_info = await self._p110.get_device_info()
        self.logger.debug("Got device info")
        device_info_dict = device_info.to_dict()
        self.logger.debug(f"device info: {device_info_dict}")
        device_on = device_info_dict["device_on"]
        self.logger.debug(f"device_on = {device_on}")

        try:
            nickname = device_info_dict["nickname"]
        except KeyError:
            nickname = None

        try:
            energy_usage = await self._p110.get_energy_usage()
            energy_usage_dict = energy_usage.to_dict()
            self.logger.debug(
                f"Got energy usage dictionary from {self.hostname}: {energy_usage_dict}"
            )
            current_power = energy_usage_dict.get("current_power")
        # pylint: disable=broad-exception-caught
        except Exception as e:
            # pylint: disable=broad-exception-raised
            raise Exception(f"Cannot get energy usage info for {self.hostname}") from e

        payload = {
            ON: device_on,
            CURRENT_POWER: current_power / 1000,
            TODAY_ENERGY: energy_usage_dict.get("today_energy"),
            TODAY_RUNTIME: energy_usage_dict.get("today_runtime"),
        }
        if nickname:
            payload[NICKNAME] = nickname

        if self._plug_config.get("data"):
            payload.update(self._plug_config["data"])

        return self.topic, payload

    def __str__(self):
        return self.hostname
