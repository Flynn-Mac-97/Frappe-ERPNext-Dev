# CLAUDE.md

Guidance for Claude Code (claude.ai/code) working in this repository.

**Feature-by-feature build history moved to `DEPLOY_LOG.md`** (every wave, every deploy, every gotcha, with commit hashes). This file carries only what you need to work *today*. When you finish a deploy, append the entry to `DEPLOY_LOG.md` and update "Current state" below — do not grow this file.

## What this project is

**MALACA ERP.** A Frappe/ERPNext app — `online_store_integration`, "OSI" — that syncs Shopee stores into ERPNext and serves a bilingual (中文/EN) seller portal at `/osi-portal`. The client is a Vietnam/Philippines cross-border seller; their warehouse prints Shopee shipping labels through this system every working day, so **label printing and the order worklists are load-bearing** — breaking them stops physical shipping.

Scope source of truth: `MALACA_GAP_ANALYSIS.md`; open client questions in `CLIENT_QUESTIONS.md`; client-facing ZH copies `MALACA_功能进度与待办_客户版.md` + `客户确认问题清单.md`; manual desk-UI QA checklist `UI_UX_REVIEW_CHECKLIST.md`. Repo/machine layout is in "Repo has two layers" and "Three layers" below.

## Current state (2026-08-13 — re-verify, don't trust)

- **Prod** (`www.erp-melaka.com`, site `frontend`) tracks OSI `main`, verified at `219ffe9`, clean tree, identical to local `main`. Re-check before assuming:
  `ssh -i $env:USERPROFILE\.ssh\codex_vps_ed25519 -o IdentitiesOnly=yes root@47.84.1.78 "su - frappe -c 'cd /home/frappe/frappe-bench/apps/online_store_integration && git log --oneline -1 && git status -sb'"`
- **Mode: DEPLOYED**, but still **build + verify on the WSL dev bench first; push/deploy only when the user says so.**
- **ERP sync is ON in stock-only mode**: `OSI Settings.enable_erpnext_sync`=1, `create_sales_invoice`=0 → each order creates a Sales Order + Delivery Note (stock moves), **no Sales Invoice**; returns reverse via return DN. Company `Melaka Erp`, warehouses VN `Warehouse in Mang Chau, Vietnam - ME` and PH `Philippines Manila – Flying Cloud Warehouse - ME`; 8 stores, ~118 products Item-linked, base stock seeded 1000 (`devtools/seed_opening_stock.py`).
- FX seeded on prod: `VND→CNY 0.000258`, `PHP→CNY 0.1098`, backdated 2026-01-01 (`devtools/fx_seed.py`).
- `sync_interval_minutes` = 30 on prod. Pushes are the fast path; 10 would tighten the fallback if the client reports lag.
- **Open:** assign the OSI roles + per-store User Permissions to the real prod portal users. Without a User Permission a portal user sees **every** store.
- Not built yet: AI customer-service module, procurement/replenishment, Lazada + TikTok adapters (Shopee-only v1 by client decision), automated 刷单 detector.

## Rules that bite

Each of these has already cost a broken prod or a wasted day.

1. **`public/osi-portal/app.js` is GENERATED.** Source is `portal_src/*.js` (25 slices), concatenated by `scripts/osi-portal-concat.py`, which `scripts/osi-build.sh` runs before `bench build`. Edit the slices — direct edits to `app.js` are silently overwritten.
2. **Run `python scripts/osi-translations.py merge` before every commit** in the app repo. As you write a new UI string, append it *with its Mandarin* to `translations/zh.pending.csv` as `"Source","中文",""`. Locales: `zh` (primary) + `fil, th, vi, ms, hi, ja, es`. There is no `tl`.
3. **`migrate` after schema/patch/fixture changes; `build` after asset changes.** Exported module docs (Report, Workspace, …) only resync if you **bump their JSON `modified` timestamp** — a stale timestamp silently ships old roles/filters.
4. **Worker-side code needs a worker restart.** Sync, ERP-doc creation and label jobs run in the RQ worker, not the web process. On prod the web self-reloads; **scheduler and worker do not.** After changing an OSI Setting, `bench --site frontend clear-cache` or the worker keeps the stale value. Always `ps` afterwards — duplicate workers have been left running twice.
5. **Read `online_store_integration/SHOPEE_API_NOTES.md` before touching any Shopee API code.** It records real live-API behaviour that the mock does not reproduce (0-based `page_no`, typed shipping-document polls, refund-completed claims reported as `ACCEPTED`, …).
6. **Webhook-driven work runs as `Guest`.** `sync_native_erp_for_order` elevates to Administrator for the sync body and restores the caller in `finally`. `frappe.flags.ignore_permissions` alone does **not** bypass the ERPNext mapper's permission check — this produced 6,385 errors in July.
7. **Stay inside `apps/online_store_integration`.** Don't edit `apps/frappe` or `apps/erpnext`; use OSI extension points. If a task seems to need framework edits, stop and explain why.
8. **Verify visual output visually.** Label stamping has shipped "correct" text that rendered off-canvas — rasterise the PDF and look at it; text-layer assertions are not enough.

## Where to change what

| Task | Path |
|---|---|
| Portal UI | `portal_src/*.js` (**never** `public/osi-portal/app.js`), styles `public/osi-portal/app.css` |
| Portal endpoints, stages, date windows | `api/portal.py` (`_stage`, `STAGE_DATE_BASIS`, `_STAGE_FIELDS`, `_date_window`) |
| Shopee HTTP client | `api/shopee/*.py` (auth, signing, http, order, logistics, product, payment, push, returns, shop) |
| Vendor-neutral logic | `api/services/*.py` · platform vocabulary in `api/adapters/` |
| Order ingest / status mapping | `api/services/order_service.py`, `order_state_service.py` (`PLATFORM_STATUS_MAP`, `normalize_order_status`) |
| ERP docs (SO/DN/SI, reversal) | `api/services/erpnext_sales_service.py` |
| Labels, stamping, print batches | `api/sync.py`, `api/utils/shipping_sku_pdf.py`, `api/print_batch.py` |
| Reports | `report/<name>/` (Script Reports) · registers in `api/dispatch_register.py`, `api/pickup_register.py` |
| Permissions / store isolation | `api/utils/isolation.py` + the `permission_query_conditions` / `has_permission` maps in `hooks.py` |
| Scheduled jobs | `tasks.py` (enqueue only) + `scheduler_events` in `hooks.py` |
| Schema change | `doctype/<name>/*.json` **plus** a patch in `patches/` appended to `patches.txt` |
| Desk (non-portal) JS | `public/js/` + `app_include_js` in `hooks.py` |
| In-app user docs | `www/osi-docs/` (generator `scripts/osi-apidocs.py`) |
| Region/timezone handling | `api/utils/helpers.py` (`REGION_TIMEZONES`, `epoch_to_region_date`, `region_today`, `region_shifted_sql`) |

## Verifying your work

Checks live in `online_store_integration/devtools/` and run on the bench:

```bash
bench --site erp.localhost execute online_store_integration.devtools.<module>.run
```

Nearly every check exposes `run`. Exceptions: `push_check` (`setup`, `forensics`, `stale_push_test`, …), `scenario` (`full_e2e`, `stress_quick`, `diag_one`), `setup` (`connect_and_seed`), `bootstrap` (`bootstrap`), `cert` (`enqueue_1000`, `run_wave`). Grep the file's `def` list if unsure.

| Area | Check |
|---|---|
| Portal endpoints + pages | `portal_check`, `portal_translation_check` |
| Roles + store isolation | `perm_check`, `store_alias_check`, `store_name_check` |
| Labels end-to-end | `label_check`, `stamp_editor_check`, `stamp_overflow_check`, `stamp_stale_probe` |
| Order dates + stages | `ship_date_check` |
| Returns / claims | `returns_check`, `disposition_check` |
| Registers + exports | `report_grain_check`, `batch_export_check`, `sku_col_check` |
| Money | `pnl_check`, `escrow_auto_check`, `recon_check` |
| Platform neutrality | `platform_neutral_check` |
| Pushes / store linking | `push_check`, `link_flow_check` |
| Packaging, docs, audit trail | `packaging_audit`, `docs_check`, `audit_check` |
| Throughput | `cert` (1000/day certification, see `PERF_CERT_1000.md`) |
| **Prod, read-only** | `shopee_live_probe` — live Shopee vs DB per store; safe to run against prod |

**The mock `full_e2e` is NOT a pre-deploy gate** (client decision, 2026-07-23) — it does not mimic real prod Shopee closely enough. Use targeted checks during development, then probe prod after deploying. Real bugs have shipped green on the mock: typed label polls, NULL report periods, 0-based return paging.

## Mock Shopee server

`mock_platform/` — a dev-only FastAPI fake of Shopee v2 (never shipped). Run `uvicorn mockshopee.main:app --port 9000`; on WSL use `mock_platform/start_mock.sh` (**port 9900** — 9000 is Frappe socketio). Routers: auth, shop, order, logistics, payment, returns, plus a `/__control` plane (`stats`, `gen_orders`, `advance`, `reset`) and a Poisson drip simulator that sends signed pushes. No product router. `devtools` refuses to run unless OSI's `api_url` points at a local mock. Build history and the endpoint checklist are in `DEPLOY_LOG.md`.

## What's built

One line per wave; full detail with commits in `DEPLOY_LOG.md`.

- **Shipped before Wave 1** — Shopee order/product sync, SKU label overlay, ERPNext SO/DN/SI, return reversal, multi-currency, HTTP retry/429/token refresh, ZH i18n pipeline.
- **Wave 1** — manual review gate + 刷单 flag (dormant, config-toggled), shipping/return summary reports, multi-locale translation scaffold.
- **Wave 2** — escrow fee ingest, daily P&L, ship-confirm reconciliation, return disposition, per-SKU COGS, `OSI Cost Entry`.
- **Wave 2.5** — audit-trail hardening, 1000/day certification, launch translations, packaging audit.
- **Wave 3** — roles/permissions/store isolation, implementation-status registry, in-app docs + API reference, vendor-neutral adapter seam.
- **Wave 4 (largest, ongoing)** — the `/osi-portal` seller portal and live ops: Shopee push ingest, shipping-label queue and print/reprint, SKU stamping and the visual stamp editor, Shopee-mirror order stages, store-local dates, return/refund claim mirror, store aliases, warehouse registers, Excel export and numbered print/export batches.
- **ERP stock flow** — stock-only mode (SO + DN, no SI), seeded opening stock, the Guest-permission fix.


## Repo has two layers

1. **Root** = provisioning + runbook for a Frappe/ERPNext bench. Not application code.
   - `setup_bench.sh` — builds a bench: `bench init` → `bench get-app erpnext` → `bench get-app private_frappe_codespace` (**a DIFFERENT, unrelated app — NOT OSI**) → `bench new-site` → `install-app`. Stable branch auto-detected from ERPNext git tags (`version-N`) unless `STABLE_BRANCH` set.
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

> Provisioning vs reality: `setup_bench.sh` (`frappe-bench` / `dev.localhost`) and BENCH_STARTUP.md (`/root/frappe_bench`) are both **stale**. They also provision the wrong app: `setup_bench.sh` + root `README.md` get-app `private_frappe_codespace`, which is a different repo from `online_store_integration` — running them does NOT give you a bench with OSI installed. The live WSL bench is `/home/frappe/frappe-bench` + `erp.localhost`, matching the OSI docs and helper scripts.

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

**Translations (multi-locale).** OSI uses the standard Frappe scheme: UI strings wrapped `_()` (Py) / `__()` (JS), translations in `online_store_integration/translations/<lang>.csv` (`"source","译文",""`). Shipped locales (MALACA spec): **zh** (primary, has content) + scaffolded empties `fil, th, vi, ms, hi, ja, es` (**`tl.csv` was renamed `fil.csv` — there is no `tl` locale**) (English is the source language, no CSV). Each locale folds from its own `<lang>.pending.csv` queue. Workflow:
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
VPS does **NOT** run `bench start`/honcho/supervisor. It runs four independently `nohup`+`setsid`-detached components as user `frappe`: **web** (`bench serve --port 8000`, auto-reloads on a Python change), **scheduler** (`bench schedule`, no reloader — restart separately), **worker** (`bench worker --queue short,default,long`, no reloader — restart separately), **socketio**. Deploy: `git pull` → `bench build` (asset changes) → `bench --site frontend migrate` (schema/patch/fixture changes) → restart **scheduler and worker by pid** via `runuser` (web self-reloads). `su -c pkill` hangs — see project memory `vps-prod-process-layout` for the exact commands, and always `ps` afterwards to confirm exactly one worker and one scheduler (duplicates have been left behind twice).

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
`online_store`, `online_product`, `online_sales_order` (+ `online_sales_order_item` child), `osi_settings` (single, admin-tunable config), `osi_sync_log`, `shipping_document_sku_overlay_rule`, `osi_cost_entry`, `online_return_claim`, `osi_print_batch` (+ `osi_print_batch_order` child), `osi_changelog` (+ `osi_changelog_item` child). **13 folders as of 2026-08-13 — glob the directory rather than trusting this list.**

Code layers (`online_store_integration/online_store_integration/`):
- **`api/`** — whitelisted endpoints + integration code. `api/services/` holds vendor-neutral logic (order, order_state, product, sync, token, erpnext_sales, escrow, returns, logistics, disposition — 10 modules as of 2026-08-13; there is no `stock_service`, stock moves via the native Delivery Note). `api/shopee/` isolates Shopee-specific code (auth, signing, http, order, logistics, product, push, returns, …). `api/utils/` helpers. **Keep vendor-specific detail under the vendor folder; shared behavior in services/utils.**
- **`tasks.py`** — scheduler entry points. They only **enqueue** RQ jobs (`frappe.enqueue`, deduplicated by job ID); actual work runs in workers (visible in System > Background Jobs). Config (enabled/intervals/scope) read from the OSI Settings singleton. Wired via `scheduler_events` in `hooks.py` — **10 entries as of 2026-08-13, read hooks.py for the live list**: `sync_changed_stores` (every tick, self-throttles); `notify_new_orders` + `retry_waiting_shipping_labels` (every minute); `refresh_missing_escrow` (*/15min); `refresh_return_claims` (*/30min); `refresh_expiring_tokens` + `refresh_missing_tracking_numbers` + `cleanup_stale_link_stores` (hourly); `cleanup_old_print_batches` + `cleanup_old_sync_logs` (daily 3am).
- **`hooks.py`** — app integration surface: `app_include_js`, `scheduler_events`, `fixtures` (Roles `OSI User` / `OSI Ops Specialist` / `OSI Ops Manager` / `OSI Finance` / `OSI Admin`, Workspace Sidebars `eCommerce` + `OSI Connection Settings Workspace`, several Custom HTML Blocks). Prefer adding behavior here over editing framework code.
- **`patches/`** + `patches.txt` — ordered data migrations (**`v1`…`v26` as of 2026-08-13 — read `patches.txt`, never assume the highest**), split `[pre_model_sync]` / `[post_model_sync]`. New patches append to the correct section. Make idempotent; use Frappe APIs over raw SQL.
- **`fixtures/`** — narrow OSI-only records shipped with the app.
- **`public/`** — desk assets; rebuild after edits.

## Guardrails (from PROJECT.md / AGENTS.md)

- All normal edits stay in `apps/online_store_integration`. Do **not** edit `apps/frappe` or `apps/erpnext` unless the user explicitly asks — use OSI extension points (DocTypes, hooks, patches, fixtures, services, API modules, assets). If a task seems to need framework edits, pause and explain why OSI extension points are insufficient.
- Run `migrate` after schema/patch/fixture changes; `build` after asset changes; verify in browser at `http://erp.localhost:8000`.
- Treat DocType JSON edits as schema changes (verify with `migrate`). For renames/data moves, add a patch, not just JSON.
- Don't commit local HTML captures, DB exports, backups, or private site exports.
- `get_shipment_manifest` **does not exist in the code and is not a real Shopee endpoint** — the dead stubs in `api/shopee/logistics.py` + `api/sync.py` were removed 2026-06-30 (they only returned `unsupported_endpoint`). Don't re-add one without confirming a real endpoint name; see SHOPEE_API_NOTES.md.
- **Module-doc JSON edits (Report/Workspace/etc.) only resync on `migrate` if the JSON `modified` timestamp is bumped** — stale-roles bug hit on report role gating; always bump `modified` when editing exported module docs.
- **`frappe.get_app_path` scrubs hyphenated path segments** (`osi-docs` → `osi_docs`); resolve files under `www/osi-docs/` relative to `__file__` (see `www/osi-docs/api.py`).
