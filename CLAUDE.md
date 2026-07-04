# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## MALACA ERP build tracker (LOCAL-ONLY — no deploy until told)

Scope source of truth: `MALACA_GAP_ANALYSIS.md` (+ client questions in `CLIENT_QUESTIONS.md`). Client-facing ZH copies: `MALACA_功能进度与待办_客户版.md`, `客户确认问题清单.md`. **Keep this tracker current** — tick items as they land.

**Mode: LOCAL ONLY.** Build + test on the WSL dev bench (`erp.localhost`). Do **not** `git push upstream main` or VPS-deploy until the user explicitly says so. (The translations `merge` step still runs at every commit per the rule below.)

### Done (shipped in OSI)
Shopee order/product sync · SKU label overlay · ERPNext SO/DN/SI creation · return reversal (credit note + return DN) · multi-currency (per-currency receivables, fail-loud FX) · HTTP retry/429/token-refresh · ZH i18n pipeline · ERP resync (single batch job) · allow-negative-stock.

### Wave 1 — low risk (building now)
- [x] **Manual review gate + 刷单 flag** (config-toggled). `OSI Settings.require_order_review` (default OFF). `Online Sales Order` fields: `review_status` (pending/approved/rejected/on_hold), `reviewed_by/at`, `is_special_order`, `special_order_reason`; `erp_sync_status` += `awaiting_review`. Gate in `order_service._upsert` holds un-approved/special orders out of ERP doc creation. API `api/review.py` (approve/reject/flag/summary). UI: list bulk actions + form buttons (`_list.js` / `.js`). Patch `v13` (existing orders → approved, never retro-block). **Verified on mock:** 90 pending held, `held_with_sales_order=0`, approve flips pending→approved. zh queued in `zh.pending.csv`.
- [x] **发货 / 退货 summary reports** — Script Reports `OSI Shipping Summary` + `OSI Return Summary` under `report/`. Filters: from/to date, period (Day/Month/Year), store, platform. Group by period × store × currency; cols Period/Store/Region/Warehouse/Currency/Orders(Returns)/Units/Value; total row; CSV/Excel export built-in. **Verified on mock:** shipping 4 rows multi-currency (MYR/PHP/VND), returns 1 row. zh queued.
- [x] **Multi-locale translation scaffold** — `scripts/osi-translations.py` now multi-locale (`merge` folds every `<lang>.pending.csv` → `<lang>.csv`; `scaffold` creates missing locale CSVs; `check` per-locale). Shipped empties `tl/th/vi/ms/hi/ja/es` alongside `zh`. Verified: non-zh fold works (th test). **Wave 1 complete.**

### Wave 2 — medium (money / external API)
- [x] **Escrow fee ingest** — `api/shopee/payment.py` `get_escrow_detail` (real v2) + `api/services/escrow_service.py` (maps `order_income` → Online Sales Order fields: escrow_amount/buyer_total/commission/service/transaction/fees_total/escrow_synced_at/escrow_payload_json) + `api/escrow.py` (single + batch enqueue + summary) + form "Sync Fees" button. Mock route `mockshopee/routers/payment.py`. **Verified on mock:** 75 synced, gross−fees==escrow exact. SHOPEE_API_NOTES Payment section added.
- [x] **Daily P&L report** — Script Report `OSI Profit and Loss`: period Day/Month/Year × store × currency; cols Gross Sales / Platform Fees (escrow) / Net Payout / COGS / Profit / Margin %; COGS = sum(qty × Item.valuation_rate) → 0 until real per-SKU costs loaded (client Q15); ad-spend/opex out of scope. **Verified on mock:** gross−fees==net, 91% margin (pre-COGS).
- [x] **Ship-confirm reconciliation worklist** — Script Report `OSI Ship Confirm Reconciliation` (one row per order, links to OSO/SO/DN/credit note). Buckets: paid-not-shipped (paid, no DN, no shipped_at, not dead) + shipped-then-cancelled (cancelled/refunded with DN or shipped_at; hides already-reversed unless `include_reversed`). Filters: bucket/store/platform/from-to/min_age_days. Summary pills + bucket chart; days>7 highlighted red. Dev check `devtools/recon_check.py`. **Verified on live site data:** 226 orders → 2 paid-not-shipped + 1 shipped-then-cancelled (DN, no CN) correctly flagged. zh queued.
- [x] **Return disposition** (restock / damaged / scrap). OSO fields `return_disposition` + `disposition_stock_entry` (read-only, one-shot — change after stock moved throws); `OSI Settings.damaged_warehouse`. restock = no stock doc (return DN already restocked); damaged = Material Transfer → damaged warehouse; scrap = Material Issue. API `api/disposition.py` (set_disposition/summary) + form Disposition buttons (show when return DN set & undecided). Dev check `devtools/disposition_check.py` (+ `make_returns`/`repair_crosslinked`). **Verified on mock: all 5 checks PASS.** zh queued+merged. **Bonus fix (15dc19a):** existing-doc lookups in `erpnext_sales_service` matched credit notes / return DNs / cancelled docs (return docs copy `sales_order` refs) → crosslinked 9 dev orders, broke reversal with "quantity must be negative number"; now filtered `docstatus < 2 AND is_return = 0`. full_e2e 6/6 PASS post-fix.
- [ ] COGS **manual entry per SKU** (client answer 2026-06-30: hand-keyed, not procurement-derived) → feeds P&L
- [ ] `OSI Cost Entry` doctype — manual ads / domestic+intl logistics / opex / FX costs into P&L (client-confirmed manual input)
- [ ] Platform + SKU dimensions on shipping/return summary reports (client ask)

### Wave 2.5 — new client requirements (spec 1.0.1 + answer sheet, see MALACA_GAP_ANALYSIS.md v2)
- [ ] Audit-trail hardening (track_changes + per-order action timeline; client: 留痕 mandatory)
- [ ] 1000 orders/day certification run (formal, with chaos; harness exists)
- [ ] Populate tl/th/vi/ms translation CSVs (launch languages zh/en/tl/th/vi/ms)
- [x] **Packaging audit** — `devtools/packaging_audit.py`; all reports/notifications/print-format/dashboard-charts/workspaces = standard module docs, roles/sidebars/HTML blocks = fixtures. Fixed: `OSI Connection Settings Workspace` sidebar added to fixtures. **PACKAGING OK** — fresh install reproduces full app.

### Wave 3 — large (client-reprioritized: Lazada/TikTok DEFERRED, Shopee-only v1)
- [ ] **Roles / permissions / data isolation** (Company→Dept→Manager→Specialist, isolation by platform/country/warehouse/dept, ~100 users / ~1000 shops) — design doc first, biggest v1 risk
- [ ] **AI customer service module** (Duoke-AI-style multi-store chat, spec 1.0.1) — XL, phase to be confirmed with client
- [~] **Vendor-neutral refactor** (281e3cd): `api/adapters/` — `PlatformAdapter` ABC + `get_adapter(platform)` registry + `ShopeeAdapter` (thin delegation; Shopee payloads = canonical shape, other adapters translate into it). All neutral code (services/tasks/sync/webhook/auth/pdf-utils) now vendor-import-free; `_sync_stores_job` store query no longer hardcodes shopee. full_e2e 6/6 PASS through seam. **Remaining: Lazada adapter → TikTok adapter** (need client API creds + mock routes).
- [ ] Procurement tracking + replenishment
- [ ] AI self-evolving translation pipeline
- [ ] Automated 刷单 detector

### Offline mock-platform server — `mock_platform/` (dev-only, never shipped)
FastAPI fake of Shopee v2 so OSI builds + stress-tests offline. Boots, seeds shops/orders from `config.yaml`, smoke-tested green. Run: `uvicorn mockshopee.main:app --port 9000` (venv in `mock_platform/.venv`).
- [x] Core server: config-driven shops/items/orders, in-memory state, envelope, chaos middleware (latency / `error_busy` / 429+Retry-After)
- [x] Routers: auth (flat token), shop (get_shop_info), order (list cursor-paginated + detail)
- [x] `/__control` plane: `stats`, `shops`, `gen_orders`, `advance`, `config`, `reset`
- [ ] Routers: product (get_item_list/base_info/model_list), logistics (5), payment (get_escrow_detail)
- [x] Seed runner `online_store_integration/online_store_integration/_mock_seed.py` (DEV-ONLY, gitignored in OSI repo; run via `bench --site erp.localhost execute online_store_integration._mock_seed.run`). Helpers: `.report` (snapshot), `.diag` (one-order traceback), `.fixschema`. Runs on the mock at **port 9900** (9000 = Frappe socketio — do NOT use).
- [x] **End-to-end PASS:** mock → OSI = 3 stores × 25 = 75 orders, 44 products auto-created, 0 errors, multi-currency (MYR/VND/PHP). Found + fixed a latent OSI bug: `product_service.py` read `item_row.product_image` (an `Image` field = no DB column) → `AttributeError` on the new-product path; now safe `.get()`.
- WSL run scripts in `mock_platform/`: `start_mock.sh` (port 9900), `wsl_poll.sh`, `wsl_poll_bench.sh`, `killport.sh`. Mock venv: `/home/frappe/osi-mock-venv`. Mock served from `/mnt/c/...`.
- [x] **Mock route** `payment.py` (`get_escrow_detail`) + control `advance_bulk` (lifecycle driver).
- [x] **Committed E2E + stress harness** — `online_store_integration/devtools/` (NOT gitignored; guarded by `assert_mock_env` → refuses unless OSI `api_url` is local). Run via bench:
  - `devtools.setup.connect_and_seed` — point OSI at mock + seed Online Stores
  - `devtools.bootstrap.bootstrap` — idempotent ERPNext seed so SO/DN/SI creation works: back-dated Currency Exchange (mock-currency→company, rates overridable), allow-stale FX, allow-negative-stock, auto-create items + per-currency receivables, OSI ERP mapping, is_billing_contact drift check
  - `devtools.scenario.full_e2e` — **PASS/FAIL per stage:** orders→gate→approve→SO/DN/SI→escrow→return reversal→reports. **Verified 6/6 PASS.**
  - `devtools.scenario.stress` (kwargs: orders/batch/return_pct/latency_ms/error_rate) + `stress_quick`. Sequential throughput: approve→SO/DN/SI ~0.44s/order.
  - **Parallel-worker mode** (real multi-worker lock contention): `devtools.scenario.stress_parallel_enqueue` enqueues one ERP-creating job per order onto the `long` queue (`devtools/workers.py:approve_and_sync_one`); launch concurrency with `mock_platform/stress_workers.sh long N`; drain-poll with `mock_platform/stress_poll.sh`; report via `parallel_status` (queued/finished/failed + Error-Log deadlock/lock-wait scan). **Verified: 533 jobs × 5 workers → 0 deadlocks, 0 lock-waits, 0 failures.** Crank workers/orders/chaos to find the ceiling. (pkill of `bench worker --queue long` also stops the bench's own long worker → restart bench to restore.)
- [ ] Routers: product (get_item_list/base_info/model_list), logistics (5).

## Repo has two layers

1. **Root** = provisioning + runbook for a Frappe/ERPNext bench. Not application code.
   - `setup_bench.sh` — builds a bench: `bench init` → `bench get-app erpnext` → `bench get-app private_frappe_codespace` (the custom app) → `bench new-site` → `install-app`. Stable branch auto-detected from ERPNext git tags (`version-N`) unless `STABLE_BRANCH` set.
   - `README.md` — quick start for `setup_bench.sh`.
   - `BENCH_STARTUP.md` — **canonical runbook** for the local WSL bench (start, verify, asset/socket troubleshooting, VPS deploy). Read before starting/diagnosing the running bench.
2. **`online_store_integration/`** = the custom Frappe app ("OSI"). Its own git repo. Real development happens here. Has its own deep docs — read them, don't duplicate:
   - `PROJECT.md` — canonical OSI guide (data model, patches, fixtures, commands, guardrails).
   - `AGENTS.md` — shortest command reference.
   - `SHOPEE_API_NOTES.md` — **read before touching any Shopee API code.**

## Three layers / where things live (verified)

1. **Windows local clone** = `online_store_integration/` in this repo. The `.git` lives here (remote `upstream` → `github.com/Flynn-Mac-97/online_store_integration.git`, branch `main`). **All editing + all git happens here.**
2. **WSL dev bench** = distro `FrappeBench`, bench `/home/frappe/frappe-bench`, runs as user `frappe`, site `erp.localhost`. Its `apps/online_store_integration` is a **symlink to the Windows clone** → editing on Windows changes the WSL app instantly (no copy). There is no separate "WSL git". (Avoid the unrelated `online_store_integration.backup.*` dir in WSL.)
3. **VPS prod** = `47.84.1.78`, bench `/home/frappe/frappe-bench`, user `frappe`, site `frontend`. Same `upstream` remote. Deployed via `git pull`.

> Provisioning vs reality: `setup_bench.sh` (`frappe-bench` / `dev.localhost`) and BENCH_STARTUP.md (`/root/frappe_bench`) are both **stale**. The live WSL bench is `/home/frappe/frappe-bench` + `erp.localhost`, matching the OSI docs and helper scripts.

## Delegation & token budget (orchestrator policy)

Principle: keep bulk text (full files, big diffs, failed-edit echoes) OUT of the Opus orchestrator context. Opus plans/routes/decides/talks to user + runs cheap shell. Push reading, editing, searching, reviewing into cheap caveman subagents — their output is caveman-compressed (~60% smaller). Opus holds only intent + compressed receipts.

Routing (model = `Agent` tool `model` override):

| Task | Agent | Model |
|------|-------|-------|
| Locate code / "where is X" / map dir | `caveman:cavecrew-investigator` | haiku |
| Broad multi-area search (conclusion only) | `Explore` | haiku |
| 1–2 file surgical edit | `caveman:cavecrew-builder` | sonnet |
| Diff / branch / PR review | `caveman:cavecrew-reviewer` | haiku |
| 3+ file change | orchestrator splits → many `cavecrew-builder` | sonnet |
| Build / migrate / restart / curl poll | orchestrator `Bash` direct | — |
| Verify behavior end-to-end | `claude` / `general-purpose` | sonnet |

Loop: 1) locate (1–3 investigators parallel → `file:line` map; skip if paths known). 2) design — Opus decides scope + acceptance; no full-file reads, ranged `Read` only if truly needed. 3) edit — `cavecrew-builder`, one per 1–2 files; parallel + `isolation: worktree` when no cross-file deps, serial when dependent. 4) review — `cavecrew-reviewer`. 5) integrate — Opus runs build/migrate/restart, polls ready. 6) verify.

Builder brief always includes: exact target, acceptance criteria, compressed constraints (e.g. SHOPEE_API_NOTES rule), and **"match on small unique anchors; on match-fail shrink the anchor, never resend the whole block; for tail-of-file rewrites use `head -n N` + append."** (This is the rule that would have killed the 250-line failed-edit waste.)

Don't delegate: trivial one-liners (faster inline), decisions/design/user comms (Opus only), anything already small + known. **Rule of thumb: delegate when the task would otherwise dump >~100 lines of file/diff text into Opus context.** Do not spawn agents the user didn't ask for when inline is cheaper.

## End-to-end workflow (all commands verified working)

PowerShell↔WSL/SSH nested quoting is fragile (see hazards below). These forms work:

**1. Start WSL dev bench** — `bench start` must stay foreground or the WSL distro shuts down. Launch it as a background process that holds the session open:
```powershell
# run_in_background; keeps WSL alive while bench serves
wsl -d FrappeBench -u root -- su - frappe -c '/home/frappe/start-bench.sh'
```
Wait until ready (poll, don't guess):
```powershell
wsl -d FrappeBench -u root -- bash -lc 'curl -s -o /dev/null -w "%{http_code}\n" --max-time 5 http://erp.localhost:8000/api/method/ping'   # 200 = up
```

**2. Build on WSL after edits** — use a `frappe` *login* shell + full bench path (don't hand-export PATH through nested quotes, it breaks):
```powershell
wsl -d FrappeBench -u root -- su - frappe -c 'cd /home/frappe/frappe-bench && /home/frappe/.local/bin/bench build --app online_store_integration'
```
For Python/schema/fixture changes use `migrate` instead/also: `... && /home/frappe/.local/bin/bench --site erp.localhost migrate`.

**3. Push to git (from the Windows clone only)** — git lives in the Windows folder; the symlink means WSL needs nothing:
```powershell
# from C:\...\Frappe-ERPNext-Dev\online_store_integration
# ALWAYS first: fold queued Mandarin translations into zh.csv (see Translations below)
python scripts/osi-translations.py merge
git add -A; git commit -m "..."; git push upstream main
```

**Translations (multi-locale).** OSI uses the standard Frappe scheme: UI strings wrapped `_()` (Py) / `__()` (JS), translations in `online_store_integration/translations/<lang>.csv` (`"source","译文",""`). Shipped locales (MALACA spec): **zh** (primary, has content) + scaffolded empties `tl, th, vi, ms, hi, ja, es` (English is the source language, no CSV). Each locale folds from its own `<lang>.pending.csv` queue. Workflow:
- **While coding:** the moment you add a new translatable string, append it *with its Mandarin* to `online_store_integration/translations/zh.pending.csv` as `"Source","中文",""`. This is the always-on queue so you never rescan the whole codebase at commit. Auto-fill the Mandarin yourself (no separate review). Other locales fill in later (translator / future AI step) via their own `<lang>.pending.csv`.
- **At every commit (mandatory first step):** `python scripts/osi-translations.py merge` — folds **every** `<lang>.pending.csv` into its `<lang>.csv` (updates matching keys in place, appends new ones; never reorders existing rows), then clears the queues. Commit the changed `<lang>.csv` + reset `<lang>.pending.csv` together.
- `python scripts/osi-translations.py check` lists what's queued (per locale) without merging. `... scaffold` creates any missing locale CSVs.
- Deploy needs nothing extra — the `<lang>.csv` files are pulled by the normal VPS deploy; translations load after the existing `bench build` / `bench --site … clear-cache`.

**4. Deploy on VPS — pull + build:**
```powershell
# inspect first — prod may have uncommitted hotfixes
ssh -i $env:USERPROFILE\.ssh\codex_vps_ed25519 -o IdentitiesOnly=yes root@47.84.1.78 "su - frappe -c 'cd /home/frappe/frappe-bench/apps/online_store_integration && git status -sb && git log --oneline -2'"
# pull (resolve any dirty state first — see guardrail) + build with explicit node/nvm PATH
ssh -i $env:USERPROFILE\.ssh\codex_vps_ed25519 -o IdentitiesOnly=yes root@47.84.1.78 "su - frappe -c 'cd /home/frappe/frappe-bench/apps/online_store_integration && git pull upstream main'"
ssh -i $env:USERPROFILE\.ssh\codex_vps_ed25519 -o IdentitiesOnly=yes root@47.84.1.78 "su - frappe -c 'cd /home/frappe/frappe-bench && export PATH=/home/frappe/.nvm/versions/node/v24.15.0/bin:/usr/local/bin:/usr/bin:/bin:/home/frappe/.local/bin && bench build --app online_store_integration'"
```
VPS is **supervisorless** (runs plain `bench start`, no supervisor). Deploy is just: `git pull` → `bench build` → restart the `bench start` process. Run `bench --site frontend migrate` only when the pull changed DocType schema/patches/fixtures. `build` alone refreshes assets but not running Python — a Python-only change needs the `bench start` restart to take effect.

> **VPS guardrail:** the prod working tree often has uncommitted hotfixes made directly on the box. Always `git status` + `git diff` before pulling. If the local commit already supersedes them, discarding is safe (`git checkout -- <files>`), but confirm with the user before destroying prod-only changes — a clean fast-forward whose diff stat matches the discarded files confirms they were the same work.

## PowerShell → WSL / SSH quoting hazards (learned the hard way)
- Wrap the remote command so PowerShell doesn't expand it: outer `'single quotes'` for `bash -lc '...'`. PowerShell tries to parse `$var:` as a drive ref — a bare `$i:` in a double-quoted string is a parse error.
- `nohup ... &` inside a one-shot `wsl -- bash -lc` does **not** survive — the distro exits when the command returns. Hold the session open with a foreground `run_in_background` process instead.
- Don't `export PATH=...:$PATH` through layered `su -c '...'` quotes; the `$PATH`/`;` get mangled. Use `su - frappe` (login shell loads PATH) + absolute `bench` path, or a fully literal `export PATH=...` with no `$PATH`.
- Loops/`$()`/multiple `;` rarely survive the PowerShell→WSL hop. For "wait until ready", poll with a single `curl` in a Bash `run_in_background` until-loop rather than a bash `for`/`while` over wsl.
- The `localhost proxy ... not mirrored` WSL stderr line is harmless noise.

## Common commands (run from bench root, inside WSL/VPS as user `frappe`)

OSI ships helper scripts (preferred low-token path):

```bash
apps/online_store_integration/scripts/osi-migrate.sh   # bench --site erp.localhost migrate
apps/online_store_integration/scripts/osi-build.sh     # bench build --app online_store_integration
apps/online_store_integration/scripts/osi-smoke.sh     # list-apps + execute frappe.utils.now
apps/online_store_integration/scripts/osi-test.sh      # run-tests --app online_store_integration
```

Raw equivalents and others:

```bash
bench --site erp.localhost migrate                       # after schema/patch/fixture changes
bench build --app online_store_integration               # after JS/CSS/image changes
bench --site erp.localhost run-tests --app online_store_integration
bench --site erp.localhost run-tests --module online_store_integration.<...>.test_<x>   # single module
bench --site erp.localhost export-fixtures               # after UI changes meant to ship
bench --site erp.localhost console                       # Python console with site context
bench --site erp.localhost execute dotted.path.to.method
bench --site erp.localhost mariadb                       # SQL shell (read-only during investigation)
bench --site erp.localhost clear-cache
```

Lint/format: `ruff` (config in `online_store_integration/pyproject.toml`, tab indent, double quotes, line-length 110). Pre-commit config at `online_store_integration/.pre-commit-config.yaml`.

## OSI architecture (the part that needs multiple files to grasp)

Frappe is **metadata-driven**: business objects are DocTypes (folder of JSON metadata + optional `.py` controller + `.js`). Tables are `tab<DocType Name>`. Single DocTypes (`"issingle": 1`, e.g. **OSI Settings**) store values in `tabSingles`, not a row-per-doc table. Never alter DocType tables with raw SQL — change metadata, then `migrate`.

Core DocTypes (`online_store_integration/online_store_integration/doctype/`):
`online_store`, `online_product`, `online_sales_order` (+ `online_sales_order_item` child), `osi_settings` (single, admin-tunable config), `osi_sync_log`, `shipping_document_sku_overlay_rule`.

Code layers (`online_store_integration/online_store_integration/`):
- **`api/`** — whitelisted endpoints + integration code. `api/services/` holds vendor-neutral logic (order, product, stock, sync, token, erpnext_sales). `api/shopee/` isolates Shopee-specific code (auth, signing, http, order, logistics, product, push, returns, …). `api/utils/` helpers. **Keep vendor-specific detail under the vendor folder; shared behavior in services/utils.**
- **`tasks.py`** — scheduler entry points. They only **enqueue** RQ jobs (`frappe.enqueue`, deduplicated by job ID); actual work runs in workers (visible in System > Background Jobs). Config (enabled/intervals/scope) read from the OSI Settings singleton. Wired via `scheduler_events` in `hooks.py`: `sync_changed_stores` (every tick, self-throttles), `refresh_expiring_tokens` (hourly), `cleanup_old_sync_logs` (daily 3am).
- **`hooks.py`** — app integration surface: `app_include_js`, `scheduler_events`, `fixtures` (Role `OSI User`, Workspace Sidebar `eCommerce`, several Custom HTML Blocks). Prefer adding behavior here over editing framework code.
- **`patches/`** + `patches.txt` — ordered data migrations (`v1`…`v9`), split `[pre_model_sync]` / `[post_model_sync]`. New patches append to the correct section. Make idempotent; use Frappe APIs over raw SQL.
- **`fixtures/`** — narrow OSI-only records shipped with the app.
- **`public/`** — desk assets; rebuild after edits.

## Guardrails (from PROJECT.md / AGENTS.md)

- All normal edits stay in `apps/online_store_integration`. Do **not** edit `apps/frappe` or `apps/erpnext` unless the user explicitly asks — use OSI extension points (DocTypes, hooks, patches, fixtures, services, API modules, assets). If a task seems to need framework edits, pause and explain why OSI extension points are insufficient.
- Run `migrate` after schema/patch/fixture changes; `build` after asset changes; verify in browser at `http://erp.localhost:8000`.
- Treat DocType JSON edits as schema changes (verify with `migrate`). For renames/data moves, add a patch, not just JSON.
- Don't commit local HTML captures, DB exports, backups, or private site exports.
- The Shopee `get_shipment_manifest` endpoint in `api/shopee/logistics.py` + `api/sync.py` is **unverified / likely invalid** — see SHOPEE_API_NOTES.md before relying on it.
