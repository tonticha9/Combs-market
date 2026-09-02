from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import traceback

from app.db import Base, engine
from app.routers import scan
from app.config import settings

app = FastAPI(title="Tennis No-Loss Arbitrage Scanner", version="0.2.0")

# CORS bado tunaiacha ikiwa wazi kwa usalama wa ziada (mfano wakati wa maendeleo/local),
# lakini kwa sababu frontend na backend sasa ziko domain moja, haitahitajika kikamilifu.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def debug_exception_handler(request: Request, exc: Exception):
    """
    MUDA MFUPI (DEBUG): inaonyesha traceback kamili kwenye response ya JSON
    badala ya kuficha 500 tupu. Hii ni kwa ajili ya kutatua matatizo tu -
    ondoa/badilisha baada ya mfumo kufanya kazi vizuri kwa sababu inaonyesha
    maelezo ya ndani ya server ambayo si salama kwa muda mrefu.
    """
    tb = traceback.format_exc()
    return JSONResponse(
        status_code=500,
        content={
            "debug_error": str(exc),
            "debug_traceback": tb,
            "path": str(request.url),
        },
    )


app.include_router(scan.router)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")


@app.on_event("startup")
def on_startup():
    # Inaunda majedwali ya database kama hayapo (kwa production, tumia Alembic migrations)
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/api/info")
def api_info():
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


@app.get("/")
def root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


# Inahudumia faili nyingine za static (kama zitaongezwa baadaye - CSS/JS/images tofauti)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
