#!/bin/bash
# start_server.sh - 手動啟動 Flask 服務

echo "=== 終止舊服務 ==="
pkill -9 python3 2>/dev/null
sleep 3

echo "=== 檢查端口 ==="
PORT=3000
if lsof -ti:$PORT > /dev/null 2>&1; then
    echo "端口 $PORT 被佔用，使用端口 3001"
    PORT=3001
fi

echo "=== 啟動 Flask ==="
cd /Users/aiserver/.openclaw/workspace/dashboard-site
python3 app.py

# 服務啟動後，訪問：
# http://localhost:$PORT/admin/health.html
# http://localhost:$PORT/admin.html
