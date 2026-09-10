"""Today's-games sensor."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .runtime import SportswallRuntime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: SportswallRuntime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SportswallGamesSensor(runtime)])


class SportswallGamesSensor(SensorEntity):
    """Count of games currently on the Sports Wall board."""

    _attr_name = "Sportswall Games"
    _attr_icon = "mdi:scoreboard"
    _attr_should_poll = False

    def __init__(self, runtime: SportswallRuntime) -> None:
        self._runtime = runtime
        self._attr_suggested_object_id = "sportswall_games"
        self._attr_unique_id = f"{runtime.entry.entry_id}_games"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, runtime.entry.entry_id)},
            name=runtime.entry.title,
            manufacturer="Sports Wall",
        )
        self._unsub: Any = None

    async def async_added_to_hass(self) -> None:
        self._unsub = self._runtime.async_add_listener(self._handle_update)
        self._handle_update()

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

    @callback
    def _handle_update(self) -> None:
        self._attr_native_value = len(self._runtime.games)
        self.schedule_update_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "status": self._runtime.status,
            "live": self._runtime.live,
            "leagues": self._runtime.leagues,
            "scope": self._runtime.scope,
            "units": self._runtime.units,
            "theme": self._runtime.board_style,
            "display_mode": self._runtime.display_mode,
            "time_format": self._runtime.time_format,
            "show_logos": self._runtime.show_logos,
            "refresh_seconds": self._runtime.refresh_seconds,
            "games": [game.as_dict(self._runtime.units) for game in self._runtime.games],
            "board": self._runtime.board,
            "last_error": self._runtime.last_error,
        }
