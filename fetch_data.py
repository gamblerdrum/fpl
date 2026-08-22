#!/usr/bin/env python3
"""
Pull a classic league's gameweek picks from the FPL API into data.json.

Usage:
    python3 fetch_data.py [league_id] [gameweek]

Gameweek defaults to the current one. Writes data.json next to the page.
Picks for other managers are only public after the gameweek deadline.
"""

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

LEAGUE_ID = 7549      # League Of Legends
MY_ENTRY_ID = 300557  # highlighted on the page

BASE = "https://fantasy.premierleague.com/api"
UA = "Mozilla/5.0 (compatible; league-summary-script)"
PAUSE = 0.4  # be polite between manager requests


def get(path, attempts=3):
    url = f"{BASE}{path}"
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if i == attempts - 1:
                raise
        except Exception:
            if i == attempts - 1:
                raise
        time.sleep(2 ** i)
    return None


def main():
    league_id = int(sys.argv[1]) if len(sys.argv) > 1 else LEAGUE_ID

    print("Fetching bootstrap-static...")
    boot = get("/bootstrap-static/")

    teams = {t["id"]: t["short_name"] for t in boot["teams"]}
    types = {t["id"]: t["singular_name_short"] for t in boot["element_types"]}
    players = {
        e["id"]: {
            "n": e["web_name"],
            "c": teams.get(e["team"], "?"),
            "p": types.get(e["element_type"], "?"),
        }
        for e in boot["elements"]
    }

    events = boot["events"]
    if len(sys.argv) > 2:
        gw = int(sys.argv[2])
    else:
        current = next((e for e in events if e["is_current"]), None)
        if current is None:
            current = next((e for e in events if e["is_next"]), events[0])
        gw = current["id"]
    ev = next(e for e in events if e["id"] == gw)
    print(f"Gameweek {gw} (finished={ev['finished']}, deadline={ev['deadline_time']})")

    # live points, keyed by element id
    live = get(f"/event/{gw}/live/") or {"elements": []}
    live_pts = {e["id"]: e["stats"]["total_points"] for e in live.get("elements", [])}
    any_points = any(live_pts.values())

    # league standings, paginated 50 at a time
    print(f"Fetching league {league_id} standings...")
    entries, page, league_name = [], 1, str(league_id)
    while True:
        data = get(f"/leagues-classic/{league_id}/standings/?page_standings={page}")
        if data is None:
            sys.exit(f"League {league_id} not found, or it is private.")
        league_name = data["league"]["name"]
        results = data["standings"]["results"]
        entries.extend(results)
        if not data["standings"]["has_next"]:
            break
        page += 1
        time.sleep(PAUSE)
    print(f"{league_name}: {len(entries)} managers")

    managers, skipped = [], 0
    for i, e in enumerate(entries, 1):
        picks = get(f"/entry/{e['entry']}/event/{gw}/picks/")
        if picks is None or "picks" not in picks:
            skipped += 1
            continue
        hist = picks.get("entry_history") or {}
        managers.append({
            "entry": e["entry"],
            "name": e["player_name"],
            "team": e["entry_name"],
            "rank": e["rank"],
            "total": e["total"],
            "event_total": hist.get("points", 0) - hist.get("event_transfers_cost", 0),
            "hits": hist.get("event_transfers_cost", 0),
            "chip": picks.get("active_chip"),
            "picks": [
                {
                    "n": players.get(p["element"], {}).get("n", str(p["element"])),
                    "c": players.get(p["element"], {}).get("c", "?"),
                    "p": players.get(p["element"], {}).get("p", "?"),
                    "s": 1 if p["multiplier"] > 0 else 0,
                    "m": p["multiplier"],
                    "C": bool(p["is_captain"]),
                    "V": bool(p["is_vice_captain"]),
                    "pts": live_pts.get(p["element"], 0),
                }
                for p in sorted(picks["picks"], key=lambda x: x["position"])
            ],
        })
        if i % 10 == 0:
            print(f"  {i}/{len(entries)}")
        time.sleep(PAUSE)

    if skipped:
        print(f"Skipped {skipped} managers with no picks available for GW{gw}")

    out = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "league": {"id": league_id, "name": league_name},
        "you": MY_ENTRY_ID,
        "event": {
            "id": gw,
            "name": ev["name"],
            "finished": ev["finished"],
            "started": any_points,
            "deadline": ev["deadline_time"],
        },
        "managers": managers,
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Wrote data.json: {len(managers)} managers, {len(managers) * 15} picks")


if __name__ == "__main__":
    main()
