# Frappe-ERPNext-Dev

Creates a Frappe bench with:
- Frappe + ERPNext on the latest stable ERPNext release branch
- Custom app: `https://github.com/Flynn-Mac-97/private_frappe_codespace.git`

## Quick start

Run:

```bash
ADMIN_PASSWORD='YOUR_ADMIN_PASSWORD_HERE' \
MYSQL_ROOT_PASSWORD='YOUR_MARIADB_ROOT_PASSWORD_HERE' \
./setup_bench.sh
```

`ADMIN_PASSWORD` and `MYSQL_ROOT_PASSWORD` must both be at least 12 characters.

Optional overrides:

```bash
STABLE_BRANCH=version-15 \
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
