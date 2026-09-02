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
from itertools import product, combinations
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
    Kwa kila comb, unaweka STAKE ILE ILE KAMILI (stake_per_combo),
    bila kuivunja/kuigawanya. 'Hakuna hasara' inahakikishwa kama comb yenye
    odd ya chini kabisa bado inarudisha angalau sawa na jumla ya gharama zote
    (total_invest = stake_per_combo x idadi ya combos).

    Inafanya kazi na idadi yoyote ya mechi (2, 3, 4, ...) - idadi ya combos
    ni 2^(idadi ya mechi).
    """
    if len(matches) < 2:
        raise ValueError("Kikundi lazima kiwe na angalau mechi 2.")

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
                            stake_per_combo: float = 1000.0,
                            top_candidates: int = 60,
                            max_results: int = 30) -> List[ComboGroupResult]:
    """
    Inapokea orodha ya mechi ZOTE za siku (duniani kote, tayari zina best odds),
    kisha:

    1. Inachagua mechi 'top_candidates' zenye uwezekano mkubwa zaidi wa kufaa -
       yaani zile ambazo odd ya upande 'salama zaidi' (favorite) bado ni kubwa
       kiasi (siyo favorite mkubwa mno).
    2. Kutoka kwenye mechi hizo za juu pekee, inajaribu MICHANGANYIKO MINGI
       (combinations) ya 'group_size' - lakini kwa HARAKA, kwa kuhesabu tu
       'worst case' ya kila mchanganyiko (kihesabu: comb mbaya zaidi daima ni
       ile inayochagua odd ya chini kabisa kwenye kila mechi - hakuna haja ya
       kuunda combos zote 2^group_size kuangalia hilo). Combos kamili
       zinaundwa TU kwa vikundi vilivyopita kigezo.
    3. Inarudisha vikundi vyenye faida (worst_profit >= 0) tu, vikiwa
       vimepangwa kutoka bora zaidi kwenda chini, hadi 'max_results'.
    """
    if len(all_matches) < group_size:
        return []

    def min_side_odd(m: MatchOdds) -> float:
        return min(m.best_home_odd, m.best_away_odd)

    sorted_matches = sorted(all_matches, key=min_side_odd, reverse=True)
    candidates = sorted_matches[:top_candidates]
    num_combos = 2 ** group_size

    # Hatua 1 (HARAKA): chuja kwa worst-case pekee, bila kuunda combos zote
    passing_combinations = []
    for combo_matches in combinations(candidates, group_size):
        worst_odd_product = 1.0
        for m in combo_matches:
            worst_odd_product *= min_side_odd(m)
        if worst_odd_product >= num_combos:  # sharti la 'hakuna hasara'
            passing_combinations.append((worst_odd_product, combo_matches))

    # Hatua 2: kwa vikundi vilivyopita tu, unda combos kamili 16 (au 2^n)
    # kwa maelezo kamili ya kuonyesha kwenye dashboard
    passing_combinations.sort(key=lambda x: x[0], reverse=True)
    profitable_groups = []
    for _, combo_matches in passing_combinations[:max_results]:
        result = generate_combo_group(list(combo_matches), stake_per_combo=stake_per_combo)
        if result.is_profitable:
            profitable_groups.append(result)

    profitable_groups.sort(key=lambda r: r.best_profit, reverse=True)
    return profitable_groups[:max_results]
