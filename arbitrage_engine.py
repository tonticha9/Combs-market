"""
Arbitrage Engine kwa Tennis (sports zisizo na draw)
=====================================================
Mantiki:
1. Chukua mechi 4 (kila moja ina outcomes 2: Home/Away, hakuna draw)
2. Kwa kila mechi, chukua odd BORA ya kila upande kutoka bookmakers wote
3. Tengeneza combos 16 (2^4) zinazofunika matokeo yote yanayowezekana
4. Kwa kila comb, hesabu combined odd (kuzidisha odds za picks 4)
5. Hesabu jumla ya implied probability (sum of 1/combined_odd kwa combos zote 16)
   - Kama jumla hii < 1.0 (100%) -> ARBITRAGE YA KWELI (guaranteed profit)
   - Kama jumla >= 1.0 -> HAKUNA faida ya uhakika, kikundi hiki kinaachwa
6. Gawanya stake kwa proportional ili faida iwe SAWA bila kujali comb gani itashinde
"""

from dataclasses import dataclass, field
from itertools import product
from typing import List, Dict, Optional


@dataclass
class MatchOdds:
    """Odd bora ya mechi moja, kutoka bookmaker yeyote mwenye odd nzuri zaidi."""
    event_key: str
    player_home: str
    player_away: str
    league_name: str
    event_date: str
    event_time: str
    best_home_odd: float
    best_home_bookmaker: str
    best_away_odd: float
    best_away_bookmaker: str

    def home_prob(self) -> float:
        return 1.0 / self.best_home_odd

    def away_prob(self) -> float:
        return 1.0 / self.best_away_odd


@dataclass
class ComboPick:
    """Pick moja ndani ya comb (chaguo la mechi moja: home au away)."""
    event_key: str
    match_label: str      # e.g. "N. Djokovic vs C. Alcaraz"
    selection: str         # "home" au "away"
    selected_player: str
    odd: float
    bookmaker: str


@dataclass
class Combo:
    """Comb moja - mchanganyiko wa picks 4 (moja kwa kila mechi)."""
    picks: List[ComboPick]
    combined_odd: float = field(init=False)
    implied_prob: float = field(init=False)

    def __post_init__(self):
        odd_product = 1.0
        for p in self.picks:
            odd_product *= p.odd
        self.combined_odd = round(odd_product, 4)
        self.implied_prob = round(1.0 / self.combined_odd, 6)


@dataclass
class ComboGroupResult:
    """Matokeo ya kikundi kimoja cha mechi 4: combos zake 16 + tathmini ya faida."""
    matches: List[MatchOdds]
    combos: List[Combo]
    total_implied_prob: float
    is_profitable: bool
    margin_percent: float
    stakes: Dict[int, float] = field(default_factory=dict)
    guaranteed_profit: Optional[float] = None


def generate_combo_group(matches: List[MatchOdds], total_stake: float = 1000.0) -> ComboGroupResult:
    if len(matches) != 4:
        raise ValueError("Kikundi lazima kiwe na mechi 4 hasa.")

    per_match_options = []
    for m in matches:
        label = f"{m.player_home} vs {m.player_away}"
        home_pick = ComboPick(m.event_key, label, "home", m.player_home, m.best_home_odd, m.best_home_bookmaker)
        away_pick = ComboPick(m.event_key, label, "away", m.player_away, m.best_away_odd, m.best_away_bookmaker)
        per_match_options.append([home_pick, away_pick])

    combos: List[Combo] = []
    for combination in product(*per_match_options):
        combos.append(Combo(picks=list(combination)))

    total_implied_prob = round(sum(c.implied_prob for c in combos), 6)
    is_profitable = total_implied_prob < 1.0
    margin_percent = round((1.0 - total_implied_prob) * 100, 3)

    result = ComboGroupResult(
        matches=matches,
        combos=combos,
        total_implied_prob=total_implied_prob,
        is_profitable=is_profitable,
        margin_percent=margin_percent,
    )

    if is_profitable:
        result.stakes = calculate_proportional_stakes(combos, total_stake)
        payout = total_stake / total_implied_prob
        result.guaranteed_profit = round(payout - total_stake, 2)

    return result


def calculate_proportional_stakes(combos: List[Combo], total_stake: float) -> Dict[int, float]:
    total_implied = sum(c.implied_prob for c in combos)
    stakes = {}
    for idx, c in enumerate(combos):
        stake = total_stake * (c.implied_prob / total_implied)
        stakes[idx] = round(stake, 2)
    return stakes


def find_profitable_groups(all_matches: List[MatchOdds], group_size: int = 4,
                            total_stake: float = 1000.0) -> List[ComboGroupResult]:
    profitable_groups = []
    for i in range(0, len(all_matches) - group_size + 1, group_size):
        group = all_matches[i:i + group_size]
        if len(group) < group_size:
            continue
        result = generate_combo_group(group, total_stake=total_stake)
        if result.is_profitable:
            profitable_groups.append(result)
    return profitable_groups
