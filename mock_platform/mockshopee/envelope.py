"""Shopee response-envelope helpers.

Shopee wraps shop/order/product results as:
    {"request_id": "...", "error": "", "message": "", "response": {...}}
Token/auth endpoints instead return their fields flat at the top level.
"""

import uuid


def _rid() -> str:
    return uuid.uuid4().hex


def ok(response: dict) -> dict:
    """Enveloped success (shop/order/product endpoints)."""
    return {"request_id": _rid(), "error": "", "message": "", "warning": "", "response": response}


def err(code: str, message: str = "") -> dict:
    """Enveloped (or flat) Shopee error body. OSI treats non-empty error as failure."""
    return {"request_id": _rid(), "error": code, "message": message or code}


def flat(fields: dict) -> dict:
    """Flat success body (auth/token endpoints)."""
    return {"request_id": _rid(), "error": "", "message": "", **fields}
