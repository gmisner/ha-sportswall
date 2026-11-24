"""Sports Wall integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import Event, HomeAssistant, ServiceCall

from .const import (
    ATTR_AUTO,
    ATTR_GAME_ID,
    CONF_LEAGUES,
    CONF_REFRESH_SECONDS,
    DEFAULT_LEAGUES,
    DEFAULT_REFRESH_SECONDS,
    DOMAIN,
    LEAGUE_MLB,
    LEAGUE_NBA,
    LEAGUE_NFL,
    LEAGUE_NHL,
    SERVICE_RECAST,
    SERVICE_SELECT_GAME,
)
from .dashboard import async_ensure_dashboard, async_write_theme, dashboard_path_for, games_entity_for
from .http_api import async_register_http
from .runtime import SportswallRuntime
from .tv import RECAST_REASON
from .www_files import async_install_www

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SELECT, Platform.SENSOR, Platform.SWITCH]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Apply config-entry schema upgrades."""
    data = dict(entry.data)
    version = entry.version

    if version < 2:
        if data.get(CONF_REFRESH_SECONDS) in (None, 45):
            data[CONF_REFRESH_SECONDS] = DEFAULT_REFRESH_SECONDS
        version = 2
        _LOGGER.info("Migrated Sports Wall config entry to version 2")

    if version < 3:
        # Enable college football for installs still on the pro-only default.
        old_default = {LEAGUE_NFL, LEAGUE_NBA, LEAGUE_MLB, LEAGUE_NHL}
        leagues = data.get(CONF_LEAGUES)
        if leagues is None or set(leagues) == old_default:
            data[CONF_LEAGUES] = list(DEFAULT_LEAGUES)
        version = 3
        _LOGGER.info("Migrated Sports Wall config entry to version 3")

    if version != entry.version or data != dict(entry.data):
        hass.config_entries.async_update_entry(entry, data=data, version=version)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sports Wall from a config entry."""
    runtime = SportswallRuntime(hass, entry)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = runtime
    entry.runtime_data = runtime

    await runtime.async_setup()
    async_register_http(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    try:
        await _async_setup_dashboard(hass, runtime)
    except Exception:
        _LOGGER.exception("Sports Wall dashboard setup failed; TV path still loads")
    if not hass.is_running:

        async def _started(_event: Event) -> None:
            await _async_setup_dashboard(hass, runtime)

        entry.async_on_unload(
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _started)
        )
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    _async_register_services(hass)
    return True


async def _async_setup_dashboard(hass: HomeAssistant, runtime: SportswallRuntime) -> None:
    await async_install_www(hass)
    await async_write_theme(hass)
    await async_ensure_dashboard(
        hass,
        runtime.ha_theme,
        path=dashboard_path_for(hass, runtime.entry),
        games_entity=games_entity_for(hass, runtime.entry),
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    runtime: SportswallRuntime | None = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if runtime is not None:
        await runtime.async_unload()
    if not hass.data.get(DOMAIN):
        if hass.services.has_service(DOMAIN, SERVICE_RECAST):
            hass.services.async_remove(DOMAIN, SERVICE_RECAST)
        if hass.services.has_service(DOMAIN, SERVICE_SELECT_GAME):
            hass.services.async_remove(DOMAIN, SERVICE_SELECT_GAME)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def _async_register_services(hass: HomeAssistant) -> None:
    if not hass.services.has_service(DOMAIN, SERVICE_RECAST):

        async def _recast(_call: ServiceCall) -> None:
            for runtime in hass.data.get(DOMAIN, {}).values():
                if isinstance(runtime, SportswallRuntime):
                    await runtime.async_cast(reason=RECAST_REASON)

        hass.services.async_register(DOMAIN, SERVICE_RECAST, _recast)

    if not hass.services.has_service(DOMAIN, SERVICE_SELECT_GAME):

        async def _select_game(call: ServiceCall) -> None:
            auto = bool(call.data.get(ATTR_AUTO))
            game_id = None if auto else call.data.get(ATTR_GAME_ID)
            if isinstance(game_id, str):
                game_id = game_id.strip() or None
            else:
                game_id = None
            for runtime in hass.data.get(DOMAIN, {}).values():
                if isinstance(runtime, SportswallRuntime):
                    await runtime.async_set_pinned_game(None if auto else game_id)

        hass.services.async_register(DOMAIN, SERVICE_SELECT_GAME, _select_game)
