from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import date

from app.db import get_db, SessionLocal
from app.services.scanner import scan_tennis_day
from app.models import ScanRun, ComboGroup, Combo
from app.config import settings

router = APIRouter(prefix="/api/scan", tags=["scan"])


def _serialize_group(group) -> dict:
    matches_json = [
        {
            "event_key": m.event_key,
            "player_home": m.player_home,
            "player_away": m.player_away,
            "league_name": m.league_name,
            "event_date": m.event_date,
            "event_time": m.event_time,
            "best_home_odd": m.best_home_odd,
            "best_home_bookmaker": m.best_home_bookmaker,
            "best_away_odd": m.best_away_odd,
            "best_away_bookmaker": m.best_away_bookmaker,
        }
        for m in group.matches
    ]
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
        combos_out.append({
            "combo_index": idx,
            "picks": picks_json,
            "combined_odd": combo.combined_odd,
            "odds_display": combo.odds_display,
            "stake": group.stake_per_combo,
            "potential_payout": group.payouts[idx],
            "profit": group.profits[idx],
        })
    return {
        "matches_json": matches_json,
        "combos_out": combos_out,
        "stake_per_combo": group.stake_per_combo,
        "total_invest": group.total_invest,
        "worst_profit": group.worst_profit,
        "best_profit": group.best_profit,
    }


async def _run_scan_background(scan_run_id: int, scan_date: str, stake_per_combo: float, group_size: int):
    """Inaendesha scan halisi 'nyuma ya pazia' - haizuii request ya HTTP isubiri."""
    db = SessionLocal()
    try:
        profitable_groups = await scan_tennis_day(scan_date, stake_per_combo=stake_per_combo, group_size=group_size)

        for group in profitable_groups:
            serialized = _serialize_group(group)
            combo_group = ComboGroup(
                scan_run_id=scan_run_id,
                matches_json=serialized["matches_json"],
                total_stake=serialized["stake_per_combo"],
                guaranteed_profit=serialized["worst_profit"],
                margin_percent=None,
                total_implied_prob=None,
            )
            db.add(combo_group)
            db.flush()

            for c in serialized["combos_out"]:
                db.add(Combo(
                    group_id=combo_group.id,
                    combo_index=c["combo_index"],
                    picks_json=c["picks"],
                    combined_odd=c["combined_odd"],
                    stake=c["stake"],
                    potential_payout=c["potential_payout"],
                ))

        scan_run = db.query(ScanRun).filter(ScanRun.id == scan_run_id).first()
        scan_run.status = "completed"
        scan_run.profitable_groups_found = len(profitable_groups)
        scan_run.total_groups_checked = len(profitable_groups)
        db.commit()
    except Exception as e:
        db.rollback()
        scan_run = db.query(ScanRun).filter(ScanRun.id == scan_run_id).first()
        if scan_run:
            scan_run.status = "failed"
            scan_run.error_message = str(e)[:500]
            db.commit()
    finally:
        db.close()


@router.post("/tennis/start")
async def start_tennis_scan(
    background_tasks: BackgroundTasks,
    scan_date: str = Query(default=None, description="yyyy-mm-dd, default = leo"),
    stake_per_combo: float = Query(default=None, description="Stake KAMILI kwa kila comb (haigawanywi)"),
    group_size: int = Query(default=4, description="Idadi ya mechi kwa kila kikundi (2, 3, 4, ...)"),
    db: Session = Depends(get_db),
):
    scan_date = scan_date or date.today().isoformat()
    stake_per_combo = stake_per_combo or settings.DEFAULT_TOTAL_STAKE

    scan_run = ScanRun(sport="tennis", scan_date=scan_date, status="running")
    db.add(scan_run)
    db.commit()
    db.refresh(scan_run)

    background_tasks.add_task(_run_scan_background, scan_run.id, scan_date, stake_per_combo, group_size)

    return {"scan_run_id": scan_run.id, "status": "running", "scan_date": scan_date}


def _group_to_response(group: ComboGroup, combos) -> dict:
    return {
        "group_id": group.id,
        "matches": group.matches_json,
        "stake_per_combo": group.total_stake,
        "total_invest": round(group.total_stake * len(combos), 2) if combos else 0,
        "worst_profit": group.guaranteed_profit,
        "combos": [
            {
                "combo_index": c.combo_index,
                "picks": c.picks_json,
                "combined_odd": c.combined_odd,
                "odds_display": " x ".join(f"{p['odd']:.2f}" for p in c.picks_json),
                "stake": c.stake,
                "potential_payout": c.potential_payout,
                "profit": round(c.potential_payout - (group.total_stake * len(combos)), 2) if combos else 0,
            }
            for c in combos
        ],
    }


@router.get("/tennis/status/{scan_run_id}")
def get_scan_status(scan_run_id: int, db: Session = Depends(get_db)):
    """Frontend inaita hii kila baada ya sekunde 3-5 kuangalia kama scan imekamilika."""
    scan_run = db.query(ScanRun).filter(ScanRun.id == scan_run_id).first()
    if not scan_run:
        return {"error": "Scan run not found"}

    response = {
        "scan_run_id": scan_run.id,
        "status": scan_run.status,
        "scan_date": scan_run.scan_date,
        "profitable_groups_found": scan_run.profitable_groups_found,
        "error_message": scan_run.error_message,
        "groups": [],
    }

    if scan_run.status == "completed":
        groups = db.query(ComboGroup).filter(ComboGroup.scan_run_id == scan_run_id).all()
        for group in groups:
            combos = db.query(Combo).filter(Combo.group_id == group.id).order_by(Combo.combo_index).all()
            response["groups"].append(_group_to_response(group, combos))

    return response


@router.get("/history")
def scan_history(limit: int = 20, db: Session = Depends(get_db)):
    runs = db.query(ScanRun).order_by(ScanRun.id.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "scan_date": r.scan_date,
            "status": r.status,
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
    return _group_to_response(group, combos)
