#!/bin/bash

# Dashboard Site Gunicorn 啟動腳本
# 測試階段：端口 3001

# 設定
APP_DIR="/Users/aiserver/.openclaw/workspace/dashboard-site"
LOG_DIR="/Users/aiserver/srv/logs"
PORT=3001
WORKERS=4

# 建立日誌目錄
mkdir -p "$LOG_DIR"

# 切換到專案目錄
cd "$APP_DIR" || exit 1

echo "[INFO] 啟動 Gunicorn..."
echo "[INFO] 端口: $PORT"
echo "[INFO] Workers: $WORKERS"
echo "[INFO] 日誌: $LOG_DIR"

# 啟動 Gunicorn
/opt/homebrew/bin/python3 -m gunicorn \
    -c gunicorn.conf.py \
    -w "$WORKERS" \
    -b "127.0.0.1:$PORT" \
    --timeout 60 \
    --access-logfile "$LOG_DIR/gunicorn_access.log" \
    --error-logfile "$LOG_DIR/gunicorn_error.log" \
    app:app
