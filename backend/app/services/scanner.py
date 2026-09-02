"""
Scanner ya siku - inachukua mechi zote za tennis za tarehe fulani,
inazichanganya na odds, na kutafuta vikundi vyenye faida (hakuna hasara
hata kwenye comb mbaya zaidi, ukiweka stake ile ile kamili kwenye kila comb).
"""

from typing import List
from datetime import datetime, timedelta, date as date_cls

from app.services import allsports_client as api
from app.services.arbitrage_engine import MatchOdds, find_profitable_groups, ComboGroupResult

# Chukua picks za mechi zenye angalau masaa haya kabla ya kuanza - hii
# inampa mtumiaji muda wa kutosha kuweka bet kabla odds hazijabadilika.
MIN_HOURS_BEFORE_KICKOFF = 10


async def scan_tennis_day(scan_date: str, stake_per_combo: float = 1000.0,
                           group_size: int = 4, risk_mode: str = "full") -> List[ComboGroupResult]:
    """
    scan_date: 'yyyy-mm-dd'
    group_size: idadi ya mechi kwa kila kikundi (2, 3, 4, ...) - idadi ya
        combos ni 2^group_size. Idadi ndogo = rahisi zaidi kupata "hakuna hasara".
    Inarudisha vikundi VYENYE FAIDA TU, tayari na payouts/profits
    zilizohesabiwa kwa stake_per_combo iliyotolewa. Mechi zenye chini ya
    masaa MIN_HOURS_BEFORE_KICKOFF kabla ya kuanza zinaachwa nje moja kwa
    moja (ili kutoa muda wa kutosha kabla odds hazijabadilika).
    """
    fixtures = await api.fetch_fixtures(scan_date, scan_date)
    if not fixtures:
        return []

    odds_by_match = await api.fetch_odds_by_date(scan_date, scan_date)

    now_utc = datetime.utcnow()
    cutoff = now_utc + timedelta(hours=MIN_HOURS_BEFORE_KICKOFF)

    matches_with_odds: List[MatchOdds] = []
    for fixture in fixtures:
        event_key = str(fixture["event_key"])
        odds_for_event = odds_by_match.get(event_key)
        if not odds_for_event:
            continue
        match_odds = api.extract_best_home_away_odds(fixture, odds_for_event)
        if not match_odds:
            continue
        # Ondoa mechi zinazoanza chini ya masaa MIN_HOURS_BEFORE_KICKOFF
        if match_odds.kickoff_utc is not None and match_odds.kickoff_utc < cutoff:
            continue
        matches_with_odds.append(match_odds)

    if len(matches_with_odds) < group_size:
        return []

    profitable_groups = find_profitable_groups(
        matches_with_odds, group_size=group_size,
        stake_per_combo=stake_per_combo, risk_mode=risk_mode,
    )
    return profitable_groups


async def scan_tennis_range(date_from: str, date_to: str, stake_per_combo: float = 1000.0,
                             group_size: int = 4, risk_mode: str = "full") -> dict:
    """
    Inachanganua siku KADHAA (mfano leo na kesho), lakini kila siku
    INACHAKATWA PEKE YAKE - mechi za siku moja HAZICHANGANYWI na za siku
    nyingine kwenye kikundi kimoja. Inarudisha dict: {scan_date: [vikundi]}.
    """
    start = datetime.strptime(date_from, "%Y-%m-%d").date()
    end = datetime.strptime(date_to, "%Y-%m-%d").date()
    if end < start:
        end = start

    results_by_date = {}
    current = start
    while current <= end:
        day_str = current.isoformat()
        groups = await scan_tennis_day(
            day_str, stake_per_combo=stake_per_combo,
            group_size=group_size, risk_mode=risk_mode,
        )
        results_by_date[day_str] = groups
        current += timedelta(days=1)

    return results_by_date
