#!/usr/bin/env bash
# Force-free port 9900 regardless of owner. Run as root.
PID=$(ss -ltnp 2>/dev/null | grep ':9900' | grep -oP 'pid=\K[0-9]+' | head -1)
echo "pid_on_9900=${PID:-none}"
if [ -n "$PID" ]; then
  ps -o pid,user,cmd -p "$PID" 2>/dev/null
  kill -9 "$PID" 2>/dev/null && echo "killed $PID"
fi
sleep 1
if ss -ltnp 2>/dev/null | grep -q ':9900'; then echo "STILL_BOUND"; else echo "9900_FREE"; fi
