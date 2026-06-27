#!/usr/bin/env bash
# Kill any prior mock, then run the current code on 127.0.0.1:9000.
pkill -f 'mockshopee.main' 2>/dev/null
pkill -f 'uvicorn' 2>/dev/null
sleep 1
cd /mnt/c/Users/DriveSIM/Documents/GitHub/Frappe-ERPNext-Dev/mock_platform || exit 1
export PYTHONPATH="$(pwd)"
exec /home/frappe/osi-mock-venv/bin/python -m uvicorn mockshopee.main:app --host 127.0.0.1 --port 9900
