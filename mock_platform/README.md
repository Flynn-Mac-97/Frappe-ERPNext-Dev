# Mock Shopee Platform Server

Dev-only fake of the Shopee Open Platform v2 API, so OSI can be built and
stress-tested **fully offline** — no real marketplace, no credentials.

It implements only the endpoints OSI actually calls (consumer-driven contract),
plus a `/__control/*` plane (NOT part of Shopee) to drive scenarios and load.

**This is not shipped.** It lives outside the OSI app and never deploys.

## Run

```bash
cd mock_platform
python -m venv .venv && . .venv/Scripts/activate   # Windows; use bin/activate on *nix
pip install -r requirements.txt
cp config.example.yaml config.yaml                 # optional; defaults work
uvicorn mockshopee.main:app --host 127.0.0.1 --port 9900
```

Then point OSI Settings `api_url` (and the bench store-seed script, coming next)
at `http://127.0.0.1:9900`. The mock ignores request signatures — OSI signs,
the mock accepts anything.

## API surface (Shopee-faithful)

| Path | Purpose |
|------|---------|
| `GET /api/v2/auth/token/get` · `/auth/access_token/get` | token issue / refresh (flat response) |
| `GET /api/v2/shop/auth_partner` | authorize landing (returns a fake code) |
| `GET /api/v2/shop/get_shop_info` | shop details |
| `GET /api/v2/order/get_order_list` | order SN page (cursor paginated) |
| `GET /api/v2/order/get_order_detail` | full order payloads |
| product / logistics / payment | *(next milestone)* |

## Control plane (load + scenarios)

| Path | Purpose |
|------|---------|
| `GET /__control/stats` | counts of shops / items / orders |
| `GET /__control/shops` | seeded shops (id, region, tokens) — used by the bench seed script |
| `POST /__control/gen_orders` | `{shop_id?, count}` — fire N new orders (stress) |
| `POST /__control/advance` | `{order_sn, status}` — move an order's state |
| `POST /__control/config` | `{latency_ms?, error_rate?, rate_limit_rate?}` — runtime tune |
| `POST /__control/reset` | wipe + re-seed from config |

## Stress test (the point of this)

1. Boot mock, seed stores into OSI, run a sync — confirm orders flow.
2. `POST /__control/gen_orders {count: 2000}` → trigger OSI sync → watch RQ
   workers + ERPNext doc creation throughput, DB locks, error rate.
3. Crank `error_rate` / `rate_limit_rate` to verify OSI retry/backoff holds.
