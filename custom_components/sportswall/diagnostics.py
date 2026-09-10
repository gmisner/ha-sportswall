"""Diagnostics for a Sports Wall config entry."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .runtime import SportswallRuntime
from .tv import cast_source_name


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    runtime: SportswallRuntime | None = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if runtime is None:
        return {"error": "runtime_not_loaded"}

    power = hass.states.get(runtime.tv_power) if runtime.tv_power else None
    player = hass.states.get(runtime.tv_player) if runtime.tv_player else None
    return {
        "leagues": runtime.leagues,
        "scope": runtime.scope,
        "units": runtime.units,
        "theme": runtime.board_style,
        "display_mode": runtime.display_mode,
        "refresh_seconds": runtime.refresh_seconds,
        "game_count": len(runtime.games),
        "live": runtime.live,
        "status": runtime.status,
        "tv_enabled": runtime.tv_enabled,
        "tv_power": runtime.tv_power,
        "tv_player": runtime.tv_player,
        "tv_on": runtime._tv_is_on(),
        "tv_source": runtime._tv_source(),
        "tv_source_list": (power.attributes.get("source_list") if power else None),
        "tv_cast_source": (
            cast_source_name(power.attributes.get("source_list")) if power else None
        ),
        "player_state": player.state if player else None,
        "player_app": (str(player.attributes.get("app_name") or "") if player else None),
        "showing_board": runtime._tv_showing_board(),
        "live_failed": runtime._live_failed,
        "last_cast_reason": runtime.last_cast_reason,
        "last_cast_error": runtime.last_cast_error,
        "last_error": runtime.last_error,
        "power_state": power.state if power else None,
    }
