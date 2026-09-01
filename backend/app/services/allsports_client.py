"""
Client ya AllSportsAPI (Tennis)
================================
Docs: https://allsportsapi.com/tennis-api-documentation
"""

import httpx
from typing import List, Dict, Optional
from app.config import settings
from app.services.arbitrage_engine import MatchOdds

BASE_URL = "https://apiv2.allsportsapi.com/tennis/"


async def fetch_fixtures(date_from: str, date_to: str) -> List[dict]:
    """Inarudisha mechi za tennis kati ya tarehe mbili (yyyy-mm-dd)."""
    params = {
        "met": "Fixtures",
        "APIkey": settings.ALLSPORTS_API_KEY,
        "from": date_from,
        "to": date_to,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(BASE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    if data.get("success") != 1:
        return []
    return data.get("result", [])


async def fetch_odds_for_matches(match_ids: List[str]) -> Dict[str, dict]:
    results = {}
    async with httpx.AsyncClient(timeout=30) as client:
        for match_id in match_ids:
            params = {
                "met": "Odds",
                "APIkey": settings.ALLSPORTS_API_KEY,
                "matchId": match_id,
            }
            resp = await client.get(BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            if data.get("success") == 1:
                results.update(data.get("result", {}))
    return results


async def fetch_odds_by_date(date_from: str, date_to: str) -> Dict[str, dict]:
    """Njia ya haraka zaidi: chukua odds za mechi zote za tarehe fulani kwa call moja."""
    params = {
        "met": "Odds",
        "APIkey": settings.ALLSPORTS_API_KEY,
        "from": date_from,
        "to": date_to,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(BASE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
    if data.get("success") != 1:
        return {}
    return data.get("result", {})


def extract_best_home_away_odds(match_fixture: dict, odds_data: dict) -> Optional[MatchOdds]:
    home_away = odds_data.get("Home/Away")
    if not home_away:
        return None

    home_books = home_away.get("Home", {})
    away_books = home_away.get("Away", {})
    if not home_books or not away_books:
        return None

    best_home_bookmaker, best_home_odd = max(
        ((bk, float(v)) for bk, v in home_books.items() if _is_float(v)),
        key=lambda x: x[1], default=(None, None)
    )
    best_away_bookmaker, best_away_odd = max(
        ((bk, float(v)) for bk, v in away_books.items() if _is_float(v)),
        key=lambda x: x[1], default=(None, None)
    )

    if best_home_odd is None or best_away_odd is None:
        return None

    return MatchOdds(
        event_key=str(match_fixture["event_key"]),
        player_home=match_fixture["event_first_player"],
        player_away=match_fixture["event_second_player"],
        league_name=match_fixture.get("league_name", ""),
        event_date=match_fixture.get("event_date", ""),
        event_time=match_fixture.get("event_time", ""),
        best_home_odd=best_home_odd,
        best_home_bookmaker=best_home_bookmaker,
        best_away_odd=best_away_odd,
        best_away_bookmaker=best_away_bookmaker,
    )


def _is_float(value) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False
