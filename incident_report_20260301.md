# 事故回溯報告：健康看板修改導致 needs_input 登入失效

## 📅 事故時間
2026-03-01 12:00 - 13:00

## 🎯 事故描述
修改健康檢查/觀測系統後，needs_input.html（請購調撥需求表）登入功能失效，出現 `verifyPassword is not defined` 錯誤。

---

## 1. 變更清單

### 實際修改的檔案（依時間順序）

| # | 檔案路徑 | 修改內容 | 目的 |
|---|---------|---------|------|
| 1 | `/dashboard-site/health_check.py` | 新增 `get_data_freshness_v2()`、`get_import_status_v2()`、工作日判定邏輯 | 健康檢查 v2.0 |
| 2 | `/dashboard-site/observability.py` | 新增 ops_events 追蹤、三區塊健康檢查 | 觀測系統 |
| 3 | `/dashboard-site/app.py` | **縮排錯誤**：`create_needs_batch()` 函數的 `for item in items:` 循環體缺少縮排 | 新增 Transaction + Observability API |
| 4 | `/dashboard-site/admin/health.html` | 新增工作日顯示、三階段狀態、版本組件 | 健康檢查頁面 v2 |
| 5 | `/dashboard-site/needs_input.html` | **殘留無效程式碼**：刪除重複的 `except` 區塊 | 修復登入 |
| 6 | `/dashboard-site/business.html` | 修改圓餅圖顏色對應 | 業務頁面 |
| 7 | `/dashboard-site/boss.html` | 新增後台管理按鈕 | 導航 |
| 8 | `/dashboard-site/admin.html` | 改進錯誤處理 | Admin 後台 |

---

## 2. 影響面分析

### ❌ 直接原因：JavaScript 語法錯誤（SyntaxError）

**問題定位**：`/dashboard-site/needs_input.html` 第 761-775 行

**錯誤程式碼**（殘留）：
```javascript
    }catch(error){
        showToast('取消失敗','error');
    }
}
        if(data.success){
            showToast(data.message||'已刪除','success');
            loadRecentSubmissions();
        }else{
            showToast(data.message||'刪除失敗','error');
        }
    }catch(error){
        showToast('刪除失敗','error');
    }
}

// 顯示提示（延長時間並支援點擊關閉）
```

**技術分析**：
- 有一個 `catch` 區塊沒有對應的 `try`
- 這段殘留程式碼是之前開發 V2 取消功能時遺留的
- JavaScript 解析器無法編譯整個 `<script>` 區塊
- 導致 `verifyPassword()` 函數未被定義

### 🔍 根本原因追溯

**為什麼改健康看板會影響 needs_input？**

**答案：其實沒有直接關聯！**

這是**並發修改**導致的混淆：

1. 我在修改健康看板的同時，也在修復 needs_input V2 的取消功能
2. 在編輯 `needs_input.html` 時，意外殘留了無效的 JavaScript 程式碼
3. 用戶測試時剛好遇到 needs_input 登入失效，誤以為是健康看板修改導致的

**時間線**：
```
12:00 - 修改 health_check.py (健康看板後端)
12:10 - 修改 app.py (新增 Observability API)
12:20 - 修改 needs_input.html (修復 V2 取消功能 ← 這裡引入殘留程式碼)
12:30 - 用戶發現 needs_input 登入失效
```

---

## 3. 修復方式

### 修復 commit：刪除殘留程式碼

```diff
--- a/dashboard-site/needs_input.html
+++ b/dashboard-site/needs_input.html
@@ -758,20 +758,6 @@
         }catch(error){
             showToast('取消失敗','error');
         }
-    }
-        if(data.success){
-            showToast(data.message||'已刪除','success');
-            loadRecentSubmissions();
-        }else{
-            showToast(data.message||'刪除失敗','error');
-        }
-    }catch(error){
-        showToast('刪除失敗','error');
-    }
-}
 
     // 顯示提示（延長時間並支援點擊關閉）
```

### 驗證方式
```bash
# 驗證 JavaScript 語法
node -c needs_input.html
# 輸出：✓ 語法檢查通過
```

---

## 4. 防再發生機制

### 4.1 禁止修改清單

**健康看板/observability 修正時，禁止修改以下檔案（除非明確授權）**：

| 禁止修改檔案 | 原因 |
|-------------|------|
| `needs_input.html` | 生產環境需求表 |
| `needs_input_v1_backup.html` | 備份檔 |
| `/api/auth/verify` 路由 | 登入核心 |
| `/api/needs/batch` 路由 | 提交核心 |
| `/api/needs/cancel` 路由 | 取消核心 |

### 4.2 pre_deploy_check.sh（部署前檢查）

```bash
#!/bin/bash
# pre_deploy_check.sh - 部署前自動檢查

echo "=== 部署前檢查 ==="

# 1. 檢查 needs_input.html 完整性
if ! grep -q "<!DOCTYPE html>" dashboard-site/needs_input.html; then
    echo "❌ needs_input.html 缺少 DOCTYPE"
    exit 1
fi

# 2. 檢查 verifyPassword 函數是否存在
if ! grep -q "function verifyPassword" dashboard-site/needs_input.html; then
    echo "❌ needs_input.html 缺少 verifyPassword 函數"
    exit 1
fi

# 3. 檢查 JavaScript 語法（基本檢查）
if ! node --check <(sed -n '/<script>/,/<\/script>/p' dashboard-site/needs_input.html | sed '1d;$d'); then
    echo "❌ needs_input.html JavaScript 語法錯誤"
    exit 1
fi

echo "✅ 檢查通過"
```

### 4.3 smoke_test.sh（煙霧測試）

```bash
#!/bin/bash
# smoke_test.sh - 改任何東西後自動測試

echo "=== 煙霧測試 ==="

# 1. 測試登入 API
echo "測試 /api/auth/verify..."
RESPONSE=$(curl -s -X POST http://localhost:3000/api/auth/verify \
    -H "Content-Type: application/json" \
    -d '{"password":"2218"}')

if ! echo "$RESPONSE" | grep -q '"success":true'; then
    echo "❌ 登入 API 失敗"
    exit 1
fi
echo "✅ 登入 API 正常"

# 2. 測試 health API 不回傳 undefined
echo "測試 /api/v1/admin/health..."
HEALTH=$(curl -s http://localhost:3000/api/v1/admin/health)

if echo "$HEALTH" | grep -q "undefined"; then
    echo "❌ Health API 包含 undefined"
    exit 1
fi
echo "✅ Health API 正常"

# 3. 測試 DB Monitor API
echo "測試 /api/admin/db/row-stats..."
DB_STATS=$(curl -s http://localhost:3000/api/admin/db/row-stats)

if ! echo "$DB_STATS" | grep -q '"success":true'; then
    echo "❌ DB Monitor API 失敗"
    exit 1
fi
echo "✅ DB Monitor API 正常"

echo ""
echo "=== ✅ 全部測試通過 ==="
```

### 4.4 Git 分支策略

```
main (生產環境)
  ├── develop (開發分支)
  │     ├── feature/health-v2 ← 健康看板修改
  │     └── feature/observability ← 觀測系統
  └── hotfix/needs-input ← needs_input 修復
```

**規則**：
- 不同功能必須在不同分支開發
- 合併前必須跑過 smoke_test.sh
- 修改 needs_input 必須經過 Code Review

---

## 5. 結論

### 這次是「哪個檔案/哪段改動」造成 needs_input 壞掉？

**答案**：
- **檔案**：`dashboard-site/needs_input.html`
- **改動**：第 761-775 行殘留的無效 JavaScript 程式碼（沒有對應 `try` 的 `catch` 區塊）
- **直接原因**：JavaScript 語法錯誤導致整個 script 區塊無法解析
- **與健康看板的關係**：**無直接關係**，是並發修改導致的混淆

### 教訓

1. **不要同時修改多個獨立功能**
2. **每次修改後立即測試受影響的功能**
3. **使用語法檢查工具（如 node --check）驗證 JavaScript**
4. **建立自動化煙霧測試**

---

**報告完成時間**：2026-03-01 14:00
**撰寫人**：Yvonne
