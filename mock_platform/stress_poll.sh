#!/usr/bin/env bash
# Poll the OSI stress queue until drained (or timeout). Prints elapsed + pending.
cd /home/frappe/frappe-bench || exit 1
BENCH=/home/frappe/.local/bin/bench
for i in $(seq 1 120); do
  N=$($BENCH --site erp.localhost execute online_store_integration.devtools.scenario.parallel_pending 2>/dev/null \
        | grep PARALLEL_PENDING | awk '{print $2}')
  echo "t=${i} pending=${N}"
  if [ "$N" = "0" ]; then echo "DRAINED at poll ${i}"; exit 0; fi
  sleep 5
done
echo "NOT_DRAINED (timeout)"
exit 1
