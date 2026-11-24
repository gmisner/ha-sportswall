"""Live vs idle poll timing helpers."""

from __future__ import annotations

from sportswall.const import (
    FEATURED_ENRICH_SECONDS,
    LIVE_REFRESH_SECONDS,
    POLL_TICK_SECONDS,
    poll_tick_interval,
)


def test_live_poll_tick() -> None:
    assert LIVE_REFRESH_SECONDS == 10
    assert POLL_TICK_SECONDS == 5
    assert FEATURED_ENRICH_SECONDS == 30
    assert poll_tick_interval().total_seconds() == POLL_TICK_SECONDS
    assert POLL_TICK_SECONDS < LIVE_REFRESH_SECONDS
