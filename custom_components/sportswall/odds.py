"""Parse ESPN summary pickcenter odds (DraftKings et al.)."""

from __future__ import annotations

from typing import Any


def parse_odds(payload: dict[str, Any] | None) -> dict[str, str] | None:
    """Return a compact odds payload for the featured hero, or None."""
    if not isinstance(payload, dict):
        return None
    rows = payload.get("pickcenter")
    if not isinstance(rows, list) or not rows:
        # Some payloads nest odds on the competition instead.
        odds = payload.get("odds")
        if isinstance(odds, list) and odds and isinstance(odds[0], dict):
            rows = odds
        else:
            return None
    chosen = _pick_row(rows)
    if chosen is None:
        return None

    provider = _clean((chosen.get("provider") or {}).get("name")) if isinstance(chosen.get("provider"), dict) else ""
    details = _clean(chosen.get("details"))
    spread_num = chosen.get("spread")
    if not details and spread_num is not None:
        try:
            details = f"{float(spread_num):+g}"
        except (TypeError, ValueError):
            details = ""

    over_under = chosen.get("overUnder")
    ou_label = ""
    if over_under is not None and over_under != "":
        try:
            ou_label = f"O/U {float(over_under):g}"
        except (TypeError, ValueError):
            ou_label = f"O/U {over_under}"

    away = chosen.get("awayTeamOdds") if isinstance(chosen.get("awayTeamOdds"), dict) else {}
    home = chosen.get("homeTeamOdds") if isinstance(chosen.get("homeTeamOdds"), dict) else {}
    away_ml = _moneyline(away.get("moneyLine"))
    home_ml = _moneyline(home.get("moneyLine"))

    parts = [bit for bit in (details, ou_label) if bit]
    ml_bits = [bit for bit in (away_ml, home_ml) if bit]
    if len(ml_bits) == 2:
        parts.append(f"ML {ml_bits[0]} / {ml_bits[1]}")
    elif ml_bits:
        parts.append(f"ML {ml_bits[0]}")

    line = " · ".join(parts).strip()
    if not line:
        return None
    return {
        "provider": provider or "Vegas",
        "spread": details,
        "over_under": ou_label,
        "away_ml": away_ml,
        "home_ml": home_ml,
        "line": line,
    }


def _pick_row(rows: list[Any]) -> dict[str, Any] | None:
    scored: list[tuple[int, dict[str, Any]]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        provider = row.get("provider") if isinstance(row.get("provider"), dict) else {}
        try:
            priority = int(provider.get("priority") or 99)
        except (TypeError, ValueError):
            priority = 99
        scored.append((priority, row))
    if not scored:
        return None
    scored.sort(key=lambda item: item[0])
    return scored[0][1]


def _moneyline(value: Any) -> str:
    try:
        if value is None or value == "":
            return ""
        number = int(float(value))
    except (TypeError, ValueError):
        return ""
    if number > 0:
        return f"+{number}"
    return str(number)


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()
