"""
Client ya AllSportsAPI (Tennis)
================================
Docs: https://allsportsapi.com/tennis-api-documentation
"""

import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.config import settings
from app.services.arbitrage_engine import MatchOdds

BASE_URL = "https://apiv2.allsportsapi.com/tennis/"

# AllSportsAPI inatoa saa kwa UTC (GMT+0). Afrika Mashariki (Tanzania, Kenya,
# Uganda) ni UTC+3 (EAT) - hakuna daylight saving, kwa hiyo tofauti ni saa
# 3 muda wote.
EAT_OFFSET_HOURS = 3


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
    """
    Inachukua odds za mechi kadhaa. AllSportsAPI Odds endpoint inaruhusu
    kuchukua odds za tarehe (from/to) badala ya kupiga call kwa kila matchId
    ili kupunguza idadi ya requests.
    """
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
    """
    Inachukua odds ya 'Home/Away' market kutoka kwenye jibu la Odds endpoint,
    na kuchagua bookmaker mwenye odd BORA (kubwa zaidi) kwa kila upande.
    Pia inabadilisha tarehe/saa kutoka UTC (asili ya API) kwenda Afrika
    Mashariki (EAT, UTC+3) kabla ya kurudisha.

    match_fixture: kipengele kimoja kutoka Fixtures endpoint
    odds_data: kipengele husika kutoka Odds endpoint (kwa event_key hiyo)
    """
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

    raw_date = match_fixture.get("event_date", "")
    raw_time = match_fixture.get("event_time", "")
    eat_date, eat_time, utc_dt = _convert_utc_to_eat(raw_date, raw_time)

    return MatchOdds(
        event_key=str(match_fixture["event_key"]),
        player_home=match_fixture["event_first_player"],
        player_away=match_fixture["event_second_player"],
        league_name=match_fixture.get("league_name", ""),
        event_date=eat_date,
        event_time=eat_time,
        best_home_odd=best_home_odd,
        best_home_bookmaker=best_home_bookmaker,
        best_away_odd=best_away_odd,
        best_away_bookmaker=best_away_bookmaker,
        kickoff_utc=utc_dt,
    )


def _convert_utc_to_eat(raw_date: str, raw_time: str):
    """
    Inapokea tarehe/saa kama zilivyotoka AllSportsAPI (UTC), inarudisha
    (tarehe_EAT, saa_EAT, datetime_UTC_halisi). Ikiwa muundo hauelewiki,
    inarudisha thamani za asili bila kubadilisha na None kwa UTC.
    """
    try:
        utc_dt = datetime.strptime(f"{raw_date} {raw_time}", "%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return raw_date, raw_time, None

    eat_dt = utc_dt + timedelta(hours=EAT_OFFSET_HOURS)
    return eat_dt.strftime("%Y-%m-%d"), eat_dt.strftime("%H:%M"), utc_dt


def _is_float(value) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False
