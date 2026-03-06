from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=0.1,
        environment="development",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await _crash_recovery()
    yield
    # Shutdown (Ressourcen freigeben falls nötig)


async def _crash_recovery():
    """
    Setzt Meetings zurück die beim letzten App-Start hängen geblieben sind.
    Milestone 2: Implementierung mit DB-Query.
    """
    # TODO (Milestone 2): Alle meetings mit status=transcribing → pending setzen
    pass


app = FastAPI(
    title="MeetMind API",
    description="DSGVO-konformes Meeting-Intelligence-System",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router einbinden
from app.api.v1 import health  # noqa: E402

app.include_router(health.router, prefix="/api/v1", tags=["health"])
