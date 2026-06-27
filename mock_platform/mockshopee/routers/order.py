"""Order endpoints: get_order_list (cursor paginated) + get_order_detail."""

import time

from fastapi import APIRouter, Query

from mockshopee.envelope import ok
from mockshopee.state import STATE

router = APIRouter()


@router.get("/api/v2/order/get_order_list")
def get_order_list(
    shop_id: int = Query(...),
    time_from: int = Query(0),
    time_to: int = Query(0),
    page_size: int = Query(50),
    cursor: str = Query(""),
    time_range_field: str = Query("create_time"),
):
    if not time_to:
        time_to = int(time.time())
    rows, more, next_cursor = STATE.list_orders(shop_id, time_from, time_to, page_size, cursor)
    from mockshopee.generators import list_row
    return ok({
        "order_list": [list_row(o) for o in rows],
        "more": more,
        "next_cursor": next_cursor,
    })


@router.get("/api/v2/order/get_order_detail")
def get_order_detail(
    shop_id: int = Query(...),
    order_sn_list: str = Query(""),
    response_optional_fields: str = Query(""),
):
    sns = [s.strip() for s in order_sn_list.split(",") if s.strip()]
    details = STATE.get_details(sns)
    return ok({"order_list": details})
