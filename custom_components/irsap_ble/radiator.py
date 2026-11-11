"""Bluetooth client for an IRSAP radiator."""
from __future__ import annotations

import asyncio
import logging
import time

from bleak import BleakClient
from bleak.exc import BleakError
from bleak.backends.device import BLEDevice
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .protocol import (
    UUID_ANNOUNCE,
    UUID_CONFIG,
    UUID_STATUS_DATA,
    UUID_STATUS_HEADER,
    RadiatorState,
    build_status_requests,
    declared_length,
    parse_state,
)

_LOGGER = logging.getLogger(__name__)

OPERATION_TIMEOUT = 40  # seconds for the read/write part of a cycle
CONNECT_TOTAL_TIMEOUT = 75  # seconds for the whole connection (a good link connects in about 8 s); a hung connection
                            # keeps the shared Bluetooth lock, so it must not last long
CONNECT_ATTEMPTS = 3        # connection attempts made by bleak-retry-connector
SERVICE_ROUNDS = 2          # times the connection is redone when the GATT services come back incomplete


# Everything the integration reads or writes: all of it must be present, or the service discovery was partial
REQUIRED_CHARACTERISTICS = (UUID_ANNOUNCE, UUID_CONFIG, UUID_STATUS_HEADER, UUID_STATUS_DATA)


class IrsapError(Exception):
    """Communication with the radiator failed."""


def _describe(err: Exception) -> str:
    """Error text that is never empty (some Bluetooth errors have no message)."""
    return f"{type(err).__name__}: {err}" if str(err) else repr(err)


class IrsapRadiator:
    """One radiator. Every operation connects, does its job and disconnects.

    The radiator accepts a single Bluetooth connection at a time, so the connection is never kept open:
    the IRSAP NOW phone app can still be used between two operations.

    A Bluetooth adapter can only start one connection at a time, so one lock is shared by all the radiators:
    with several radiators their polls (and commands) run one after the other, never together.
    """

    def __init__(self, hass: HomeAssistant, address: str, name: str) -> None:
        self._hass = hass
        self.address = address
        self._name = name
        self._lock: asyncio.Lock = hass.data.setdefault(DOMAIN, {}).setdefault("bluetooth_lock", asyncio.Lock())

    def _lookup(self) -> BLEDevice | None:
        """Best connectable adapter or proxy for the radiator right now."""
        return bluetooth.async_ble_device_from_address(self._hass, self.address, connectable=True)

    async def _async_connect(self) -> BleakClient:
        last_error: Exception | None = None
        for round_no in range(1, SERVICE_ROUNDS + 1):
            device = self._lookup()
            if device is None:
                raise IrsapError(
                    f"{self._name} ({self.address}) is not in range of any connectable Bluetooth adapter or proxy "
                    "(Shelly devices and other advertisement-only gateways cannot connect: use a local adapter or an "
                    "ESPHome Bluetooth proxy with bluetooth_proxy: active: true)"
                )
            started = time.monotonic()
            try:
                async with asyncio.timeout(CONNECT_TOTAL_TIMEOUT):
                    # establish_connection retries, looks the device up again before each attempt (another adapter
                    # or proxy may now have the best signal) and reuses the cached GATT services
                    client = await establish_connection(
                        BleakClientWithServiceCache,
                        device,
                        self._name,
                        max_attempts=CONNECT_ATTEMPTS,
                        ble_device_callback=lambda: self._lookup() or device,
                    )
            except (BleakError, TimeoutError, OSError) as err:
                last_error = err
                _LOGGER.debug("Connection to %s failed after %.1f s: %s", self._name, time.monotonic() - started, _describe(err))
                break
            _LOGGER.debug("Connected to %s in %.1f s", self._name, time.monotonic() - started)
            missing = [uuid for uuid in REQUIRED_CHARACTERISTICS if client.services.get_characteristic(uuid) is None]
            if not missing:
                return client
            # Incomplete service discovery (stale BlueZ cache or slow radiator): drop the cache and retry
            last_error = IrsapError(f"GATT services incomplete after connect (missing {', '.join(missing)})")
            _LOGGER.debug("Services of %s incomplete (missing %s), clearing the cache and retrying", self._name, missing)
            try:
                await client.clear_cache()
            except (BleakError, AttributeError, NotImplementedError) as err:
                _LOGGER.debug("clear_cache failed: %s", _describe(err))
            await self._async_disconnect(client)
        raise IrsapError(
            f"Cannot connect to {self._name}: {_describe(last_error) if last_error else 'device not in range'}"
        ) from last_error

    @staticmethod
    def _char(client: BleakClient, uuid: str):
        char = client.services.get_characteristic(uuid)
        if char is None:
            raise IrsapError(f"Characteristic {uuid} not found: is this an IRSAP radiator?")
        return char

    async def async_read_state(self) -> RadiatorState:
        """Request and read the full radiator state."""
        async with self._lock:
            client = await self._async_connect()
            try:
                async with asyncio.timeout(OPERATION_TIMEOUT):
                    announce = self._char(client, UUID_ANNOUNCE)
                    for packet in build_status_requests():
                        await client.write_gatt_char(announce, packet, response=True)
                        await asyncio.sleep(0.1)
                    await asyncio.sleep(0.5)
                    header = bytes(await client.read_gatt_char(self._char(client, UUID_STATUS_HEADER)))
                    total = declared_length(header)
                    data_char = self._char(client, UUID_STATUS_DATA)
                    raw = b""
                    for _ in range(10):  # each read returns the next chunk
                        raw += bytes(await client.read_gatt_char(data_char))
                        if len(raw) >= total:
                            break
            except (BleakError, TimeoutError) as err:
                await self._async_clear_cache(client)
                raise IrsapError(f"Reading {self._name} failed: {_describe(err)}") from err
            finally:
                await self._async_disconnect(client)
        state = parse_state(raw)
        if state is None:
            raise IrsapError(f"Unrecognised state data from {self._name} ({len(raw)} bytes)")
        return state

    async def async_send(self, announce: bytes, blob: bytes) -> None:
        """Write a command (announce, then configuration table)."""
        async with self._lock:
            client = await self._async_connect()
            try:
                async with asyncio.timeout(OPERATION_TIMEOUT):
                    await client.write_gatt_char(self._char(client, UUID_ANNOUNCE), announce, response=True)
                    await asyncio.sleep(0.5)
                    await client.write_gatt_char(self._char(client, UUID_CONFIG), blob, response=True)
            except (BleakError, TimeoutError) as err:
                await self._async_clear_cache(client)
                raise IrsapError(f"Sending the command to {self._name} failed: {_describe(err)}") from err
            finally:
                await self._async_disconnect(client)

    async def _async_clear_cache(self, client: BleakClient) -> None:
        """After a failed read or write drop the cached GATT services, so a stale handle (GATT error 133) cannot repeat."""
        try:
            await client.clear_cache()
        except (BleakError, AttributeError, NotImplementedError) as err:
            _LOGGER.debug("clear_cache for %s failed: %s", self._name, _describe(err))

    async def _async_disconnect(self, client: BleakClient) -> None:
        try:
            await client.disconnect()
        except (BleakError, TimeoutError) as err:
            _LOGGER.debug("Disconnect from %s failed: %s", self._name, _describe(err))
        await asyncio.sleep(1)  # let the adapter settle before the next radiator connects
