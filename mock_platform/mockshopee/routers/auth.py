"""Auth/token endpoints. Responses are FLAT (token fields at top level), matching
Shopee. The mock issues deterministic tokens per shop and ignores signatures."""

from fastapi import APIRouter, Query, Request

from mockshopee.envelope import err, flat
from mockshopee.state import STATE

router = APIRouter()


def _tokens_for(shop_id: int) -> dict:
    shop = STATE.shops.get(int(shop_id))
    if not shop:
        # Unknown shop: still hand back usable tokens so offline flows don't wedge.
        return {
            "access_token": f"mock-access-{shop_id}",
            "refresh_token": f"mock-refresh-{shop_id}",
            "expire_in": 14400,
        }
    return {
        "access_token": shop["access_token"],
        "refresh_token": shop["refresh_token"],
        "expire_in": shop["expire_in"],
    }


async def _shop_id_from(request: Request, shop_id: int | None) -> int:
    if shop_id:
        return shop_id
    try:
        body = await request.json()
    except Exception:
        body = {}
    return int(body.get("shop_id") or body.get("shopid") or 0)


@router.api_route("/api/v2/auth/token/get", methods=["GET", "POST"])
async def token_get(request: Request, shop_id: int | None = Query(None)):
    sid = await _shop_id_from(request, shop_id)
    if not sid:
        return err("error_param", "shop_id required")
    return flat(_tokens_for(sid))


@router.api_route("/api/v2/auth/access_token/get", methods=["GET", "POST"])
async def access_token_get(request: Request, shop_id: int | None = Query(None)):
    sid = await _shop_id_from(request, shop_id)
    if not sid:
        return err("error_param", "shop_id required")
    return flat(_tokens_for(sid))


@router.get("/api/v2/shop/auth_partner")
def auth_partner(shop_id: int = Query(0)):
    # Authorize landing. Real Shopee redirects the seller's browser back to the
    # app callback with a `code`. Offline we just hand back a fake code.
    sid = shop_id or next(iter(STATE.shops), 0)
    return flat({"auth_code": f"mock-code-{sid}", "shop_id": sid})
