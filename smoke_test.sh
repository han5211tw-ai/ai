#!/bin/bash
# smoke_test.sh - 改任何東西後自動測試
# 使用方法：./smoke_test.sh

echo "=== 煙霧測試 ==="

ERRORS=0
BASE_URL="http://localhost:3000"

# 等待服務啟動
echo "等待服務啟動..."
sleep 2

# 1. 測試登入 API
echo "1. 測試 /api/auth/verify..."
RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/verify" \
    -H "Content-Type: application/json" \
    -d '{"password":"2218"}' 2>/dev/null)

if ! echo "$RESPONSE" | grep -q '"success":true'; then
    echo "   ❌ 登入 API 失敗"
    echo "   回應：$RESPONSE"
    ERRORS=$((ERRORS + 1))
else
    echo "   ✅ 登入 API 正常"
fi

# 2. 測試 health API 不回傳 undefined
echo "2. 測試 /api/v1/admin/health..."
HEALTH=$(curl -s "$BASE_URL/api/v1/admin/health" 2>/dev/null)

if [ -z "$HEALTH" ]; then
    echo "   ❌ Health API 無回應"
    ERRORS=$((ERRORS + 1))
elif echo "$HEALTH" | grep -q "undefined"; then
    echo "   ❌ Health API 包含 undefined"
    ERRORS=$((ERRORS + 1))
else
    echo "   ✅ Health API 正常"
fi

# 3. 測試 DB Monitor API
echo "3. 測試 /api/admin/db/row-stats..."
DB_STATS=$(curl -s "$BASE_URL/api/admin/db/row-stats" 2>/dev/null)

if ! echo "$DB_STATS" | grep -q '"success":true'; then
    echo "   ❌ DB Monitor API 失敗"
    ERRORS=$((ERRORS + 1))
else
    echo "   ✅ DB Monitor API 正常"
fi

# 4. 測試需求單最近記錄 API
echo "4. 測試 /api/needs/recent..."
NEEDS=$(curl -s "$BASE_URL/api/needs/recent?department=潭子門市&current_user=測試" 2>/dev/null)

if ! echo "$NEEDS" | grep -q '"items"'; then
    echo "   ❌ Needs Recent API 失敗"
    ERRORS=$((ERRORS + 1))
else
    echo "   ✅ Needs Recent API 正常"
fi

# 5. 檢查 needs_input.html 可訪問
echo "5. 測試 needs_input.html..."
HTML_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/needs_input.html" 2>/dev/null)

if [ "$HTML_STATUS" != "200" ]; then
    echo "   ❌ needs_input.html 回應 $HTML_STATUS"
    ERRORS=$((ERRORS + 1))
else
    echo "   ✅ needs_input.html 可訪問"
fi

echo ""
if [ $ERRORS -eq 0 ]; then
    echo "=== ✅ 全部煙霧測試通過 ==="
    exit 0
else
    echo "=== ❌ 測試失敗，共 $ERRORS 個錯誤 ==="
    exit 1
fi
