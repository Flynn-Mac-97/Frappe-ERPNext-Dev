"""Shop endpoints: get_shop_info + get_profile."""

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


@router.get("/api/v2/shop/get_profile")
def get_profile(shop_id: int = Query(...)):
    # Real Shopee: get_shop_info.shop_name can be the account username while
    # get_profile.shop_name is the seller-set storefront name. Return a
    # DISTINCT value so OSI's overlay precedence is exercised in dev.
    shop = STATE.shops.get(int(shop_id))
    if not shop:
        return err("error_not_found", f"shop {shop_id} not found")
    return ok({
        "shop_name": f"{shop['shop_name']} Official",
        "shop_logo": "",
        "description": f"Mock storefront for {shop['shop_name']}",
    })
