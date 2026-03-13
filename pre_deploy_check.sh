#!/bin/bash
# pre_deploy_check.sh - 部署前自動檢查
# 使用方法：./pre_deploy_check.sh

echo "=== 部署前檢查 ==="

ERRORS=0

# 1. 檢查 needs_input.html 完整性
echo "1. 檢查 needs_input.html DOCTYPE..."
if ! grep -q "<!DOCTYPE html>" dashboard-site/needs_input.html; then
    echo "   ❌ needs_input.html 缺少 DOCTYPE"
    ERRORS=$((ERRORS + 1))
else
    echo "   ✅ DOCTYPE 正常"
fi

# 2. 檢查 verifyPassword 函數是否存在
echo "2. 檢查 verifyPassword 函數..."
if ! grep -q "function verifyPassword\|async function verifyPassword" dashboard-site/needs_input.html; then
    echo "   ❌ needs_input.html 缺少 verifyPassword 函數"
    ERRORS=$((ERRORS + 1))
else
    echo "   ✅ verifyPassword 函數存在"
fi

# 3. 檢查 login 函數是否存在
echo "3. 檢查 login 函數..."
if ! grep -q "function login\|async function login" dashboard-site/needs_input.html; then
    echo "   ❌ needs_input.html 缺少 login 函數"
    ERRORS=$((ERRORS + 1))
else
    echo "   ✅ login 函數存在"
fi

# 4. 檢查 /api/auth/verify 路由是否存在
echo "4. 檢查 /api/auth/verify 路由..."
if ! grep -q "'/api/auth/verify'" dashboard-site/app.py; then
    echo "   ❌ app.py 缺少 /api/auth/verify 路由"
    ERRORS=$((ERRORS + 1))
else
    echo "   ✅ /api/auth/verify 路由存在"
fi

# 5. 檢查 app.py 語法
echo "5. 檢查 app.py Python 語法..."
if ! python3 -m py_compile dashboard-site/app.py 2>/dev/null; then
    echo "   ❌ app.py Python 語法錯誤"
    ERRORS=$((ERRORS + 1))
else
    echo "   ✅ app.py 語法正常"
fi

echo ""
if [ $ERRORS -eq 0 ]; then
    echo "=== ✅ 全部檢查通過，可以部署 ==="
    exit 0
else
    echo "=== ❌ 檢查失敗，共 $ERRORS 個錯誤 ==="
    exit 1
fi
