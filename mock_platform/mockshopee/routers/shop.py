"""Shop endpoints: get_shop_info."""

from fastapi import APIRouter, Query

from mockshopee.envelope import err, ok
from mockshopee.state import STATE

router = APIRouter()


@router.get("/api/v2/shop/get_shop_info")
def get_shop_info(shop_id: int = Query(...)):
    shop = STATE.shops.get(int(shop_id))
    if not shop:
        return err("error_not_found", f"shop {shop_id} not found")
    return ok({
        "shop_id": shop["shop_id"],
        "shop_name": shop["shop_name"],
        "region": shop["region"],
        "status": shop["status"],
        "currency": shop["currency"],
        "is_cb": False,
    })
