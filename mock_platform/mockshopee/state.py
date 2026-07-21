"""In-memory mock state: shops, items, orders + runtime knobs.

Single process, single dict store. Good enough for a dev mock and stress driver;
reset re-seeds from config.
"""

import itertools
import threading

from mockshopee import generators
from mockshopee.config import load_config

# Shopee raw order_status -> lifecycle rank. Logistics (tracking number / shipping
# document) allocation only becomes available once an order reaches READY_TO_SHIP
# or later — mirrors real Shopee: an unpaid order has nothing for logistics to
# allocate yet. Unrecognized/unset statuses rank 0 (not eligible), same as UNPAID.
_STATUS_RANK = {
    "UNPAID": 0,
    "PENDING": 0,
    "READY_TO_SHIP": 1,
    "RETRY_SHIP": 1,
    "PROCESSED": 2,
    "SHIPPED": 3,
    "TO_CONFIRM_RECEIVE": 3,
    "TO_RETURN": 3,
    "COMPLETED": 4,
    "REFUNDED": 4,
    "RETURNED": 4,
    "CANCELLED": -1,
    "CANCELED": -1,
    "IN_CANCEL": -1,
}
_READY_RANK = _STATUS_RANK["READY_TO_SHIP"]
TRACKING_NUMBER_PREFIX = "MOCKTRK"


class MockState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.config: dict = {}
        self.shops: dict[int, dict] = {}
        self.orders: dict[str, dict] = {}        # order_sn -> order detail
        self.runtime = {"latency_ms": 0, "error_rate": 0.0, "rate_limit_rate": 0.0}
        self._tracking_seq = itertools.count(1)
        # order_sn -> {"document_type", "status", "polls", "created_at"} for
        # create_shipping_document / get_shipping_document_result / download.
        self.shipping_docs: dict[str, dict] = {}

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
        self._tracking_seq = itertools.count(1)
        self.shipping_docs = {}
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

    def gen_orders_detailed(self, count: int, shop_id: int | None = None) -> list[dict]:
        """Like gen_orders but return [{"order_sn", "shop_id"}] for each created order."""
        created = []
        with self._lock:
            target_ids = [int(shop_id)] if shop_id else list(self.shops.keys())
            # Persistent cursor so successive per_tick=1 drip calls round-robin
            # across shops instead of always hitting target_ids[0].
            cursor = getattr(self, "_rr_cursor", 0)
            for _ in range(int(count)):
                sid = target_ids[cursor % len(target_ids)]
                cursor += 1
                order = self.add_order(sid)
                created.append({"order_sn": order["order_sn"], "shop_id": order["shop_id"]})
            self._rr_cursor = cursor
        return created

    def advance(self, order_sn: str, status: str) -> dict:
        import time as _t
        with self._lock:
            order = self.orders.get(order_sn)
            if not order:
                raise KeyError(f"unknown order_sn {order_sn}")
            order["order_status"] = status
            order["update_time"] = int(_t.time())
            # Real Shopee stamps pickup_done_time when the courier collects the
            # parcel (PROCESSED -> SHIPPED); keep it once set.
            if str(status).strip().upper() == "SHIPPED" and not order.get("pickup_done_time"):
                order["pickup_done_time"] = int(_t.time())
            return order

    def snapshot_orders(self) -> list[dict]:
        """Thread-safe shallow snapshot for the drip lifecycle scanner (which runs
        in the event loop while sync endpoints mutate state in the threadpool)."""
        with self._lock:
            return [
                {
                    "order_sn": o["order_sn"],
                    "shop_id": o["shop_id"],
                    "order_status": o["order_status"],
                    "create_time": o.get("create_time"),
                    "update_time": o.get("update_time"),
                }
                for o in self.orders.values()
            ]

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

    # -- logistics -----------------------------------------------------------
    @staticmethod
    def _rank(order: dict) -> int:
        return _STATUS_RANK.get(str(order.get("order_status") or "").strip().upper(), 0)

    def _eligibility(self, order_sn: str) -> tuple[dict | None, str]:
        """(order, reason) — reason is "" when logistics actions are allowed."""
        order = self.orders.get(order_sn)
        if not order:
            return None, "not_found"
        rank = self._rank(order)
        if rank < 0:
            return order, "cancelled"
        if rank < _READY_RANK:
            return order, "not_ready"
        return order, ""

    def check_logistics_eligibility(self, order_sn: str) -> str:
        """Public, locked view of _eligibility for the routers ("" = eligible)."""
        with self._lock:
            _order, reason = self._eligibility(order_sn)
            return reason

    def allocate_tracking_number(self, order_sn: str) -> dict:
        """Lazily allocate MOCKTRK########## on first request for an eligible order.

        Once allocated, the tracking number is written onto the order detail dict
        (top level + every package row) so subsequent get_order_detail payloads
        carry it — mirroring Shopee, where detail shows tracking after allocation.
        """
        with self._lock:
            order, reason = self._eligibility(order_sn)
            if reason == "not_found":
                return {"ok": False, "reason": reason}
            packages = order.get("package_list") or [{}]
            package_number = str(packages[0].get("package_number") or "")
            if reason:
                return {"ok": False, "reason": reason, "package_number": package_number}
            tracking = order.get("tracking_number")
            if not tracking:
                tracking = f"{TRACKING_NUMBER_PREFIX}{next(self._tracking_seq):010d}"
                order["tracking_number"] = tracking
                for pkg in order.get("package_list") or []:
                    pkg["tracking_number"] = tracking
            return {"ok": True, "tracking_number": tracking, "package_number": package_number}

    def create_shipping_doc(self, order_sn: str, document_type: str, tracking_number: str = "") -> dict:
        """Record a shipping-document generation request (Shopee queues these)."""
        import time as _t
        with self._lock:
            order, reason = self._eligibility(order_sn)
            if reason:
                return {"ok": False, "reason": reason}
            if not (order.get("tracking_number") or tracking_number):
                return {"ok": False, "reason": "no_tracking"}
            self.shipping_docs[order_sn] = {
                "document_type": document_type or "THERMAL_AIR_WAYBILL",
                "status": "PROCESSING",
                "polls": 0,
                "created_at": int(_t.time()),
            }
            return {"ok": True}

    def shipping_doc_status(self, order_sn: str) -> dict:
        """Poll result: first poll after create returns PROCESSING, then READY."""
        with self._lock:
            rec = self.shipping_docs.get(order_sn)
            if not rec:
                return {"ok": False, "reason": "not_created"}
            rec["polls"] += 1
            if rec["polls"] >= 2:
                rec["status"] = "READY"
            return {"ok": True, "status": rec["status"], "document_type": rec["document_type"]}

    def shipping_doc_for_download(self, order_sn: str) -> dict:
        """Fetch the doc record for download; forgivingly promotes to READY so a
        direct download right after create doesn't wedge dev flows."""
        with self._lock:
            rec = self.shipping_docs.get(order_sn)
            if not rec:
                return {"ok": False, "reason": "not_created"}
            rec["status"] = "READY"
            return {"ok": True, "document_type": rec["document_type"]}

    # -- introspection -------------------------------------------------------
    def stats(self) -> dict:
        return {
            "shops": len(self.shops),
            "items": sum(len(s["items"]) for s in self.shops.values()),
            "orders": len(self.orders),
            "runtime": dict(self.runtime),
        }


STATE = MockState()
