#!/bin/bash
# ============================================
# Operations System Deploy Script
# 切換到 V2 版本（含備份與驗證）
# ============================================

set -e  # 發生錯誤時停止

WORKSPACE="/Users/aiserver/.openclaw/workspace/dashboard-site"
BACKUP_DIR="$WORKSPACE/backups"
TIMESTAMP=$(date +%Y%m%d%H%M%S)
LOG_FILE="$WORKSPACE/deploy_log.txt"

echo "=========================================="
echo "Operations System Deploy - V2 Switch"
echo "時間: $(date)"
echo "=========================================="

# Step 1: 建立備份目錄
mkdir -p "$BACKUP_DIR"

# Step 2: 備份當前版本
echo "[1/5] 備份當前版本..."
if [ -f "$WORKSPACE/needs_input.html" ]; then
    cp "$WORKSPACE/needs_input.html" "$BACKUP_DIR/needs_input_$TIMESTAMP.html"
    echo "✓ 備份完成: needs_input_$TIMESTAMP.html"
else
    echo "⚠ 找不到 needs_input.html，跳過備份"
fi

# Step 3: 驗證 V2 檔案存在
echo "[2/5] 驗證 V2 檔案..."
if [ ! -f "$WORKSPACE/needs_input_v2.html" ]; then
    echo "❌ 錯誤: 找不到 needs_input_v2.html"
    exit 1
fi

# 驗證版本號
VERSION=$(grep -o 'PAGE_VERSION=["0-9.]*' "$WORKSPACE/needs_input_v2.html" | head -1)
echo "✓ V2 版本號: $VERSION"

# Step 4: 覆蓋檔案
echo "[3/5] 部署 V2 版本..."
cp "$WORKSPACE/needs_input_v2.html" "$WORKSPACE/needs_input.html"
echo "✓ 已覆蓋 needs_input.html"

# Step 5: 驗證部署
echo "[4/5] 驗證部署..."
DEPLOYED_VERSION=$(grep -o 'PAGE_VERSION=["0-9.]*' "$WORKSPACE/needs_input.html" | head -1)
if [ "$DEPLOYED_VERSION" == "$VERSION" ]; then
    echo "✓ 驗證成功: 版本號符合"
else
    echo "❌ 驗證失敗: 版本號不符"
    echo "[$TIMESTAMP] 部署失敗: 版本驗證失敗" >> "$LOG_FILE"
    exit 1
fi

# Step 6: 記錄日誌
echo "[5/5] 記錄部署日誌..."
echo "[$TIMESTAMP] DEPLOY | Version: $VERSION | Backup: needs_input_$TIMESTAMP.html | Status: SUCCESS" >> "$LOG_FILE"
echo "✓ 部署完成"

echo ""
echo "=========================================="
echo "部署成功！"
echo "版本: $VERSION"
echo "備份: $BACKUP_DIR/needs_input_$TIMESTAMP.html"
echo "日誌: $LOG_FILE"
echo "=========================================="
