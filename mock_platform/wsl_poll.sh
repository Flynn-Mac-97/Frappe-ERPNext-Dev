#!/usr/bin/env bash
# Wait until the mock answers, then print its stats.
for i in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 http://127.0.0.1:9900/__control/stats)
  if [ "$code" = "200" ]; then
    echo "MOCK_READY after ${i}s"
    curl -s http://127.0.0.1:9900/__control/stats
    echo
    exit 0
  fi
  sleep 1
done
echo "MOCK_NOT_READY"
exit 1
