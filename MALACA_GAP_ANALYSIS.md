# MALACA ERP — Gap Analysis & Task List (v2, spec 1.0.1)

**Source spec:** `MALACA ERP 1.0.1.docx` (2026-06-30 update of the 2026-06-27 draft, 王仲征 / 厦门美瑞传芳贸易公司)
**Client answers:** `客户确认问题清单(1).docx` (2026-06-30) — resolves most of `CLIENT_QUESTIONS.md`.
**Current implementation:** `online_store_integration/` (OSI) — Frappe/ERPNext custom app, Shopee adapter live behind a vendor-neutral seam.

Status legend: ✅ done · ⚠️ partial · ❌ missing
Risk = blast radius if it breaks. Effort = rough build size (S < 1 day, M 1–3 days, L 1–2 weeks, XL multi-week).

---

## 0. What changed since v1 of this doc

**Spec 1.0.1 deltas:**
1. **Load bar:** internal test must prove **1000 orders/day sustained** — data integrity, storage stability, model soundness, extensibility.
2. **New module:** store **AI customer-service system** (ref 多客AI/Duoke AI): mobile-capable, multi-site multi-store chat handling, auto-respond to buyer actions across the order journey.

**Client answers (headline decisions):**
- Multi-company system; hierarchy **Company → Department → Manager → Specialist**; permissions granted top-down; data **isolated by platform/country/warehouse/department** unless authorized.
- ~**100 concurrent users**, ~**1000 connected shops**, 1000+ orders/day.
- **Every order reviewed**, bulk approve allowed. 刷单 manual flag OK for v1 (auto-detect later).
- Single-level approval (ops specialist), supervisors/GM view + recheck. **Audit trail mandatory.**
- No external users; partners = second-level departments.
- Warehouse-level stock OK v1 (no bins). Return disposition needed.
- Reports: day/month/year × site × warehouse **+ platform and SKU columns**.
- Finance: profit net of Shopee fees ✓; **manual input** for COGS (per SKU), ads, domestic/cross-border logistics, opex, FX cost.
- Platforms: **Shopee only for v1**; Lazada/TikTok later (client HAS API access already).
- Languages at launch: **zh/en/tl/th/vi/ms**; hi/ja/es later. AI translation = later phase.

---

## 1. Orders (订单)

**Have:**
- ✅ Shopee order ingest → `Online Sales Order` (via adapter seam).
- ✅ **Manual review gate** — `review_status` + bulk approve (list actions + form buttons), config-toggled (`require_order_review`). Matches "all orders reviewed, batch allowed".
- ✅ **刷单 manual flag** — `is_special_order` + reason; held out of ERP creation.
- ✅ SKU label overlay on shipping docs (per-region coords).
- ✅ SO/DN/SI creation; return reversal (credit note + return DN).
- ✅ **Ship-confirm reconciliation worklist** — `OSI Ship Confirm Reconciliation` report (paid-not-shipped / shipped-then-cancelled buckets).

**Gaps + tasks:**
- [ ] ⚠️ **Audit trail hardening** — reviewed_by/at exists; Frappe versioning tracks edits. _Risk: Low · Effort: S–M_
  - Enable `track_changes` on OSI doctypes (verify Online Sales Order/Store/Product have it); surface a per-order "who did what" timeline (review → approve → ship → return). Confirm Version records cover `frappe.db.set_value` paths we use (they don't — decide: doc.save for auditable transitions or explicit OSI Sync Log entries per action).
- [ ] ❌ **Automated 刷单 detector** — later phase per client. _(unchanged, Wave 3)_

---

## 2. Inventory (库存)

**Have:**
- ✅ ERPNext native stock; ship decrements; multi-warehouse.
- ✅ Return reversal + **return disposition** (restock/damaged/scrap → correct Stock Entry; damaged warehouse in OSI Settings).
- ✅ 发货/退货 summary reports (day/month/year × store × currency).
- ✅ Warehouse-level stock confirmed sufficient for v1 (no bin work needed — client answer).

**Gaps + tasks:**
- [ ] ⚠️ **Report dimensions: platform + SKU** — client wants platform and SKU visible in shipping/return summaries. _Risk: Low · Effort: S–M_
  - Add platform column (store join already there); add optional "group by SKU" mode or SKU drill-down variant of both reports.

---

## 3. Procurement (采购)

Unchanged: lean on ERPNext PO/PR later; replenishment Wave 3. Client's COGS answer (manual input) removes the "derive cost from procurement" dependency for finance.

---

## 4. Finance (财务)

**Have:**
- ✅ Escrow fee ingest (commission/service/transaction fees, net payout) via adapter.
- ✅ Daily P&L report (gross − platform fees = net payout; COGS from Item.valuation_rate).
- ✅ Multi-currency posting, fail-loud FX.

**Gaps + tasks (all UNBLOCKED by client answers):**
- [ ] ❌ **COGS manual entry per SKU** — client will hand-key unit costs. _Risk: Low · Effort: S–M_
  - Entry surface: bulk-editable cost field (use ERPNext Item valuation_rate via Stock Reconciliation, or an OSI `unit_cost` field on Online Product feeding P&L). Recommend OSI-level `unit_cost` (simpler for non-accountant users; P&L already joins items).
- [ ] ❌ **Manual cost inputs for P&L** — ads, domestic logistics, cross-border logistics, company opex, FX cost (client: "allow manual input, formula unchanged"). _Risk: Low · Effort: M_
  - New doctype `OSI Cost Entry` (date, store/site, cost_type, currency, amount, note) + P&L report subtracts by period×store. Types: ad_spend, domestic_logistics, intl_logistics, opex, fx_cost, other.
- [ ] ⚠️ **P&L formula completion** — once both above land: profit = net payout − COGS − manual costs; show amount + margin %.

---

## 5. Platforms

**Have:**
- ✅ Shopee adapter complete; **vendor-neutral adapter seam** (`api/adapters/`, `get_adapter(platform)`) — services/tasks/sync/webhook are vendor-import-free.

**Client decision:** **Shopee-only v1.** Lazada/TikTok deferred (they hold seller API credentials; models similar).

**Gaps + tasks:**
- [ ] ❌ Lazada adapter — Wave 3+, unblocked technically by the seam, deferred by client.
- [ ] ❌ TikTok adapter — same.

---

## 6. Localization / Translation

**Have:**
- ✅ Multi-locale pipeline: zh populated; tl/th/vi/ms/hi/ja/es scaffolded; per-locale pending queues.

**Client decision:** launch languages = **zh/en/tl/th/vi/ms** (en = source). AI self-evolving translation = later.

**Gaps + tasks:**
- [ ] ❌ **Populate tl/th/vi/ms CSVs** — content work over existing scaffold (~525 strings each). _Risk: Low · Effort: M (content)_ — can be AI-drafted + spot-checked even before the "self-evolving" pipeline exists.
- [ ] ❌ AI self-evolving translation pipeline — later phase (client confirmed).

---

## 7. NEW — Accounts, roles & data isolation (biggest v1 addition)

**Client requires:** multi-company tenancy; Company → Department → Manager → Specialist hierarchy; top-down permission granting; isolation by platform/country/warehouse/department; partners as second-level departments; ~100 concurrent users; no external access.

**Have:** ✅ **SHIPPED (local, 2026-07-08)** — `devtools/perm_check.py` 8/8 PASS.

**Tasks:** _done_
- [x] Design doc `PERMISSIONS_DESIGN.md` — hierarchy mapped to Company + Department (partners = child departments) + Users + Roles + User Permission rows; store = isolation grain (platform/country isolation by grouping stores into departments — UP targets Link doctypes only).
- [x] `permission_query_conditions` + `has_permission` hooks on 5 OSI doctypes (`api/utils/isolation.py`) honoring User Permissions on Online Store / Department (incl. descendants) / Company / Warehouse (union; System Manager / Administrator / no-UP users unrestricted → background jobs unaffected). All 6 reports row-filtered; all 49 whitelisted endpoints role-guarded + store-scoped.
- [x] Role fixtures: OSI Ops Specialist / OSI Ops Manager / OSI Finance / OSI Admin (+ legacy OSI User). Review = ops roles; finance reports + Cost Entry = Finance/Admin; settings/platform connect/token export = Admin. (Procurement role deferred with procurement module.)
- [x] `Online Store` += `company` + `department` fields (patch `v14` backfills company from OSI Settings).
- [ ] Concurrency: 100 users fine for Frappe/MariaDB; optionally revalidate under §9 load test with isolation hooks on (expected negligible — hooks no-op for unrestricted users, single indexed IN-clause for restricted).

---

## 8. NEW — AI customer service (spec 1.0.1 §2)

**Client requires:** Duoke-AI-style multi-store chat console — mobile, all sites/stores in one place, AI auto-replies keyed to buyer's order-journey stage.

**Have:** ❌ nothing — this is a **new product surface**, not an ERP report.

**Recommendation:** treat as **separate phase / separate module** (possibly separate app talking to OSI data). Needs per-platform chat APIs (Shopee `sellerchat`, etc.), websocket/mobile UX, AI reply engine. _Effort: XL._
- [ ] Confirm with client: launch-blocking or post-launch? (Doc says "可放后期开发、升级" for AI evolution generally — chat module phase should be confirmed explicitly.)
- [ ] If v1: scope minimal read-only unified inbox first (fetch + display + manual reply), AI replies later.

---

## 9. NEW — 1000 orders/day certification (spec 1.0.1 §1)

**Have:**
- ✅ Stress harness: parallel workers, 533 jobs × 5 workers, 0 deadlocks; sequential ~0.44 s/order.
- ⚠️ Not yet run as a formal "1000 orders/day, sustained, with chaos" certification.

**Tasks:** _Risk: Low · Effort: S–M_
- [ ] Scripted cert run: 1000 orders through full pipeline (ingest → review → SO/DN/SI → escrow → reports) in < 24 h wall-clock equivalent, with mock chaos on; record throughput, error rate, DB growth. Store results doc in repo.
- [ ] Repeat at 2–3× for headroom (extensibility ask).

---

## Prioritized roadmap (updated)

**Wave 2 finish (unblocked, small):**
1. §4 COGS manual entry per SKU.
2. §4 `OSI Cost Entry` manual costs + P&L completion.
3. §2 platform + SKU dimensions on summary reports.

**Wave 2.5 — new client requirements, medium:**
4. §1 audit-trail hardening (track_changes + action timeline).
5. §9 1000/day certification run.
6. §6 populate tl/th/vi/ms translations (AI-drafted, spot-checked).

**Wave 3 — large:**
7. §7 roles/permissions/data isolation (design doc first — biggest v1 risk).
8. §8 AI customer service (confirm phase with client; XL).
9. §5 Lazada → TikTok adapters (client-deferred).
10. §3 procurement + replenishment.
11. §6 AI self-evolving translation pipeline.
12. §1 automated 刷单 detector.

---

## Open questions for client (new round)

- **AI customer service:** launch-blocking for v1, or first post-launch upgrade? If v1: which platforms' chat first (Shopee only?)?
- **Multi-company:** are the "multiple e-commerce companies" separate legal entities needing separate ERPNext Companies (separate books), or operating departments under one entity?
- **Partner second-level departments:** what exactly may a partner see — their own stores' orders only?
- **Costs:** manual cost entries — per order, per day-store, or per month-store granularity?
- **100 concurrent users:** all desk users, or mostly mobile/report viewers? (Affects sizing + the chat module.)

---

## Guardrails (carry-over)

- All work stays in `online_store_integration` (OSI extension points only). No `apps/frappe`/`apps/erpnext` edits without explicit ask.
- `migrate` after schema/patch/fixture; `build` after assets; verify at `http://erp.localhost:8000`.
- Shopee `get_shipment_manifest` is unverified — see `SHOPEE_API_NOTES.md`.
- Translations: `python scripts/osi-translations.py merge` mandatory at every commit.
- **Packaging rule:** everything user-visible ships in the app — Script Reports / Notifications / Print Formats / Dashboard Charts / Workspaces as standard module documents; Roles / Workspace Sidebars / Custom HTML Blocks via hooks `fixtures`. Verify with `devtools/packaging_audit.py` (PACKAGING OK on 2026-07-04); site DB must never be the only home of a feature.
