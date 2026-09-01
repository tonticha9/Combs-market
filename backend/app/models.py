from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db import Base


class ScanRun(Base):
    """Rekodi ya kila scan iliyofanyika (siku fulani, mfumo uliangalia mechi)."""
    __tablename__ = "scan_runs"

    id = Column(Integer, primary_key=True, index=True)
    sport = Column(String, default="tennis")
    scan_date = Column(String, index=True)       # yyyy-mm-dd
    status = Column(String, default="running")
error_message = Column(String, nullable=True)
    total_matches_found = Column(Integer, default=0)
    total_groups_checked = Column(Integer, default=0)
    profitable_groups_found = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    groups = relationship("ComboGroup", back_populates="scan_run", cascade="all, delete-orphan")


class ComboGroup(Base):
    """Kikundi kimoja cha mechi 4 chenye faida (surebet)."""
    __tablename__ = "combo_groups"

    id = Column(Integer, primary_key=True, index=True)
    scan_run_id = Column(Integer, ForeignKey("scan_runs.id"))
    matches_json = Column(JSON)          # taarifa za mechi 4 (players, odds, bookmakers)
    total_implied_prob = Column(Float)
    margin_percent = Column(Float)
    total_stake = Column(Float)
    guaranteed_profit = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    scan_run = relationship("ScanRun", back_populates="groups")
    combos = relationship("Combo", back_populates="group", cascade="all, delete-orphan")


class Combo(Base):
    """Comb moja (mojawapo ya 16) ndani ya kikundi, na stake yake."""
    __tablename__ = "combos"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("combo_groups.id"))
    combo_index = Column(Integer)
    picks_json = Column(JSON)            # orodha ya picks 4 (player, selection, odd, bookmaker)
    combined_odd = Column(Float)
    stake = Column(Float)
    potential_payout = Column(Float)

    group = relationship("ComboGroup", back_populates="combos")
