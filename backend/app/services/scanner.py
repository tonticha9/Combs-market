"""
Scanner ya siku - inachukua mechi zote za tennis za tarehe fulani,
inazichanganya na odds, na kutafuta vikundi vyenye faida (surebets).
"""

from typing import List
from datetime import date

from app.services import allsports_client as api
from app.services.arbitrage_engine import MatchOdds, find_profitable_groups, ComboGroupResult


async def scan_tennis_day(scan_date: str, total_stake: float = 1000.0) -> List[ComboGroupResult]:
    """
    scan_date: 'yyyy-mm-dd'
    Inarudisha vikundi VYENYE FAIDA TU (surebets), tayari na stakes zilizohesabiwa.
    """
    fixtures = await api.fetch_fixtures(scan_date, scan_date)
    if not fixtures:
        return []

    odds_by_match = await api.fetch_odds_by_date(scan_date, scan_date)

    matches_with_odds: List[MatchOdds] = []
    for fixture in fixtures:
        event_key = str(fixture["event_key"])
        odds_for_event = odds_by_match.get(event_key)
        if not odds_for_event:
            continue
        match_odds = api.extract_best_home_away_odds(fixture, odds_for_event)
        if match_odds:
            matches_with_odds.append(match_odds)

    if len(matches_with_odds) < 4:
        return []

    profitable_groups = find_profitable_groups(matches_with_odds, group_size=4, total_stake=total_stake)
    return profitable_groups
