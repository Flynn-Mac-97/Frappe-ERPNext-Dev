"""Fake-data factories: shops, items, and Shopee-shaped orders.

Order/detail dicts match the Shopee Open Platform v2 response shapes that OSI's
parser consumes (see api/services/order_service.py + api/shopee/order.py).
"""

import itertools
import random
import time

_BASE_SHOP_ID = 700000
# Seed the SN counter from boot time so order SNs never collide across mock
# restarts — a fresh counter would regenerate SNs an OSI dev site already
# ingested, turning every "new" order into a silent update.
_order_seq = itertools.count(int(time.time()) % 100_000_000)

_FIRST = ["Wei", "Mei", "Anh", "Linh", "Jose", "Maria", "Siti", "Arun", "Nok", "Tien"]
_LAST = ["Tan", "Lim", "Nguyen", "Tran", "Cruz", "Reyes", "Bin", "Rao", "Wong", "Le"]
_PRODUCTS = ["Phone Case", "USB Cable", "Earbuds", "Water Bottle", "Notebook",
             "T-Shirt", "Sneakers", "Backpack", "Mug", "Desk Lamp",
             "Power Bank", "Keyboard", "Mouse Pad", "Sticker Pack", "Sunglasses"]


def build_shops(config: dict) -> dict:
    """Return {shop_id: shop_dict} seeded from config.shops."""
    sconf = config["shops"]
    regions = sconf["regions"] or ["MY"]
    currencies = sconf["currencies"] or ["MYR"]
    shops = {}
    for i in range(int(sconf["count"])):
        shop_id = _BASE_SHOP_ID + i
        region = regions[i % len(regions)]
        currency = currencies[i % len(currencies)]
        shops[shop_id] = {
            "shop_id": shop_id,
            "shop_name": f"Mock Shop {region} {i + 1}",
            "region": region,
            "currency": currency,
            "status": "NORMAL",
            "access_token": f"mock-access-{shop_id}",
            "refresh_token": f"mock-refresh-{shop_id}",
            "expire_in": 14400,
            "items": build_items(shop_id, currency, int(sconf["items_per_shop"])),
        }
    return shops


def build_items(shop_id: int, currency: str, count: int) -> list[dict]:
    items = []
    for j in range(count):
        item_id = shop_id * 1000 + j
        name = _PRODUCTS[j % len(_PRODUCTS)]
        items.append({
            "item_id": item_id,
            "item_name": f"{name} #{j + 1}",
            "item_sku": f"SKU-{shop_id}-{j + 1:03d}",
            "currency": currency,
            "price": round(random.uniform(5, 120), 2),
            "stock": random.randint(10, 500),
        })
    return items


def make_order(shop: dict, status: str | None = None, create_time: int | None = None) -> dict:
    """Build one Shopee get_order_detail-shaped order for a shop."""
    n = next(_order_seq)
    now = int(time.time())
    ct = create_time if create_time is not None else now
    status = status or "READY_TO_SHIP"
    region = shop["region"]
    currency = shop["currency"]

    chosen = random.sample(shop["items"], k=min(random.randint(1, 3), len(shop["items"])))
    item_list = []
    total = 0.0
    for it in chosen:
        qty = random.randint(1, 4)
        price = it["price"]
        total += price * qty
        item_list.append({
            "item_id": it["item_id"],
            "item_name": it["item_name"],
            "item_sku": it["item_sku"],
            "model_id": 0,
            "model_name": "",
            "model_sku": it["item_sku"],
            "model_quantity_purchased": qty,
            "model_original_price": price,
            "model_discounted_price": price,
            "weight": round(random.uniform(0.1, 2.0), 2),
        })

    fullname = f"{random.choice(_FIRST)} {random.choice(_LAST)}"
    order_sn = f"24{region}{n:08d}"
    return {
        "order_sn": order_sn,
        "shop_id": shop["shop_id"],
        "region": region,
        "order_status": status,
        "currency": currency,
        "total_amount": round(total, 2),
        "cod": False,
        "payment_method": "Credit Card",
        "shipping_carrier": "Standard Delivery",
        "message_to_seller": "",
        "note": "",
        "days_to_ship": 3,
        "ship_by_date": ct + 3 * 86400,
        "create_time": ct,
        "update_time": ct,
        "pay_time": ct,
        "recipient_address": {
            "name": fullname,
            "phone": f"+60{random.randint(100000000, 199999999)}",
            "full_address": f"{random.randint(1, 999)} Jalan Mock, {region}",
            "city": "Mock City",
            "state": "Mock State",
            "region": region,
            "zipcode": f"{random.randint(10000, 99999)}",
        },
        "item_list": item_list,
        "package_list": [{
            "package_number": f"PKG{order_sn}",
            "logistics_status": "LOGISTICS_READY",
        }],
    }


def list_row(order: dict) -> dict:
    """Shopee get_order_list row: just sn + status."""
    return {"order_sn": order["order_sn"], "order_status": order["order_status"]}
