"""In-memory mock state: shops, items, orders + runtime knobs.

Single process, single dict store. Good enough for a dev mock and stress driver;
reset re-seeds from config.
"""

import threading

from mockshopee import generators
from mockshopee.config import load_config


class MockState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.config: dict = {}
        self.shops: dict[int, dict] = {}
        self.orders: dict[str, dict] = {}        # order_sn -> order detail
        self.runtime = {"latency_ms": 0, "error_rate": 0.0, "rate_limit_rate": 0.0}

    # -- lifecycle -----------------------------------------------------------
    def seed(self, config: dict | None = None) -> None:
        self.config = config or load_config()
        srv = self.config.get("server", {})
        self.runtime = {
            "latency_ms": int(srv.get("latency_ms", 0)),
            "error_rate": float(srv.get("error_rate", 0.0)),
            "rate_limit_rate": float(srv.get("rate_limit_rate", 0.0)),
        }
        self.shops = generators.build_shops(self.config)
        self.orders = {}
        oconf = self.config.get("orders", {})
        per_shop = int(oconf.get("seed_per_shop", 0))
        status = oconf.get("default_status", "READY_TO_SHIP")
        window_days = int(oconf.get("window_days", 7))
        import time as _t
        now = int(_t.time())
        for shop in self.shops.values():
            for k in range(per_shop):
                # spread create_time back over the window so list queries paginate
                ct = now - int((k / max(per_shop, 1)) * window_days * 86400)
                self.add_order(shop["shop_id"], status=status, create_time=ct)

    def reset(self) -> dict:
        with self._lock:
            self.seed(load_config())
        return self.stats()

    # -- orders --------------------------------------------------------------
    def add_order(self, shop_id: int, status: str | None = None, create_time: int | None = None) -> dict:
        shop = self.shops.get(int(shop_id))
        if not shop:
            raise KeyError(f"unknown shop_id {shop_id}")
        order = generators.make_order(shop, status=status, create_time=create_time)
        self.orders[order["order_sn"]] = order
        return order

    def gen_orders(self, count: int, shop_id: int | None = None) -> list[str]:
        with self._lock:
            target_ids = [int(shop_id)] if shop_id else list(self.shops.keys())
            created = []
            for i in range(int(count)):
                sid = target_ids[i % len(target_ids)]
                created.append(self.add_order(sid)["order_sn"])
            return created

    def advance(self, order_sn: str, status: str) -> dict:
        order = self.orders.get(order_sn)
        if not order:
            raise KeyError(f"unknown order_sn {order_sn}")
        order["order_status"] = status
        import time as _t
        order["update_time"] = int(_t.time())
        return order

    def list_orders(self, shop_id: int, time_from: int, time_to: int,
                    page_size: int, cursor: str) -> tuple[list[dict], bool, str]:
        rows = [
            o for o in self.orders.values()
            if o["shop_id"] == int(shop_id) and time_from <= o["create_time"] <= time_to
        ]
        rows.sort(key=lambda o: (o["create_time"], o["order_sn"]))
        start = int(cursor) if cursor else 0
        page = rows[start:start + page_size]
        more = (start + page_size) < len(rows)
        next_cursor = str(start + page_size) if more else ""
        return page, more, next_cursor

    def get_details(self, order_sns: list[str]) -> list[dict]:
        return [self.orders[sn] for sn in order_sns if sn in self.orders]

    # -- introspection -------------------------------------------------------
    def stats(self) -> dict:
        return {
            "shops": len(self.shops),
            "items": sum(len(s["items"]) for s in self.shops.values()),
            "orders": len(self.orders),
            "runtime": dict(self.runtime),
        }


STATE = MockState()
