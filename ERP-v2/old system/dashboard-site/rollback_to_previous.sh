#!/bin/bash
# ============================================
# Operations System Rollback Script
# 回滾到上一個版本
# ============================================

set -e

WORKSPACE="/Users/aiserver/.openclaw/workspace/dashboard-site"
BACKUP_DIR="$WORKSPACE/backups"
LOG_FILE="$WORKSPACE/rollback_log.txt"

echo "=========================================="
echo "Operations System Rollback"
echo "時間: $(date)"
echo "=========================================="

# Step 1: 找到最近的備份
echo "[1/3] 查找最近備份..."
LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/needs_input_*.html 2>/dev/null | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "❌ 錯誤: 找不到任何備份檔案"
    echo "[$TIMESTAMP] 回滾失敗: 無可用備份" >> "$LOG_FILE"
    exit 1
fi

BACKUP_NAME=$(basename "$LATEST_BACKUP")
echo "✓ 找到備份: $BACKUP_NAME"

# Step 2: 執行回滾
echo "[2/3] 執行回滾..."
cp "$LATEST_BACKUP" "$WORKSPACE/needs_input.html"
echo "✓ 已還原: $BACKUP_NAME -> needs_input.html"

# Step 3: 記錄日誌
echo "[3/3] 記錄回滾日誌..."
TIMESTAMP=$(date +%Y%m%d%H%M%S)
echo "[$TIMESTAMP] ROLLBACK | Restored: $BACKUP_NAME | Status: SUCCESS" >> "$LOG_FILE"
echo "✓ 回滾完成"

echo ""
echo "=========================================="
echo "回滾成功！"
echo "還原版本: $BACKUP_NAME"
echo "日誌: $LOG_FILE"
echo "=========================================="
