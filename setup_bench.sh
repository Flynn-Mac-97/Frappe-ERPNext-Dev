#!/usr/bin/env bash
set -euo pipefail

BENCH_DIR="${BENCH_DIR:-frappe-bench}"
SITE_NAME="${SITE_NAME:-dev.localhost}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-$(python3 -c 'import secrets; print(secrets.token_urlsafe(16))')}"
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-$(python3 -c 'import secrets; print(secrets.token_urlsafe(16))')}"
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

detect_stable_branch_from_tags() {
  local latest_tag latest_major
  latest_tag="$(
    git ls-remote --tags --refs https://github.com/frappe/erpnext.git 'v*' \
      | awk -F/ '{print $3}' \
      | sed 's/^v//' \
      | sort -V \
      | tail -n 1
  )"
  latest_major="$(printf '%s' "${latest_tag}" | cut -d. -f1)"
  if [ -n "${latest_major}" ]; then
    printf 'version-%s\n' "${latest_major}"
  fi
}

if [ -z "${STABLE_BRANCH:-}" ]; then
  STABLE_BRANCH="$(detect_stable_branch_from_tags || true)"
fi

if [ -z "${STABLE_BRANCH:-}" ]; then
  echo "Unable to auto-detect stable branch. Set STABLE_BRANCH (for example: version-16)." >&2
  exit 1
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
if [ "${DRY_RUN}" = "1" ]; then
  echo "Admin password: ${ADMIN_PASSWORD}"
  echo "MariaDB root password: ${MYSQL_ROOT_PASSWORD}"
else
  echo "Admin password (generated if not supplied): ${ADMIN_PASSWORD}"
  echo "MariaDB root password (generated if not supplied): ${MYSQL_ROOT_PASSWORD}"
fi
