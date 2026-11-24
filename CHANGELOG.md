# Changelog

## 1.1.0

- Art'ifacts carousel on the HTML board (pages of four, auto-rotate) so more chips fit a TV layout
- New Art'ifacts: field surface (grass/turf), O-line average weight, and current QB with years on the club
- Weather chip: clean AccuWeather crumbs (`55°F A Shower` → `55°F · Showers`)
- Enable college football by default (existing pro-only installs migrate on upgrade)
- Replace the native featured-game dropdown with a scrollable button list (Fire TV / Silk friendly) and return from pin before PNG/Cast so picking a game does not time out
- Game picker: Live/All/Upcoming + league chips and team search
- Game picker: don’t rebuild/steal focus while the menu is open; optimistic pin; larger remote-friendly list with scores
- Game picker: single menu scroller (no nested list) so Fire TV remotes can move through every game
- Game picker: remote Up/Down always moves focus between games (not just scroll); Select/Enter pins; search sits after the list
- Game picker: sticky ▲ Up / ▼ Down / ✓ Pin controls for Fire TV (list uses a cursor, not 70 focus stops)
- Art'ifacts section uses the face crest as the strip label (no duplicate title text)
- College football: travel distance via stadium geocoding; coach tenure from ESPN coach seasons when roster omits experience
- Live possession marker on the featured hero (ESPN team id) plus down-and-distance when published
- Featured hero shows Vegas odds from ESPN pickcenter (spread, O/U, moneyline) when available
- Live games poll ESPN every ~10s (idle still uses the configured refresh interval); timer ticks every 5s so a slow PNG write cannot stretch the interval to 30s
- Publish `board.json` before the Cast PNG so the Silk board stays current
- HTML board polls `board.json` every 3s while games are live
- Pick the featured game with `select.sportswall_featured_game` or `sportswall.select_game`
- Show box-score leaders for the featured matchup
- Optional ESPN Fantasy overlay: your starters in the featured live NFL game (`espn_s2` + `SWID`)
- Fluid HTML board scaling for Fire TV / Silk and other short viewports
- Group TV / weather / venue / travel / elevation as **Art'ifacts** (extensible fact strip)
- Prototype-based SPA board: Game Focus, Multiview, Fantasy HQ, Ambient
- Themes: Midnight, Clean Light, Team Colors, Stadium (+ Arena / Broadcast)
- `select.sportswall_board_view` and `POST /api/sportswall/mode` for layout control
- Live `board.json` only — no demo fantasy or fabricated venue capacity

## 1.0.3

- Tighten the board for a 75-inch TV: larger type, less empty card space
- Recast and reload the dashboard only when scores or status change
- Slow the default poll from 45 seconds to 2 minutes

## 1.0.2

- Feature the latest live kickoff so primetime football is not buried under afternoon baseball

## 1.0.1

- Fetch ESPN with a User-Agent it does not block, so today's games load
- Keep live games on the board even when ESPN files them on the next UTC date

## 1.0.0

- Featured matchup plus ESPN-style bottom ticker (inspired by
  [Sports Ticker](https://github.com/LiquidFXX/sports-ticker))
- Scores, venue weather, club-to-club travel, home cities, and network
- NFL, NBA, MLB, NHL by default; college football and basketball optional
- Arena, broadcast, night, and daylight themes
- Chromecast image mode with the same TV takeover rules as Flight Wall
- Live Lovelace dashboard: Cast-safe markdown card on
  `sensor.sportswall_games` (featured matchup plus the rest of the slate)
