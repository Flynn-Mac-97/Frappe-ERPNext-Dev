#!/usr/bin/env bash
# Wait until the bench web server answers ping.
for i in $(seq 1 45); do
  b=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 http://erp.localhost:8000/api/method/ping)
  if [ "$b" = "200" ]; then echo "BENCH_READY after ${i} tries"; exit 0; fi
  sleep 2
done
echo "BENCH_NOT_READY"
exit 1
