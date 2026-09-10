"""Render a 4K Sports Wall PNG for Chromecast Default Media Receiver."""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .board import build_board
from .const import DEFAULT_THEME, STYLE_ARENA, STYLE_BROADCAST, STYLE_DAYLIGHT, STYLE_NIGHT, UNIT_IMPERIAL
from .games import Game

FONT_DIR = Path(__file__).parent / "fonts"
CANVAS = (3840, 2160)
USER_AGENT = "SportsWall/1.0 (+https://github.com/gmisner/ha-sportswall)"

PALETTES = {
    STYLE_ARENA: {
        "bg": (7, 10, 18),
        "bg2": (12, 18, 32),
        "header": (10, 14, 26),
        "card": (18, 26, 44),
        "card_live": (24, 36, 62),
        "ink": (246, 248, 252),
        "muted": (148, 162, 188),
        "accent": (255, 196, 72),
        "live": (255, 70, 82),
        "line": (40, 54, 82),
        "chip": (28, 40, 64),
    },
    STYLE_BROADCAST: {
        "bg": (8, 8, 10),
        "bg2": (16, 16, 18),
        "header": (12, 12, 14),
        "card": (22, 22, 26),
        "card_live": (32, 22, 24),
        "ink": (250, 250, 250),
        "muted": (168, 168, 176),
        "accent": (255, 214, 10),
        "live": (230, 28, 40),
        "line": (48, 48, 54),
        "chip": (36, 36, 40),
    },
    STYLE_NIGHT: {
        "bg": (4, 6, 10),
        "bg2": (8, 10, 16),
        "header": (6, 8, 14),
        "card": (12, 16, 24),
        "card_live": (16, 22, 34),
        "ink": (168, 180, 200),
        "muted": (88, 102, 124),
        "accent": (140, 170, 120),
        "live": (180, 70, 70),
        "line": (28, 36, 48),
        "chip": (18, 24, 34),
    },
    STYLE_DAYLIGHT: {
        "bg": (232, 236, 242),
        "bg2": (244, 246, 250),
        "header": (248, 250, 252),
        "card": (255, 255, 255),
        "card_live": (255, 248, 240),
        "ink": (18, 24, 36),
        "muted": (90, 102, 122),
        "accent": (196, 90, 28),
        "live": (196, 36, 42),
        "line": (214, 220, 230),
        "chip": (236, 240, 246),
    },
}

_LOGO_CACHE: dict[str, Image.Image | None] = {}
_FONT_CACHE: dict[tuple[str, int], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}


def _palette(style: str) -> dict[str, Any]:
    return PALETTES.get(style, PALETTES[STYLE_ARENA])


def _font(size: int, weight: str = "Bold") -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    key = (weight, size)
    cached = _FONT_CACHE.get(key)
    if cached is not None:
        return cached
    path = FONT_DIR / f"Roboto-{weight}.ttf"
    try:
        font = ImageFont.truetype(str(path), size)
    except OSError:
        try:
            font = ImageFont.truetype(str(FONT_DIR / "Roboto-Bold.ttf"), size)
        except OSError:
            font = ImageFont.load_default()
    _FONT_CACHE[key] = font
    return font


def _hex_rgb(value: str, fallback: tuple[int, int, int] = (26, 40, 72)) -> tuple[int, int, int]:
    raw = str(value or "").strip().lstrip("#")
    if len(raw) != 6:
        return fallback
    try:
        return (int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16))
    except ValueError:
        return fallback


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _fit(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    if not text:
        return ""
    if _text_size(draw, text, font)[0] <= max_width:
        return text
    trimmed = text
    while trimmed and _text_size(draw, trimmed + "…", font)[0] > max_width:
        trimmed = trimmed[:-1]
    return (trimmed + "…") if trimmed else ""


def _rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int, fill: tuple[int, int, int]) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def _shadow(
    image: Image.Image,
    box: tuple[int, int, int, int],
    radius: int,
    night: bool = True,
) -> None:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    color = (0, 0, 0, 90) if night else (20, 30, 50, 40)
    draw.rounded_rectangle(
        (box[0] + 10, box[1] + 16, box[2] + 10, box[3] + 16),
        radius=radius,
        fill=color,
    )
    blurred = overlay.filter(ImageFilter.GaussianBlur(18))
    image.alpha_composite(blurred)


def _load_logo(url: str, dest: Path | None) -> Image.Image | None:
    if not url:
        return None
    if url in _LOGO_CACHE:
        return _LOGO_CACHE[url]
    if dest is not None and dest.is_file():
        try:
            logo = Image.open(dest).convert("RGBA")
        except OSError:
            logo = None
        else:
            _LOGO_CACHE[url] = logo
            return logo
    try:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=6) as response:
            logo = Image.open(BytesIO(response.read())).convert("RGBA")
    except OSError:
        _LOGO_CACHE[url] = None
        return None
    if dest is not None:
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            logo.save(dest, format="PNG")
        except OSError:
            pass
    _LOGO_CACHE[url] = logo
    return logo


def _team_mark(
    abbreviation: str,
    color: str,
    size: int,
    logo_url: str,
    show_logos: bool,
    logo_dir: Path | None,
) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    fill = _hex_rgb(color)
    draw.ellipse((0, 0, size - 1, size - 1), fill=(*fill, 255))
    if show_logos and logo_url:
        dest = None
        if logo_dir is not None:
            safe = "".join(ch for ch in abbreviation.lower() if ch.isalnum())
            dest = logo_dir / f"{safe}.png"
        logo = _load_logo(logo_url, dest)
        if logo is not None:
            inner = int(size * 0.78)
            logo = logo.resize((inner, inner), Image.Resampling.LANCZOS)
            x = (size - inner) // 2
            image.alpha_composite(logo, (x, x))
            return image
    font = _font(max(18, int(size * 0.32)))
    label = (abbreviation or "?")[:4]
    tw, th = _text_size(draw, label, font)
    draw.text(((size - tw) / 2, (size - th) / 2 - 2), label, font=font, fill=(255, 255, 255, 255))
    return image


def _brand_mark(size: int, accent: tuple[int, int, int], ink: tuple[int, int, int]) -> Image.Image:
    """Simple stadium scoreboard glyph for the header."""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    width = max(4, size // 14)
    draw.rounded_rectangle(
        (2, int(size * 0.22), size - 3, int(size * 0.92)),
        radius=size // 8,
        outline=(*ink, 255),
        width=width,
    )
    draw.rectangle(
        (int(size * 0.16), int(size * 0.08), int(size * 0.84), int(size * 0.34)),
        fill=(*accent, 255),
    )
    draw.rectangle(
        (int(size * 0.28), int(size * 0.46), int(size * 0.72), int(size * 0.78)),
        fill=(*accent, 255),
    )
    return image


def _weather_icon(kind: str, size: int, ink: tuple[int, int, int], accent: tuple[int, int, int]) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    cx = cy = size / 2
    if kind in {"sun", "cloud_sun"}:
        draw.ellipse((size * 0.22, size * 0.22, size * 0.78, size * 0.78), fill=(*accent, 255))
        if kind == "cloud_sun":
            draw.ellipse((size * 0.08, size * 0.46, size * 0.72, size * 0.92), fill=(*ink, 220))
    elif kind == "cloud":
        draw.ellipse((size * 0.12, size * 0.38, size * 0.88, size * 0.88), fill=(*ink, 220))
        draw.ellipse((size * 0.28, size * 0.18, size * 0.78, size * 0.68), fill=(*ink, 220))
    elif kind in {"rain", "storm", "sleet"}:
        draw.ellipse((size * 0.12, size * 0.18, size * 0.88, size * 0.62), fill=(*ink, 220))
        for i, x in enumerate((0.28, 0.48, 0.68)):
            x0 = size * x
            draw.line((x0, size * 0.68, x0 - size * 0.08, size * 0.92), fill=(120, 170, 255, 255), width=max(3, size // 14))
        if kind == "storm":
            draw.polygon(
                [
                    (cx + size * 0.04, size * 0.42),
                    (cx - size * 0.08, size * 0.68),
                    (cx + size * 0.02, size * 0.68),
                    (cx - size * 0.06, size * 0.92),
                    (cx + size * 0.16, size * 0.58),
                    (cx + size * 0.04, size * 0.58),
                ],
                fill=(*accent, 255),
            )
    elif kind == "snow":
        draw.ellipse((size * 0.16, size * 0.16, size * 0.84, size * 0.58), fill=(*ink, 220))
        for x, y in ((0.3, 0.72), (0.5, 0.82), (0.7, 0.72)):
            r = size * 0.06
            draw.ellipse((size * x - r, size * y - r, size * x + r, size * y + r), fill=(230, 240, 255, 255))
    elif kind == "fog":
        for i, y in enumerate((0.32, 0.5, 0.68)):
            draw.rounded_rectangle(
                (size * 0.12, size * y, size * 0.88, size * y + size * 0.1),
                radius=size // 10,
                fill=(*ink, 180 - i * 30),
            )
    else:
        draw.ellipse((size * 0.28, size * 0.28, size * 0.72, size * 0.72), outline=(*ink, 200), width=max(3, size // 16))
    return image


def render_board_png(
    games: list[Game],
    now: datetime | None = None,
    units: str = UNIT_IMPERIAL,
    style: str = DEFAULT_THEME,
    time_format: str = "follow_units",
    show_logos: bool = True,
    leagues: list[str] | None = None,
    next_game: Game | None = None,
    logo_dir: Path | None = None,
) -> bytes:
    now = now or datetime.now(UTC)
    colors = _palette(style)
    board = build_board(
        games,
        now,
        units=units,
        theme=style,
        time_format=time_format,
        show_logos=show_logos,
        leagues=leagues,
        next_game=next_game,
    )
    image = Image.new("RGBA", CANVAS, (*colors["bg"], 255))
    _paint_backdrop(image, colors)
    draw = ImageDraw.Draw(image)
    _draw_header(image, draw, board, colors)
    if board["empty"]:
        _draw_empty(image, draw, board, colors, style, logo_dir)
    else:
        _draw_featured(image, draw, board["featured"] or board["games"][0], colors, style, logo_dir)
        _draw_ticker(image, draw, board, colors, style, logo_dir)
    buf = BytesIO()
    image.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def write_board_png(
    path: Path,
    games: list[Game],
    now: datetime | None = None,
    units: str = UNIT_IMPERIAL,
    style: str = DEFAULT_THEME,
    time_format: str = "follow_units",
    show_logos: bool = True,
    leagues: list[str] | None = None,
    next_game: Game | None = None,
    logo_dir: Path | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        render_board_png(
            games,
            now=now,
            units=units,
            style=style,
            time_format=time_format,
            show_logos=show_logos,
            leagues=leagues,
            next_game=next_game,
            logo_dir=logo_dir,
        )
    )


def _paint_backdrop(image: Image.Image, colors: dict[str, Any]) -> None:
    overlay = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.ellipse((-400, -500, 1400, 900), fill=(*colors["bg2"], 255))
    draw.ellipse((2400, 900, 4300, 2500), fill=(*colors["bg2"], 180))
    image.alpha_composite(overlay.filter(ImageFilter.GaussianBlur(8)))


def _draw_header(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    board: dict[str, Any],
    colors: dict[str, Any],
) -> None:
    _rounded(draw, (0, 0, CANVAS[0], 188), 0, colors["header"])
    draw.rectangle((0, 188, CANVAS[0], 196), fill=colors["accent"])
    mark = _brand_mark(88, colors["accent"], colors["ink"])
    image.alpha_composite(mark, (64, 50))
    title_font = _font(80)
    draw.text((176, 32), board["title"].upper(), font=title_font, fill=colors["ink"])
    sub_font = _font(40, "Medium")
    draw.text((176, 118), board["subtitle"], font=sub_font, fill=colors["muted"])
    clock_font = _font(96)
    date_font = _font(36, "Medium")
    clock = board["clock"]
    cw, _ = _text_size(draw, clock, clock_font)
    draw.text((CANVAS[0] - 72 - cw, 24), clock, font=clock_font, fill=colors["ink"])
    dw, _ = _text_size(draw, board["date"], date_font)
    draw.text((CANVAS[0] - 72 - dw, 124), board["date"], font=date_font, fill=colors["muted"])


TICKER_H = 320
FEATURE_BOTTOM = CANVAS[1] - TICKER_H


def _draw_empty(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    board: dict[str, Any],
    colors: dict[str, Any],
    style: str,
    logo_dir: Path | None,
) -> None:
    nxt = board.get("next_game")
    if nxt:
        _draw_featured(image, draw, nxt, colors, style, logo_dir)
        _draw_ticker(image, draw, board, colors, style, logo_dir)
        return
    box = (200, 280, CANVAS[0] - 200, FEATURE_BOTTOM - 28)
    _shadow(image, box, 40, style != STYLE_DAYLIGHT)
    _rounded(draw, box, 40, colors["card"])
    title_font = _font(72)
    body_font = _font(36, "Medium")
    draw.text((400, 520), "No games on the board", font=title_font, fill=colors["ink"])
    draw.text((400, 640), board["subtitle"], font=body_font, fill=colors["muted"])
    draw.text((400, 760), "Check back when the next slate starts.", font=body_font, fill=colors["muted"])
    _draw_ticker(image, draw, board, colors, style, logo_dir)


def _status_words(game: dict[str, Any]) -> str:
    kind = game.get("status_kind")
    if kind == "live":
        return "LIVE"
    if kind == "final":
        return "FINAL"
    return "UPCOMING"


def _draw_featured(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    game: dict[str, Any],
    colors: dict[str, Any],
    style: str,
    logo_dir: Path | None,
) -> None:
    top, bottom = 220, FEATURE_BOTTOM - 20
    box = (48, top, CANVAS[0] - 48, bottom)
    _shadow(image, box, 36, style != STYLE_DAYLIGHT)
    fill = colors["card_live"] if game.get("status_kind") == "live" else colors["card"]
    _rounded(draw, box, 36, fill)

    kind = game.get("status_kind")
    pill = _status_words(game)
    pill_font = _font(40)
    pw, ph = _text_size(draw, pill, pill_font)
    cx = CANVAS[0] // 2
    pill_fill = colors["live"] if kind == "live" else colors["chip"]
    pill_ink = (255, 255, 255) if kind == "live" else colors["ink"]
    _rounded(draw, (cx - pw // 2 - 40, top + 24, cx + pw // 2 + 40, top + 24 + ph + 24), 28, pill_fill)
    draw.text((cx - pw // 2, top + 34), pill, font=pill_font, fill=pill_ink)

    league = " · ".join(bit for bit in (game.get("league_label"), game.get("network")) if bit)
    league_font = _font(36, "Medium")
    lw, _ = _text_size(draw, league, league_font)
    draw.text((cx - lw // 2, top + 104), league, font=league_font, fill=colors["muted"])

    panel_w = 1320
    panel_top = top + 164
    panel_bottom = bottom - 188
    _draw_team_panel(
        image,
        draw,
        game.get("away") or {},
        game.get("away_score") or "—",
        (88, panel_top, 88 + panel_w, panel_bottom),
        colors,
        game.get("show_logos", True),
        logo_dir,
        dim=bool(game.get("is_final") and not (game.get("away") or {}).get("winner")),
        align="left",
    )
    _draw_team_panel(
        image,
        draw,
        game.get("home") or {},
        game.get("home_score") or "—",
        (CANVAS[0] - 88 - panel_w, panel_top, CANVAS[0] - 88, panel_bottom),
        colors,
        game.get("show_logos", True),
        logo_dir,
        dim=bool(game.get("is_final") and not (game.get("home") or {}).get("winner")),
        align="right",
    )

    vs = "@" if kind == "pre" else "VS"
    vs_font = _font(56)
    vw, vh = _text_size(draw, vs, vs_font)
    mid_y = (panel_top + panel_bottom) // 2
    vs_box = (cx - 78, mid_y - 78, cx + 78, mid_y + 78)
    _rounded(draw, vs_box, 78, colors["bg"])
    draw.text((cx - vw // 2, mid_y - vh // 2), vs, font=vs_font, fill=colors["muted"])

    detail = game.get("status_meta") or game.get("status_label") or ""
    detail_font = _font(44, "Medium")
    dw, _ = _text_size(draw, str(detail), detail_font)
    draw.text((cx - dw // 2, panel_bottom + 12), str(detail), font=detail_font, fill=colors["ink"])

    facts_y = bottom - 148
    draw.line((120, facts_y, CANVAS[0] - 120, facts_y), fill=colors["line"], width=2)
    _draw_fact_chips(image, draw, game, (120, facts_y + 16, CANVAS[0] - 120, bottom - 20), colors)


def _draw_team_panel(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    team: dict[str, Any],
    score: str,
    box: tuple[int, int, int, int],
    colors: dict[str, Any],
    show_logos: bool,
    logo_dir: Path | None,
    dim: bool,
    align: str,
) -> None:
    x0, y0, x1, y1 = box
    stripe = _hex_rgb(team.get("color") or "")
    _rounded(draw, box, 32, colors["bg2"])
    if align == "left":
        draw.rectangle((x0, y0 + 24, x0 + 16, y1 - 24), fill=stripe)
    else:
        draw.rectangle((x1 - 16, y0 + 24, x1, y1 - 24), fill=stripe)
    ink = colors["muted"] if dim else colors["ink"]
    mark = _team_mark(
        str(team.get("abbreviation") or "?"),
        str(team.get("color") or ""),
        200,
        str(team.get("logo_url") or ""),
        show_logos,
        logo_dir,
    )
    city_font = _font(44, "Medium")
    name_font = _font(76)
    abbr_font = _font(88)
    score_font = _font(176)
    city = str(team.get("city_label") or team.get("location") or "")
    name = str(team.get("nickname") or team.get("name") or "")
    abbr = str(team.get("abbreviation") or "")
    inner_w = x1 - x0 - 96
    city_fit = _fit(draw, city, city_font, inner_w)
    name_fit = _fit(draw, name, name_font, inner_w)
    if align == "left":
        image.alpha_composite(mark, (x0 + 48, y0 + 32))
        draw.text((x0 + 48, y0 + 248), city_fit, font=city_font, fill=colors["muted"])
        draw.text((x0 + 48, y0 + 304), name_fit, font=name_font, fill=ink)
        draw.text((x0 + 48, y0 + 400), abbr, font=abbr_font, fill=ink)
        draw.text((x0 + 48, y0 + 500), score, font=score_font, fill=ink)
    else:
        image.alpha_composite(mark, (x1 - 48 - 200, y0 + 32))
        cw, _ = _text_size(draw, city_fit, city_font)
        nw, _ = _text_size(draw, name_fit, name_font)
        aw, _ = _text_size(draw, abbr, abbr_font)
        sw, _ = _text_size(draw, score, score_font)
        draw.text((x1 - 48 - cw, y0 + 248), city_fit, font=city_font, fill=colors["muted"])
        draw.text((x1 - 48 - nw, y0 + 304), name_fit, font=name_font, fill=ink)
        draw.text((x1 - 48 - aw, y0 + 400), abbr, font=abbr_font, fill=ink)
        draw.text((x1 - 48 - sw, y0 + 500), score, font=score_font, fill=ink)


def _draw_fact_chips(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    game: dict[str, Any],
    box: tuple[int, int, int, int],
    colors: dict[str, Any],
) -> None:
    x0, y0, x1, _y1 = box
    font = _font(36, "Medium")
    chips = []
    if game.get("network"):
        chips.append(("TV", str(game["network"])))
    weather = game.get("weather_line") or ("Indoor" if game.get("indoor") else "")
    if weather:
        chips.append(("WX", weather))
    venue = game.get("venue") or game.get("venue_label") or ""
    if venue:
        chips.append(("VENUE", venue))
    travel = " · ".join(bit for bit in (game.get("travel_label"), game.get("cities_route")) if bit)
    if travel:
        chips.append(("TRAVEL", travel))
    if not chips:
        return
    gap = 24
    x = x0
    max_w = x1 - x0
    each = max(280, (max_w - gap * (len(chips) - 1)) // max(len(chips), 1))
    for label, value in chips:
        if x + each > x1 + 8:
            break
        _rounded(draw, (x, y0, x + each, y0 + 120), 22, colors["chip"])
        draw.text((x + 24, y0 + 12), label, font=_font(24, "Medium"), fill=colors["accent"])
        draw.text((x + 24, y0 + 52), _fit(draw, value, font, each - 48), font=font, fill=colors["ink"])
        if label == "WX":
            icon = _weather_icon(str(game.get("weather_icon") or "unknown"), 48, colors["muted"], colors["accent"])
            image.alpha_composite(icon, (x + each - 68, y0 + 12))
        x += each + gap


def _draw_ticker(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    board: dict[str, Any],
    colors: dict[str, Any],
    style: str,
    logo_dir: Path | None,
) -> None:
    y0 = FEATURE_BOTTOM
    _rounded(draw, (0, y0, CANVAS[0], CANVAS[1]), 0, colors["header"])
    draw.rectangle((0, y0, CANVAS[0], y0 + 6), fill=colors["accent"])
    label_w = 260
    draw.rectangle((0, y0, label_w, CANVAS[1]), fill=colors["chip"])
    leagues = board.get("leagues") or []
    label = str(leagues[0] if len(leagues) == 1 else "SPORTS")
    lab_font = _font(42)
    lw, lh = _text_size(draw, label, lab_font)
    draw.text(((label_w - lw) // 2, y0 + (TICKER_H - lh) // 2), label, font=lab_font, fill=colors["ink"])
    games = board.get("games") or []
    if not games:
        empty = "Waiting for the next slate"
        ew, eh = _text_size(draw, empty, _font(40, "Medium"))
        draw.text((label_w + 40, y0 + (TICKER_H - eh) // 2), empty, font=_font(40, "Medium"), fill=colors["muted"])
        return
    chip_gap = 18
    available = CANVAS[0] - label_w - 40
    count = max(1, min(len(games), 7))
    chip_w = (available - chip_gap * (count - 1)) // count
    x = label_w + 20
    for game in games[:count]:
        _draw_ticker_chip(image, draw, game, (x, y0 + 28, x + chip_w, CANVAS[1] - 28), colors, logo_dir)
        x += chip_w + chip_gap


def _draw_ticker_chip(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    game: dict[str, Any],
    box: tuple[int, int, int, int],
    colors: dict[str, Any],
    logo_dir: Path | None,
) -> None:
    x0, y0, x1, y1 = box
    fill = colors["card_live"] if game.get("status_kind") == "live" else colors["card"]
    _rounded(draw, box, 22, fill)
    away = game.get("away") or {}
    home = game.get("home") or {}
    show = game.get("show_logos", True)
    mark_a = _team_mark(str(away.get("abbreviation") or "?"), str(away.get("color") or ""), 80, str(away.get("logo_url") or ""), show, logo_dir)
    mark_h = _team_mark(str(home.get("abbreviation") or "?"), str(home.get("color") or ""), 80, str(home.get("logo_url") or ""), show, logo_dir)
    cy = y0 + 28
    image.alpha_composite(mark_a, (x0 + 16, cy))
    image.alpha_composite(mark_h, (x1 - 96, cy))
    abbr_font = _font(36)
    score_font = _font(48)
    a = str(away.get("abbreviation") or "")
    h = str(home.get("abbreviation") or "")
    if game.get("status_kind") == "pre":
        mid = "@"
        mid_font = _font(36, "Medium")
    else:
        mid = f"{game.get('away_score')} - {game.get('home_score')}"
        mid_font = score_font
    aw, _ = _text_size(draw, a, abbr_font)
    hw, _ = _text_size(draw, h, abbr_font)
    mw, _ = _text_size(draw, mid, mid_font)
    draw.text((x0 + 108, cy + 18), a, font=abbr_font, fill=colors["ink"])
    draw.text(((x0 + x1 - mw) // 2, cy + 10), mid, font=mid_font, fill=colors["ink"])
    draw.text((x1 - 108 - hw, cy + 18), h, font=abbr_font, fill=colors["ink"])
    status = game.get("status_label") or ""
    if game.get("status_kind") == "live":
        status = game.get("status_meta") or "LIVE"
    st_font = _font(28, "Medium")
    sw, sh = _text_size(draw, str(status), st_font)
    pill_fill = colors["live"] if game.get("status_kind") == "live" else colors["chip"]
    pill_ink = (255, 255, 255) if game.get("status_kind") == "live" else colors["muted"]
    _rounded(draw, ((x0 + x1 - sw) // 2 - 18, y1 - sh - 24, (x0 + x1 + sw) // 2 + 18, y1 - 14), 16, pill_fill)
    draw.text(((x0 + x1 - sw) // 2, y1 - sh - 18), str(status), font=st_font, fill=pill_ink)
