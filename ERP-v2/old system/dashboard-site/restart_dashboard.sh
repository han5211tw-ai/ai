#!/bin/bash

# Flask Dashboard 重啟腳本
# 確保只有一個 Flask instance 在 port 3000 執行

echo "🛑 正在終止舊的 Flask process..."

# 終止所有 Python app.py process
pkill -9 -f "python3 app.py" 2>/dev/null
pkill -9 -f "python.*app.py" 2>/dev/null
pkill -9 -f "run_flask.py" 2>/dev/null

# 等待端口釋放
sleep 2

# 檢查端口是否仍被佔用
if python3 -c "
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    sock.bind(('0.0.0.0', 3000))
    sock.close()
    exit(0)
except:
    exit(1)
" 2>/dev/null; then
    echo "✅ Port 3000 已釋放"
else
    echo "⚠️  Port 3000 仍被佔用，等待釋放..."
    sleep 3
fi

# 清除 Python 快取
echo "🧹 清除 Python 快取..."
cd /Users/aiserver/.openclaw/workspace/dashboard-site
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null

echo "🚀 啟動新的 Flask..."

# 使用 run_flask.py 啟動（確保正確載入所有 API）
nohup python3 run_flask.py > flask.log 2>&1 &

# 等待 Flask 啟動
sleep 4

# 檢查是否成功啟動
if curl -s "http://localhost:3000/api/system/announcements" > /dev/null 2>&1; then
    echo "✅ Flask 已成功啟動在 port 3000"
    echo "📊 Dashboard: http://localhost:3000"
    echo "📝 Log 檔案: $(pwd)/flask.log"
    
    # 顯示 API 狀態
    echo ""
    echo "📡 API 狀態:"
    curl -s "http://localhost:3000/api/system/announcements" | python3 -c "
import json,sys
data=json.load(sys.stdin)
print(f\"  系統公告 API: {'✅' if data.get('success') else '❌'} ({len(data.get('items',[]))} 筆公告)\")
" 2>/dev/null
    
    curl -s "http://localhost:3000/api/staff" | python3 -c "
import json,sys
data=json.load(sys.stdin)
print(f\"  員工管理 API: {'✅' if data.get('success') else '❌'} ({len(data.get('data',[]))} 位員工)\")
" 2>/dev/null
    
    curl -s "http://localhost:3000/api/summary" | python3 -c "
import json,sys
data=json.load(sys.stdin)
print(f\"  摘要 API: {'✅' if 'total' in data else '❌'}\")
" 2>/dev/null
else
    echo "❌ Flask 啟動失敗，請檢查 flask.log"
    exit 1
fi
