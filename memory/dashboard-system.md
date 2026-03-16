# ERP 營運系統

## 系統概述

**正名**: ERP 營運系統（原名 Dashboard 營運系統）

- **URL**: http://localhost:3000
- **技術**: Flask + HTML/JavaScript
- **圖表**: Chart.js

## 頁面結構

| 頁面 | 用途 | 路徑 |
|------|------|------|
| 首頁 | 總覽、每日銷售趨勢 | `/` |
| 部門 | 部門業績分析 | `/department.html` |
| 門市 | 門市業績分析 | `/store.html` |
| 個人 | 個人業績排名 | `/personal.html` |
| 班表 | 班表查詢 | `/roster.html` |
| 老闆控制台 | 總合控制台 | `/boss.html` |
| 門市主管控制台 | 門市專用 | `/Store_Manager.html` |
| 會計專區 | 會計專用看板 | `/Accountants.html` |
| 客戶查詢 | 客戶資料查詢 | `/customer_search.html` |

## API 列表

| API | 用途 | 資料來源 |
|-----|------|----------|
| `/api/sales/daily` | 每日銷售（門市部+業務部）| sales_history 即時計算 |
| `/api/sales/daily/store` | 每日銷售（僅門市部）| sales_history 即時計算 |
| `/api/sales/daily/by-store` | 每日銷售（各門市明細）| sales_history 即時計算 |
| `/api/performance/department` | 部門績效 | performance_metrics |
| `/api/performance/store` | 門市績效 | performance_metrics + sales_history |
| `/api/performance/personal` | 個人績效 | performance_metrics + sales_history |
| `/api/performance/business` | 業務部績效 | sales_history 即時計算 |
| `/api/store/reviews` | 五星評論數 | store_reviews |
| `/api/store/supervision` | 督導評分總覽 | supervision_scores |
| `/api/store/supervision/detail` | 督導評分明細 | supervision_scores |
| `/api/roster/weekly` | 本週班表 | staff_roster |
| `/api/roster/today` | 今日班表 | staff_roster |
| `/api/analysis/<type>` | AI 分析（department/store/personal）| analysis_results |
| `/api/needs/latest` | 最新需求表（待處理）| needs |
| `/api/service-records/summary` | 業務服務記錄統計 | service_records |
| `/api/customer/detail/<id>` | 客戶詳細資料 | customers + sales_history |
| `/api/health` | 系統健康檢查 | 多資料表 |

## 業績計算邏輯

### 門市部計算
- **豐原門市**：林榮祺 + 林峙文
- **潭子門市**：劉育仕 + 林煜捷
- **大雅門市**：張永承 + 張家碩
- **門市部總計**：三個門市人員 + 主管（莊圍迪）

### 業務部計算
- **業務員**：鄭宇晉 + 梁仁佑
- **業務部總計**：業務員 + 主管（萬書佑）

### 個人績效
- 從 sales_history 即時計算實際業績
- 從 performance_metrics 讀取目標
- 即時計算達成率和毛利率

## 2026-02-26 更新

### 個人業績頁面調整
- 表格欄位順序調整：排名 → 業務員 → **目標業績** → **實際業績** → 達成率 → 毛利率 → 單數 → 平均單價
- 圖表標題從「總業績」改為「實際業績」

## 老闆控制台需求表欄位

| 欄位 | 說明 |
|------|------|
| 項次 | 自動編號 |
| 日期 | 需求日期 |
| 產品編號 | 從 Excel 讀取 |
| 產品名稱 | 有編號→從庫存表撈取；無編號→顯示 Excel 名稱 |
| 數量 | 需求數量 |
| 需求部門 | 需求單位 |
| 客戶編號/需求用途 | 用途說明 |
| 庫存倉庫 | 顯示有庫存的倉庫名稱及數量 |

**產品名稱下方顯示：** 廠商名稱 - 進價: NT$ X,XXX

## 顏色規則

| 類別 | 顏色代碼 | 用途 |
|------|----------|------|
| 門市部 | `#00d4ff` | 藍色 |
| 業務部 | `#ffc107` | 黃色 |
| 豐原門市 | `#ff9800` | 橘色 |
| 潭子門市 | `#9c27b0` | 紫色 |
| 大雅門市 | `#4caf50` | 綠色 |

---

## 需求表系統

### 產品搜尋功能

| 時間 | 更新 | 說明 |
|------|------|------|
| 2026-03-04 | 顯示全部結果 | 移除 `.slice(0,5)` 限制，改為顯示所有符合條件的產品 |

**搜尋邏輯：**
- 關鍵字匹配 `products` 表的 `product_code` 和 `product_name`
- 即時顯示下拉選單
- 點擊後自動帶入產品編號和名稱
- 同時查詢並顯示庫存資訊

---

## 系統架構圖

| 版本 | 檔案 | 狀態 | 說明 |
|------|------|------|------|
| V3 | `system_map_v3.html` | ✅ 正式版 | 霓虹主題、貝茲爾曲線、動態粒子 |
| V2 | `system_map.html` | ⏸️ 已下線 | 功能完整但視覺較舊 |

### V3 特性 (2026-03-04)
- **視覺風格**: 霓虹主題 (Cyan/Purple/Orange 漸層)
- **連線方式**: 貝茲爾曲線 (Bezier Curves)
- **背景效果**: 浮動粒子 + 網格
- **字體**: Inter + JetBrains Mono
- **特效**: 霓虹發光 + 模糊光暈

---

## 登入組件

| 版本 | 檔案 | 狀態 | 說明 |
|------|------|------|------|
| v2.0 | `shared/auth_ui.js` + `auth_ui.css` | ✅ 正式版 | 科技風格、玻璃擬態 |
| v1.x | - | ⏸️ 已下線 | 舊版樣式 |

### v2.0 特性 (2026-03-04)
- **玻璃擬態**: backdrop-filter 模糊效果
- **霓虹光暈**: 藍色/紫色漸層光暈動畫
- **旋轉圓環**: 雙層旋轉裝飾圓環
- **盾牌圖示**: SVG 科技風格盾牌
- **密碼切換**: 顯示/隱藏密碼功能
- **焦點動畫**: 鎖圖示聚焦時變閃電
- **載入動畫**: 按鈕圖示旋轉效果
- **底部狀態列**: 系統狀態 + 忘記密碼連結

---

## 2026-02-28 需求表 Bug 修復記錄

### 🐛 問題 1：JavaScript 變數作用域錯誤（最嚴重）

**問題描述**
- 員工點擊「提交送出」後按鈕卡在「提交中...」，頁面無反應
- Console 顯示 `ReferenceError: items is not defined`

**根本原因**
```javascript
// 錯誤寫法
async function submitForm() {
    try {
        const items = [];  // ← items 只在 try 區塊內有效
        // ... 迴圈處理 ...
    } catch (e) {
        // ...
    }
    // ← 這裡存取 items 會報錯！
    console.log(items.length);
}
```

**修復方式**
```javascript
// 正確寫法
async function submitForm() {
    const items = [];  // ← 移到 try 外面宣告
    try {
        // ... 迴圈處理 ...
    } catch (e) {
        // ...
    }
    console.log(items.length);  // ← 現在可以正常存取
}
```

**影響範圍**
- 所有需求表送單功能完全失效
- 調撥、請購、新品都無法提交

---

### 🐛 問題 2：新品判斷邏輯缺陷

**問題描述**
- 員工直接輸入品名（不搜尋產品）時，系統無法識別為「新品」
- 導致新品沒有建立 staging 記錄

**根本原因**
- 原本只依賴 `data-is-new` 屬性判斷新品
- 但此屬性只在「搜尋後選擇新品」時才會設置
- 員工手動輸入品名時不會觸發搜尋，因此沒有此屬性

**修復方式**
```javascript
// 原來
const isNewProduct = codeInput.getAttribute('data-is-new') === 'true';

// 現在：增加自動檢測邏輯
const hasNewTag = codeInput.getAttribute('data-is-new') === 'true';
const isNewProduct = hasNewTag || (!code && name);  // 沒編號但有品名 = 新品
```

---

### 🐛 問題 3：Staging API 呼叫卡住

**問題描述**
- 當新品建立 staging 時，API 可能無回應或回應過慢
- 導致整個送單流程卡住，按鈕永遠顯示「提交中...」

**根本原因**
- `fetch('/api/staging/product')` 沒有設定超時
- API 未回應時，JavaScript 會無限期等待

**修復方式**
```javascript
// 加入 AbortController 超時處理
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 5000); // 5秒超時

const response = await fetch('/api/staging/product', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({...}),
    signal: controller.signal  // ← 綁定取消訊號
});

clearTimeout(timeoutId);  // ← 成功後清除計時器
```

**影響範圍**
- 新品送單時可能卡住
- 已修復為即使 staging 失敗也繼續提交需求

---

### 🐛 問題 4：驗證失敗時按鈕鎖定

**問題描述**
- 當表單驗證失敗（如調撥未選來源門市），彈出錯誤訊息後
- 按鈕持續顯示「提交中...」且無法再次點擊

**根本原因**
- 驗證失敗時直接 `return`，但沒有重置 `isSubmitting` 旗標

**修復方式**
```javascript
if (requestType === '調撥' && !transferFrom) {
    showToast('請選擇調撥來源門市', 'error');
    isSubmitting = false;  // ← 加上這行
    submitBtn.disabled = false;
    submitBtn.textContent = '提交送出';
    return;
}
```

**影響範圍**
- 所有驗證失敗場景（調撥未選來源、產品編號格式錯誤等）

---

### 🐛 問題 5：重複提交報錯

**問題描述**
- 員工重複提交相同資料時，後端拋出 SQL 錯誤
- 前端顯示卡住，沒有任何提示訊息

**根本原因**
- 資料表有 `UNIQUE(date, item_name, quantity, requester, product_code)` 限制
- 重複資料插入時拋出異常，但前端沒有處理

**修復方式**
```python
# 後端改用 INSERT OR IGNORE
cursor.execute("""
    INSERT OR IGNORE INTO needs (......)
    VALUES (......)
""")

# 回傳明確訊息
if cursor.rowcount > 0:
    inserted += 1
else:
    print(f"跳過重複資料: {product_name}")

return jsonify({
    'success': True, 
    'count': inserted, 
    'message': f'成功新增 {inserted} 筆，{total_items - inserted} 筆因重複已跳過'
})
```

---

### 🐛 問題 6：後端 API 錯誤處理不完善

**問題描述**
- API 發生異常時，資料庫連線可能未關閉
- 錯誤訊息可能洩漏給前端

**修復範圍**
為以下 API 加入 try-except-finally 處理：
- `GET /api/needs/latest`
- `GET /api/needs/recent`
- `POST /api/needs/cancel`
- `POST /api/needs/complete`
- `POST /api/needs/remark`
- `POST /api/needs/batch`（已有）

**統一處理模式**
```python
conn = get_db_connection()
cursor = conn.cursor()

try:
    # 業務邏輯
    ...
    return jsonify({'success': True})
except Exception as e:
    print(f"API 錯誤: {e}")
    return jsonify({'success': False, 'message': '系統錯誤'}), 500
finally:
    conn.close()  # 確保一定關閉連線
```

---

### 📝 修改檔案清單

| 檔案 | 修改內容 |
|------|----------|
| `needs_input.html` | JavaScript 邏輯修復（6處問題） |
| `app.py` | 後端 API 錯誤處理、重複提交處理 |

### ✅ 測試結果

- ✅ 正常請購送單
- ✅ 調撥送單（選擇來源門市）
- ✅ 新品送單（直接輸入品名）
- ✅ 重複提交提示
- ✅ 驗證失敗後可重新提交
- ✅ 30分鐘內取消功能正常
