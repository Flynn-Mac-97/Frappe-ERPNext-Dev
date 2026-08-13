# Frappe-ERPNext-Dev

Creates a Frappe bench with:
- Frappe + ERPNext on the latest stable ERPNext release branch
- Custom app: `https://github.com/Flynn-Mac-97/private_frappe_codespace.git`

## Quick start

> **Note:** the custom app this script installs is `private_frappe_codespace`, NOT `online_store_integration` (OSI) — the app actually under active development in this workspace. The live OSI dev bench is the WSL `FrappeBench` bench at `/home/frappe/frappe-bench`, site `erp.localhost`; this script's defaults (`frappe-bench` / `dev.localhost`) do not match it.

Run:

```bash
ADMIN_PASSWORD='YOUR_ADMIN_PASSWORD_HERE' \
MYSQL_ROOT_PASSWORD='YOUR_MARIADB_ROOT_PASSWORD_HERE' \
./setup_bench.sh
```

`ADMIN_PASSWORD` and `MYSQL_ROOT_PASSWORD` must both be at least 12 characters.

Optional overrides:

```bash
STABLE_BRANCH=version-16 \
BENCH_DIR=frappe-bench \
SITE_NAME=dev.localhost \
ADMIN_PASSWORD='YOUR_ADMIN_PASSWORD_HERE' \
MYSQL_ROOT_PASSWORD='YOUR_MARIADB_ROOT_PASSWORD_HERE' \
./setup_bench.sh
```

Dry-run command preview:

```bash
DRY_RUN=1 ./setup_bench.sh
```
