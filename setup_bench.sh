#!/usr/bin/env bash
set -euo pipefail

BENCH_DIR="${BENCH_DIR:-frappe-bench}"
SITE_NAME="${SITE_NAME:-dev.localhost}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-}"
CUSTOM_APP_REPO="${CUSTOM_APP_REPO:-https://github.com/Flynn-Mac-97/private_frappe_codespace.git}"
ERPNEXT_REPO="${ERPNEXT_REPO:-https://github.com/frappe/erpnext.git}"
DRY_RUN="${DRY_RUN:-0}"

is_dry_run() {
  case "${DRY_RUN}" in
    1|true|TRUE|yes|YES) return 0 ;;
    *) return 1 ;;
  esac
}

run_cmd() {
  if is_dry_run; then
    printf '[dry-run] %q ' "$@"
    printf '\n'
  else
    "$@"
  fi
}

detect_stable_branch_from_tags() {
  local latest_tag latest_major
  latest_tag="$(
    git ls-remote --tags --refs "${ERPNEXT_REPO}" 'v*' \
      | awk -F/ '{print $3}' \
      | sed 's/^v//' \
      | sort -V \
      | tail -n 1
  )"
  latest_major="$(printf '%s' "${latest_tag}" | cut -d. -f1)"
  if [ -n "${latest_major}" ]; then
    printf 'version-%s\n' "${latest_major}"
    return 0
  fi
  return 1
}

if [ -z "${STABLE_BRANCH:-}" ]; then
  if ! STABLE_BRANCH="$(detect_stable_branch_from_tags)"; then
    echo "Warning: Failed to detect stable ERPNext branch. Verify network/GitHub access, or set STABLE_BRANCH (for example: version-XX)." >&2
    STABLE_BRANCH=""
  fi
fi

if [ -z "${STABLE_BRANCH:-}" ]; then
  echo "Error: Unable to auto-detect stable branch. Set STABLE_BRANCH (for example: version-XX)." >&2
  exit 1
fi

if ! is_dry_run && { [ -z "${ADMIN_PASSWORD}" ] || [ -z "${MYSQL_ROOT_PASSWORD}" ]; }; then
  echo "Set both ADMIN_PASSWORD and MYSQL_ROOT_PASSWORD before running setup." >&2
  exit 1
fi
if ! is_dry_run && { [ "${#ADMIN_PASSWORD}" -lt 12 ] || [ "${#MYSQL_ROOT_PASSWORD}" -lt 12 ]; }; then
  echo "Use ADMIN_PASSWORD and MYSQL_ROOT_PASSWORD with at least 12 characters." >&2
  exit 1
fi

run_cmd bench init "${BENCH_DIR}" --frappe-branch "${STABLE_BRANCH}"
if ! is_dry_run; then
  cd "${BENCH_DIR}" || { echo "Failed to change to directory ${BENCH_DIR}." >&2; exit 1; }
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
