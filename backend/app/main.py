from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import Base, engine
from app.routers import scan
from app.config import settings

app = FastAPI(title="Tennis No-Loss Arbitrage Scanner", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scan.router)


@app.on_event("startup")
def on_startup():
    # Inaunda majedwali ya database kama hayapo (kwa production, tumia Alembic migrations)
    Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "Tennis No-Loss Arbitrage Scanner",
        "endpoints": {
            "start_scan": "POST /api/scan/tennis/start?scan_date=yyyy-mm-dd&total_stake=1000",
            "check_status": "GET /api/scan/tennis/status/{scan_run_id}",
            "history": "GET /api/scan/history",
            "group_detail": "GET /api/scan/groups/{group_id}",
        },
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
