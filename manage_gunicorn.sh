#!/bin/bash

# Dashboard Gunicorn 服務管理腳本
# 用法: ./manage_gunicorn.sh [start|stop|restart|status|logs]

SERVICE_NAME="com.dashboard.gunicorn"
LOG_DIR="/Users/aiserver/srv/logs"

case "$1" in
    start)
        echo "🚀 啟動 Gunicorn 服務..."
        launchctl start $SERVICE_NAME
        sleep 2
        launchctl list | grep $SERVICE_NAME
        ;;
    stop)
        echo "🛑 停止 Gunicorn 服務..."
        launchctl stop $SERVICE_NAME
        ;;
    restart)
        echo "🔄 重新啟動 Gunicorn 服務..."
        launchctl stop $SERVICE_NAME
        sleep 2
        launchctl start $SERVICE_NAME
        sleep 2
        launchctl list | grep $SERVICE_NAME
        ;;
    status)
        echo "📊 服務狀態:"
        launchctl list | grep $SERVICE_NAME
        echo ""
        echo "🌐 API 測試:"
        curl -s http://localhost:3001/api/health
        ;;
    logs)
        echo "📋 錯誤日誌 (最後 20 行):"
        tail -20 $LOG_DIR/gunicorn_error.log
        ;;
    unload)
        echo "⏏️  卸載服務 (測試階段用):"
        launchctl unload ~/Library/LaunchAgents/$SERVICE_NAME.plist
        ;;
    load)
        echo "📥 載入服務:"
        launchctl load ~/Library/LaunchAgents/$SERVICE_NAME.plist
        ;;
    *)
        echo "用法: $0 [start|stop|restart|status|logs|unload|load]"
        echo ""
        echo "指令說明:"
        echo "  start   - 啟動服務"
        echo "  stop    - 停止服務"
        echo "  restart - 重新啟動"
        echo "  status  - 查看狀態"
        echo "  logs    - 查看錯誤日誌"
        echo "  unload  - 卸載服務 (測試階段)"
        echo "  load    - 載入服務"
        ;;
esac
