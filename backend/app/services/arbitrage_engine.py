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
    odds_display: str = field(init=False)

    def __post_init__(self):
        odd_product = 1.0
        for p in self.picks:
            odd_product *= p.odd
        self.combined_odd = round(odd_product, 4)
        self.implied_prob = round(1.0 / self.combined_odd, 6)
        self.odds_display = " x ".join(f"{p.odd:.2f}" for p in self.picks)


@dataclass
class ComboGroupResult:
    """Matokeo ya kikundi kimoja cha mechi 4: combos zake 16 + tathmini ya faida."""
    matches: List[MatchOdds]
    combos: List[Combo]
    stake_per_combo: float
    total_invest: float
    worst_profit: float
    best_profit: float
    is_profitable: bool          # True kama worst_profit >= 0 (hakuna hasara HATA kwenye comb mbaya zaidi)
    payouts: Dict[int, float] = field(default_factory=dict)     # combo index -> unapata (payout)
    profits: Dict[int, float] = field(default_factory=dict)     # combo index -> profit


def generate_combo_group(matches: List[MatchOdds], stake_per_combo: float = 1000.0) -> ComboGroupResult:
    """
    Kwa kila comb (kati ya 16), unaweka STAKE ILE ILE KAMILI (stake_per_combo),
    bila kuivunja/kuigawanya. 'Hakuna hasara' inahakikishwa kama comb yenye
    odd ya chini kabisa bado inarudisha angalau sawa na jumla ya gharama zote
    (total_invest = stake_per_combo x idadi ya combos).
    """
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

    num_combos = len(combos)
    total_invest = round(stake_per_combo * num_combos, 2)

    payouts = {}
    profits = {}
    for idx, c in enumerate(combos):
        payout = round(stake_per_combo * c.combined_odd, 2)
        profit = round(payout - total_invest, 2)
        payouts[idx] = payout
        profits[idx] = profit

    worst_profit = min(profits.values())
    best_profit = max(profits.values())
    is_profitable = worst_profit >= 0

    return ComboGroupResult(
        matches=matches,
        combos=combos,
        stake_per_combo=stake_per_combo,
        total_invest=total_invest,
        worst_profit=worst_profit,
        best_profit=best_profit,
        is_profitable=is_profitable,
        payouts=payouts,
        profits=profits,
    )


def find_profitable_groups(all_matches: List[MatchOdds], group_size: int = 4,
                            stake_per_combo: float = 1000.0) -> List[ComboGroupResult]:
    """
    Inapokea orodha ya mechi zote za siku (tayari zina best odds),
    inazipanga kwa vikundi vya 4-4 (bila kurudia), na kurudisha
    vikundi VYENYE FAIDA TU (worst_profit >= 0, yaani HAKUNA HASARA
    hata kwenye comb mbaya zaidi).
    """
    profitable_groups = []
    for i in range(0, len(all_matches) - group_size + 1, group_size):
        group = all_matches[i:i + group_size]
        if len(group) < group_size:
            continue
        result = generate_combo_group(group, stake_per_combo=stake_per_combo)
        if result.is_profitable:
            profitable_groups.append(result)
    return profitable_groups
