"""Outbound push client: fire Shopee-style order-status pushes at the OSI webhook.

OSI verifies HMAC-SHA256(key, raw_body) hex in the Authorization header
(body-only scheme). We therefore sign the exact bytes we POST (content=body).
"""

import hashlib
import hmac
import json
import logging
import time

import httpx

log = logging.getLogger("mockshopee.push")


def build_push_body(shop_id: int, order_sn: str, code: int = 3) -> str:
    """Serialize a Shopee v2 order-status push body (compact, stable key order)."""
    payload = {
        "code": code,
        "shop_id": int(shop_id),
        "timestamp": int(time.time()),
        "data": {"ordersn": order_sn},
    }
    return json.dumps(payload, separators=(",", ":"))


def sign_body(key: str, body: str) -> str:
    """HMAC-SHA256 hex over the raw body, matching OSI's body-only scheme."""
    return hmac.new(key.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()


async def send_push(
    url: str,
    key: str,
    shop_id: int,
    order_sn: str,
    code: int = 3,
    timeout: float = 10.0,
    host: str | None = None,
) -> tuple[bool, str]:
    """POST one push to OSI. Returns (ok, detail). Never raises — logs and reports.

    *host*, when set, overrides the Host header. This lets the URL point at a raw
    loopback IP (dodging WSL's flaky ``erp.localhost`` resolution) while Frappe
    still routes to the right site by Host. The body-only HMAC is unaffected."""
    body = build_push_body(shop_id, order_sn, code)
    headers = {
        "Authorization": sign_body(key, body),
        "Content-Type": "application/json",
    }
    if host:
        headers["Host"] = host
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, content=body, headers=headers)
        ok = resp.status_code == 200
        log.info("push order_sn=%s shop=%s -> HTTP %s", order_sn, shop_id, resp.status_code)
        if not ok:
            log.warning("push rejected order_sn=%s body=%s", order_sn, resp.text[:200])
        return ok, str(resp.status_code)
    except Exception as exc:  # noqa: BLE001 - fire-and-forget, never crash the mock
        log.warning("push failed order_sn=%s: %s", order_sn, exc)
        return False, str(exc)
