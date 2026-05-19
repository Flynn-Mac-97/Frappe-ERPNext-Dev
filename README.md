# Frappe-ERPNext-Dev

Creates a Frappe bench with:
- Frappe + ERPNext on the latest stable ERPNext release branch
- Custom app: `https://github.com/Flynn-Mac-97/private_frappe_codespace.git`

## Quick start

Run:

```bash
./setup_bench.sh
```

Optional overrides:

```bash
STABLE_BRANCH=version-15 \
BENCH_DIR=frappe-bench \
SITE_NAME=dev.localhost \
ADMIN_PASSWORD=admin \
MYSQL_ROOT_PASSWORD=root \
./setup_bench.sh
```

Dry-run command preview:

```bash
DRY_RUN=1 ./setup_bench.sh
```
