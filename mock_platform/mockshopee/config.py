"""Config loading for the mock Shopee server.

Reads YAML from MOCKSHOPEE_CONFIG, else ./config.yaml, else built-in defaults.
"""

import os

try:
    import yaml
except ImportError:  # pragma: no cover - yaml is a hard dep at runtime
    yaml = None

DEFAULTS = {
    "server": {
        "latency_ms": 0,
        "error_rate": 0.0,
        "rate_limit_rate": 0.0,
    },
    "shops": {
        "count": 3,
        "regions": ["MY", "VN", "PH"],
        "currencies": ["MYR", "VND", "PHP"],
        "items_per_shop": 15,
    },
    "orders": {
        "seed_per_shop": 25,
        "default_status": "READY_TO_SHIP",
        "window_days": 7,
    },
    "push": {
        "enabled": False,
        "url": "http://erp.localhost:8000/api/method/online_store_integration.api.webhook.shopee_push_webhook",
        "host": None,   # override the Host header (set when url uses a raw IP; see config.yaml)
        "key": "dev-shopee-push-key",
        "code": 3,
    },
    "drip": {
        "enabled": False,
        "mode": "sporadic",          # "sporadic" (Poisson arrivals) | "fixed" (legacy interval)
        "orders_per_day": 1000,      # sporadic-mode target daily volume
        "time_scale": 1.0,           # >1 compresses wall-clock (24 = one day of traffic per hour)
        "diurnal": True,             # shape arrivals by time of day (peak mid-afternoon)
        "shop_id": None,             # None = round-robin across all shops
        "max_orders": 0,             # 0 = unlimited
        "interval_seconds": 5,       # fixed-mode only
        "lifecycle": {
            "enabled": True,
            "grace_seconds": 3600,   # scaled by time_scale; recent orders left for manual processing
            "tick_seconds": 300,     # scaled; how often the advancer runs
            "cancel_pct": 0.05,      # READY_TO_SHIP -> CANCELLED
            "return_pct": 0.05,      # SHIPPED -> REFUNDED (else COMPLETED)
        },
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, val in (override or {}).items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = val
    return out


def load_config(path: str | None = None) -> dict:
    """Return the merged config dict (defaults <- file)."""
    path = path or os.environ.get("MOCKSHOPEE_CONFIG")
    if not path:
        candidate = os.path.join(os.getcwd(), "config.yaml")
        path = candidate if os.path.exists(candidate) else None

    if not path or not os.path.exists(path):
        return _deep_merge(DEFAULTS, {})

    if yaml is None:
        raise RuntimeError("pyyaml is required to read a config file; pip install -r requirements.txt")

    with open(path, encoding="utf-8") as fh:
        loaded = yaml.safe_load(fh) or {}
    return _deep_merge(DEFAULTS, loaded)
