"""Pick featured game and SPA board view on the Sports Wall."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import BOARD_VIEW_LABELS, DEFAULT_BOARD_VIEW, DOMAIN, FEATURED_AUTO
from .runtime import SportswallRuntime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: SportswallRuntime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            SportswallFeaturedSelect(runtime),
            SportswallBoardViewSelect(runtime),
        ]
    )


class SportswallFeaturedSelect(SelectEntity, RestoreEntity):
    """Choose Auto or a specific game for the featured matchup."""

    _attr_name = "Sportswall Featured Game"
    _attr_icon = "mdi:star-box"
    _attr_should_poll = False

    def __init__(self, runtime: SportswallRuntime) -> None:
        self._runtime = runtime
        self._attr_suggested_object_id = "sportswall_featured_game"
        self._attr_unique_id = f"{runtime.entry.entry_id}_featured_game"
        self._attr_options = ["Auto"]
        self._attr_current_option = "Auto"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, runtime.entry.entry_id)},
            name=runtime.entry.title,
            manufacturer="Sports Wall",
        )
        self._unsub: Any = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state and last.state != "Auto":
            game_id = last.attributes.get("game_id")
            if not isinstance(game_id, str) or not game_id:
                game_id = self._runtime.game_id_for_option(last.state)
            if game_id and any(game.id == game_id for game in self._runtime.games):
                await self._runtime.async_set_pinned_game(game_id)
        self._unsub = self._runtime.async_add_listener(self._handle_update)
        self._handle_update()

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

    @callback
    def _handle_update(self) -> None:
        self._attr_options = self._runtime.featured_options() or ["Auto"]
        self._attr_current_option = self._runtime.option_for_game_id(self._runtime.pinned_game_id)
        if self._attr_current_option not in self._attr_options:
            self._attr_current_option = "Auto"
        self.schedule_update_ha_state()

    async def async_select_option(self, option: str) -> None:
        game_id = self._runtime.game_id_for_option(option)
        if option.strip().lower() == FEATURED_AUTO or option == "Auto":
            game_id = None
        await self._runtime.async_set_pinned_game(game_id)
        self._handle_update()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "game_id": self._runtime.pinned_game_id,
            "mode": FEATURED_AUTO if not self._runtime.pinned_game_id else "pinned",
        }


class SportswallBoardViewSelect(SelectEntity, RestoreEntity):
    """Choose Game Focus / Multiview / Fantasy HQ / Ambient."""

    _attr_name = "Sportswall Board View"
    _attr_icon = "mdi:view-dashboard-variant"
    _attr_should_poll = False

    def __init__(self, runtime: SportswallRuntime) -> None:
        self._runtime = runtime
        self._attr_suggested_object_id = "sportswall_board_view"
        self._attr_unique_id = f"{runtime.entry.entry_id}_board_view"
        self._attr_options = runtime.board_view_options()
        self._attr_current_option = runtime.board_view_label()
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, runtime.entry.entry_id)},
            name=runtime.entry.title,
            manufacturer="Sports Wall",
        )
        self._unsub: Any = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state:
            view = self._runtime.board_view_for_label(last.state)
            if view:
                await self._runtime.async_set_board_view(view)
        self._unsub = self._runtime.async_add_listener(self._handle_update)
        self._handle_update()

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

    @callback
    def _handle_update(self) -> None:
        self._attr_options = self._runtime.board_view_options()
        self._attr_current_option = self._runtime.board_view_label()
        if self._attr_current_option not in self._attr_options:
            self._attr_current_option = BOARD_VIEW_LABELS[DEFAULT_BOARD_VIEW]
        self.schedule_update_ha_state()

    async def async_select_option(self, option: str) -> None:
        view = self._runtime.board_view_for_label(option)
        if view:
            await self._runtime.async_set_board_view(view)
        self._handle_update()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"board_view": self._runtime.board_view}
