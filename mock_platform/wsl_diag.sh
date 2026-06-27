#!/usr/bin/env bash
# Free port 9000 of any stale mock, then report bench + port state.
echo "=== port 9000 before ==="
ss -ltnp 2>/dev/null | grep ':9000' || echo "nothing on 9000"
pkill -f 'uvicorn mockshopee' 2>/dev/null && echo "killed stale uvicorn" || echo "no uvicorn to kill"
sleep 1
echo "=== port 9000 after ==="
ss -ltnp 2>/dev/null | grep ':9000' || echo "9000 free"
echo "=== bench ping ==="
curl -s -o /dev/null -w "bench=%{http_code}\n" --max-time 4 http://erp.localhost:8000/api/method/ping || echo "bench unreachable"
