from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routes import router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm the local Yorùbá TTS model at startup so the first /tts request is
    # already fast (model loaded + one warm-up pass done). No-op unless
    # TTS_PROVIDER=local.
    if settings.tts_provider == "local":
        from starlette.concurrency import run_in_threadpool

        from . import tts_local

        await run_in_threadpool(
            tts_local.preload, settings.local_tts_model, settings.tts_num_threads
        )
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Backend for Afara — Yorùbá <-> English voice bridge.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# All endpoints live under /api/v1 so the mobile app has a stable prefix.
app.include_router(router, prefix="/api/v1")


@app.get("/", tags=["meta"])
async def root():
    return {"service": settings.app_name, "docs": "/docs", "health": "/api/v1/health"}
