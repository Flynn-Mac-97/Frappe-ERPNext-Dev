# MALACA ERP — 1000-orders/day load certification

**Spec requirement (MALACA ERP 1.0.1 §1):** internal test at ≥1000 orders/day sustained — data relations stable, storage stable, model sound, headroom for growth.

**Run:** 2026-07-04, local WSL dev bench (`erp.localhost`), offline mock Shopee (port 9900), MariaDB, 5 parallel RQ workers on the `long` queue + wave-based enqueue (Frappe caps a queue at 550 jobs — `devtools/cert.py` enqueues in waves while workers drain).

**Pipeline exercised per order:** mock order ingest → OSI upsert → review approve → ERPNext Sales Order → Delivery Note → Sales Invoice (multi-currency MYR/PHP/VND, FX conversion, stock movement, GL postings) → audit timeline comment.

## Result — PASS with ~188× headroom

| Metric | Value |
|---|---|
| Orders processed (full ERP pipeline) | 1068 |
| Wall-clock drain time | 491 s (~8.2 min) |
| Throughput | **2.17 orders/s** = 7 830/hour |
| Projected daily capacity | **~187 900 orders/day** |
| Deadlocks | 0 |
| Lock-wait timeouts | 0 |
| Failed jobs | 1 / 1277 (0.08%, transient mock chaos) |
| Orders in erp_sync_status=error | 2 (pre-existing dev-data artifacts, not from this run) |

The 1000-orders/day bar corresponds to ~0.012 orders/s; measured sustained throughput is ~188× that on a laptop-class dev VM. Concurrency safety re-confirmed (0 deadlocks / lock-waits across 5 workers, matching the earlier 533-job run).

## Reproduce

```bash
bench --site erp.localhost execute online_store_integration.devtools.cert.enqueue_1000
mock_platform/stress_workers.sh long 5           # hold open
bench --site erp.localhost execute online_store_integration.devtools.cert.mark_start
# loop until run_wave prints remaining=0 and pending prints queue=0 candidates=0:
bench --site erp.localhost execute online_store_integration.devtools.cert.run_wave
bench --site erp.localhost execute online_store_integration.devtools.cert.pending
bench --site erp.localhost execute online_store_integration.devtools.cert.report
```

Note: killing the stress workers also kills the bench's own long worker — restart `bench start` afterwards.

## Caveats

- Dev VM + mock platform: real Shopee API latency/rate-limits would slow ingest, but ingest is not the bottleneck the spec targets (ERP document creation is), and HTTP retry/backoff is already verified separately.
- Storage growth for the run: ~1.3k orders + ~3.9k ERP docs, no anomalies.
- Repeat on VPS-class hardware before go-live for a production-environment number.
