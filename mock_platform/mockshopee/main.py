"""FastAPI app: mounts the Shopee-faithful routers + control plane, seeds state
at startup, and injects latency / retryable errors / 429s to exercise OSI's
retry+backoff under load."""

import asyncio
import random

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from mockshopee.config import load_config
from mockshopee.envelope import err
from mockshopee.routers import auth, control, logistics, order, payment, shop
from mockshopee.state import STATE

app = FastAPI(title="Mock Shopee Platform", version="0.1.0")

app.include_router(auth.router)
app.include_router(shop.router)
app.include_router(order.router)
app.include_router(payment.router)
app.include_router(logistics.router)
app.include_router(control.router)


@app.on_event("startup")
def _seed_on_startup() -> None:
    config = load_config()
    STATE.seed(config)
    from .drip import DRIP
    DRIP.configure(config)
    if (config.get("drip") or {}).get("enabled"):
        DRIP.start({})


@app.on_event("shutdown")
async def _shutdown():
    from .drip import DRIP
    await DRIP.stop()


@app.middleware("http")
async def _chaos(request: Request, call_next):
    """Only affects /api/v2/* (the Shopee surface). Control plane + health are
    never throttled/failed so tests stay drivable."""
    path = request.url.path
    if not path.startswith("/api/v2/"):
        return await call_next(request)

    rt = STATE.runtime
    latency_ms = int(rt.get("latency_ms", 0))
    if latency_ms:
        await asyncio.sleep(latency_ms / 1000.0)

    if random.random() < float(rt.get("rate_limit_rate", 0.0)):
        return JSONResponse(
            err("error_too_many_request", "injected 429"),
            status_code=429,
            headers={"Retry-After": "1"},
        )

    if random.random() < float(rt.get("error_rate", 0.0)):
        # HTTP 200 with a Shopee app-level busy code (OSI retries these).
        return JSONResponse(err("error_busy", "injected busy"))

    return await call_next(request)


@app.get("/")
def health():
    return {"ok": True, **STATE.stats()}
