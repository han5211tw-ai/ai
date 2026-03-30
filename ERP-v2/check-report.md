# OpenClaw ERP v2 全面自我檢查報告
**檢查日期**：2026-03-28
**系統版本**：OpenClaw v2.0 · Port 8800
**app.py 行數**：3,048 行
**覆蓋頁面**：27 頁 (templates/) + 4 admin 頁面

---

## 總覽

| 項目 | 結果 |
|------|------|
| 語法正確性 | ✅ 通過 |
| 頁面完整性 | ✅ 通過（29/29 頁，含合併項）|
| 白皮書 API 覆蓋率 | ⚠️ 32/41 實作，9 個更名/重組，1 個重複定義 |
| 禁止項目（舊系統/DB/Parser）| ✅ 完全未動 |
| 環境變數設定 | ✅ 通過 |
| Gunicorn 設定 | ✅ 通過 |

---

## 第一階段：功能完整性

### 1.1 頁面清單比對

| 頁面 | 狀態 | 備註 |
|------|------|------|
| index.html | ✅ | |
| department.html | ✅ | |
| store.html | ✅ | |
| personal.html | ✅ | |
| business.html | ✅ | |
| monthly_report.html | ✅ | |
| boss.html | ✅ | |
| Store_Manager.html | ✅ | |
| Accountants.html | ✅ | |
| admin.html | ✅ | |
| needs_input.html | ✅ | |
| customer_search.html | ✅ | |
| service_record.html | ✅ | |
| sales_input.html | ✅ | |
| roster.html | ✅ | |
| roster_input.html | ✅ | |
| supervision_score.html | ✅ | |
| staging_center_v2.html | ✅ | |
| target_input.html | ✅ | |
| line_replies.html | ✅ | |
| line_replies_edit.html | ✅ 合併 | 功能已合併至 line_replies.html（inline 編輯）|
| admin/announcement_management.html | ✅ | |
| admin/recommended_products.html | ✅ | |
| admin/bonus_rules.html | ✅ | |
| admin/bonus_report.html | ✅ | |
| staff_management.html | ✅ | |
| system_map_v3.html | ✅ | |
| bonus_personal.html | ✅ | |
| recommended_products.html | ✅ | |
| inventory_query.html | ✅ 額外 | 白皮書未列，實用頁面 |

**結論：29/29 白皮書頁面全數涵蓋（含合併），另外補充 inventory_query.html。**

---

### 1.2 API 端點比對

#### ✅ 已實作（含更名/重組）

| 白皮書路由 | 實際路由 | 說明 |
|-----------|---------|------|
| `/api/sales/daily` | `/api/sales/daily` | 完全對應 |
| `/api/performance/*` | `/api/performance/*` | 4 個全數對應 |
| `/api/needs/batch、cancel、arrive、purchase、transfer、overdue-arrival、history、latest` | 同名 | 全數對應 |
| `/api/needs/complete` | `/api/needs/<id>/complete` | ✅ 更名為 RESTful 形式 |
| `/api/customer/search、detail` | 同名 | 對應 |
| `/api/roster/monthly` | 同名 | 對應 |
| `/api/roster/today` | `/api/store-manager/today` | ✅ 已整合至 store-manager 回應 |
| `/api/system/announcements`、`/api/health` | 同名 | 對應 |
| `/api/store/reviews`、`/api/google-reviews` | 同名 | 對應 |
| `/api/line/replies` | `/api/line-replies` | ✅ 路由格式不同，功能完整（GET/POST/PUT/DELETE）|
| `/api/supervision/score` | `/api/supervision/submit` | ✅ 更名，功能一致 |
| `/api/store/supervision`、`/api/personal/supervision` | 同名 | 對應 |

#### ⚠️ 缺少或待確認

| 白皮書路由 | 狀態 | 影響評估 |
|-----------|------|---------|
| `/api/sales/daily/store` | ❌ 缺少 | store.html 未呼叫，前端暫無影響 |
| `/api/sales/daily/by-store` | ❌ 缺少 | store.html 未呼叫，前端暫無影響 |
| `/api/roster/weekly` | ❌ 缺少 | roster.html 只用 monthly，暫無影響 |
| `/api/google-reviews/stats` | ❌ 缺少 | 無頁面呼叫，暫無影響 |
| `/api/line/categories` | ❌ 缺少 | LINE 回覆表不使用分類，暫無影響 |
| `/api/store/employees` | ❌ 缺少 | Store_Manager.html 未呼叫，暫無影響 |

#### 🔴 必修問題

| 問題 | 位置 | 說明 |
|------|------|------|
| **重複定義** `/api/products/search` | app.py 第 919 行 & 第 2621 行 | Flask 以最後定義為準，第 919 行（僅查 products 表）被靜默覆蓋。第 2621 行（查 inventory 優先，fallback products）是更完整的版本，行為正確，但會觸發 Flask 警告。 |

---

## 第二階段：視覺一致性

### 2.1 色票使用

**標準色票**（可直接使用）：
```
#f5f0e8  #e8e2d8  #2c2720  #9a9188  #6b5f52  #FABF13
#faf7f2  #3d342c  #b8b0a6  #4a7c59  #8b3a3a  #3d7a3d
```

**發現問題（共 24 個檔案有非標準色）**：

| 嚴重程度 | 檔案 | 問題 |
|---------|------|------|
| 建議 | Accountants.html | Bootstrap 風格色票（#cfe2ff, #d4edda, #fff3cd, #084298）與設計系統不符 |
| 建議 | Store_Manager.html | 同上，另有 #432874（紫色）完全超出色系 |
| 次要 | boss.html | 圖表系列色用了自訂色（#7a6f9a, #8a4a4a, #6b8a5c）—圖表色系獨立尚可接受 |
| 次要 | department.html | 圖表系列色（#a87a4a, #6b8a5c, #b8893a, #a85c5c）—同上 |
| 次要 | store.html | 同上模式 |
| 次要 | needs_input.html | 狀態色有些非標準（#fdf5f5, #b8b0a8, #a88a5c）|
| 次要 | roster.html | 班別色彩（#7090c0, #432874, #c07070）—班表用途合理 |
| 次要 | supervision_score.html | 評分等級色（#664d03, #7a3a10）—功能用途可接受 |
| 次要 | admin/announcement_management.html | #eee, #999 速記色（未用 rgba 方式）|
| 次要 | admin/bonus_rules.html | 同上 |
| 次要 | 其餘 14 個檔案 | 圖表/Badge 輔助色，影響輕微 |

### 2.2 按鈕樣式

| 問題 | 影響頁面 | 嚴重程度 |
|------|---------|---------|
| border-radius 不一致：白皮書規定膠囊形（999px），但多數新頁面用 8px/6px | boss.html, department.html, index.html, needs_input.html, personal.html, store.html 用 999px；Phase 3–6 頁面用 8px | 次要—風格已形成，兩種都在使用，但不統一 |

### 2.3 輸入框

- **padding** 標準應為 `10px 14px`，部分新頁面用 `8px 12px`（次要差異）
- **border-radius** 標準 `10px`，部分新頁面用 `8px`（次要差異）
- **font-size** 統一 `.83rem`/`.84rem`，通過

### 2.4 字體

- Noto Serif TC 中文字體：✅ 所有頁面透過 base.html 全局載入
- Cormorant Garamond 數字裝飾：✅ 統計數字頁面正確套用
- font-weight 300/200：✅ 統一

### 2.5 手機版 RWD

- **main.css** 有兩個全局斷點：`@media (max-width: 768px)` 和 `@media (max-width: 480px)`
  - 覆蓋：sidebar 收合、content-area padding 縮減
- **8 個頁面** 有自訂 @media（boss, business, department, index, monthly_report, needs_input, store, supervision_score）
- **21 個頁面** 完全依賴 main.css 的全局 RWD，本機欄位 grid/flex 在小螢幕可能擠壓
- **結論**：基本可用，但細節頁面（如 sales_input.html 的產品表格、staging_center_v2.html 的雙 Tab）在手機上可能需要橫向滾動

---

## 第三階段：禁止項目確認

| 項目 | 狀態 | 說明 |
|------|------|------|
| `old system/` 資料夾 | ✅ **完全未動** | 110 個檔案，無任何修改時間異常 |
| Parser 腳本（~/srv/parser/）| ✅ **未涉及** | 掛載路徑以外，完全未存取 |
| 資料庫本體（company.db）| ✅ **結構完整** | 49 張表全數在位；業務資料寫入屬正常運作 |
| .env 現有變數 | ✅ **完整保留** | SECRET_KEY, PORT 均在位；DB_PATH 已以備註形式保留 |
| Cron 排程 | ✅ **未涉及** | 本次工作範圍不包含 |

---

## 第四階段：技術檢查

### 4.1 app.py 語法

```
✅ ast.parse() 通過，無語法錯誤
```

### 4.2 Import 完整性

| 模組 | 狀態 | 說明 |
|------|------|------|
| os | ✅ | |
| sqlite3 | ✅ | |
| json | ✅ | |
| datetime, timedelta | ✅ | |
| functools.wraps | ✅ | |
| flask | ✅ | render_template, jsonify, request, abort, send_from_directory |
| python-dotenv | ⚠️ 未用 | 改用自訂 load_env() 函數讀取 .env，功能等效，無問題 |

### 4.3 環境變數讀取

| 變數 | 讀取方式 | 狀態 |
|------|---------|------|
| DB_PATH | `os.environ.get('DB_PATH', 預設路徑)` | ✅ |
| PORT | `os.environ.get('PORT', 8800)` | ✅ |
| SECRET_KEY | 在 .env 定義，load_env() 載入 | ✅ |

### 4.4 Gunicorn 設定

| 項目 | 設定值 | 狀態 |
|------|-------|------|
| bind | 127.0.0.1:8800 | ✅ |
| workers | 4 (gthread) | ✅ |
| threads | 4 | ✅ |
| timeout | 120s | ✅ |
| max_requests | 1000 + jitter | ✅ |
| log 路徑 | /Users/aiserver/srv/logs/ | ✅ |

### 4.5 重複路由問題

```
⚠️ /api/products/search 定義兩次：
   第 919 行：products_search()  — 查 products 表
   第 2621 行：products_search() — 查 inventory 優先，fallback products（更完整）
```

Flask 行為：同名 view function 在 Python 層面後者覆蓋前者，實際執行第 2621 行版本。功能正確，但會在啟動時輸出 AssertionError 或 Warning。

---

## 問題清單與修正順序

### 🔴 必修（影響運作）

| # | 問題 | 位置 | 修正方式 |
|---|------|------|---------|
| M1 | `/api/products/search` 重複定義 | app.py 第 919 行 | 刪除第 919–942 行的舊版定義，僅保留第 2621 行的完整版 |

### 🟡 建議（影響一致性 / 潛在需求）

| # | 問題 | 位置 | 修正方式 |
|---|------|------|---------|
| R1 | Accountants.html / Store_Manager.html 使用 Bootstrap 色票 | 兩個檔案 | 將 #cfe2ff → `rgba(107,95,82,.08)`，#d4edda → `#e8f4e8`，#fff3cd → `#fff8e8` 等換成設計系統色 |
| R2 | `/api/roster/weekly` 缺少 | app.py | 若 roster.html 未來加入「本週視圖」，需補實作 |
| R3 | `/api/sales/daily/store`, `/api/sales/daily/by-store` 缺少 | app.py | 分析 store.html 實際需求後補充，或確認由 `/api/performance/store` 取代 |
| R4 | `/api/store/employees` 缺少 | app.py | Store_Manager.html 若需員工班表篩選功能時補充 |

### ⚪ 次要（美觀 / 非急）

| # | 問題 | 位置 | 修正方式 |
|---|------|------|---------|
| N1 | 按鈕 border-radius 不一致（999px vs 8px）| 全站 | 統一採用 8px（近年設計），或在 main.css 定義 `.btn-primary { border-radius: 8px }` |
| N2 | 輸入框 padding/border-radius 細微差異 | 多頁面 | 加入 main.css 全局 `.field-input` 規範並套用 |
| N3 | 21 個頁面無自訂 @media | 多頁面 | 針對有水平表格的頁面（sales_input, staging_center, line_replies）加入 `overflow-x:auto` |
| N4 | 圖表色系各頁面各自定義 | boss, dept, store 等 | 抽出至 static/js/chartColors.js 共用 |
| N5 | admin 頁面使用 `#eee`, `#999` 速記色 | admin/*.html | 換成 `rgba(107,95,82,.15)`, `#9a9188` |

---

## 建議修正順序

```
1. M1 — 刪除重複的 /api/products/search（10 分鐘）
2. R1 — 修正 Accountants / Store_Manager Bootstrap 色票（30 分鐘）
3. N3 — 表格頁面加 overflow-x:auto（20 分鐘）
4. N5 — admin 頁面 #eee #999 統一（15 分鐘）
5. R2~R4 — API 補充（依實際使用需求決定優先順序）
6. N1~N2 — 按鈕/輸入框全站統一（可在下一次大改版處理）
7. N4 — 圖表色系抽出（重構時處理）
```

---

## 通過項目彙總

- ✅ 語法：app.py 3,048 行無語法錯誤
- ✅ 頁面：29/29 白皮書頁面全數完成（含合併）
- ✅ 核心 API：needs 系統、業績、公告、客戶、班表、LINE 回覆、獎金、待建檔 等主要 API 完整
- ✅ 禁止項目：old system / Parser / DB schema / .env 均完整未異動
- ✅ 環境設定：DB_PATH, PORT, SECRET_KEY 正確讀取
- ✅ Gunicorn：port 8800，4 workers × 4 threads，log 路徑正確
- ✅ 認證機制：localStorage 模式，onAppReady callback 全站一致
- ✅ 字體：Noto Serif TC / Cormorant Garamond 統一載入
- ✅ 色票：核心色票（#f5f0e8, #2c2720, #FABF13 等）一致

---

*報告生成時間：2026-03-28 by OpenClaw 自我檢查程序*
