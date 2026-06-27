# MALACA ERP 1.0 — Gap Analysis & Task List

**Source spec:** `MALACA ERP 1.0.docx` (draft 2026-06-27, 王仲征 / 厦门美瑞传芳贸易公司)
**Current implementation:** `online_store_integration/` (OSI) — a Frappe/ERPNext custom app, Shopee-only today.
**This doc maps spec → what exists → gaps → buildable tasks**, ordered low-risk first.

Status legend: ✅ done · ⚠️ partial · ❌ missing
Risk = blast radius if it breaks. Effort = rough build size (S < 1 day, M 1–3 days, L 1–2 weeks, XL multi-week).

---

## 0. Spec at a glance

| Spec area | Intent |
|-----------|--------|
| Markets | PH, TH, VN, MY, SG, JP, US, EU |
| Languages | ZH/EN/Filipino/Thai/Vietnamese/Malay/Hindi/JP/Spanish — accurate, ideally **AI self-evolving** |
| Platforms | **Phase 1:** Shopee, Lazada, TikTok · **Phase 2:** US/EU platforms |
| Core purpose | Multi-site / multi-platform / multi-store: fetch → analyze → classify → process orders; finance, procurement, warehouse. Kill manual/error/no-system pain. |
| Flow described | Order → review → waybill+label(SKU stamp) → ship-confirm → inventory move → summaries → procurement → finance P&L |

---

## 1. Orders (订单)

**Spec requires:**
1. Manual order review after ingest — check stock + order errors. **Single** AND **batch** review.
2. Reserve **special-order (刷单 / brushing)** handling — flag + analyze/process fraud-like data separately.
3. After review → request waybill no.; platform auto-assigns carrier → **print label with SKU stamped** at country-correct position (no platform-format violation).
4. Track ship success/failure (customer cancels mid-way; carrier miss-ships).

**Have:**
- ✅ Order ingest from Shopee → `Online Sales Order` (status, payment, fulfillment, financials, customer, logistics, items).
- ✅ SKU stamping on shipping labels — `Shipping Document SKU Overlay Rule` + `api/utils/shipping_sku_pdf.py` (per-region coords).
- ✅ ERP doc creation on sync (SO/DN/SI) via `erpnext_sales_service.py`.
- ✅ `platform` field enum already allows `lazada/tiktok` (data model ready; no adapters).

**Gaps + tasks:**
- [ ] ❌ **Manual review gate** — no approve step; orders flow straight to ERP. _Risk: Med · Effort: M_
  - Add `review_status` (pending/approved/rejected/hold) + `reviewed_by`/`reviewed_at` to `Online Sales Order`.
  - Gate `enable_erpnext_sync` doc creation behind `review_status == approved` (config toggle to keep auto-approve for back-comfrom).
  - List-view bulk action **"Approve selected"** + single-doc button. (Pattern already used: `online_sales_order_list.js` "Resync ERP".)
- [ ] ❌ **Special-order / 刷单 flag** — none. _Risk: Low · Effort: S→M_
  - Phase 1 (S): manual `is_special_order` + `special_order_reason` checkbox/field; excluded from finance + inventory rollups.
  - Phase 2 (M): heuristic detector (same buyer/address burst, instant-cancel, abnormal qty) raising the flag automatically.
- [ ] ⚠️ **Waybill / ship-confirm tracking** — fields exist (`tracking_number`, `shipped_at`, `delivered_at`) but no active reconciliation of "did it actually ship / get cancelled mid-way". _Risk: Med · Effort: M_
  - Pull Shopee logistics + order-status deltas on sync; surface `fulfillment_status` mismatches (paid-but-not-shipped, shipped-then-cancelled) as a worklist.
- [ ] ⚠️ **SKU label coverage** — overlay exists for Shopee region formats; confirm each target country format covered as markets expand. _Risk: Low · Effort: S each._

---

## 2. Inventory (库存)

**Spec requires:**
1. Manual stock master entry — name, features, specs, SKU, **bin location (库位)**, qty, unit price (pro-WMS grade).
2. Auto stock change on ship; failed-delivery handling — returned? intact? re-shelf vs damaged/scrap.
3. Per-site / per-warehouse **daily 发货汇总表 (Shipping Summary)** + **退货汇总表 (Return Summary)**; roll up monthly/yearly; export.
4. Inventory feeds sales/procurement/logistics/market decisions.

**Have:**
- ✅ ERPNext native stock: ship → Delivery Note decrements warehouse qty; multi-warehouse + Bin built into ERPNext.
- ✅ Return reversal — `_reverse_native_erp_for_order` (credit note + return delivery note).
- ✅ `online_product` mirror (stock_qty, sku, item_code→ERPNext Item, low_stock_threshold).
- ✅ `allow_negative_stock` enabled on prod (orders post before stock seeded).

**Gaps + tasks:**
- [ ] ❌ **Bin location (库位) surfaced** — ERPNext has Warehouse/Bin, but no MALACA-grade bin-level pick location on the product/stock view. _Risk: Low · Effort: M_
  - Decide: use ERPNext Warehouse hierarchy as bins vs add explicit `bin_location` field. Recommend ERPNext-native first; custom field only if pickface granularity needed.
- [ ] ❌ **Failed-delivery disposition flow** — return reversal exists, but no "intact → re-shelf vs damaged → scrap" decision capture. _Risk: Med · Effort: M_
  - Add return disposition (`restock`/`damaged`/`scrap`) driving the right ERPNext stock entry (restock to sellable vs write-off warehouse).
- [ ] ❌ **发货汇总表 / 退货汇总表 reports** — **no `report/` dir exists at all.** _Risk: Low · Effort: M_
  - Build Query/Script Reports: Shipping Summary + Return Summary, grouped by site/warehouse, with day/month/year filters + export (ERPNext gives CSV/XLSX free).
- [ ] ⚠️ **Stock master manual entry** — ERPNext Item form covers it; gap is a MALACA-tailored entry UX if the native form is too heavy. _Risk: Low · Effort: S→M (UX only)._

---

## 3. Procurement (采购)

**Spec requires:** track product purchase, domestic logistics, international logistics, inbound time, inbound qty.

**Have:**
- ✅ ERPNext native Purchasing (Purchase Order / Receipt / Supplier) exists in the bench — **not yet wired into OSI or used by MALACA flow.**

**Gaps + tasks:**
- [ ] ❌ **Procurement tracking surface** — nothing in OSI. _Risk: Low · Effort: M→L_
  - Phase 1 (M): lean on ERPNext PO/PR; add domestic-vs-international logistics stage fields + inbound ETA/actual on PR.
  - Phase 2 (L): replenishment suggestions from inventory + sales velocity (ties to §2/§4 data).

---

## 4. Finance (财务)

**Spec requires:** daily P&L from order+inventory. Logic: `sales − commission − ad fee − tax − product cost − logistics cost − opex → profit/loss amount + ratio`.

**Have:**
- ✅ Sales recorded as ERPNext Sales Invoices (revenue + tax captured).
- ✅ Multi-currency posting (per-currency Receivable accounts, fail-loud FX).
- ⚠️ Commission/shipping/escrow fees: Shopee escrow API researched (`get_escrow_detail`) but **payment.py is a stub** — fees not yet ingested.

**Gaps + tasks:**
- [ ] ❌ **Marketplace fee ingest (escrow)** — commission, service fee, transaction fee, shipping subsidy not pulled. _Risk: Med · Effort: M_ — **prerequisite for real P&L.**
  - Implement `get_escrow_detail` in `api/shopee/payment.py`; map fees onto the order / a fee ledger.
- [ ] ❌ **Product cost (COGS)** — relies on ERPNext valuation; needs item costs seeded (today stock is negative/unseeded). _Risk: Med · Effort: M (data) + S (wiring)._
- [ ] ❌ **Ad fee + opex inputs** — no source. _Risk: Low · Effort: M_ — manual entry doctype or import; allocation rules.
- [ ] ❌ **Daily P&L dashboard/report** — no finance rollup view. _Risk: Low · Effort: M_
  - Build once fee + COGS inputs land: per-day/site/platform P&L = revenue − (commission+ad+tax+COGS+logistics+opex), amount + ratio. ERPNext Dashboard Chart / Script Report.

---

## 5. Platforms — Lazada & TikTok (Phase 1 breadth)

**Spec requires:** Phase 1 = Shopee **+ Lazada + TikTok**. Phase 2 = US/EU.

**Have:**
- ✅ Shopee adapter complete (`api/shopee/`: auth, signing, http+retry, order, product, logistics, push).
- ✅ Data model is platform-agnostic (`platform` enum already lists lazada/tiktok/shopify).

**Gaps + tasks:**
- [ ] ❌ **Lazada adapter** — _Risk: Med · Effort: L._ New `api/lazada/` mirroring shopee module shape (auth/sign/http/order/product/logistics); reuse vendor-neutral `services/`.
- [ ] ❌ **TikTok Shop adapter** — _Risk: Med · Effort: L._ Same shape under `api/tiktok/`.
- [ ] Architectural prep (do before either adapter, **S→M**): confirm `services/` + `Online Sales Order`/`Online Product` are truly vendor-neutral; extract any Shopee assumptions leaking into shared code. Low risk, high leverage.

---

## 6. Localization / Translation (系统语言)

**Spec requires:** 9 languages, accurate, ideally **AI self-evolving** translation.

**Have:**
- ✅ Standard Frappe i18n: `_()`/`__()` + `translations/zh.csv`; commit-time merge via `scripts/osi-translations.py` + `zh.pending.csv` queue (auto-filled Mandarin).
- ⚠️ Only ZH today.

**Gaps + tasks:**
- [ ] ❌ **Add target-language CSVs** — Filipino/Thai/Vietnamese/Malay/JP/ES etc. _Risk: Low · Effort: M (per language, mostly content)._ Extend the existing pending-queue → merge pipeline to multi-locale.
- [ ] ❌ **"AI self-evolving" translation** — _Risk: Low · Effort: M→L · Decision needed._ Pipeline that auto-drafts new-string translations across all locales (Claude) at commit, human-spot-check. Natural extension of `osi-translations.py`. **Confirm scope with user before building.**

---

## Prioritized roadmap (low-risk first, per your steer)

**Wave 1 — low risk, high clarity (mostly additive, no money math):**
1. §2 发货/退货 summary reports (`report/` Script Reports) — visible value, zero blast radius.
2. §1 special-order/刷单 manual flag + exclusion from rollups.
3. §1 manual review gate (config-toggled so it can't break existing auto-flow).
4. §6 multi-locale CSV scaffolding.

**Wave 2 — medium risk (touches money / external APIs):**
5. §4 escrow fee ingest (`payment.py`) — unblocks real finance.
6. §1 ship-confirm reconciliation worklist.
7. §2 return disposition (restock/damaged/scrap).
8. §4 COGS seeding + daily P&L report.

**Wave 3 — large (new platforms / intelligence):**
9. §5 vendor-neutral refactor → Lazada adapter → TikTok adapter.
10. §3 procurement tracking + replenishment.
11. §6 AI self-evolving translation pipeline.
12. §1 automated 刷单 detector.

---

## Decisions needed from you (block some tasks)

- **Review gate:** default-on (every order waits for approval) or default-off/opt-in per store? (Affects current auto-sync prod flow.)
- **Bin location:** ERPNext Warehouse hierarchy as bins, or explicit pickface `bin_location` field?
- **AI translation:** in-scope now, or keep manual auto-fill? Which engine/budget?
- **Lazada/TikTok:** real seller API credentials available to build/test against, or model-only stubs for now?
- **Finance:** escrow fee ingest needs **no new creds** (same Shopee token as order sync) — it's a build task, not a client blocker. Remaining finance unknowns for the client = **COGS source** + **ad/opex source**.

---

## Guardrails (carry-over)

- All work stays in `online_store_integration` (OSI extension points: DocTypes, hooks, patches, fixtures, services, API, assets). No `apps/frappe`/`apps/erpnext` edits without explicit ask.
- `migrate` after schema/patch/fixture; `build` after assets; verify at `http://erp.localhost:8000`.
- Shopee `get_shipment_manifest` is unverified — see `SHOPEE_API_NOTES.md` before relying on it.
- Translations: `python scripts/osi-translations.py merge` is the mandatory first step of every commit.
