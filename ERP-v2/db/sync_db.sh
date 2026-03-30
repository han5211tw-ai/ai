#!/bin/bash
# ERP 資料庫單向同步腳本
# 每 10 分鐘將舊系統資料庫同步到新系統
# 來源: /Users/aiserver/srv/db/company.db
# 目標: /Users/aiserver/srv/web-site/computershop-erp/db/company.db

SOURCE_DB="/Users/aiserver/srv/db/company.db"
TARGET_DB="/Users/aiserver/srv/web-site/computershop-erp/db/company.db"
LOG_FILE="/Users/aiserver/srv/web-site/computershop-erp/db/sync.log"
PID_FILE="/Users/aiserver/srv/web-site/computershop-erp/db/sync.pid"

# 檢查是否已在執行（加強版：處理殘留 PID 檔案）
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 同步程序已在執行 (PID: $OLD_PID)" >> "$LOG_FILE"
        exit 0
    else
        # PID 不存在，清理殘留檔案（可能因重開機或程序異常結束導致）
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 發現殘留 PID 檔案 (PID: $OLD_PID 不存在)，清理後重新啟動" >> "$LOG_FILE"
        rm -f "$PID_FILE"
    fi
fi

# 記錄 PID
echo $$ > "$PID_FILE"

# 清理函數
cleanup() {
    rm -f "$PID_FILE"
    exit 0
}
trap cleanup EXIT INT TERM

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 資料庫同步服務啟動" >> "$LOG_FILE"

# 無限迴圈：每 10 分鐘同步一次
while true; do
    # 檢查來源檔案是否存在
    if [ ! -f "$SOURCE_DB" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 錯誤：來源資料庫不存在 $SOURCE_DB" >> "$LOG_FILE"
        sleep 600
        continue
    fi
    
    # 檢查目標目錄是否存在
    TARGET_DIR=$(dirname "$TARGET_DB")
    if [ ! -d "$TARGET_DIR" ]; then
        mkdir -p "$TARGET_DIR"
    fi
    
    # 使用 SQLite 備份模式複製（確保資料完整性）
    # 先建立臨時檔案，成功後再覆蓋，避免損壞目標資料庫
    TEMP_DB="${TARGET_DB}.tmp"
    
    if sqlite3 "$SOURCE_DB" ".backup '${TEMP_DB}'" 2>> "$LOG_FILE"; then
        # 備份成功，移動到正式位置
        if mv "$TEMP_DB" "$TARGET_DB"; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] 同步成功 ($(stat -f%z "$SOURCE_DB" 2>/dev/null || stat -c%s "$SOURCE_DB" 2>/dev/null) bytes)" >> "$LOG_FILE"
        else
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] 錯誤：無法移動臨時檔案" >> "$LOG_FILE"
            rm -f "$TEMP_DB"
        fi
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 錯誤：SQLite 備份失敗" >> "$LOG_FILE"
        rm -f "$TEMP_DB"
    fi
    
    # 等待 10 分鐘
    sleep 600
done
