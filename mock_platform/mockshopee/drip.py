"""Live-traffic simulator: sporadic order arrivals + lifecycle progression, each
change pushed to OSI's Shopee webhook (no OSI-side polling).

Two background asyncio tasks:

* **arrivals** — new orders appear as a Poisson process at ``orders_per_day``
  (realistic sporadic gaps, natural bursts), optionally shaped by a diurnal
  day/night curve. ``time_scale`` compresses wall-clock so a "day" of traffic
  can be watched in minutes while keeping the *shape* realistic.
* **lifecycle** — orders that have aged past a grace window progress on the
  Shopee side (READY_TO_SHIP → SHIPPED → COMPLETED, with small cancel / return
  branches). Recent orders are left untouched so a human can process them by
  hand in the portal. Every progression fires a push too, so escrow / finance /
  returns light up as orders settle.

Every created/advanced order fires ``push_client.send_push`` (code 3 = order
status), so OSI ingests via the real webhook exactly as production would.
"""

import asyncio
import logging
import math
import random
import time

from . import push_client
from .state import STATE

log = logging.getLogger("mockshopee.drip")

# Shopee raw statuses (OSI's parser maps these to its own vocabulary).
_READY = "READY_TO_SHIP"
_PROCESSED = "PROCESSED"
_SHIPPED = "SHIPPED"
_COMPLETED = "COMPLETED"
_CANCELLED = "CANCELLED"
_REFUNDED = "REFUNDED"
_TERMINAL = {_COMPLETED, _CANCELLED, _REFUNDED}


def _diurnal_factor(enabled: bool) -> float:
    """Multiplier on the base arrival rate. Mean over 24h is ~1.0 so the daily
    total still lands near ``orders_per_day``; peaks mid-afternoon, troughs
    pre-dawn. Returns 1.0 when disabled."""
    if not enabled:
        return 1.0
    hour = time.localtime().tm_hour + time.localtime().tm_min / 60.0
    # cosine peaking at 15:00; amplitude 0.7 -> range ~[0.3, 1.7], mean 1.0
    factor = 1.0 + 0.7 * math.cos((hour - 15.0) / 24.0 * 2.0 * math.pi)
    return max(0.05, factor)


class DripManager:
    def __init__(self):
        self._tasks: list[asyncio.Task] = []
        self.running = False
        self.created = 0
        self.advanced = 0
        self.last_error = ""
        self.cfg = {}       # effective drip cfg
        self.push_cfg = {}  # effective push cfg

    # -- config / status ----------------------------------------------------
    def configure(self, config: dict):
        """Store base drip/push config (called at startup)."""
        self.cfg = dict(config.get("drip") or {})
        self.push_cfg = dict(config.get("push") or {})

    def status(self) -> dict:
        return {
            "running": self.running,
            "created": self.created,
            "advanced": self.advanced,
            "last_error": self.last_error,
            "mode": self.cfg.get("mode", "sporadic"),
            "orders_per_day": self.cfg.get("orders_per_day"),
            "time_scale": self.cfg.get("time_scale", 1.0),
            "diurnal": bool(self.cfg.get("diurnal")),
            "lifecycle": bool((self.cfg.get("lifecycle") or {}).get("enabled")),
            "push_enabled": bool(self.push_cfg.get("enabled")),
        }

    # -- lifecycle ----------------------------------------------------------
    def start(self, overrides: dict | None = None) -> dict:
        if self.running:
            return {"started": False, "reason": "already running", **self.status()}
        self.cfg = {**self.cfg, **(overrides or {})}
        self.running = True
        self.created = 0
        self.advanced = 0
        self.last_error = ""
        self._tasks = [asyncio.create_task(self._arrival_loop())]
        if (self.cfg.get("lifecycle") or {}).get("enabled"):
            self._tasks.append(asyncio.create_task(self._lifecycle_loop()))
        log.info("drip started: %s", self.status())
        return {"started": True, **self.status()}

    async def stop(self) -> dict:
        self.running = False
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks = []
        log.info("drip stopped after %s created / %s advanced", self.created, self.advanced)
        return {"stopped": True, **self.status()}

    async def _push(self, shop_id, order_sn):
        if not self.push_cfg.get("enabled"):
            return
        await push_client.send_push(
            self.push_cfg.get("url"),
            self.push_cfg.get("key"),
            shop_id,
            order_sn,
            int(self.push_cfg.get("code", 3) or 3),
            host=self.push_cfg.get("host"),
        )

    # -- arrivals -----------------------------------------------------------
    async def _arrival_loop(self):
        mode = self.cfg.get("mode", "sporadic")
        shop_id = self.cfg.get("shop_id")
        max_orders = int(self.cfg.get("max_orders", 0) or 0)
        time_scale = max(0.001, float(self.cfg.get("time_scale", 1.0) or 1.0))
        diurnal = bool(self.cfg.get("diurnal"))
        try:
            while self.running:
                if max_orders and self.created >= max_orders:
                    log.info("drip reached max_orders=%s", max_orders)
                    break
                try:
                    new = STATE.gen_orders_detailed(1, shop_id)
                    self.created += len(new)
                    for o in new:
                        await self._push(o["shop_id"], o["order_sn"])
                except Exception as exc:  # noqa: BLE001 - never kill the loop
                    self.last_error = str(exc)
                    log.warning("arrival tick error: %s", exc)
                await asyncio.sleep(self._next_gap(mode, time_scale, diurnal))
        finally:
            self.running = False

    def _next_gap(self, mode: str, time_scale: float, diurnal: bool) -> float:
        """Seconds to sleep before the next arrival."""
        if mode == "fixed":
            # legacy behaviour: steady interval / per_tick (per_tick handled by
            # simply using the interval; kept for existing scripts).
            return max(0.01, float(self.cfg.get("interval_seconds", 5) or 5) / time_scale)
        # sporadic: exponential inter-arrival for a Poisson process.
        per_day = float(self.cfg.get("orders_per_day", 1000) or 1000)
        rate = (per_day / 86400.0) * time_scale * _diurnal_factor(diurnal)
        rate = max(1e-6, rate)
        return min(3600.0, random.expovariate(rate))

    # -- lifecycle progression ---------------------------------------------
    async def _lifecycle_loop(self):
        lc = self.cfg.get("lifecycle") or {}
        time_scale = max(0.001, float(self.cfg.get("time_scale", 1.0) or 1.0))
        tick = max(1.0, float(lc.get("tick_seconds", 300) or 300) / time_scale)
        grace = float(lc.get("grace_seconds", 3600) or 3600) / time_scale
        cancel_pct = float(lc.get("cancel_pct", 0.05) or 0)
        return_pct = float(lc.get("return_pct", 0.05) or 0)
        try:
            while self.running:
                await asyncio.sleep(tick)
                try:
                    self._advance_due(grace, cancel_pct, return_pct)
                except Exception as exc:  # noqa: BLE001
                    self.last_error = str(exc)
                    log.warning("lifecycle tick error: %s", exc)
        finally:
            pass

    def _advance_due(self, grace: float, cancel_pct: float, return_pct: float):
        """Advance one age-appropriate step for orders past the grace window."""
        now = int(time.time())
        for snap in STATE.snapshot_orders():
            status = snap["order_status"]
            if status in _TERMINAL:
                continue
            age = now - int(snap.get("update_time") or snap.get("create_time") or now)
            if age < grace:
                continue  # leave recent orders for the human to process
            sn, sid = snap["order_sn"], snap["shop_id"]
            if status == _READY:
                # READY_TO_SHIP -> PROCESSED (shipment arranged, waybill printable)
                # before SHIPPED, matching Shopee; cancels branch off pre-arrangement.
                roll = random.random()
                nxt = _CANCELLED if roll < cancel_pct else _PROCESSED
            elif status == _PROCESSED:
                nxt = _SHIPPED
            elif status == _SHIPPED:
                nxt = _REFUNDED if random.random() < return_pct else _COMPLETED
            else:
                continue
            try:
                STATE.advance(sn, nxt)
                self.advanced += 1
            except KeyError:
                continue
            # push the status change so OSI re-fetches + escrow/finance update
            asyncio.create_task(self._push(sid, sn))


DRIP = DripManager()
