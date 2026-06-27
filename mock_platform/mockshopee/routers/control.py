"""Control plane — NOT part of Shopee. Drives scenarios and load for testing OSI."""

from fastapi import APIRouter
from pydantic import BaseModel

from mockshopee.state import STATE

router = APIRouter(prefix="/__control")


class GenOrders(BaseModel):
    count: int = 1
    shop_id: int | None = None


class Advance(BaseModel):
    order_sn: str
    status: str


class RuntimeConfig(BaseModel):
    latency_ms: int | None = None
    error_rate: float | None = None
    rate_limit_rate: float | None = None


@router.get("/stats")
def stats():
    return STATE.stats()


@router.get("/shops")
def shops():
    """Seeded shops incl. tokens — consumed by the bench store-seed script."""
    return {
        "shops": [
            {
                "shop_id": s["shop_id"],
                "shop_name": s["shop_name"],
                "region": s["region"],
                "currency": s["currency"],
                "access_token": s["access_token"],
                "refresh_token": s["refresh_token"],
            }
            for s in STATE.shops.values()
        ]
    }


@router.post("/gen_orders")
def gen_orders(body: GenOrders):
    created = STATE.gen_orders(body.count, body.shop_id)
    return {"created": len(created), "order_sns": created[:50], "truncated": len(created) > 50}


@router.post("/advance")
def advance(body: Advance):
    order = STATE.advance(body.order_sn, body.status)
    return {"order_sn": order["order_sn"], "order_status": order["order_status"]}


@router.post("/config")
def set_config(body: RuntimeConfig):
    for key in ("latency_ms", "error_rate", "rate_limit_rate"):
        val = getattr(body, key)
        if val is not None:
            STATE.runtime[key] = val
    return {"runtime": STATE.runtime}


@router.post("/reset")
def reset():
    return STATE.reset()
