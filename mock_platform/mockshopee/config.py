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
