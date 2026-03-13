#!/bin/bash
# start_flask.sh - 啟動 Flask 服務（固定端口 3000）

echo "=== Flask 服務啟動腳本 ==="

# 檢查端口 3000 是否被佔用
echo "檢查端口 3000..."

python3 -c "
import socket
import sys

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    result = s.connect_ex(('127.0.0.1', 3000))
    s.close()
    if result == 0:
        print('端口 3000 已被佔用')
        sys.exit(1)
    else:
        print('端口 3000 未被佔用')
        sys.exit(0)
except Exception as e:
    print(f'檢查失敗: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 端口 3000 已被佔用，無法啟動"
    echo ""
    echo "請先終止佔用端口 3000 的進程："
    echo "  ps aux | grep python3"
    echo "  kill -9 <PID>"
    echo ""
    exit 1
fi

echo ""
echo "✅ 端口 3000 可用，啟動 Flask..."
echo ""

cd /Users/aiserver/.openclaw/workspace/dashboard-site

# 啟動 Flask（固定 3000，不使用 threaded/reloader）
python3 -c "from app import app; app.run(host='0.0.0.0', port=3000, debug=False, use_reloader=False)" &

FLASK_PID=$!
echo "Flask PID: $FLASK_PID"
echo ""

# 等待啟動
sleep 3

# 驗證啟動
echo "驗證服務..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3000/needs_input.html 2>/dev/null)

if [ "$HTTP_CODE" = "200" ]; then
    echo ""
    echo "=== ✅ Flask 啟動成功 ==="
    echo ""
    echo "訪問地址："
    echo "  需求表:     http://localhost:3000/needs_input.html"
    echo "  Admin後台:  http://localhost:3000/admin.html"
    echo "  健康檢查:   http://localhost:3000/admin/health.html"
    echo ""
    echo "停止服務：kill $FLASK_PID"
    echo ""
else
    echo ""
    echo "❌ 啟動失敗，HTTP 狀態碼: $HTTP_CODE"
    echo ""
    exit 1
fi
