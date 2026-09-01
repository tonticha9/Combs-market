from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date

from app.db import get_db
from app.services.scanner import scan_tennis_day
from app.models import ScanRun, ComboGroup, Combo
from app.config import settings

router = APIRouter(prefix="/api/scan", tags=["scan"])


@router.post("/tennis")
async def run_tennis_scan(
    scan_date: str = Query(default=None, description="yyyy-mm-dd, default = leo"),
    total_stake: float = Query(default=None, description="Jumla ya stake kwa kikundi kimoja"),
    db: Session = Depends(get_db),
):
    scan_date = scan_date or date.today().isoformat()
    total_stake = total_stake or settings.DEFAULT_TOTAL_STAKE

    profitable_groups = await scan_tennis_day(scan_date, total_stake=total_stake)

    scan_run = ScanRun(
        sport="tennis",
        scan_date=scan_date,
        total_groups_checked=len(profitable_groups),
        profitable_groups_found=len(profitable_groups),
    )
    db.add(scan_run)
    db.flush()

    response_groups = []

    for group in profitable_groups:
        matches_json = [
            {
                "event_key": m.event_key,
                "player_home": m.player_home,
                "player_away": m.player_away,
                "league_name": m.league_name,
                "event_time": m.event_time,
                "best_home_odd": m.best_home_odd,
                "best_home_bookmaker": m.best_home_bookmaker,
                "best_away_odd": m.best_away_odd,
                "best_away_bookmaker": m.best_away_bookmaker,
            }
            for m in group.matches
        ]

        combo_group = ComboGroup(
            scan_run_id=scan_run.id,
            matches_json=matches_json,
            total_implied_prob=group.total_implied_prob,
            margin_percent=group.margin_percent,
            total_stake=total_stake,
            guaranteed_profit=group.guaranteed_profit,
        )
        db.add(combo_group)
        db.flush()

        combos_out = []
        for idx, combo in enumerate(group.combos):
            picks_json = [
                {
                    "match_label": p.match_label,
                    "selection": p.selection,
                    "selected_player": p.selected_player,
                    "odd": p.odd,
                    "bookmaker": p.bookmaker,
                }
                for p in combo.picks
            ]
            stake = group.stakes.get(idx, 0)
            payout = round(stake * combo.combined_odd, 2)

            db.add(Combo(
                group_id=combo_group.id,
                combo_index=idx,
                picks_json=picks_json,
                combined_odd=combo.combined_odd,
                stake=stake,
                potential_payout=payout,
            ))
            combos_out.append({
                "combo_index": idx,
                "picks": picks_json,
                "combined_odd": combo.combined_odd,
                "stake": stake,
                "potential_payout": payout,
            })

        response_groups.append({
            "group_id": combo_group.id,
            "matches": matches_json,
            "total_implied_prob": group.total_implied_prob,
            "margin_percent": group.margin_percent,
            "guaranteed_profit": group.guaranteed_profit,
            "total_stake": total_stake,
            "combos": combos_out,
        })

    db.commit()

    return {
        "scan_run_id": scan_run.id,
        "scan_date": scan_date,
        "profitable_groups_found": len(profitable_groups),
        "groups": response_groups,
    }


@router.get("/history")
def scan_history(limit: int = 20, db: Session = Depends(get_db)):
    runs = db.query(ScanRun).order_by(ScanRun.id.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "scan_date": r.scan_date,
            "profitable_groups_found": r.profitable_groups_found,
            "created_at": r.created_at.isoformat(),
        }
        for r in runs
    ]


@router.get("/groups/{group_id}")
def get_group(group_id: int, db: Session = Depends(get_db)):
    group = db.query(ComboGroup).filter(ComboGroup.id == group_id).first()
    if not group:
        return {"error": "Group not found"}
    combos = db.query(Combo).filter(Combo.group_id == group_id).order_by(Combo.combo_index).all()
    return {
        "group_id": group.id,
        "matches": group.matches_json,
        "total_implied_prob": group.total_implied_prob,
        "margin_percent": group.margin_percent,
        "guaranteed_profit": group.guaranteed_profit,
        "total_stake": group.total_stake,
        "combos": [
            {
                "combo_index": c.combo_index,
                "picks": c.picks_json,
                "combined_odd": c.combined_odd,
                "stake": c.stake,
                "potential_payout": c.potential_payout,
            }
            for c in combos
        ],
    }
