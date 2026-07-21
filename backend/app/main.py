"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    audit,
    citizen_shield,
    counterfeit,
    fraud_graph,
    geospatial,
    health,
    scam_detection,
)
from app.fir_agent.api import router as fir_agent_router
from app.core.auth import log_auth_status_warning
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)

    # --- Security warnings ---
    log_auth_status_warning(settings)
    if settings.alert_webhook_url:
        logger.info("Alert webhook configured: %s", settings.alert_webhook_url)
    else:
        logger.info(
            "No ALERT_WEBHOOK_URL configured — high-risk alerts will fall back to JSONL."
        )

    # --- Database ---
    from db.session import init_db
    init_db()
    logger.info("Database ready")

    # --- Expire stale call sessions from previous runs ---
    from db.session import get_session_factory
    from app.services.call_session import expire_sessions
    with get_session_factory()() as db:
        expired = expire_sessions(db)
        if expired:
            logger.info("Expired %d stale call session chunk(s) at startup", expired)

    logger.info("Startup complete — %s v%s is ready.", settings.app_name, settings.app_version)
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Production-hardened hackathon scaffold for a digital public-safety platform covering "
        "scam detection, counterfeit goods, fraud graphs, geospatial risk, "
        "and citizen shield reporting."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health + observability (unversioned — k8s probes)
app.include_router(health.router)

# Legal-admissibility AI audit log (unversioned path per spec)
app.include_router(audit.public_router)

# Real-time scam scoring (Prompt 2.3): POST /api/scam-detection/score
app.include_router(scam_detection.score_router)

# Currency note scan (Prompt 3.3): POST /api/counterfeit/scan
app.include_router(counterfeit.scan_router)

# Fraud graph clusters/export (Prompt 4.3): /api/fraud-graph/...
app.include_router(fraud_graph.public_router)

# Geospatial hotspots (Prompt 5.2): /api/geospatial/hotspots
app.include_router(geospatial.public_router)

# Citizen shield assess (Prompt 6.2): POST /api/citizen-shield/assess
app.include_router(citizen_shield.public_router)

# Versioned module routers — /api/v1/...
api = settings.api_prefix
app.include_router(scam_detection.router, prefix=api)
app.include_router(counterfeit.router, prefix=api)
app.include_router(fraud_graph.router, prefix=api)
app.include_router(geospatial.router, prefix=api)
app.include_router(citizen_shield.router, prefix=api)
app.include_router(audit.router, prefix=api)

# FIR Drafting Agent (Section 11): POST/PATCH/GET /api/fir-agent/...
app.include_router(fir_agent_router)
