#!/usr/bin/env bash
# Launch N concurrent RQ workers on the OSI stress queue (DEV ONLY).
# Usage: stress_workers.sh [queue] [count]
# Run via run_in_background so it holds the workers open; pkill it when done:
#   pkill -f 'bench worker --queue long'
QUEUE="${1:-long}"
COUNT="${2:-4}"
cd /home/frappe/frappe-bench || exit 1
for i in $(seq 1 "$COUNT"); do
  /home/frappe/.local/bin/bench worker --queue "$QUEUE" &
done
wait
