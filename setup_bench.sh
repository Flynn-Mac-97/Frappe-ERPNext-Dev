#!/usr/bin/env bash
set -euo pipefail

BENCH_DIR="${BENCH_DIR:-frappe-bench}"
SITE_NAME="${SITE_NAME:-dev.localhost}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-root}"
CUSTOM_APP_REPO="${CUSTOM_APP_REPO:-https://github.com/Flynn-Mac-97/private_frappe_codespace.git}"
DRY_RUN="${DRY_RUN:-0}"

run_cmd() {
  if [ "${DRY_RUN}" = "1" ]; then
    printf '[dry-run] %q ' "$@"
    printf '\n'
  else
    "$@"
  fi
}

if [ -n "${STABLE_BRANCH:-}" ]; then
  STABLE_BRANCH="${STABLE_BRANCH}"
else
  STABLE_BRANCH="$(
    python3 - <<'PY'
import json
import re
import urllib.request

with urllib.request.urlopen("https://api.github.com/repos/frappe/erpnext/releases/latest", timeout=15) as r:
    data = json.load(r)

tag = data["tag_name"]
match = re.match(r"v?(\d+)\.", tag)
if not match:
    raise SystemExit(f"Could not derive stable branch from tag: {tag}")

print(f"version-{match.group(1)}")
PY
  )"
fi

run_cmd bench init "${BENCH_DIR}" --frappe-branch "${STABLE_BRANCH}"
if [ "${DRY_RUN}" != "1" ]; then
  cd "${BENCH_DIR}"
fi

run_cmd bench get-app erpnext --branch "${STABLE_BRANCH}"
run_cmd bench get-app private_frappe_codespace "${CUSTOM_APP_REPO}"

run_cmd bench new-site "${SITE_NAME}" --admin-password "${ADMIN_PASSWORD}" --mariadb-root-password "${MYSQL_ROOT_PASSWORD}"
run_cmd bench --site "${SITE_NAME}" install-app erpnext
run_cmd bench --site "${SITE_NAME}" install-app private_frappe_codespace

echo "Setup complete."
echo "Bench dir: ${BENCH_DIR}"
echo "Site: ${SITE_NAME}"
echo "Stable branch: ${STABLE_BRANCH}"
