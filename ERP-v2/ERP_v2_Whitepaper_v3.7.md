# OpenClaw — ERP v2 系統白皮書

**電腦舖 COSH · 台中豐原／潭子／大雅**

| 項目 | 值 |
|------|---|
| 文件版本 | v3.7 |
| 系統代號 | OpenClaw |
| 服務端口 | Port 8800 |
| 最後更新 | 2026-04-06 |
| 系統負責人 | Alan（黃柏翰） |

---

## 目錄

1. [專案概述](#1-專案概述)
2. [系統架構](#2-系統架構)
3. [技術棧](#3-技術棧)
4. [設計規範](#4-設計規範)
5. [資料庫設計](#5-資料庫設計)
6. [頁面結構](#6-頁面結構)
7. [API 架構](#7-api-架構)
8. [權限系統](#8-權限系統)
9. [業務邏輯詳解](#9-業務邏輯詳解)
10. [部署與維運](#10-部署與維運)
11. [Parser 系統（參考）](#11-parser-系統參考)
12. [版本紀錄](#12-版本紀錄)
13. [附錄](#13-附錄)

---

## 1. 專案概述

### 1.1 背景與目標

OpenClaw ERP v2 是 COSH 電腦舖第二代內部 ERP 系統，針對舊系統（Port 3000）的架構進行全面重建。新系統採用全新的視覺語言與程式架構，在不中斷舊系統服務的前提下完整重建，並於 Port 8800 提供服務。

### 1.2 系統統計

| 項目 | 數量 |
|------|------|
| 前端頁面（templates/） | 63 個 |
| API 路由 | 237 個 |
| 資料庫資料表 | 66 張 |
| 後台管理頁面 | 6 個 |
| 程式碼行數（app.py） | 9,560 行 |
| 開發 Phase | 6 個 + QA 修正 + KPI 模組 + 財務模組 + 廠商管理 + 手機版優化 + 手機版導覽強化 + 智慧銷貨建議 + 操作日誌 + 電腦檢測系統 + 維修作業系統 |

### 1.3 核心功能

- **即時業績追蹤**：部門、門市、個人三層業績每日更新
- **需求表系統**：採購類與調撥類雙軌流程管理
- **單據管理**：銷貨輸入、進貨輸入、報價/訂單、統一查詢
- **人員管理**：班表、督導評分、獎金計算完整串聯
- **後台管理**：員工、公告、獎金規則、推薦備貨一站式管理
- **LINE 客服**：回覆記錄管理，含結案追蹤
- **待建檔中心**：需求表／外勤紀錄自動觸發待建檔，手機號碼去重、臨時編號（TEMP-YYYYMMDD-NNN）、人工配對解消
- **KPI 考核系統**：季度 KPI 評分、關鍵貢獻申報審核、獎金池計算，完整角色分流
- **財務管理**：零用金共用池、應收帳款、應付帳款、收支日記帳、財務總覽（P&L）、稅務統計、現金流預測、廠商對帳，含雙公司抬頭（電瑙舖/鋒鑫）支援
- **維修作業系統**：六步驟漸進式流程（收件→檢測→報價→維修→取件→結案），A4 雙聯收件單（客戶聯＋店留聯）、正式維修單（含零件報價明細），客戶不修／無法維修結案路徑，銷貨輸入一鍵帶入維修單，統一工資品項 SV-LABOR；步驟 2 內嵌 AI 診斷輔助（oMLX 本地模型）與 218 個故障情境知識庫瀏覽搜尋，診斷結論直接回填工單
- **AI 幫手**：本地 oMLX 模型（gemma-4-e4b-it-8bit），全站浮動對話框，意圖分類引擎自動查詢 ERP 資料庫（銷貨/進貨/庫存/客戶/財務/班表/督導/獎金/盤點/外勤），支援多意圖合併與人名個人化查詢，首次登入自動展開今日摘要（依角色區分老闆版/員工版），之後每 2 小時自動展開一次
- **廠商管理**：廠商建檔、查詢、編輯，結構化帳期（結帳日 + 付款方式），進貨自動產生應付帳款與到期日計算
- **智慧銷貨建議**：銷貨輸入選擇客戶後自動推薦常購品項、近期購買、潛在興趣商品，一鍵加入購物車
- **操作日誌**：全站關鍵操作自動記錄（登入/銷貨/需求/單據/建檔/財務/KPI），支援篩選查詢與 CSV 匯出，老闆專用管理頁面
- **PWA 推播通知**：VAPID Web Push 即時通知，Service Worker 背景接收；觸發情境含採購到貨、調撥到貨、新採購需求（→老闆）、新調撥需求（→會計）、盤點待審核（→老闆）、回訪到期提醒、應收帳款到期預警；側邊欄與手機版「更多」面板皆可一鍵啟用/停用

---

## 2. 系統架構

### 2.1 整體架構

系統採用標準 MVC 架構，前端以純 HTML5 + Vanilla JS 實作，後端以 Flask + SQLite 提供 REST API。

```
使用者層（老闆 / 主管 / 門市 / 業務 / 會計）
↓
前端層（HTML5 + JS + Chart.js 4.x，Jinja2 模板）
↓
API 層（Flask 3.x + Gunicorn，Port 8800）
↓
資料層（SQLite 3，WAL 模式，62 張表）
```

### 2.2 目錄結構

```
computershop-erp/
├── app.py                ← Flask 主程式（9,560 行）
├── gunicorn.conf.py      ← Gunicorn 設定（Port 8800）
├── .env                  ← 環境變數（DB_PATH、PORT、VAPID 金鑰）
├── ERP_v2_Whitepaper_v3.7.md  ← 本白皮書
├── templates/            ← 所有前端頁面（63 個）
│   ├── base.html         ← 母版（側邊欄 + 頂部 + 字體）
│   ├── kpi_review.html   ← KPI 考核總覽
│   ├── kpi_contribution.html ← 關鍵貢獻填報
│   ├── supplier_create.html  ← 廠商建檔
│   ├── supplier_search.html  ← 廠商查詢（含編輯）
│   ├── admin/            ← 後台管理頁面（5 個）
│   └── ...（其餘頁面）
├── static/
│   ├── css/main.css      ← 全局樣式
│   └── js/
├── kpi_evidence/         ← KPI 關鍵貢獻佐證照片（本機儲存）
├── db/
│   └── company.db        ← SQLite 主資料庫
└── old system/           ← 舊系統參考（唯讀）
```

---

## 3. 技術棧

### 3.1 後端

| 技術 | 用途 | 版本 |
|------|------|------|
| Python | 後端語言 | 3.11+ |
| Flask | Web 框架 + Jinja2 模板 | 3.x |
| SQLite3 | 資料庫（WAL 模式） | 3.x |
| Gunicorn | WSGI 伺服器 | 20.x |

### 3.2 前端

| 技術 | 用途 |
|------|------|
| HTML5 + Jinja2 | 頁面結構與伺服器端渲染 |
| Vanilla JavaScript（ES6+） | 互動邏輯，無框架依賴 |
| Chart.js 4.x | 業績圖表、趨勢線 |
| CSS3 Custom Properties | 設計系統色票管理 |

### 3.3 設計系統

| 項目 | 規格 |
|------|------|
| 主字體 | `var(--font-serif)` → Noto Serif TC 200/300（中文纖細體） |
| 數字裝飾字體 | `var(--font-en)` → Cormorant Garamond 300（英文數字） |
| 等寬字體 | `var(--font-mono)` → Menlo / Consolas |
| 主背景色 | #f5f0e8（暖白） |
| 主文字色 | #2c2720（深墨） |
| 品牌黃 | #FABF13（僅 focus/active 使用） |
| 最大內容寬度 | 1,160px（寬螢幕兩側留白） |
| 手機斷點 | 768px / 480px |

所有字型引用一律透過 CSS 變數，禁止在 CSS / `<style>` 中寫死字體名稱。JS 內（如 Chart.js config）無法直接用 CSS 變數，以 `getComputedStyle(document.documentElement).getPropertyValue('--font-serif')` 讀取。唯一例外為 SVG `<text>` inline 屬性（不支援 CSS 變數）。

---

## 4. 設計規範

### 4.1 色票系統

所有頁面統一引用以下色票，禁止寫死不相干的 hex 值。

| 變數用途 | Hex 值 | 使用場景 |
|----------|--------|----------|
| 主背景 | #f5f0e8 | 頁面背景、輸入框底色 |
| 次要背景 | #e8e2d8 | 分區底色、Hover 狀態 |
| 主文字 | #2c2720 | 標題、重要數字 |
| 次要文字 | #9a9188 | 標籤、說明文字 |
| 線條 | #6b5f52 | 細分隔線、邊框 |
| 品牌黃 | #FABF13 | Focus Ring、Active 指示 |
| 成功綠 | #3d7a3d | 已到貨、已完成狀態 |
| 警示紅 | #8b3a3a | 刪除、取消操作 |

### 4.2 版面原則

- 主內容最大寬度 1,160px，超出兩側自動留白
- 統計數字為第一視覺焦點：Cormorant Garamond + 2.5~2.6rem
- 圖表高度：主圖 340–360px，輔助圖 240–300px
- 不新增元素，透過留白、間距與層級建立主次關係

### 4.3 元件規格

| 元件 | 規格 |
|------|------|
| 卡片圓角 | 14–16px |
| Focus 光暈 | 0 0 0 3px rgba(250,191,19,.12) |

#### 按鈕樣式規範

全系統按鈕分為三個層級，各層級有固定的尺寸與樣式規格。語意由**顏色**區分，形狀全部統一為圓角矩形、outlined 或 filled 風格。

**① 頁面級按鈕 — 儲存/送出/清除等主要操作**

| 類型 | 樣式 |
|------|------|
| 主要（Primary） | `background: #2c2720; color: #f5f0e8; border: none; border-radius: 8px; padding: 10px 26px; font-size: .82rem;` hover: `opacity: .85` disabled: `opacity: .5; cursor: default` |
| 次要（Outline） | `background: none; border: 1px solid rgba(107,95,82,.25); border-radius: 8px; padding: 8px 18px; font-size: .8rem; color: #6b5f52;` hover: `background: rgba(107,95,82,.05)` |
| 重設（Reset） | `background: none; border: 1px solid rgba(107,95,82,.3); border-radius: 8px; padding: 10px 16px; font-size: .8rem; color: #6b5f52;` |

**② 表格列按鈕 — 表格內的刪除、新增行等操作**

| 類型 | 樣式 |
|------|------|
| 刪除（Danger） | `background: none; border: 1px solid rgba(139,58,58,.3); border-radius: 5px; padding: 4px 9px; font-size: .72rem; color: #8b3a3a; white-space: nowrap;` hover: `background: rgba(139,58,58,.06)` — 按鈕文字統一使用「刪除」（不使用 ✕ 或 × 圖示） |
| 新增行（Add row） | `background: none; border: 1px dashed rgba(107,95,82,.3); border-radius: 7px; padding: 7px 16px; font-size: .8rem; color: #6b5f52;` hover: `background: rgba(107,95,82,.05)` |

**③ 老闆專區表格按鈕 — 待請購清單的操作、備注儲存等**

統一規格：`padding: 5px 12px; font-size: .76rem; border-radius: 6px; background: none; white-space: nowrap; transition: background .15s;`

| 語意 | 差異化樣式 |
|------|-----------|
| 確認（Success） | `border: 1px solid rgba(107,138,92,.4); color: #3d7a3d;` hover: `background: rgba(107,138,92,.08)` |
| 已採購（Primary） | `border: 1px solid rgba(44,39,32,.35); color: #2c2720;` hover: `background: rgba(44,39,32,.07)` |
| 取消（Danger） | `border: 1px solid rgba(168,92,92,.3); color: #a85c5c;` hover: `background: rgba(168,92,92,.07)` |
| 儲存 / 重新整理（Secondary） | `border: 1px solid rgba(107,95,82,.3); color: #6b5f52;` hover: `background: rgba(107,95,82,.07)` |

**共通規則**

- 所有按鈕加 `transition: background .15s`（或 `opacity .2s`）確保互動有過渡效果
- 所有按鈕加 `cursor: pointer`
- disabled 狀態統一 `opacity: .5; cursor: default`（或 `cursor: not-allowed`）
- 按鈕文字一律使用中文（「刪除」「儲存」「取消」），不使用符號圖示

#### 輸入欄位兩級樣式（main.css 統一管理）

所有 input 的基礎樣式由 `main.css` 全局管理，分為「表單級」與「表格級」兩層，**各頁面不需自行定義 input 大小相關屬性**：

**① 表單級（預設）— 所有非表格內的 input**

```css
input[type="text"], input[type="number"], input[type="date"],
input[type="password"], input[type="email"], input[type="search"],
input:not([type]),   /* ← 捕捉未寫 type 的 input */
select, textarea {
  padding: 10px 14px;
  border: 1px solid var(--border-mid);     /* rgba(107,95,82,.25) */
  border-radius: var(--radius);            /* 10px */
  font-size: 16px;
  font-family: var(--font-serif);
  font-weight: 300;
  color: var(--text);
  background: var(--bg-card);
}
/* focus */
input:focus { border-color: var(--brand); box-shadow: 0 0 0 3px rgba(250,191,19,.10); }
```

**② 表格級 — `<table>` 內的 input 自動覆蓋為緊湊尺寸**

```css
table input[type="text"], table input[type="number"],
table input[type="date"], table input:not([type]),
table select {
  padding: 5px 7px;
  font-size: .82rem;
  border: 1px solid var(--border);         /* rgba(107,95,82,.15) */
  border-radius: var(--radius-sm);         /* 6px */
  background: var(--bg);                   /* #f5f0e8 */
}
table input:focus { border-color: var(--accent); box-shadow: none; }
```

#### ⚠️ input type 屬性注意事項

CSS 屬性選擇器 `input[type="text"]` **只匹配 HTML 中明確寫了 `type="text"` 的元素**。未寫 `type` 的 `<input>` 雖然行為上等同 `type="text"`，但**不會被 `input[type="text"]` 選中**。

`main.css` 已透過 `input:not([type])` 補捉這類 input，specificity 同為 `(0,1,1)`，不影響各頁面 class 的覆蓋關係。開發時建議：

- 表格內的 text input **不寫** `type="text"`（避免與全局選擇器衝突，由 `table input:not([type])` 覆蓋）
- `type="number"`、`type="date"` 因功能需要必須保留，由 `table input[type="number"]` 等規則覆蓋
- 表單區的 input 寫不寫 `type` 皆可，全局樣式都會正確匹配

#### 表單欄位交錯色（ID selector 覆蓋）

所有頁面的表單區使用 `auto-fit grid`，視覺上奇數位欄位為暖米色（`#f5f0e8`）、偶數位為淺色（`var(--bg-card)`）。

由於 CSS specificity 衝突（`.f-select` 0,1,0 勝 `select` 0,0,1，但 `.f-input` 0,1,0 輸 `input[type="date"]` 0,1,1），class 層級無法可靠控制交錯色。解法為逐欄位以 **ID selector**（specificity 1,0,0）覆蓋：

```css
/* 範例：purchase_input.html */
#fDate      { background: #f5f0e8; }          /* 奇數 — 暖米 */
#fCompany   { background: var(--bg-card); }    /* 偶數 — 淺色 */
#fOrderNo   { background: #f5f0e8; }          /* 奇數 */
#fSupplier  { background: var(--bg-card); }    /* 偶數 */
```

新增頁面時，先確認第一個欄位是 input 還是 select，再決定奇偶起始順序。因為 `auto-fit` 會隨視窗寬度改變欄數，ID 覆蓋確保無論幾欄排列，每個欄位的底色都固定正確。

#### 字體大小層級總覽

| 層級 | font-size | 適用場景 |
|------|-----------|----------|
| 全域表單 | `16px` | main.css 定義的 input / select / textarea 預設 |
| 頁面級控件 | `.84rem` | `.f-input` / `.f-select` / `.f-textarea` / `.edit-field input` |
| 表格內控件 | `.82rem` | `table input` / `table select`（main.css 自動覆蓋） |
| 顯示用文字 | `.86rem` | `.empty-hint` / `.item-desc` 等非表單元素（可接受） |

禁止在任何表單控件上使用 `.86rem`。`font-weight` 一律用數值（300 / 600 / 700），禁止寫 `bold`。

### 4.4 onAppReady 規範（重要）

所有子頁面必須以 **定義** 方式宣告 `onAppReady`，而非以 callback 方式呼叫：

```js
// ✅ 正確寫法
function onAppReady(user) {
  // 初始化邏輯
}

// ❌ 錯誤寫法（會導致 ReferenceError，頁面停在載入中）
onAppReady(user => {
  // 初始化邏輯
});
```

base.html 負責在認證完成後呼叫 `onAppReady(user)`，子頁面只需定義此函式。

---

## 5. 資料庫設計

### 5.1 資料庫概覽

資料庫位於 `db/company.db`，採 SQLite 3 WAL 模式，共 66 張資料表，由外部 Parser 腳本自動維護核心業務資料。

### 5.2 資料表分組

| 分組 | 資料表 |
|------|--------|
| 核心業務 | sales_history, customers, customer_master, inventory, needs, purchase_history, products, suppliers, service_records, sales, sales_documents, sales_document_items |
| 人員 / 班表 | staff, staff_passwords, staff_roster, supervision_scores |
| 獎金 | bonus_rules, bonus_results, bonus_payments |
| 系統 / 管理 | system_announcements, notification_logs, login_attempts, boss_password, admin_audit_log, chat_logs, api_metrics, ops_events, audit_log |
| 暫存 / 備份 | customer_staging, product_staging, staging_records, sales_history_deleted_backup, staging_records_backup |
| 財務管理 | finance_payables, finance_receivables, finance_transactions, finance_petty_cash, finance_petty_cash_log, finance_ledger |
| 盤點 | inventory_count, inventory_count_items, inventory_adjustments |
| 電腦檢測 | fault_groups, fault_scenarios, fault_reports |
| 維修作業 | repair_orders, repair_order_items, repair_phrases |
| 特殊功能 | google_reviews, store_reviews, line_replies, recommended_products, recommended_categories, crm_tasks |
| 目錄 / 快取 | product_categories, _deprecated_product_master, freshness_cache, performance_metrics, sqlite_sequence |

### 5.3 核心資料表說明

#### needs（需求表）

雙軌流程核心，`request_type` 欄位區分採購類與調撥類：

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | INTEGER PK | 自動遞增 |
| date | TEXT | 日期 YYYY-MM-DD |
| request_type | TEXT | 採購 / 調撥 / 請購 |
| item_name | TEXT | 商品名稱 |
| quantity | INTEGER | 數量 |
| requester | TEXT | 填表人員 |
| department | TEXT | 部門（申請單位） |
| transfer_from | TEXT | 調撥來源倉庫（調撥類專用） |
| status | TEXT | 待處理 / 已採購 / 已調撥 / 已完成 / 已取消 |
| product_code | TEXT | ERP 料號 |
| remark | TEXT | 備注（推薦備貨自動帶入 `[推薦備貨]` 標記） |
| processed_at / arrived_at / cancelled_at | DATETIME | 各階段時間戳 |

#### sales_history（銷貨歷史）

由 sales_parser 自動匯入，亦提供 sales_input.html 手動輸入。每筆明細逐行存放，以 `sales_invoice_no` 欄位歸組為同一張銷貨單。

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | INTEGER PK | 唯一識別（逐筆刪除用） |
| sales_invoice_no | TEXT | **銷貨單號**（`{門市代碼}-{YYYYMMDD}-{NNN}`，如 `FY-20260403-001`），同一筆交易的多項明細共用同一單號 |
| invoice_no | TEXT | 發票號碼（選填，如 `EK12345678`；舊資料存放民國曆日期） |
| date | TEXT | 銷售日期 |
| customer_id / customer_name | TEXT | 客戶資訊 |
| salesperson / salesperson_id | TEXT | 銷售人員 |
| product_code / product_name | TEXT | 商品資訊 |
| quantity, price, amount | INTEGER | 數量、單價、小計 |
| cost, profit, margin | REAL | 成本、毛利、毛利率（老闆/會計可見） |
| warehouse | TEXT | 出貨倉庫（v1.7 新增） |
| payment_method | TEXT | 付款方式（v1.7 新增） |
| deposit_amount | INTEGER | 訂金金額（v1.7 新增） |
| source_doc_no | TEXT | 來源訂單單號（v1.7 新增） |

> **銷貨單號產生邏輯**：格式為 `{門市代碼}-{YYYYMMDD}-{NNN}`，門市代碼由出貨倉庫決定（豐原門市→FY、潭子門市→TZ、大雅門市→DY、業務部→OW），序號每日每門市獨立從 001 開始。頁面載入、切換倉庫、切換日期時自動呼叫 `/api/sales/next-invoice-no` 產生。單號產生後不佔用，僅儲存時寫入資料庫。

> **成本計算邏輯**：`cost` 欄位於銷貨寫入時即帶入成本，優先序為：**最近一次進貨單價** → **近 90 天加權平均進貨成本** → **0**（服務費等無進貨品項）。`profit = amount - cost`，`margin` 同步計算。服務類品項（SE- 開頭）成本自然為 0，毛利率 100%。

#### purchase_history（進貨歷史）

由 purchase_parser 自動匯入，亦提供 purchase_input.html 手動輸入。

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | INTEGER PK | 唯一識別（逐筆刪除用） |
| order_no | TEXT | 進貨單號（PO-YYYYMMDD-NNN） |
| invoice_number | TEXT | 發票號碼（選填） |
| date | TEXT | 進貨日期 |
| supplier_name | TEXT | 供應商名稱 |
| product_code / product_name | TEXT | 商品資訊 |
| quantity, price, amount | INTEGER | 數量、單價、小計 |
| warehouse | TEXT | 入庫倉庫（選填） |
| company | TEXT | 進貨公司抬頭（電瑙舖資訊有限公司／鋒鑫資訊有限公司） |
| created_by | TEXT | 建立者 |

#### inventory（庫存）

由 inventory_parser 每日 10:30 更新，以 `report_date` 區分快照版本。

> **單位成本計算邏輯**：庫存查詢頁面的 `unit_cost` 以**當月 purchase_history 加權平均進貨價**即時計算，覆蓋快照中的原始值。`total_cost = stock_quantity × unit_cost`。

> **倉庫排序順序**（全系統統一）：豐原門市 → 潭子門市 → 大雅門市 → 業務部 → 總公司倉庫

#### sales_documents / sales_document_items（報價/訂單）

| 欄位（sales_documents） | 說明 |
|------------------------|------|
| doc_no | 單號（報價：QT{date}-NNN，訂單：SO{date}-NNN） |
| doc_type | QUOTE / ORDER |
| status | DRAFT / CONFIRMED / CONVERTED / CANCELLED |
| target_name | 客戶名稱 |
| total_amount / deposit_amount / balance_amount | 金額資訊 |
| source_doc_no | 轉換來源單號（訂單由報價轉入時填入） |
| created_by | 建立者 |

#### line_replies（LINE 客服回覆）

| 欄位 | 型別 | 說明 |
|------|------|------|
| reply_datetime | TEXT | 回覆日期時間 |
| customer_line_name | TEXT | 客戶 LINE 顯示名稱 |
| inquiry_content | TEXT | 詢問內容 |
| reply_content | TEXT | 回覆內容 |
| reply_store / reply_staff | TEXT | 回覆門市 / 負責人員 |
| is_resolved | INTEGER | 0=未結案, 1=已結案 |

#### finance_payables（應付帳款）

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | INTEGER PK | 自動遞增 |
| vendor_name | TEXT | 廠商名稱 |
| order_no | TEXT | 相關訂單編號 |
| amount | REAL | 應付金額（含稅總額） |
| pretax_amount | REAL | 未稅金額（預設 0） |
| tax_amount | REAL | 稅額（預設 0，有發票時 = 未稅 × 5%） |
| due_date | TEXT | 到期日 |
| status | TEXT | unpaid / paid |
| company | TEXT | 進貨公司抬頭（電瑙舖/鋒鑫） |
| note | TEXT | 備註 |
| paid_at | DATETIME | 付款時間 |
| created_at | DATETIME | 建立時間 |

#### finance_receivables（應收帳款）

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | INTEGER PK | 自動遞增 |
| customer_name | TEXT | 客戶名稱 |
| order_no | TEXT | 相關單號 |
| amount | REAL | 應收金額 |
| due_date | TEXT | 到期日 |
| status | TEXT | unpaid / paid |
| note | TEXT | 備註 |
| confirmed_at | DATETIME | 確認收款時間 |
| created_at | DATETIME | 建立時間 |

#### finance_transactions（收支日記帳）

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | INTEGER PK | 自動遞增 |
| date | TEXT | 交易日期 |
| type | TEXT | income / expense |
| category | TEXT | 交易分類 |
| store | TEXT | 門市/部門 |
| amount | REAL | 金額 |
| description | TEXT | 說明 |
| created_at | DATETIME | 建立時間 |

#### finance_petty_cash / finance_petty_cash_log（零用金）

採共用池制度，全公司共用 $50,000/月額度。`finance_petty_cash` 存帳戶餘額資訊，`finance_petty_cash_log` 存支出/撥補明細，含 `department`（豐原門市/潭子門市/大雅門市/業務部/總公司）、`category`（文具/交通/餐飲/雜支/設備維修/郵資）、`invoice_no`（發票號碼）欄位。

#### suppliers（廠商建檔）

| 欄位 | 型別 | 說明 |
|------|------|------|
| supplier_id | TEXT PK | 廠商編號（SP-0001，依進貨頻率排序編排） |
| supplier_name | TEXT | 廠商全名（唯一值） |
| short_name | TEXT | 簡稱 |
| tax_id | TEXT | 統一編號 |
| contact_person | TEXT | 聯絡人 |
| phone / mobile / email | TEXT | 聯絡方式 |
| address | TEXT | 地址 |
| payment_method | TEXT | 付款方式：匯款 / 支票 / 現金自取 |
| closing_day | INTEGER | 每月結帳日（如 25、26、28，各廠商不同） |
| pay_day | INTEGER | 匯款日（每月固定，預設 28） |
| bank_name | TEXT | 銀行名稱 |
| bank_branch | TEXT | 分行名稱 |
| bank_account | TEXT | 銀行帳號 |
| status | TEXT | 正常 / 停用 |
| remark | TEXT | 備注 |
| created_by / updated_by | TEXT | 建立/更新者 |
| created_at / updated_at | DATETIME | 建立/更新時間 |

> **編號規則**：SP-0001 為進貨次數最多的廠商，依進貨頻率遞減排序。進貨輸入時若遇到新廠商，系統自動在 suppliers 表建檔。

---

## 6. 頁面結構

共 57 個頁面，分十一個 Phase 開發，QA 階段新增 3 個。所有頁面繼承 base.html 母版。

| Phase | 頁面 | 路由 | 最低權限 |
|-------|------|------|----------|
| Phase 0 基礎 | base.html（母版） | （全域） | 所有角色 |
| Phase 1 核心每日 | index.html | / | 所有角色 |
| | needs_input.html | /needs_input | 所有角色 |
| | boss.html | /boss | 老闆 |
| Phase 2 業績分析 | department.html | /department | 老闆/主管 |
| | store.html | /store | 老闆/主管 |
| | personal.html | /personal | 所有角色 |
| | business.html | /business | 老闆/業務 |
| | monthly_report.html | /monthly_report | 老闆/主管 |
| Phase 3 控制台查詢 | Store_Manager.html | /Store_Manager | 老闆/主管 |
| | Accountants.html | /Accountants | 老闆/會計 |
| | customer_search.html | /customer_search | 所有角色 |
| | inventory_query.html | /inventory_query | 所有角色 |
| | roster.html | /roster | 所有角色 |
| Phase 4 輸入頁面 | service_record.html | /service_record | 業務人員 |
| | supervision_score.html | /supervision_score | 老闆/主管 |
| | roster_input.html | /roster_input | 老闆/會計 |
| | sales_input.html | /sales_input | 老闆/會計 |
| | target_input.html | /target_input | 老闆/會計 |
| | **purchase_input.html** | **/purchase_input** | **老闆/會計** |
| | **quote_input.html** | **/quote_input** | **老闆/會計** |
| | **query.html** | **/query** | **老闆/會計** |
| Phase 5 後台管理 | admin.html | /admin | 老闆 |
| | staff_management.html | /staff_management | 老闆 |
| | admin/announcement_management.html | /admin/announcement_management | 老闆 |
| | admin/bonus_rules.html | /admin/bonus_rules | 老闆 |
| | admin/bonus_report.html | /admin/bonus_report | 老闆 |
| | admin/recommended_products.html | /admin/recommended_products | 老闆/會計 |
| | admin/health.html | /admin/health | 老闆 |
| | admin/audit_log.html | /admin/audit_log | 老闆 |
| Phase 6 特殊功能 | line_replies.html | /line_replies | 所有角色 |
| | bonus_personal.html | /bonus_personal | 所有角色 |
| | recommended_products.html | /recommended_products | 所有角色 |
| | staging_center_v2.html | /staging_center_v2 | 老闆/會計 |
| | system_map_v3.html | /system_map_v3 | 老闆 |
| Phase 7 財務管理 | finance_dashboard.html | /finance_dashboard | 老闆/會計 |
| | finance_petty_cash.html | /finance_petty_cash | 所有角色 |
| | finance_receivables.html | /finance_receivables | 老闆/會計 |
| | finance_payables.html | /finance_payables | 老闆/會計 |
| | finance_transactions.html | /finance_transactions | 老闆/會計 |
| | finance_tax.html | /finance_tax | 老闆/會計 |
| | finance_cashflow.html | /finance_cashflow | 老闆/會計 |
| | finance_vendor_reconcile.html | /finance_vendor_reconcile | 老闆/會計 |
| Phase 7 廠商管理 | supplier_create.html | /supplier_create | 老闆/會計 |
| | supplier_search.html | /supplier_search | 老闆/會計 |
| Phase 8 庫存盤點 | inventory_count.html | /inventory_count | 老闆/會計 |
| Phase 9 待辦清單 | pending_needs.html | /pending_needs | 所有角色 |
| | pending_purchase.html | /pending_purchase | 老闆 |
| | pending_transfer.html | /pending_transfer | 老闆/會計 |
| Phase 10 電腦檢測 | fault_diagnose.html | /fault_diagnose | （已整合至維修作業步驟 2，路由重導向） |
| | print_repair_report.html | /print/repair-report | （已停用，路由重導向） |
| Phase 11 維修作業 | repair_order.html | /repair_order | 老闆/會計/工程師/主管（含 AI 診斷輔助 + 知識庫瀏覽） |
| | repair_receipt.html | /repair_receipt/\<order_no\> | （列印專用，A4 雙聯收件單） |
| | repair_workorder.html | /repair_workorder/\<order_no\> | （列印專用，正式維修單） |

---

## 7. API 架構

### 7.1 認證機制

系統採用 JWT-less localStorage 認證，無需 Server Session。

- **登入**：員工編號 + 密碼 → `POST /api/auth/verify` → 寫入 localStorage
- **儲存格式**：`{ name, role, loginTime, expiresAt }`（key: `erp_v2_user`）
- **自動過期**：登入後 4 小時過期（key: `erp_v2_exp`）
- **前端模式**：子頁面定義 `function onAppReady(user) {...}`，base.html 認證後自動呼叫

### 7.2 API 端點一覽

#### 銷售與業績

| 端點 | 方法 | 說明 |
|------|------|------|
| /api/sales/daily | GET | 每日銷售總覽（門市部 + 業務部） |
| /api/sales/next-invoice-no | GET | **自動產生銷貨單號**（參數 warehouse, date → 回傳 `{門市代碼}-{YYYYMMDD}-{NNN}`） |
| /api/sales/list | GET | 銷貨紀錄分頁列表（含 sales_invoice_no 欄位，支援 q, salesperson, page） |
| /api/sales/submit | POST | 手動新增銷貨單（必填 sales_invoice_no，選填 invoice_no） |
| /api/sales/\<invoice_no\> | DELETE | 整批刪除（依發票號碼） |
| /api/sales/row/\<id\> | DELETE | **逐筆刪除**（依 id，老闆限定） |
| /api/query/sales | GET | 單據查詢用銷貨列表（支援 from, to 日期範圍） |
| /api/performance/department | GET | 部門業績 |
| /api/performance/department/daily | GET | 部門每日趨勢 |
| /api/performance/store | GET | 門市業績 |
| /api/performance/personal | GET | 個人業績排名 |
| /api/performance/business | GET | 業務部績效 |

#### 進貨

| 端點 | 方法 | 說明 |
|------|------|------|
| /api/purchase/next-no | GET | 取得下一個 PO 編號（PO-YYYYMMDD-NNN） |
| /api/purchase/suppliers | GET | 從進貨歷史取得供應商清單 |
| /api/purchase/submit | POST | 新增進貨單 |
| /api/purchase/list | GET | 進貨紀錄列表（支援 q, from, to, company, page） |
| /api/purchase/row/\<id\> | PUT | 修改進貨明細（company, invoice_number, warehouse） |
| /api/purchase/row/\<id\> | DELETE | 逐筆刪除進貨紀錄（老闆限定） |

#### 廠商管理

| 端點 | 方法 | 說明 |
|------|------|------|
| /api/supplier/next-id | GET | 取得下一個 SP 編號 |
| /api/supplier/list | GET | 廠商分頁列表（支援 q, page） |
| /api/supplier/detail/\<id\> | GET | 廠商詳細 + 近期進貨紀錄 |
| /api/supplier/create | POST | 新增廠商（含 payment_method, closing_day, pay_day） |
| /api/supplier/\<id\> | PUT | 更新廠商資料 |

#### 需求表

| 端點 | 方法 | 說明 |
|------|------|------|
| /api/needs/latest | GET | 最新待處理需求 |
| /api/needs/batch | POST | 批次新增需求（採購類 / 調撥類） |
| /api/needs/cancel | POST | 取消需求 |
| /api/needs/purchase | POST | 標記已採購（老闆操作） |
| /api/needs/transfer | POST | 標記已調撥（會計操作） |
| /api/needs/\<id\>/transfer | POST | 單筆標記已調撥 |
| /api/needs/arrive | POST | 批次到貨 |
| /api/needs/\<id\>/arrive | POST | 單筆到貨 |
| /api/needs/\<id\>/complete | POST | 完成需求 |
| /api/needs/overdue-arrival | GET | 逾期收貨提醒 |
| /api/needs/history | GET | 需求歷史紀錄 |
| /api/needs/recent | GET | 最近 14 天紀錄 |
| /api/needs/transfers | GET | 調撥列表（`request_type='調撥'` 篩選） |

#### 報價 / 訂單（單據）

| 端點 | 方法 | 說明 |
|------|------|------|
| /api/quote/next-no | GET | 取得下一個報價單號（QT{date}-NNN） |
| /api/sales-doc/create | POST | 新增報價單或訂單 |
| /api/sales-doc/list | GET | 列表（舊版，僅支援 type 篩選） |
| /api/sales-doc/query | GET | 列表（新版，支援 type, status, from, to, q, page） |
| /api/sales-doc/status | POST | 更新單據狀態 |
| /api/sales-doc/delete | POST | 刪除單據及品項 |
| /api/sales-doc/convert | POST | 報價單轉訂單（QUOTE → ORDER） |

#### 客戶 / 庫存 / 班表

| 端點 | 方法 | 說明 |
|------|------|------|
| /api/customer/search | GET | 客戶搜尋 |
| /api/customer/detail/\<id\> | GET | 客戶詳細資料 + 購買紀錄 |
| /api/customer/smart-suggest | GET | 客戶智慧推薦（常購/近購/興趣三組，銷貨輸入用） |
| /api/customers/search | GET | 客戶模糊搜尋（需求表用） |
| /api/inventory/list | GET | 庫存分頁列表（單位成本用當月均價即時計算） |
| /api/inventory/product/\<code\> | GET | 單品各倉庫存（依豐原→潭子→大雅→業務部→總公司排序） |
| /api/products/search | GET | 產品搜尋（先查庫存，再 fallback products，直接回傳陣列） |
| /api/roster/monthly | GET | 整月班表 |
| /api/roster/batch | POST | 批次儲存班表 |

#### 人員 / 督導 / 獎金

| 端點 | 方法 | 說明 |
|------|------|------|
| /api/staff/list | GET | 員工列表 |
| /api/staff/\<id\> | PUT | 更新員工資料 |
| /api/supervision/submit | POST | 儲存督導評分 |
| /api/supervision/recent | GET | 最近督導評分 |
| /api/store/supervision | GET | 門市督導環境分 |
| /api/personal/supervision | GET | 個人督導人員分 |
| /api/service-records | GET / POST | 外勤服務紀錄 |
| /api/service-records/\<id\> | DELETE | 刪除服務紀錄 |
| /api/bonus-rules | GET / POST | 獎金規則管理 |
| /api/bonus-rules/\<id\> | PUT / DELETE | 更新 / 刪除規則 |
| /api/bonus-calculate | POST | 計算日期範圍獎金 |
| /api/bonus-results | GET | 獎金結果列表 |
| /api/bonus-personal | GET | 個人獎金查詢 |

#### 公告 / 推薦備貨 / 目標

| 端點 | 方法 | 說明 |
|------|------|------|
| /api/system/announcements | GET / POST | 公告列表 / 新增 |
| /api/system/announcements/all | GET | 全部公告 |
| /api/system/announcements/\<id\> | PUT / DELETE | 更新 / 刪除公告 |
| /api/recommended-categories | GET / POST | 推薦備貨分類 |
| /api/recommended-categories/\<id\> | DELETE | 刪除分類 |
| /api/recommended-products | GET / POST | 推薦備貨商品 |
| /api/recommended-products/\<id\> | PUT / DELETE | 更新 / 刪除商品 |
| /api/targets | GET | 目標讀取 |
| /api/targets/save | POST | 目標儲存 |

#### LINE 回覆 / 待建檔 / 系統

| 端點 | 方法 | 說明 |
|------|------|------|
| /api/line-replies | GET / POST | LINE 回覆記錄列表 / 新增 |
| /api/line-replies/\<id\> | PUT / DELETE | 更新 / 刪除回覆 |
| /api/staging/list | GET | 暫存記錄列表（含 temp_customer_id, temp_product_id） |
| /api/staging/\<id\>/resolve | PUT | 配對解消（接受 resolved_code, resolved_name, resolve_method） |
| /api/staging/stats | GET | 各類型待處理數量 |
| /api/product-staging/list | GET | 產品待建檔列表 |
| /api/product-staging/\<id\>/resolve | PUT | 標記產品待建檔完成 |
| /api/boss/pending-needs | GET | 老闆待審核需求 |
| /api/boss/needs/\<id\>/status | POST | 更新需求狀態 |
| /api/boss/needs/\<id\>/notes | POST | 新增備註 |
| /api/store-manager/today | GET | 今日門市數據 |
| /api/store/reviews | GET | 門市評論統計 |
| /api/google-reviews | GET | Google 評論列表 |
| /api/summary | GET | 首頁摘要 |
| /api/health | GET | 綜合系統健康檢查（系統資源/資料庫/資料新鮮度/匯入筆數/整體燈號） |
| /api/ai/chat | POST | AI 幫手對話（本地 oMLX 模型，意圖分類 + 自動注入 ERP 資料上下文） |
| /api/ai/daily-summary | GET | 今日摘要（純 DB 查詢，依角色回傳老闆版或員工版） |
| /api/audit-log | GET | 操作日誌查詢（支援 operator, action, date_from, date_to 篩選 + 分頁） |
| /api/audit-log/export | GET | 操作日誌 CSV 匯出（UTF-8 BOM，最多 5000 筆） |

#### 財務管理

| 端點 | 方法 | 說明 |
|------|------|------|
| /api/finance/dashboard | GET | 財務總覽（P&L、門市營收、毛利率） |
| /api/finance/petty-cash/info | GET | 零用金共用池餘額與額度 |
| /api/finance/petty-cash/log | GET | 零用金支出明細（支援 department 篩選） |
| /api/finance/petty-cash/log | POST | 登記零用金支出（含 department, invoice_no） |
| /api/finance/petty-cash/refill | POST | 零用金撥補 |
| /api/finance/petty-cash/init | POST | 設定零用金月額度 |
| /api/finance/receivables | GET | 應收帳款列表（支援 status 篩選） |
| /api/finance/receivables | POST | 新增應收帳款 |
| /api/finance/receivables/confirm | POST | 標記單筆應收已收款 |
| /api/finance/receivables/batch-confirm | POST | 整批沖帳（同一客戶同一帳期） |
| /api/finance/receivables/summary | GET | 月結摘要（按客戶 × 帳期彙總） |
| /api/finance/payables | GET | 應付帳款列表（支援 status, company 篩選） |
| /api/finance/payables | POST | 新增應付帳款（含 company, pretax_amount, tax_amount） |
| /api/finance/payables/confirm | POST | 標記應付已付款 |
| /api/finance/transactions | GET | 收支日記帳列表（支援 store, type, month 篩選） |
| /api/finance/transactions | POST | 新增收支紀錄 |
| /api/finance/tax | GET | 年度稅務統計（營業稅 = 銷售額 × 5/105） |
| /api/finance/cashflow | GET | 30 天現金流預測 |
| /api/finance/vendor-reconcile | GET | 廠商對帳月報（支援 company 篩選） |

#### 盤點作業

| 端點 | 方法 | 說明 |
|------|------|------|
| /api/inventory-count/create | POST | 建立盤點單（自動快照庫存） |
| /api/inventory-count/list | GET | 盤點單列表 |
| /api/inventory-count/\<id\> | GET | 盤點單明細（含所有品項） |
| /api/inventory-count/\<id\>/save | POST | 暫存實際數量 |
| /api/inventory-count/\<id\>/submit | POST | 送出審核 |
| /api/inventory-count/\<id\>/approve | POST | 老闆核准（寫入調整紀錄） |
| /api/inventory-count/\<id\>/reject | POST | 老闆退回重盤 |
| /api/inventory-count/\<id\> | DELETE | 刪除盤點單（僅 drafting 狀態） |

#### 電腦故障檢測

| 端點 | 方法 | 說明 |
|------|------|------|
| /api/fault/groups | GET | 取得所有故障群組（含各群組情境數量） |
| /api/fault/scenarios | GET | 依 group_key 取得群組內所有情境（含 steps/causes/tests/fix JSON） |
| /api/fault/scenario/\<id\> | GET | 單一情境詳細資料（含 group_label） |
| /api/fault/search | GET | 關鍵字搜尋情境（LIKE 比對 title + keywords） |
| /api/fault/ai-diagnose | POST | AI 故障診斷（多關鍵字搜尋 → 前 3 情境注入 system prompt → oMLX 模型回答） |
| /api/fault/next-no | GET | 自動產生檢測單號（RPT-YYYYMMDD-NNN 流水號） |
| /api/fault/save-report | POST | 儲存檢測結論單至 fault_reports 資料表 |
| /print/repair-report | GET | 檢測結論單列印頁（信紙風格，含印章 + 存為 PDF） |

#### 維修作業

| 端點 | 方法 | 說明 |
|------|------|------|
| /api/repair/create | POST | 建立維修作業（自動產生工單號 RO-{店碼}{YYYYMMDD}-{NNN}，預設狀態「檢測中」） |
| /api/repair/update | POST | 更新工單（狀態推進、診斷、零件、工資等） |
| /api/repair/list | GET | 工單列表（支援 status, q 篩選 + 分頁） |
| /api/repair/detail/\<order_no\> | GET | 工單詳細（含零件明細） |
| /api/repair/delete/\<order_no\> | DELETE | 刪除工單（老闆限定） |
| /api/repair/phrases | GET | 常用診斷短語列表 |
| /api/repair/delete | POST | 刪除工單（老闆限定，記入 audit_log） |
| /api/repair/phrases | POST | 新增常用短語 |
| /repair_receipt/\<order_no\> | GET | 收件單 HTML 列印頁（A4 雙聯，客戶聯＋店留聯） |
| /repair_workorder/\<order_no\> | GET | 維修單 HTML 列印頁（含零件報價明細、注意事項、簽章欄） |

#### 客戶單據列印（HTML 信紙風格）

| 端點 | 方法 | 說明 |
|------|------|------|
| /print/quote/\<doc_no\> | GET | 報價單 HTML 列印頁（信紙風格，含存為 PDF） |
| /print/order/\<doc_no\> | GET | 訂購單 HTML 列印頁（信紙風格，含存為 PDF） |
| /print/sales/\<sales_no\> | GET | 銷貨單 HTML 列印頁（信紙風格，含存為 PDF） |

#### PDF 列印（內部用）

| 端點 | 方法 | 說明 |
|------|------|------|
| /api/pdf/quote/\<doc_no\> | GET | 報價單 PDF（舊版 reportlab，已停用） |
| /api/pdf/order/\<doc_no\> | GET | 訂單 PDF（舊版 reportlab，已停用） |
| /api/pdf/sales/\<invoice_no\> | GET | 銷貨單 PDF（舊版 reportlab，已停用） |
| /api/pdf/inventory-count/\<count_id\> | GET | 盤點表 PDF（reportlab，仍使用中） |

---

## 8. 權限系統

### 8.1 角色定義

| 角色 | 主要權限範圍 |
|------|-------------|
| 老闆 | 全部功能，含成本/毛利資訊、刪除操作 |
| 會計 | 需求調撥處理、銷貨/進貨輸入、獎金報表、庫存成本可見、財務管理全模組 |
| 門市部主管 | 門市業績、督導評分、班表管理 |
| 業務部主管 | 業務部績效、業務員管理 |
| 門市工程師 | 需求表、班表查詢、客戶查詢 |
| 業務人員 | 需求表、外勤服務紀錄、客戶查詢 |

### 8.2 敏感資訊控制

- 成本、毛利、毛利率：僅老闆、會計可見（`canViewCost` flag）
- 刪除操作：僅老闆（`canDelete` flag）
- 老闆控制台、admin 頁面：僅老闆可存取
- Password 欄位：API 從不回傳

### 8.3 業績人員對應

| 部門 / 門市 | 人員 |
|------------|------|
| 門市部（主管） | 莊圍迪 |
| 豐原門市 | 林榮祺、林峙文 |
| 潭子門市 | 劉育仕、林煜捷 |
| 大雅門市 | 張永承、張家碩 |
| 業務部（主管） | 萬書佑 |
| 業務人員 | 鄭宇晉、梁仁佑 |

---

## 9. 業務邏輯詳解

### 9.1 需求表雙軌流程

需求表分兩種類型，流程略有差異：

**採購類（request_type = '採購'）**

| 階段 | 角色 | 動作 | 狀態 |
|------|------|------|------|
| 1 | 員工 | 送出需求 | 待處理 |
| 2 | 老闆 | 按採購 | 已採購 |
| 3 | 申請人 | 按到貨 | 已完成 |

**調撥類（request_type = '調撥'）**

| 階段 | 角色 | 動作 | 狀態 |
|------|------|------|------|
| 1 | 員工 | 送出需求（含 transfer_from） | 待處理 |
| 2 | 會計 | 按調撥 | 已調撥 |
| 3 | 申請人 | 按到貨 | 已完成 |

取消規則：老闆可取消任意待處理需求；一般員工僅可取消自己的需求，且需在 30 分鐘內。

### 9.2 推薦備貨流程

推薦備貨選購（`recommended_products.html`）送出後，統一建立**調撥類**需求：

- `request_type = '調撥'`
- `transfer_from = '總公司倉庫'`（未來採購統一進總公司倉庫，再調撥各門市）
- `department = 填表人部門`
- `remark` 自動加入 `[推薦備貨]` 標記

因此推薦備貨送出後，會在**會計頁面**的待調撥清單中出現，由會計確認後執行調撥。

### 9.3 調撥來源倉庫

需求表調撥來源（`transfer_from`）可選：豐原門市、潭子門市、大雅門市、**總公司倉庫**。
系統會自動排除填表人自身所在門市。

### 9.4 成本計算邏輯

銷貨寫入時即帶入成本，採三級 fallback 機制：

**優先序：最近一次進貨單價 → 近 90 天加權平均 → 0**

```sql
-- 1) 最近一次進貨單價（per product_code）
WITH last_purchase AS (
    SELECT product_code,
           CAST(amount AS REAL) / quantity AS unit_cost,
           ROW_NUMBER() OVER (PARTITION BY product_code ORDER BY date DESC, id DESC) AS rn
    FROM purchase_history
    WHERE quantity > 0 AND amount > 0
),
-- 2) 近 90 天加權平均
recent_avg AS (
    SELECT product_code,
           CAST(SUM(amount) AS REAL) / SUM(quantity) AS avg_cost
    FROM purchase_history
    WHERE date >= date('now','-90 days') AND quantity > 0 AND amount > 0
    GROUP BY product_code
)
-- COALESCE(last_purchase.unit_cost, recent_avg.avg_cost, 0) AS unit_cost
```

`sales_history.cost` 存放**總成本**（unit_cost × quantity），`profit = amount - cost`。服務類品項（SE- 開頭）無進貨紀錄，成本自然為 0，毛利率 100%。

### 9.8 雙公司抬頭

系統支援兩家公司抬頭交替使用：

| 公司名稱 | 統一編號 |
|----------|----------|
| 電瑙舖資訊有限公司 | 27488187 |
| 鋒鑫資訊有限公司 | 90284112 |

進貨輸入（`purchase_input.html`）新增公司選單，提交後寫入 `purchase_history.company`。應付帳款與廠商對帳頁面皆支援以公司篩選，方便各公司獨立對帳。

### 9.14 進貨未稅／含稅金額邏輯

進貨輸入頁面支援未稅與含稅金額自動計算，依發票號碼欄位觸發：

| 情境 | 發票號碼 | 金額處理 |
|------|----------|----------|
| 有發票 | 已填入 | 含稅金額 = 未稅金額 × 1.05（台灣營業稅 5%），稅額自動顯示 |
| 無發票 | 空白 | 僅使用未稅金額，稅額為 0 |

提交時 `tax_amount` 隨 payload 送出，後端計算 `payable amount = total + tax`。應付帳款（`finance_payables`）同步記錄 `pretax_amount` 與 `tax_amount`，統計列分別顯示未付款（未稅）、稅額、未付款（含稅）、已付款四組數字。

進貨紀錄修改（編輯 Modal）亦支援修改進貨公司（下拉選單）、發票號碼、入庫倉庫三個欄位。

### 9.15 客戶建檔規則

#### 客戶編號前綴

| 前綴 | 所屬 | 狀態 |
|------|------|------|
| FY | 豐原門市 | 使用中 |
| TZ | 潭子門市 | 使用中 |
| DY | 大雅門市 | 使用中 |
| OW | 業務部 | 使用中 |
| SL | （已停用） | 停用 |

#### 必填欄位

客戶建檔必填項：客戶姓名、手機號碼（09 開頭 10 碼，前端驗證格式）。

#### 付款方式

| 選項 | 值 | 說明 |
|------|---|------|
| 不指定 | 空字串 | 預設值 |
| 現金 | C | 一般現金交易 |
| 月結 | M | 月結客戶，銷貨時自動切換付款方式 |

### 9.16 報價單與銷貨輸入強化

報價單（`quote_input.html`）與銷貨輸入（`sales_input.html`）新增以下功能：

- **客戶名稱欄位加寬**：跨 2 個 grid column，避免長公司名被截斷
- **產品即時搜尋**：產品名稱欄位輸入時即時呼叫 `/api/products/search` 進行模糊搜尋，下拉選取
- **報價單新增產品編號欄位**：表格新增「產品編號」欄，支援以編號搜尋產品（`searchProdByCode()`），選取後自動帶入品名
- **報價單預設 3 列**：開啟時自動顯示 3 列產品輸入行（可繼續新增）
- **供應商選單統一風格**：進貨輸入的供應商欄位由 autocomplete 改為標準 `<select>` 下拉選單，與其他頁面一致

### 9.18 盤點作業

會計每月兩次到各門市盤點庫存，系統提供完整的盤點建立、填寫、送審、核准流程。

#### 資料表結構

**inventory_count（盤點單表頭）**

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | INTEGER PK | 自動遞增 |
| count_no | TEXT | 盤點單號，格式 `IC-YYYYMMDD-NNN` |
| warehouse | TEXT | 盤點倉庫（豐原門市、潭子門市、大雅門市、業務部、總公司倉庫） |
| status | TEXT | 狀態：drafting / submitted / approved / rejected |
| note | TEXT | 備註 |
| created_by | TEXT | 建立者 |
| created_at | DATETIME | 建立時間 |
| submitted_at | DATETIME | 送審時間 |
| reviewed_by | TEXT | 審核者 |
| reviewed_at | DATETIME | 審核時間 |

**inventory_count_items（盤點品項明細）**

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | INTEGER PK | 自動遞增 |
| count_id | INTEGER FK | 對應 inventory_count.id |
| product_code | TEXT | 產品編號（來自 inventory.product_id） |
| product_name | TEXT | 產品名稱（來自 inventory.item_spec） |
| book_qty | INTEGER | 帳面數量（建立時快照） |
| actual_qty | INTEGER | 實際盤點數量（盤點人填入） |
| diff | INTEGER GENERATED | 差異 = actual_qty - book_qty（actual_qty 為 NULL 時 diff 亦為 NULL） |
| remark | TEXT | 差異說明備註 |

**inventory_adjustments（庫存調整紀錄）**

核准後系統自動寫入差異調整紀錄，欄位包含 count_id、product_code、product_name、warehouse、book_qty、actual_qty、adjust_qty、approved_by。

#### 狀態流程

```
drafting（盤點中）→ submitted（待審核）→ approved（已核准）
                                      → rejected（已退回）→ drafting
```

- **建立**：選擇倉庫後自動從 `inventory` 表快照該倉庫所有品項與帳面數量
- **填寫**：盤點人逐項填入實際數量，可多次暫存
- **送審**：需所有品項皆已填入實際數量，送出後鎖定不可編輯
- **核准**：老闆審核，僅顯示有差異的品項，核准後寫入 inventory_adjustments
- **退回**：老闆退回至 drafting 狀態，盤點人可重新填寫
- **刪除**：僅 drafting 狀態的盤點單可刪除

#### API 端點

| 端點 | 方法 | 說明 |
|------|------|------|
| /api/inventory-count/create | POST | 建立盤點單（自動快照庫存） |
| /api/inventory-count/list | GET | 盤點單列表 |
| /api/inventory-count/\<id\> | GET | 盤點單明細（含所有品項） |
| /api/inventory-count/\<id\>/save | POST | 暫存實際數量 |
| /api/inventory-count/\<id\>/submit | POST | 送出審核 |
| /api/inventory-count/\<id\>/approve | POST | 老闆核准 |
| /api/inventory-count/\<id\>/reject | POST | 老闆退回 |
| /api/inventory-count/\<id\> | DELETE | 刪除盤點單（僅 drafting） |

#### 頁面

`inventory_count.html`，側邊欄入口「盤點作業」，權限限老闆與會計。頁面分兩個 Tab：「建立盤點」（選擇倉庫、建立新單）和「盤點紀錄」（歷史列表、開啟/刪除）。盤點詳情含可捲動表格供填入實際數量，老闆審核區僅顯示差異品項。

### 9.9 零用金管理

採**共用池**制度，全公司共用每月 $50,000 額度，由老闆/會計撥補。各門市與部門（豐原門市、潭子門市、大雅門市、業務部、總公司）登入後可登記支出，系統依登入者自動帶入所屬部門。支出分類含：文具、交通、餐飲、雜支、設備維修、郵資。每筆支出可填寫發票號碼以利核銷。

### 9.10 財務總覽（P&L）

財務總覽儀表板顯示：營業收入（`SUM(sales_history.amount)`）、銷貨成本（`SUM(amount) - SUM(profit)`，即實際成本）、毛利與毛利率、本月進貨總額、獎金支出、其他支出、其他收入、淨利。各門市/部門營收以長條圖呈現，數據來源為 `staff` 表的 `store`/`department` 欄位對應。

### 9.11 廠商管理與帳期

#### 廠商資料來源

初始資料由 `purchase_history` 彙整匯入，依進貨次數排序編號（SP-0001 為最常使用廠商）。進貨輸入提交時，若廠商不存在於 `suppliers` 表，系統自動建檔並分配下一個 SP 編號。

#### 結構化帳期

每家廠商設定三個帳期欄位：

| 欄位 | 說明 | 範例 |
|------|------|------|
| payment_method | 付款方式 | 匯款 / 支票 / 現金自取 |
| closing_day | 每月結帳日 | 25、26、28（各廠商不同） |
| pay_day | 匯款日 | 28（匯款專用，預設 28） |

顯示格式範例：「25日結 / 每月28日匯款」、「25日結 / 月底支票」、「現金自取」。

#### 自動產生應付帳款

進貨輸入提交時，若金額 > 0 且廠商已設定帳期，系統自動在 `finance_payables` 建立應付帳款並計算到期日：

1. **判定帳期**：以進貨日期與 `closing_day` 比較，決定歸屬哪個結帳月份。若進貨日 ≤ 結帳日，歸屬當月；否則歸屬下月。
2. **計算付款月**：結帳月份的下一個月為付款月。
3. **決定到期日**：
   - 匯款：付款月的 `pay_day`（預設 28 日）
   - 支票：付款月的最後一天（月底寄出）
   - 現金自取：不設到期日

範例：3/20 進貨、結帳日 25 → 歸屬 3 月帳期 → 付款月 4 月 → 匯款到期日 4/28、支票到期日 4/30。

### 9.12 銷貨自動產生應收帳款

銷貨輸入提交時，系統依付款方式自動判斷是否掛帳：

| 付款方式 | 觸發條件 | 應收金額 | 到期日 | 備註標記 |
|----------|----------|----------|--------|----------|
| 月結 | 前端選擇「月結」或客戶 `payment_type='M'` | 總金額 − 訂金 | 下月月底（結帳日統一 25 號） | 帳期 YYYY-MM |
| 申辦分期 | 前端選擇「申辦分期」 | 總金額 − 訂金 | 銷貨日 + 7 天 | 申辦分期 |
| 現金 / 匯款 / 刷卡 | — | 不產生應收 | — | — |

月結客戶（`customers.payment_type='M'`）目前有 15 家，選擇客戶時自動將付款方式切為「月結」。非月結客戶也可在銷貨時手動選擇「月結」掛帳。

#### 月結整批沖帳

應收帳款頁面提供「月結摘要」頁籤，將同一客戶同一帳期的應收帳款彙總為一組，顯示發票張數與總金額。客戶月底匯款後，點擊「整批沖帳」一次沖銷該組所有未收款項。

### 9.13 報價→訂單→銷貨（訂金扣除）

完整單據流程：

1. **報價**（quote_input）：建立報價單（QT 開頭），含品項明細。
2. **轉訂單**：報價轉訂單時填入訂金金額，系統計算 `balance_amount = total_amount − deposit_amount`，產生訂單（SO 開頭）。
3. **確認訂單**：訂單狀態改為 CONFIRMED 後，可在銷貨輸入中帶入。
4. **銷貨帶入**：「從訂單帶入」自動填入客戶資料與品項，合計列顯示「總金額 − 訂金 ＝ 應收」。
5. **扣除訂金**：提交銷貨時，自動產生的應收帳款金額 = 總金額 − 訂金。備註中標記「已扣訂金 $N」。

### 9.5 督導評分系統

16 項 32 分制，分三大類。

| 類別 | 項目數 | 總分 | 顯示位置 |
|------|--------|------|----------|
| 環境整潔（1–5 項） | 5 項 | 25 分 | 門市業績頁 |
| 人員表現（6–11 項） | 6 項 | 30 分 | 個人業績頁 |
| LINE 回覆（12–16 項） | 5 項 | 25 分 | 個人業績頁 |
| 合計 | 16 項 | 80 分 | 百分比 = 得分 ÷ 80 × 100（每項 5 分制） |

> **老闆視角**：個人業績頁的督導評分區，老闆登入時顯示「全員督導評分」，列出所有有評分紀錄的人員及各項分數，依百分比降序排列。

### 9.6 銷售獎金系統

- `bonus_rules`：設定商品代碼、時間區間、獎金類型（固定金額 / 百分比）
- `bonus_calculate`：POST 日期範圍 → 交叉比對 sales_history → 寫入 bonus_results
- `bonus_results`：人員 + 商品 + 銷售額 + 獎金金額，可按月份 / 人員查詢

### 9.7 待建檔中心

待建檔中心負責管理尚未建立正式 ERP 編號的客戶與產品，採**自動觸發 + 人工配對解消**雙階段流程。

#### 自動觸發來源

| 來源 | 觸發條件 | 建立類型 |
|------|----------|----------|
| 需求表（`/api/needs/batch`） | 提交時偵測到 `is_new_customer` 或 `is_new_product` | 客戶 / 產品 |
| 外勤服務紀錄（`/api/service-records POST`） | 提交時偵測到 `is_new_customer` | 客戶 |

#### 臨時編號格式

所有待建檔記錄自動分配臨時編號：**`TEMP-YYYYMMDD-NNN`**（日期 + 三位流水號），例如 `TEMP-20260403-001`。由後端 `_gen_temp_id()` 函式產生，依當日現有最大序號遞增。

#### 客戶去重邏輯（手機號碼）

同一手機號碼（09 開頭 10 碼）視為同一客戶，不重複建立待建檔記錄：

1. 清洗手機號碼（`_clean_mobile()`）：移除非數字字元，驗證 `09XXXXXXXX` 格式
2. 查詢 `staging_records` 是否已有相同手機且狀態為 pending 的客戶記錄
3. 若已存在：回傳既有 `temp_customer_id`，若姓名不同則寫入 `audit_log` 記錄差異
4. 若不存在：產生新 `TEMP-YYYYMMDD-NNN` 編號，插入 `staging_records`

產品待建檔不做去重，每次提交皆獨立建立記錄。

#### 配對解消流程（staging_center_v2.html）

管理員在待建檔中心操作兩種解消方式：

| 操作 | 說明 | API |
|------|------|-----|
| 配對既有 | 搜尋現有客戶/產品，選取配對後填入 `resolved_code` + `resolved_name` | `PUT /api/staging/<id>/resolve`（`resolve_method='matched'`） |
| 標記完成 | 已由其他管道處理完畢，直接標記為 resolved | `PUT /api/staging/<id>/resolve`（`resolve_method='manual'`） |

#### 相關資料表

| 資料表 | 用途 |
|--------|------|
| staging_records | 客戶與產品待建檔主表（type='customer' / 'product'，status='pending' / 'resolved'） |
| product_staging | 銷貨輸入品名無法對應 products 表時建立（獨立於 staging_records） |

### 9.17 客戶單據列印（信紙風格 HTML）

客戶三大單據（報價單、訂購單、銷貨單）改為 HTML + CSS 信紙風格呈現，取代舊版 reportlab 表格式 PDF。設計理念為「一封有溫度的信」，讓單據如同店家親筆寫給客戶的書信，而非冰冷的商業表單。

#### 支援單據

| 單據類型 | 路由 | 來源資料表 | 前端按鈕位置 |
|---------|------|----------|------------|
| 報價單 | `GET /print/quote/<doc_no>` | sales_documents + sales_document_items | 報價輸入 → 歷史列表 |
| 訂購單 | `GET /print/order/<doc_no>` | sales_documents + sales_document_items | 銷貨輸入 → 匯入訂單列表 |
| 銷貨單 | `GET /print/sales/<sales_no>` | sales_history（依 sales_invoice_no 歸組） | 銷貨輸入 → 近期銷貨紀錄 |
| 盤點表 | `GET /api/pdf/inventory-count/<count_id>` | inventory_count + inventory_count_items | 盤點作業（仍使用 reportlab PDF） |

#### 信紙版面結構

三張單據共用 `templates/print_letter.html` 模板，透過 Jinja2 `doc_type` 變數切換內容：

1. **信頭**：品牌名（COSH 電腦舖）、公司名稱、地區標示，底部金色分隔線
2. **問候語**：「{客戶姓名}　您好：」
3. **開場段落**：感謝詞 + 單據類型 + 專屬服務顧問姓名
4. **商品明細引言**：依單據類型不同（「報價的商品明細」/「訂購的商品明細」/「消費的商品明細」）
5. **品項列表**：以「· 品名　×數量　NT$ 金額」自然排列，非表格形式
6. **合計區塊**：靠右對齊，含小計、稅額、總計
7. **單據資訊段落**：單號、有效期限（報價單）、訂金/尾款（訂購單）、付款/出貨資訊（銷貨單）
8. **備註區**（如有）
9. **結尾問候**：「有任何問題歡迎隨時與我們聯繫」
10. **署名**：COSH 電腦舖 + 專屬服務顧問 + 日期
11. **公司印章**：SVG 圓形印章（電瑙舖資訊有限公司 / 收發專用 / 日期），opacity 0.82、rotate -30deg
12. **簽收欄**：簽收 + 日期，坐落於信紙橫線上
13. **頁尾**：電話、LINE ID 聯絡資訊

#### 視覺設計

- **字體**：Noto Serif TC（Google Fonts CDN 載入），400/600/700 三重量
- **配色**：白色底（#ffffff）、深墨文字（#2c2720）、信紙橫線（#efe9e0）、棕金強調（#5a3e28）
- **信紙橫線**：CSS `repeating-linear-gradient` 模擬橫線信紙效果
- **印刷適性**：`@page` A4 尺寸、`page-break-inside: avoid` 防止品項與結尾區段斷頁

#### 功能按鈕（列印頁上方，列印時隱藏）

- **列印**：`window.print()` 觸發瀏覽器列印
- **存為 PDF**：使用 `html2pdf.js`（CDN v0.10.2）客戶端直接產生 PDF 下載，不經後端
- **隱藏細項金額**：切換 `.hide-detail` class，隱藏個別品項價格與小計，僅保留總計與數量，適用於不希望客戶看到個別品項定價的場景

#### 技術架構

- **模板**：`templates/print_letter.html`（Jinja2），三種單據共用
- **後端路由**：`app.py` 新增 `/print/quote/`、`/print/order/`、`/print/sales/` 三支路由，查詢資料後 render 模板
- **日期格式輔助函式**：`_fmt_date_zh()` → 「2026 年 4 月 3 日」、`_fmt_date_dot()` → 「2026 . 4 . 3」
- **舊版 PDF 路由**：`/api/pdf/quote/`、`/api/pdf/order/`、`/api/pdf/sales/` 仍保留但前端不再連結，`/api/pdf/inventory-count/` 盤點表仍使用 reportlab
- **`pdf_utils.py`**：盤點表 PDF 仍使用此共用模組

### 9.19 電腦故障檢測系統

整合門市維修經驗，建立結構化故障知識庫，搭配 AI 對話診斷與信紙風格報告列印，讓工程師快速判斷問題並提供客戶專業檢測報告。

#### 知識庫結構

- **fault_groups**（31 組）：故障群組（如「電源與供電」「硬碟與儲存」），欄位 id / group_key / label / sort_order
- **fault_scenarios**（218 個）：故障情境，欄位 id / group_key / title / severity（高/中/低）/ steps（JSON 陣列）/ causes / tests / fix / keywords
- **fault_reports**：檢測結論單紀錄，欄位 id / report_no（UNIQUE）/ report_date / customer_id / customer_name / technician / scenario / steps / suggestion / created_at
- **資料來源**：由 `import_fault_data.py` 一次性腳本從舊系統 `repair/index.php` 匯入，自動解析 JavaScript `const APP = {...}` 物件

#### 三大功能區塊

1. **AI 對話診斷**：使用者描述故障現象 → 後端多關鍵字分詞搜尋 fault_scenarios → 取前 3 匹配情境注入 system prompt → 轉發至 oMLX 本地模型（gemma-4-e4b-it-8bit）→ 回傳診斷建議 + 匹配情境卡片，點擊卡片可直接帶入結論單
2. **故障樹瀏覽**：左右分欄介面，左側群組列表（含情境數量 badge）→ 點選載入右側情境列表 → 展開查看排查步驟、可能原因、檢測方式、處置建議 → 「帶入結論單」按鈕一鍵填入；支援關鍵字搜尋全庫情境
3. **檢測結論單**：檢測單號（自動產生 RPT-YYYYMMDD-NNN）+ 客戶姓名（結合客戶資料庫即時搜尋，支援姓名/手機號碼模糊搜尋帶入客戶編號）+ 檢測人員（登入自動帶入，唯讀）+ 故障情境 + 排查步驟 + 處置建議，列印時自動儲存至 `fault_reports` 資料表；「列印結論單」開啟獨立信紙風格列印頁（`print_repair_report.html`），含 COSH 品牌信頭、檢測單號、橫線稿紙背景、SVG 公司圓形印章（動態日期）、雙方簽名欄、html2pdf.js 存為 PDF

#### 側邊欄入口

「維修作業」與「維修知識庫」置於「維修檢測」獨立群組下，可見角色：老闆、會計、工程師、業務人員、業務部主管、門市部主管。故障檢測頁面（`fault_diagnose.html`）已於 v3.6 整合至維修作業步驟 2，獨立頁面路由改為重導向至 `/repair_order`。

### 9.20 維修作業系統

六步驟漸進式維修流程，每一步完成後才解鎖下一步，搭配收件單與維修單兩種列印文件。步驟 2（檢測診斷）內嵌 AI 診斷輔助面板與故障知識庫瀏覽面板，技術人員不需離開工單頁面即可使用完整的故障診斷工具。

#### 工單號碼格式

`RO-{店碼}{YYYYMMDD}-{NNN}`，店碼依技術人員所屬門市（FY/TZ/DY/OW），每日每店獨立流水號。

#### 六步驟流程

| 步驟 | 名稱 | 狀態值 | 操作內容 | 可列印文件 |
|------|------|--------|----------|------------|
| 1 | 收件登記 | 檢測中 | 填寫客戶、設備、故障描述 | 收件單（選填） |
| 2 | 檢測診斷 | 檢測中 | 填寫診斷結論（含 AI 輔助 + 知識庫） | — |
| 3 | 報價確認 | 維修中 | 零件明細 + 工資，客戶簽名確認 | 維修單（自動彈出） |
| 4 | 維修作業 | 待取件 | 填寫維修說明 | — |
| 5 | 客戶取件 | 已結案 | 確認取件完成 | — |
| 6 | 結案 | 已結案 | 自動結案，供查詢 | — |

#### 結案路徑

- **正常結案**：步驟 1→2→3→4→5→6，依序推進
- **無法維修**（步驟 2）：技術人員判定無法修復 → 填寫原因 → 狀態改為「已結案」，維修說明追加「【結案】{原因}」
- **客戶不維修**（步驟 3）：報價後客戶放棄 → 填寫原因 → 狀態改為「已結案」，維修說明追加「【結案】{原因}」

#### 步驟 2 診斷輔助（v3.6 整合）

步驟 2（檢測診斷）內嵌兩個可收合面板，展開即用、收合不佔空間：

- **「✦ AI 診斷輔助」面板**：技術人員描述故障現象 → 後端多關鍵字搜尋 fault_scenarios → 前 3 匹配情境注入 system prompt → oMLX 本地模型回答 → 匹配情境卡片點擊直接填入工單檢測結果欄位；底部「將最新回覆填入檢測結果」按鈕可一鍵帶入 AI 回覆全文
- **「📖 故障知識庫瀏覽」面板**：左右分欄介面（群組列表 / 情境列表），支援關鍵字搜尋全庫情境，展開可查排查步驟、可能原因、檢測方式、處置建議，「填入檢測結果」按鈕一鍵帶入工單。知識庫首次展開時才載入（lazy load），不影響頁面載入速度

原獨立故障檢測頁面（`fault_diagnose.html`）與檢測結論單列印（`print_repair_report.html`）已停用，路由改為重導向至 `/repair_order`。

#### 列印文件

- **收件單**（`repair_receipt.html`）：A4 雙聯設計，上半為客戶聯（工單號碼、客戶/設備資訊、故障狀況、注意事項），下半為店留聯（同上 + 客戶簽名欄），中間虛線裁切，含「列印」與「存為 PDF」按鈕
- **維修單**（`repair_workorder.html`）：A4 正式維修單，含店家抬頭、客戶/設備/故障描述/檢測診斷四區段，零件報價明細表（品名/產品編號/數量/單價/小計），費用摘要（零件合計/工資/總計），注意事項五條款，客戶簽名確認欄、技術人員欄、日期欄，含「列印」與「存為 PDF」按鈕

#### 維修工資統一品項

工資使用統一產品代碼 `SV-LABOR`（品名「維修工資」，分類「服務」，單位「次」），系統啟動時自動建立。維修單帶入銷貨輸入時，工資以 `SV-LABOR` 品項寫入，日後可透過工單上的設備類型（桌機/筆電）區分維修貢獻。

#### 銷貨整合

銷貨輸入頁面新增「🔧 從維修單帶入」按鈕，開啟搜尋 Modal 優先顯示「待取件」狀態工單，選取後自動帶入客戶資訊、零件明細與工資。

#### 資料表

- **repair_orders**：id / order_no（UNIQUE）/ customer_id / customer_name / phone / device_type / brand / model / serial_no / symptom / diagnosis / repair_note / status / technician / received_by / labor_fee / parts_total / total_amount / created_at / updated_at / operator
- **repair_order_items**：id / order_no / product_code / product_name / quantity / price / amount
- **repair_phrases**：id / category / content / sort_order（常用診斷短語）

---

## 10. 部署與維運

### 10.1 Gunicorn 設定

| 設定項 | 值 | 說明 |
|--------|---|------|
| bind | 127.0.0.1:8800 | 監聽本機 Port 8800 |
| worker_class | gthread | 多執行緒 Worker |
| workers | 4 | CPU 核心數 × 1 |
| threads | 4 | 每 Worker 執行緒數 |
| timeout | 120s | 請求逾時 |
| max_requests | 1000 + jitter | 防記憶體洩漏自動重啟 |

### 10.2 環境變數（.env）

| 變數 | 預設值 | 說明 |
|------|--------|------|
| DB_PATH | db/company.db | SQLite 資料庫路徑 |
| SECRET_KEY | openclaw-erp-v2-2026 | Flask 密鑰 |
| PORT | 8800 | 服務端口 |

### 10.3 啟動指令

```bash
cd ~/srv/web-site/computershop-erp

# 開發模式（debug=True，自動 reload）
python3 app.py

# 生產模式
gunicorn -c gunicorn.conf.py app:app

# 健康檢查（回傳 overall_status / system / database / data_freshness / import_status）
curl http://127.0.0.1:8800/api/health

# 系統健康頁面（瀏覽器）
open http://127.0.0.1:8800/admin/health
```

### 10.4 日誌位置

- Access Log：`/Users/aiserver/srv/logs/erp_v2_access.log`
- Error Log：`/Users/aiserver/srv/logs/erp_v2_error.log`

### 10.5 絕對禁止事項

- `old system/` 資料夾：唯讀參考，禁止修改
- Parser 腳本（`~/srv/parser/`）：禁止異動
- 資料庫本體：禁止手動刪除資料表或欄位
- Cron 排程：需先確認再調整

---

## 11. Parser 系統（參考）

Parser 系統獨立於新系統之外，位於 `~/srv/parser/`，共 11 支腳本，由 cron 自動排程執行。

| 腳本 | 功能 | 執行時間 |
|------|------|----------|
| sales_parser_v22.py | 銷貨資料匯入 | 每日 10:40 |
| inventory_parser.py | 庫存資料匯入 | 每日 10:30 |
| purchase_parser.py | 進貨資料匯入 | 每日 10:35 |
| customer_parser.py | 客戶資料匯入 | 每日 10:45 |
| feedback_parser.py | 五星評論匯入 | 每日 10:50 |
| roster_parser.py | 班表匯入 | 每日 10:55 |
| performance_parser.py | 績效匯入 | 每日 11:00 |
| supervision_parser.py | 督導評分匯入 | 每日 11:10 |
| service_record_parser.py | 服務記錄匯入 | 每日 11:15 |
| google_reviews_parser.py | Google 評論抓取 | 每日 00:00 |
| needs_parser.py | 需求表即時匯入 | 每 10 分鐘 |

---

## 12. 版本紀錄

| 版本 | 日期 | 更新內容 |
|------|------|----------|
| v1.0 | 2026-03-28 | Phase 0–6 全數完成，系統正式進入測試階段 |
| | | Phase 1–6 全頁面完成，自我檢查修正重複路由、視覺一致性問題 |
| v1.1 | 2026-03-30 | **QA 人工檢查階段修正** |
| | | **新增頁面**：進貨輸入（/purchase_input）、報價作業（/quote_input）、單據查詢（/query） |
| | | **全站 onAppReady 修正**：18 個頁面從 callback 寫法改為 function 定義，修復載入中問題 |
| | | **會計頁面**：修正預設全門市載入失敗、操作改為「調撥」（非「到貨」）、新增 `/api/needs/<id>/transfer` 端點 |
| | | **銷貨輸入**：改為逐筆顯示（移除 GROUP BY）、移除批號欄、刪除改為逐筆（/api/sales/row/<id>）、每筆均顯示日期 |
| | | **庫存查詢**：修正 onAppReady、新增倉庫固定排序（豐原→潭子→大雅→業務部→總公司）、單位成本改為當月均價即時計算 |
| | | **成本計算邏輯**：銷貨列表、庫存查詢統一採當月 purchase_history 加權均價，fallback 至原始值 |
| | | **老闆頁面**：移除產品代碼欄、縮減表格 padding 與 min-width |
| | | **需求頁面**：調撥來源加入總公司倉庫、修正品名即時搜尋（API 格式判斷錯誤）、修正庫存顯示欄位名稱 |
| | | **推薦備貨**：送出改為調撥類需求（transfer_from=總公司倉庫），修正 item_name/remark 欄位對應 |
| | | **進貨 API**：purchase/list 新增日期範圍篩選（from/to） |
| | | **單據查詢頁**：三頁籤設計（銷貨/進貨/報價訂單），新增 /api/sales-doc/query、/api/sales-doc/status、/api/sales-doc/delete |
| v1.2 | 2026-04-01 | **KPI 考核模組上線** |
| | | 季度 KPI 評分、關鍵貢獻申報審核、獎金池計算，完整角色分流 |
| v1.3 | 2026-04-02 | **財務管理模組完整上線** |
| | | **新增 8 個財務頁面**：財務總覽、零用金管理、應收帳款、應付帳款、收支日記帳、稅務統計、現金流預測、廠商對帳 |
| | | **新增 17 個財務 API 端點**（/api/finance/*） |
| | | **新增 6 張財務資料表**：finance_payables, finance_receivables, finance_transactions, finance_petty_cash, finance_petty_cash_log, finance_ledger |
| | | **成本計算邏輯重構**：改為三級 fallback（最近一次進貨單價 → 近 90 天加權平均 → 0），銷貨寫入時即計算 |
| | | **毛利率修正**：P&L 改用 SUM(sales_history.profit) 計算實際毛利，而非以進貨總額作為成本 |
| | | **零用金改共用池**：從每店獨立帳戶改為全公司共用 $50,000/月，新增部門分類、發票號碼欄位、郵資分類 |
| | | **雙公司抬頭支援**：進貨輸入、應付帳款、廠商對帳皆支援電瑙舖資訊有限公司（27488187）／鋒鑫資訊有限公司（90284112）篩選 |
| | | **進貨列表新增公司欄位顯示與篩選** |
| v1.4 | 2026-04-02 | **廠商管理模組上線** |
| | | **新增 2 個廠商頁面**：廠商建檔（/supplier_create）、廠商查詢含編輯（/supplier_search） |
| | | **新增 5 個廠商 API 端點**（/api/supplier/*）：next-id、list、detail、create、update |
| | | **suppliers 資料表強化**：新增 payment_method、closing_day、pay_day、bank_branch 欄位 |
| | | **結構化帳期模型**：付款方式（匯款/支票/現金自取）+ 每月結帳日 + 匯款日，取代舊的文字型 payment_terms |
| | | **進貨自動建檔廠商**：進貨輸入時若廠商不存在自動建檔並分配 SP 編號 |
| | | **進貨自動產生應付帳款**：根據廠商帳期計算到期日，自動寫入 finance_payables |
| | | **廠商編號依進貨頻率排序**：SP-0001 為最常進貨廠商，33 家廠商完成重新編號 |
| | | **廠商查詢頁新增完整編輯功能**：含帳期、銀行資訊（銀行+分行+帳號）編輯 |
| v1.5 | 2026-04-03 | **應收帳款自動化 + 訂單帶入流程強化** |
| | | **月結自動掛帳**：銷貨時付款方式選「月結」或客戶為月結戶，自動產生應收帳款（結帳日統一 25 號，下月月底到期） |
| | | **月結整批沖帳**：應收帳款新增「月結摘要」頁籤，按客戶×帳期彙總，支援一鍵整批沖銷 |
| | | **新增 2 個應收 API**：batch-confirm（整批沖帳）、summary（月結摘要） |
| | | **付款方式調整**：移除「支票」，新增「申辦分期」（分期公司取貨後 7 天匯款） |
| | | **申辦分期自動掛帳**：銷貨日 + 7 天為到期日，自動寫入應收帳款 |
| | | **月結客戶自動辨識**：customers.payment_type='M' 的 15 家客戶選取時自動切換付款方式為月結 |
| | | **銷貨帶入訂單強化**：訂單選單顯示訂金/餘額、帶入後合計列顯示「總金額 − 訂金 ＝ 應收」 |
| | | **訂金扣除**：銷貨提交時應收金額自動扣除訂金，備註標記「已扣訂金 $N」 |
| v1.6 | 2026-04-03 | **待建檔中心完整重建 + 進貨稅額邏輯 + 輸入頁面強化** |
| | | **待建檔中心 v1 邏輯移植**：需求表與外勤服務紀錄自動觸發待建檔，臨時編號 TEMP-YYYYMMDD-NNN 格式，手機號碼去重（同手機 = 同客戶），配對解消 UI（搜尋既有客戶/產品 → 配對 or 標記完成） |
| | | **新增後端 staging helper**：`_gen_temp_id()`、`_clean_mobile()`、`staging_ensure_customer()`、`staging_ensure_product()` 四支函式，needs/batch 與 service-records POST 自動呼叫 |
| | | **進貨未稅／含稅金額**：進貨輸入頁面新增稅額列，有發票時含稅 = 未稅 × 1.05 自動計算，無發票僅用未稅金額 |
| | | **應付帳款稅額支援**：finance_payables 新增 `pretax_amount`、`tax_amount` 欄位，統計列顯示未稅/稅額/含稅/已付款四組數字 |
| | | **進貨紀錄編輯強化**：編輯 Modal 新增進貨公司（下拉選單）、發票號碼、入庫倉庫三個欄位，`PUT /api/purchase/row/<id>` 支援 |
| | | **入庫倉庫對齊庫存**：進貨輸入倉庫選項改為與 inventory 表一致（總公司倉庫、豐原門市、潭子門市、大雅門市、業務部） |
| | | **供應商下拉選單修正**：由 autocomplete 改為標準 `<select>` 下拉選單，與全站風格一致 |
| | | **報價單強化**：新增產品編號欄位 + 即時搜尋（by code / by name）、預設 3 列產品行 |
| | | **銷貨輸入產品搜尋**：產品名稱欄位新增即時模糊搜尋下拉 |
| | | **客戶名稱欄位加寬**：報價與銷貨輸入的客戶名稱改為跨 2 column 顯示 |
| | | **銷貨異常警示修正**：老闆／會計頁面移除「發票號」欄（實為民國曆日期，非發票），修復因 DB 同步遺失欄位導致的載入失敗 |
| | | **客戶建檔調整**：手機改為必填（09 開頭 10 碼前端驗證）、付款方式精簡為 不指定/現金/月結 三選項、移除英文括號標記、OW 前綴改為業務部、SL 前綴停用 |
| | | **手機顯示優先邏輯**：全站客戶搜尋頁面優先顯示 09 開頭手機號碼 |
| v1.7 | 2026-04-03 | **盤點作業功能 + PDF 列印 + 銷貨單號自動產生** |
| | | **盤點作業完整功能**：新增 `inventory_count`、`inventory_count_items`、`inventory_adjustments` 三張資料表，頁面 `inventory_count.html`，側邊欄入口限老闆/會計 |
| | | **盤點流程**：建立盤點單時自動從 inventory 表快照倉庫品項 → 盤點人填寫實際數量（可多次暫存）→ 送審（需全填）→ 老闆核准/退回，核准後寫入調整紀錄 |
| | | **盤點單號格式**：`IC-YYYYMMDD-NNN`，差異欄為 GENERATED ALWAYS AS 自動計算 |
| | | **盤點 API**：create / list / detail / save / submit / approve / reject / delete 共 8 支端點 |
| | | **盤點刪除修復**：`deleteCount()` 加入 try/catch 與 res.ok 檢查，修復 confirm 後無反應的問題 |
| | | **PDF 列印模組**：新增 `pdf_utils.py` 共用模組，使用 reportlab 產生正式商業文件 PDF，混合字型架構支援 Windows / macOS / Linux 三平台 |
| | | **報價單 PDF**：`GET /api/pdf/quote/<doc_no>`，含公司表頭、品項明細、合計、備註、簽核欄 |
| | | **訂單 PDF**：`GET /api/pdf/order/<doc_no>`，額外顯示訂金與尾款明細 |
| | | **銷貨單 PDF**：`GET /api/pdf/sales/<sales_no>`，依 `sales_invoice_no` 聚合同一單號的多筆品項，向下相容舊 `invoice_no` |
| | | **盤點表 PDF**：`GET /api/pdf/inventory-count/<count_id>`，顯示帳面/實際/差異/備註，統計品項數與差異項數 |
| | | **PDF 版面設計**：A4 尺寸，金色分隔線、深色表頭、交替底色、簽核欄、頁尾版權聲明 |
| | | **前端列印按鈕**：報價輸入、銷貨輸入（含訂單列表）、盤點作業頁面新增「列印」按鈕，瀏覽器新分頁預覽 PDF |
| | | **銷貨單號自動產生**：新增 `/api/sales/next-invoice-no` API，格式 `{門市代碼}-{YYYYMMDD}-{NNN}`（FY/TZ/DY/OW），每日每門市獨立流水號 |
| | | **銷貨輸入改版**：出貨倉庫移至首位並預設門市、新增唯讀「銷貨單號」欄位（頁面載入/切換倉庫/切換日期自動產生）、發票號碼改為選填 |
| | | **銷貨紀錄列表**：新增「單號」欄位，以 `sales_invoice_no` 分組顯示，列印按鈕依單號範圍產生整張 PDF |
| | | **sales_history 欄位擴充**：新增 `warehouse`、`payment_method`、`deposit_amount`、`source_doc_no` 欄位，`_ensure_sales_no_column` 自動補齊 |
| | | **歷史資料遷移**：`migrate_sales_no.py` 一次性腳本，將 v1 逐筆獨立單號依「同日期+同業務+同客戶」合併為同一單號，門市代碼由 staff.store 對照（8817 筆 → 4983 組） |
| v1.8 | 2026-04-03 | **客戶單據信紙風格改版** |
| | | **信紙風格列印**：報價單、訂購單、銷貨單改為 HTML + CSS 信紙風格呈現，取代舊版 reportlab 表格式 PDF，設計理念為「一封有溫度的信」 |
| | | **共用模板**：`templates/print_letter.html`（Jinja2），三種客戶單據共用，透過 `doc_type` 變數切換內容（問候語、明細引言、單據資訊段落） |
| | | **新增路由**：`/print/quote/<doc_no>`、`/print/order/<doc_no>`、`/print/sales/<sales_no>` 三支 HTML 列印路由 |
| | | **視覺設計**：Noto Serif TC 字體、白底深墨文字、CSS repeating-linear-gradient 信紙橫線、棕金配色、A4 列印適性 |
| | | **SVG 公司印章**：圓形印章內嵌 SVG（電瑙舖資訊有限公司 / 收發專用 / 動態日期），opacity 0.82、rotate -30deg |
| | | **存為 PDF**：使用 html2pdf.js（CDN v0.10.2）客戶端直接產生 PDF 下載，不經後端 |
| | | **隱藏細項金額**：toggle 功能隱藏個別品項價格，僅保留數量與總計 |
| | | **日期格式函式**：`_fmt_date_zh()` → 「2026 年 4 月 3 日」、`_fmt_date_dot()` → 「2026 . 4 . 3」 |
| | | **前端按鈕更新**：報價輸入、銷貨輸入的列印按鈕改指向 `/print/` 路由（舊 `/api/pdf/` 路由保留但不再連結） |
| | | **全站輸入欄位尺寸統一**：修正 main.css 全局選擇器，新增 `input:not([type])` 捕捉未寫 type 屬性的 input，解決同一行表單欄位忽大忽小的問題；新增 `table input` 緊湊覆蓋規則，表格內所有 input 自動套用小尺寸，不再依賴各頁面自行定義 |
| | | **需求表產品欄位統一**：表頭從「產品代碼 / 品名規格」改為「產品編號 / 產品名稱」，下拉選單改為名稱在上、編號+庫存在下，與報價/銷貨/進貨頁面一致 |
| | | **白皮書 §4.3 改版**：元件規格重寫為「表單級 / 表格級」兩級樣式架構，新增 input type 屬性注意事項說明 |
| | | **全站按鈕樣式統一**：統一三個層級的按鈕規格 — ① 頁面級（儲存/清除）：padding 10px 26px、font-size .82rem、border-radius 8px ② 表格列（刪除/新增行）：刪除按鈕補齊 hover 效果、新增行按鈕統一 dashed 邊框 border-radius 7px ③ 老闆專區表格按鈕：全部改為 outlined 風格 border-radius 6px，取消 999px 膠囊形；按鈕文字一律用中文「刪除」不用符號圖示 |
| | | **老闆專區對齊修正**：操作欄 `.action-wrap` 加 `align-items: center`，備注輸入框 border-radius 8→6px，修正備注與操作按鈕垂直不對齊問題 |
| | | **白皮書 §4.3 按鈕規範**：新增完整三級按鈕樣式規範（頁面級 / 表格列 / 老闘專區），含語意色彩對照表與共通規則 |
| v1.9 | 2026-04-03 | **系統健康檢查頁面上線** |
| | | **綜合健康 API 重構**：`/api/health` 從簡易 DB 連線檢查擴充為五大區塊 — 系統資源（記憶體/磁碟/開機時間，需 psutil）、資料庫（連線/journal mode/DB 大小/WAL 大小）、資料新鮮度（銷貨/進貨/客戶依工作日規則判定 green/yellow/red）、昨日匯入筆數、整體燈號 |
| | | **工作日規則引擎**：進貨 週一～五、銷貨 週一～六、客戶 週一～五，非工作日自動跳過檢查（yellow），工作日缺資料為異常（red） |
| | | **新增頁面**：`templates/admin/health.html`（v2 暖色調風格，extends base.html），四張狀態卡片（系統資源/資料庫/資料新鮮度/匯入筆數）+ 整體狀態橫幅，記憶體與磁碟進度條，匯入明細表格，重新檢查按鈕 |
| | | **側邊欄入口**：系統健康（/admin/health），僅老闆可見 |
| | | **報價有效期限預設值**：從 14 天改為 7 天 |
| | | **零用金權限收窄**：側邊欄零用金管理僅老闆與會計可見（原含工程師、業務人員等） |
| | | **需求表歷史載入修正**：`loadHistory()` 中 `json.data.items` → `json.items`（配合 `ok()` helper 回傳格式，kwargs 在頂層而非 data 下） |
| | | **老闆頁面備注欄位對齊**：`.notes-input` 統一為標準表格輸入規格（padding 5px 7px、border rgba(.15)、font-family Noto Serif TC、font-weight 300），`.btn-save-note` 加 box-sizing: border-box 修正高度不一致 |
| v2.0 | 2026-04-03 | **AI 幫手上線（本地 oMLX 模型）** |
| | | **AI 對話 API**：`POST /api/ai/chat` — 接收使用者訊息與歷史對話，自動依問題關鍵字查詢 ERP 資料庫（銷貨/進貨/庫存/客戶/報價訂單/需求/財務），將即時資料注入 system prompt，再轉發至本地 oMLX 模型取得回答 |
| | | **本地模型配置**：oMLX API `http://127.0.0.1:8001/v1`，模型 `gemma-4-e4b-it-8bit`，API Key `5211`，啟動指令 `'/Applications/oMLX.app/Contents/MacOS/omlx-cli' launch openclaw --model 'gemma-4-e4b-it-8bit' --api-key '5211' --tools-profile 'full'` |
| | | **ERP 資料自動注入**：`_ai_gather_context()` 根據訊息關鍵字智慧查詢 — 銷貨（今日/本月/門市分佈）、進貨（本月）、庫存（總覽/倉庫分佈/產品搜尋）、客戶（總數/月結戶）、報價訂單（張數/待出貨）、需求（各狀態筆數）、財務（零用金/應收/應付），無匹配時 fallback 今日摘要 |
| | | **全站浮動對話框**：右下角 ✦ 浮動按鈕（登入後顯示），點擊展開 380px 對話視窗，深色標題列、暖白訊息區、即時打字指示器，支援 Enter 發送、Shift+Enter 換行、歷史保留 10 輪 |
| | | **權限**：所有角色皆可使用，不限老闆/會計 |
| | | **手機適配**：行動裝置對話框自動全寬、按鈕縮小 |
| v2.1 | 2026-04-04 | **關鍵貢獻審核流程 + 全站佈局統一 + 銷貨單號重整** |
| | | **關鍵貢獻審核流程**：老闆審核主管提交的貢獻、主管填寫自己的並審核所屬員工提交的貢獻，頁面以 Tab 切換「我的填報」與「待審核」（老闆僅顯示審核 Tab） |
| | | **新增 API**：`GET /api/kpi/contributions/review-list` — 依審核者角色回傳下屬 pending 項目（老闆看全部、門市部主管看 engineer、業務部主管看 sales） |
| | | **登入 API 擴充**：`/api/auth/verify` 回傳新增 `role` 欄位（boss/manager/engineer/sales/accountant），供前端判斷權限 |
| | | **待審核 UI**：顯示提交者姓名、職稱、部門、貢獻類別、說明與佐證照片，核准/不通過按鈕，操作後即時刷新並重算 KPI⑤ 分數 |
| | | **全站佈局寬度統一**：7 個頁面移除主佈局容器 `max-width` 限制（customer_create 860px、product_create 760px、supplier_create 860px、supplier_search 900px、needs_input 900px、kpi_contribution 860px、admin/health 960px），統一由 `.content-area` 控制（最大內寬 1160px） |
| | | **銷貨單號重新合併**：全數 8857 筆銷售紀錄重新依「同日期+同業務+同客戶」合併為 4998 張銷貨單，格式統一為西元年 `{店碼}-{YYYYMMDD}-{NNN}`（清除舊民國年格式） |
| | | **側邊欄調整**：「老闆控制台」簡化為「老闆」 |
| | | **CLAUDE.md 規範更新**：新增頁面佈局寬度規則、銷貨單號規則（含店碼對照）、後端注意事項（ok() 格式、macOS 26 trust_env 規則、AI 助手設定） |
| v2.2 | 2026-04-04 | **手機版全面優化 + 待辦頁面新增** |
| | | **底部導覽列**：手機版（≤767px）隱藏左側側邊欄，改為底部 5 入口導覽列（首頁/需求/庫存/班表/更多），「更多」展開全選單面板，角色過濾與側邊欄一致 |
| | | **base.html 手機適配**：底部導覽列 HTML + CSS + JS 寫入共用骨架，main.css 新增 `@media (max-width: 767px)` 區塊控制顯示切換 |
| | | **CLAUDE.md 手機版規範**：所有手機版樣式一律在 `@media (max-width: 767px)` 內新增，禁止修改桌機版樣式 |
| | | **6 頁手機版優化**（僅在各 template `<style>` 內新增媒體查詢，桌機版零異動）： |
| | | — needs_input.html：品項表格卡片化、數量 ±按鈕、歷史表格 data-label 卡片化 |
| | | — inventory_query.html：搜尋列 sticky + 垂直堆疊、倉庫卡片橫向捲動、表格卡片化（隱藏倉庫類型欄） |
| | | — roster.html：月曆隱藏→日卡片垂直列表（今天優先排序、自動捲動到今天）、控制列堆疊 |
| | | — inventory_count.html：盤點表卡片化、實盤輸入加大（font-size 1.1rem）、即時進度條、歷史卡片化 |
| | | — service_record.html：服務類型改為按鈕組選擇（隱藏 select）、紀錄表格卡片化、服務內容取消截斷 |
| | | — supervision_score.html：1–5 分按鈕加大等寬（42px）、固定底部送出按鈕列（毛玻璃效果）、紀錄卡片化 |
| | | **新增 3 個待辦頁面**：待採購清單（`pending_purchase.html`，老闆）、待調撥清單（`pending_transfer.html`，老闆+會計）、待處理需求（`pending_needs.html`，全角色），卡片式 UI 複用現有 API |
| | | **新增 3 個路由**：`/pending_purchase`、`/pending_transfer`、`/pending_needs` |
| | | **側邊欄新增**：「待辦清單」群組加入待處理需求（全角色）、待採購清單（老闆）、待調撥清單（老闆+會計） |
| v2.3 | 2026-04-04 | **手機版導覽強化 + 角色分流 + 待辦頁手機優化** |
| | | **底部導覽列調整**：班表移至「更多」面板，改由「待處理需求」取代（首頁/需求/庫存/待處理/更多），更符合員工日常操作頻率 |
| | | **「更多」面板角色分流**：手機版「更多」僅顯示已完成手機版優化的頁面（`_MOBILE_ROUTES` 白名單機制），桌面版不受影響；各角色看到的項目不同 — 一般員工：班表；會計多看盤點、待調撥；門市主管多看督導評分；業務人員多看外勤服務表；老闆：全部六項（含待採購、待調撥） |
| | | **首頁手機版精簡**：`index.html` 手機版隱藏「待處理需求清單」（`.needs-card`），僅保留營收統計與趨勢圖表；`boss.html` 手機版隱藏銷貨異常警示與待請購清單 |
| | | **3 頁待辦手機版優化**：pending_needs.html、pending_purchase.html、pending_transfer.html 新增 `@media (max-width: 767px)` — 統計列緊湊化、卡片間距縮減、按鈕加大（min-height 46px）、待採購按鈕改上下堆疊、toast 位置移至底部導覽列上方 |
| | | **`_BNAV_ROUTES` 同步更新**：高亮判斷從 roster 改為 pending_needs |
| v2.4 | 2026-04-04 | **AI 幫手強化：意圖分類 + 查詢擴充 + 今日摘要** |
| | | **查詢能力擴充**：`_ai_gather_context()` 新增四組查詢觸發 — 班表（staff_roster 今日各門市值班）、督導評分（supervision_scores 最近三次 + 門市平均）、獎金（bonus_results 本月已確認依人員彙總）、盤點（inventory_count 最近一次差異前五名），所有查詢皆有 LIMIT 控制 |
| | | **意圖分類引擎**：新增 `_ai_classify_intent(message)` 取代原有 if/elif 關鍵字匹配，回傳意圖清單 + 提及人名；13 組意圖（sales/purchase/inventory/customer/document/needs/finance/roster/supervision/bonus/count/product_search/service）對應 13 支獨立查詢函式（`_aiq_*`），支援多意圖合併查詢 |
| | | **人名個人化查詢**：啟動時從 staff 表載入員工名冊，訊息中偵測到人名自動追加 sales + service + bonus 意圖，查詢該人個人銷貨/外勤服務/獎金明細（如「林榮祺這個月怎樣」→ 三組查詢合併回答） |
| | | **時間詞意圖擴展**：「今天/今日/昨天」自動追加 roster + sales 意圖 |
| | | **今日摘要 API**：新增 `GET /api/ai/daily-summary`，純資料庫查詢不走 AI 模型；老闆/會計版（待處理需求筆數 + 各部門本月達成率 + 本週到期應收帳款 + 今日各門市值班人員）；員工版（個人本月業績與達成率 + 本人待處理需求 + 今日班表） |
| | | **登入自動展開摘要**：前端 `_aiLoadDailySummary(user)` 登入成功後自動呼叫 daily-summary API 並顯示今日摘要（v2.8 改為首次登入 + 每 2 小時一次），失敗時靜默忽略 |
| | | **對話記憶延長**：歷史保留從 10 輪延長至 20 輪（前端 `_aiHistory.slice(-20)` + 後端 `history[-20:]`），陣列超過 40 條自動裁切防溢出 |
| | | **新增外勤服務查詢**：意圖 `service` 對應 `_aiq_service()` 查詢 service_records 本月外勤紀錄，支援人名篩選 |
| v2.5 | 2026-04-04 | **智慧銷貨建議 + 操作日誌**（詳見下方） |
| | | **智慧銷貨建議**：新增 `GET /api/customer/smart-suggest`，銷貨輸入選擇客戶後自動推薦三組商品 — ①常購品項（180 天 GROUP BY product_code LIMIT 5）、②近期購買（ORDER BY date DESC LIMIT 5）、③潛在興趣（同付款方式或同業務其他客戶購買但本客戶未購品項，90 天 LIMIT 3）；前端一鍵加入購物車呼叫 `addRow()`，手機版可收合 |
| | | **操作日誌系統**：新增 `audit_log` 資料表（id / timestamp / operator / role / action / target_type / target_id / description / ip_address / extra_json），啟動時自動建表含三個索引（timestamp / operator / action） |
| | | **log_action() 共用函式**：獨立連線寫入，try/except 包覆失敗不影響主流程，自動擷取 IP（X-Forwarded-For fallback remote_addr） |
| | | **埋點 19 處**：auth.login / auth.fail / sales.create / sales.delete / needs.create / needs.cancel（員工＋老闆）/ needs.purchase / needs.transfer / needs.arrive（兩端點）/ needs.complete / doc.create / doc.delete / customer.create / supplier.create / finance.expense / finance.refill / kpi.update |
| | | **查詢 API**：`GET /api/audit-log`（operator / action / date_from / date_to 篩選 + 分頁 50/頁上限 200）、`GET /api/audit-log/export`（CSV UTF-8 BOM，最多 5000 筆） |
| | | **管理頁面**：`admin/audit_log.html`（老闆限定），操作者/動作下拉/日期區間篩選，動作 badge 依類型著色（登入藍/新增綠/刪除紅/更新黃），分頁導覽，CSV 匯出按鈕；側欄系統管理區新增「操作日誌」入口 |
| v2.6 | 2026-04-04 | **電腦故障檢測系統** |
| | | **故障知識庫匯入**：由 `import_fault_data.py` 從舊系統 `repair/index.php` 解析 JavaScript `const APP = {...}` 物件，匯入 31 組故障群組 + 218 個故障情境，自動產生搜尋關鍵字 |
| | | **新增 2 張資料表**：`fault_groups`（id / group_key / label / sort_order）、`fault_scenarios`（id / group_key / title / severity / steps / causes / tests / fix / keywords，steps~fix 為 JSON 陣列） |
| | | **新增 5 支 API**：`GET /api/fault/groups`（群組列表含情境數量）、`GET /api/fault/scenarios`（依 group_key 查）、`GET /api/fault/scenario/<id>`（單一情境含 group_label）、`GET /api/fault/search`（LIKE 搜尋 title + keywords）、`POST /api/fault/ai-diagnose`（多關鍵字分詞搜尋 → 前 3 情境注入 system prompt → oMLX 模型回答） |
| | | **新增頁面 `fault_diagnose.html`**：三區塊介面 — ① AI 對話診斷（描述問題 → AI 回覆 + 匹配情境卡片）、② 故障樹瀏覽（左右分欄群組/情境 + 關鍵字搜尋）、③ 檢測結論單（帶入情境 → 填寫客戶 → 列印），手機版群組改水平捲動 |
| | | **新增列印模板 `print_repair_report.html`**：獨立 HTML 信紙風格（不繼承 base.html），COSH 品牌信頭、CSS 橫線稿紙背景、排查步驟編號列、處置建議圓點列、SVG 圓形公司印章（電瑙舖資訊有限公司 / 收發專用 / 動態日期）、雙方簽名欄、html2pdf.js 存為 PDF |
| | | **側邊欄入口**：「電腦檢測」加入「單據與需求」群組，可見角色：老闆、會計、工程師、業務人員、業務部主管、門市部主管 |
| | | **CSS 快取修正**：base.html CSS 連結加入版本參數（`?v=20260404`），解決瀏覽器快取舊版 main.css 導致底部導覽列與更多面板在桌機版異常顯示的問題 |
| v2.7 | 2026-04-04 | **檢測結論單強化：客戶搜尋 + 單號 + 人員** |
| | | **客戶即時搜尋**：檢測結論單「客戶姓名」欄位結合客戶資料庫，支援與銷貨輸入等頁面一致的即時模糊搜尋（姓名/手機號碼），下拉選單帶入客戶編號（customer_id），復用 `/api/customers/search` API |
| | | **檢測單號自動產生**：新增 `GET /api/fault/next-no` API，格式 `RPT-YYYYMMDD-NNN` 流水號；頁面載入時自動取號，API 不可用時客戶端 fallback 為 `RPT-YYYYMMDD-HHMM` |
| | | **檢測人員自動帶入**：`onAppReady(user)` 登入驗證後自動將當前使用者姓名寫入唯讀欄位 |
| | | **新增資料表 `fault_reports`**：id / report_no（UNIQUE）/ report_date / customer_id / customer_name / technician / scenario / steps / suggestion / created_at，列印時自動儲存 |
| | | **新增 API `POST /api/fault/save-report`**：列印結論單時同步寫入 fault_reports，支援 INSERT OR REPLACE |
| | | **列印模板更新**：`print_repair_report.html` 信頭下方新增檢測單號顯示 |
| | | **JS 衝突修正**：fault_diagnose.html 的 AI 對話歷史變數從 `_aiHistory` 改為 `_fdHistory`，解決與 base.html 全站 AI 助理重複宣告的 SyntaxError |
| v2.8 | 2026-04-04 | **電腦檢測手機版 + AI 展開頻率控制 + 登入時效調整** |
| | | **電腦檢測手機版優化**：fault_diagnose.html 新增完整 `@media (max-width: 767px)` 樣式 — AI 對話輸入/送出按鈕垂直全寬、故障群組水平捲動（隱藏滾動條）、情境詳情與「帶入結論單」按鈕全寬加大、結論單表單單欄排列、列印/清除按鈕上下堆疊全寬、客戶搜尋下拉觸控加大（min-height 44px）、Toast 移至底部導覽列上方 |
| | | **手機版「更多」面板入口**：`/fault_diagnose` 加入 `_MOBILE_ROUTES` 白名單，手機版「更多」面板顯示「電腦檢測」連結 |
| | | **按鈕文字修正**：「列印結論單」改為「列印檢測結果」 |
| | | **AI 助手展開頻率控制**：從「每次載入頁面都自動展開」改為「首次登入展開 + 每 2 小時展開一次」，localStorage `erp_v2_ai_last_open` 記錄上次展開時間，手動打開也重置計時，登出時清除 |
| | | **登入有效期調整**：從「當天 21:00 過期」改為「登入後 4 小時過期」，`saveUser()` 計算 `Date.now() + 4h` 寫入 `erp_v2_exp` |
| v2.9 | 2026-04-04 | **客戶回訪系統 + AI 人格強化** |
| | | **新增資料表 `followup_tasks`**：id / task_no（FU-YYYYMMDD-NNN，UNIQUE）/ source_type / source_id / customer_id / customer_name / customer_phone / assigned_to / assigned_name / round / due_date / status / completed_at / completed_by / result / note / skip_reason / created_at，含 5 組索引（status / assigned_to / due_date / source 複合 / 防重複 UNIQUE） |
| | | **自動產生回訪任務**：`generate_followup_tasks('sale', sales_no, ...)` — 銷貨金額 ≥ $15,000 時自動產生 3 輪回訪（+7 天 / +30 天 / +365 天），負責人為原業務員（離職則回退門市主管），INSERT OR IGNORE 防重複，獨立連線 + try/except 不影響主流程 |
| | | **觸發點**：`sales_submit()` 在 conn.commit() 成功後呼叫（僅銷貨，不含服務記錄） |
| | | **任務單號格式**：`FU-YYYYMMDD-NNN`，每日獨立流水號 |
| | | **新增 6 支回訪 API**：`GET /api/followup/list`（全部清單，支援 status / assigned_to / date_from / date_to / keyword 篩選 + 分頁）、`GET /api/followup/my`（我的待辦，依 staff_id）、`GET /api/followup/today`（今日到期含逾期，可選 staff_id）、`POST /api/followup/complete/<id>`（完成，需填結果）、`POST /api/followup/skip/<id>`（跳過，需填原因）、`GET /api/followup/stats`（統計總覽 + 各人明細） |
| | | **新增頁面 `followup.html`**：5 區塊介面 — ① 統計卡片（全部/待回訪/今日到期/已逾期/已完成/已跳過）、② 篩選列（狀態/人員/日期/關鍵字 debounce）、③ 任務列表（逾期紅底高亮、狀態 badge、完成/跳過按鈕、分頁）、④ 人員統計格、⑤ 圖表（Chart.js 圓餅圖 + 堆疊長條圖） |
| | | **完成彈窗**：回訪結果下拉（客戶滿意/反映問題/有加購意願/未接聽/其他）+ 備註，寫入 audit_log |
| | | **跳過彈窗**：跳過原因 textarea，寫入 audit_log |
| | | **首頁回訪提醒**：`index.html` 新增綠色橫幅（有逾期改紅色），顯示員工今日/逾期回訪任務（最多 5 筆），含「查看全部 →」連結 |
| | | **老闆頁面回訪總覽**：`boss.html` 新增「客戶回訪總覽」區塊（5 張迷你統計卡 + 各人員待辦/逾期/完成明細），含「查看全部 →」連結 |
| | | **AI 意圖辨識擴充**：新增 `followup` 意圖（關鍵字：回訪/追蹤/回電/客戶回訪/跟進），對應 `_aiq_followup()` 查詢函式 — 指定人名列出個人待辦（含逾期標記），無人名顯示全體統計 + 今日到期明細 |
| | | **每日摘要整合**：老闆/會計版新增「📞 客戶回訪：待辦 X 筆（今日/逾期 Y 筆）」；員工版新增「📞 今日回訪任務：X 筆待處理」 |
| | | **側邊欄入口**：「客戶回訪紀錄」加入「工作紀錄」群組（LINE 回覆表下方），全角色可見 |
| | | **手機版**：頁面含完整 `@media (max-width: 767px)` 響應式樣式，但不加入手機版「更多」面板（桌機版專用） |
| | | **AI 人格強化**：柔柔稱呼同事時只叫後兩字（如「榮祺」而非「林榮祺」），每日摘要同步適用 |
| | | **每日摘要改用本地模型**：`/api/ai/daily-summary` 從硬編碼模板改為收集 ERP 資料後交由 oMLX 本地模型（柔柔人格）生成自然語氣問候，每次登入內容不重複；模型不可用時自動 fallback 為靜態格式 |
| | | **班別時段客製化**：每日摘要根據個人當日班別（早班 10–18 / 晚班 12–20 / 全天 10–20 / 值班 10–18 / 休假）精準判斷上下班時段，prompt 包含星期、營業時間（週一～六 10–20、週日 10–18）、班別工時，讓柔柔的問候貼合個人排班（如晚班早上登入提醒「還沒到上班時間」、快下班前「再撐一下，18:00 就下班了」、休假登入「怎麼還登入系統啦～好認真」） |
| | | **系統規模**：62 張資料表、209 支 API 路由、8,508 行 app.py |
| v3.0 | 2026-04-05 | **每日摘要精簡 + 登入時效統一 + 故障診斷 JS 修復** |
| | | **每日摘要精簡（老闆版）**：移除全部 5 項資料查詢（待處理需求/部門達成率/本週應收/值班人員/回訪總覽），改為僅打招呼 + 待採購筆數（有才顯示） |
| | | **每日摘要精簡（會計版）**：同樣移除 5 項資料查詢，改為僅打招呼 + 待調撥筆數（有才顯示） |
| | | **每日摘要精簡（員工版）**：移除個人本月業績與達成率；待處理需求縮窄為僅「已採購」或「已調撥」狀態（提醒按已到貨）；班表改口語化（如「今天在豐原早班」）；保留回訪任務 |
| | | **time_hint 改為事實描述**：所有時段提示改為客觀描述（如「剛上班不久」「再一個小時左右就下班了」「今天休假但登入了系統」），讓本地 AI 模型自由發揮語氣，不再硬編碼加油話 |
| | | **新增剛上班時段判斷**：`hour < my_start + 1` 時識別為「剛上班不久」，精確對應個人班別上班時間 |
| | | **登入有效期統一**：從 4 小時改為 2 小時，與 AI 自動展開間隔一致 |
| | | **故障診斷 JS 衝突修復**：`fault_diagnose.html` 全部函數和元素 ID 加上 `fd` 前綴（`aiSend` → `fdAiSend`、`aiInput` → `fdAiInput`、`chatLog` → `fdChatLog` 等），解決與 `base.html` 柔柔對話框同名衝突導致 AI 診斷回應跑到柔柔對話框的問題 |
| v3.1 | 2026-04-05 | **維修知識庫管理 + PWA 支援 + 介面微調** |
| | | **維修知識庫管理頁面**：新增 `fault_kb.html`，左右分欄介面 — 左側群組列表（新增/改名/刪除）、右側情境卡片（排查步驟/可能原因/檢測方式/處置建議），Modal 彈窗編輯情境（標題/嚴重度/步驟/原因/檢測/建議/關鍵字），上方統計列顯示群組數與情境總數 |
| | | **新增 7 支知識庫管理 API**：`GET /api/fault/kb-stats`（統計 + 維護者 + 最後更新日期）、`POST /api/fault/group/create`、`POST /api/fault/group/update`、`POST /api/fault/group/delete`（須先清空情境）、`POST /api/fault/scenario/create`、`POST /api/fault/scenario/update`、`POST /api/fault/scenario/delete` |
| | | **知識庫統計動態化**：故障檢測頁面知識庫標題改為動態（情境數/群組數/維護者姓名/最後更新日期），資料即時從 DB 取得 |
| | | **側邊欄調整**：「電腦檢測」與「維修知識庫」從「單據與需求」移出，新建「維修檢測」獨立群組；「電腦檢測」更名為「故障檢測」；維修知識庫僅老闆、門市部主管、業務部主管可見 |
| | | **故障診斷輸入改為按鈕送出**：移除 Enter 自動送出行為，使用者需手動按「診斷」按鈕才會呼叫 AI |
| | | **柔柔對話框放大**：桌機版對話視窗從 380×560 放大至 460×640 |
| | | **柔柔漂移範圍縮小**：右邊從 300px 縮至 120px、下方從 300px 縮至 200px，避免遮蓋工作區操作按鈕 |
| | | **標題列高度縮小**：`.top-bar` 從 56px 縮至 38px |
| | | **登入後導向首頁**：`handleLogin` 成功後自動 `location.href = '/'`，確保每次登入回到首頁 |
| | | **每日摘要修正**：老闆/會計版查詢狀態從不存在的「待採購」「待調撥」改為「待處理」，修復登入後柔柔不顯示待處理筆數的問題 |
| | | **PWA 支援**：新增 `static/manifest.json`（App 名稱/圖示/主題色/全螢幕模式）、`static/sw.js`（Service Worker，網路優先 + 靜態資源快取）、`static/icons/` 192×192 及 512×512 App 圖示；`/sw.js` 路由從根路徑提供確保 scope 覆蓋全站；`base.html` 加入 manifest / theme-color / apple-touch-icon / SW 註冊；CSS 版本號更新至 `v=20260405` |
| | | **scenario detail API 修正**：`/api/fault/scenario/<id>` 回傳新增 `keywords` 欄位，供知識庫編輯 Modal 正確載入關鍵字 |
| v3.2 | 2026-04-05 | **PWA 品牌化 + 完整 Favicon 套件 + 登入時效延長** |
| | | **PWA 名稱更新**：`manifest.json` App 名稱從「COSH ERP」改為「電腦舖ERP」（short_name），安裝到手機桌面時顯示中文名稱 |
| | | **完整 Favicon 套件**：重新製作 9 個圖示檔案，統一黑底 + 白色 COSH 文字 + 金色微笑弧線（`#FABF13`）風格 — `icon-512x512.png`（PWA 啟動畫面，COSH+微笑）、`icon-192x192.png`（PWA 主畫面，COSH+微笑）、`apple-touch-icon.png`（iOS 180×180，COSH+微笑）、`mstile-150x150.png`（Windows 磚，微笑）、`favicon-48x48.png`（高解析 favicon，微笑）、`favicon-32x32.png`（標準 favicon，微笑）、`favicon-16x16.png`（最小 favicon，微笑）、`favicon.ico`（16+32+48 多尺寸 ICO）、`safari-pinned-tab.svg`（Safari 釘選分頁，單色微笑輪廓） |
| | | **base.html 圖示引用完善**：新增 `favicon.ico`、`favicon-32x32.png`、`favicon-16x16.png`、`msapplication-TileImage`、`mask-icon` 等 meta/link 標籤，`apple-touch-icon` 修正指向正確的 `apple-touch-icon.png`（原指向 `icon-192x192.png`） |
| | | **登入有效期延長**：從 2 小時延長至 24 小時，適合手機 PWA 整天免重登；AI 助手自動展開間隔維持 2 小時不變 |
| v3.3 | 2026-04-05 | **PWA 推播通知系統 + HTML 快取控制** |
| | | **VAPID Web Push 全端實作**：使用 EC P-256 金鑰對（`.env` 存放），後端 `pywebpush` 發送推播，前端 `PushManager.subscribe()` 訂閱；Service Worker（`sw.js` CACHE_NAME v3.2）新增 `push` 事件（顯示通知含圖示/badge/url）與 `notificationclick` 事件（聚焦既有視窗或開新分頁） |
| | | **新增資料表 `push_subscriptions`**：username / endpoint（UNIQUE）/ p256dh / auth / user_agent / created_at / last_used，啟動時自動建表含 username 索引 |
| | | **共用推播函式 `send_push()`**：依 username 查詢所有訂閱端點逐一發送，HTTP 410 自動清除過期訂閱，獨立連線 + try/except 不影響主流程 |
| | | **新增 4 支推播 API**：`GET /api/push/vapid-public-key`（回傳公鑰供前端訂閱）、`POST /api/push/subscribe`（UPSERT 訂閱紀錄）、`POST /api/push/send`（手動/測試推播）、`POST /api/push/scheduled-check`（排程觸發：回訪到期提醒 + 應收帳款 3 日內到期預警） |
| | | **7 個推播觸發情境**：① 需求已採購 → 通知填單人 ② 需求已調撥 → 通知填單人 ③ 新採購需求 → 通知所有老闆 ④ 新調撥需求 → 通知所有會計 ⑤ 盤點單送審 → 通知所有老闆 ⑥ 排程：回訪任務今日到期/已逾期 → 通知負責人 ⑦ 排程：應收帳款 3 日內到期 → 通知所有會計 |
| | | **前端推播 UI**：側邊欄新增「推播通知」開關按鈕（`#pushNotifRow` / `#pushEnableBtn`），手機版「更多」面板同步新增（`#morePushRow` / `#morePushBtn`）；`initPushNotification()` 偵測瀏覽器支援度與現有訂閱狀態，`_updatePushUI()` 同步兩處按鈕顯示（已啟用綠色/未啟用灰色） |
| | | **雙路徑初始化修正**：`initPushNotification()` 同時在 `initApp()`（新登入）與 IIFE auto-login（既有 session）兩條路徑呼叫，確保推播按鈕始終可見 |
| | | **HTML 快取控制**：`@app.after_request` 為所有 `text/html` 回應加入 `Cache-Control: no-cache, no-store, must-revalidate` + `Pragma: no-cache` + `Expires: 0`，解決 Cloudflare Tunnel / 瀏覽器快取導致舊版 HTML 被載入的問題 |
| | | **系統規模**：62 張資料表、222 支 API 路由、8,964 行 app.py |
| v3.4 | 2026-04-05 | **帳號密碼系統 + 啟動畫面 + 登入時效延長 + iOS 密碼提示修復** |
| | | **帳號密碼自建系統**：員工首次用預設密碼登入後，強制引導至帳號設定畫面（自訂帳號 + 新密碼），設定完成後改用帳號密碼登入；`staff_passwords` 新增 `username`（UNIQUE 索引）、`has_setup`、`pw_hash` 三個欄位；密碼以 `werkzeug.security.generate_password_hash` 儲存（不存明碼）；密碼區分大小寫、至少 6 位 |
| | | **雙模式登入**：`POST /api/auth/verify` 支援兩種模式 — ① 帳號 + 密碼（已設定帳號者，`pw_hash` 驗證）② 僅密碼（尚未設定帳號者，`has_setup=0` + 明碼比對），回傳 `needSetup` 標記引導前端顯示設定畫面 |
| | | **新增 2 支帳號 API**：`POST /api/auth/check-username`（即時檢查帳號是否可用，前端 debounce 400ms 呼叫）、`POST /api/auth/setup-account`（寫入帳號、hash 密碼、標記 `has_setup=1`） |
| | | **帳號設定 UI**：登入遮罩與設定遮罩分離，設定畫面顯示姓名（唯讀）+ 帳號（即時可用性檢查，綠色✓/紅色✗）+ 新密碼 + 確認密碼，前端驗證密碼長度與一致性 |
| | | **啟動畫面（Splash Screen）**：頁面載入時顯示深色全屏遮罩（COSH 圖示 + 金色旋轉圈），至少停留 1 秒後淡出（0.4 秒 transition），`_splashStart` 記錄起始時間確保最低顯示時長 |
| | | **登入時效延長**：從 24 小時延長至 14 天（`14 * 24 * 60 * 60 * 1000`），適合 PWA 長期免登入 |
| | | **iOS 密碼記憶提示修復**：登入密碼欄位從 `type="password"` 改為 `type="text"` + `-webkit-text-security: disc`，form 與 input 加 `autocomplete="off"`，抑制 iOS Safari 記憶密碼彈窗 |
| | | **HTML 快取控制**：`@app.after_request` 為 `text/html` 回應加入 no-cache headers，確保每次載入最新 HTML |
| | | **系統規模**：62 張資料表、224 支 API 路由、9,075 行 app.py |
| v3.5 | 2026-04-05 | **維修作業系統上線** |
| | | **六步驟漸進式維修流程**：收件登記→檢測診斷→報價確認→維修作業→客戶取件→結案，每步完成才解鎖下一步，CSS 類別 `.step-section.locked / .active / .done` 控制步驟狀態，`STEP_STATUS_MAP` 對應 DB 狀態與步驟編號 |
| | | **新增頁面 `repair_order.html`**（~1200 行）：完整重寫為六步驟漸進式表單，各步驟有確認按鈕（`confirmStep1()` ~ `confirmStep5()`），步驟 2 & 3 新增「無法維修」「客戶不維修」取消路徑（`cancelRepair()` 填寫原因後直接結案），步驟 3 確認後自動彈出正式維修單列印頁 |
| | | **收件單 `repair_receipt.html`**（新增）：A4 雙聯收件單 — 上半客戶聯（工單號碼、客戶/設備資訊、故障狀況、四點注意事項、收件人員）、下半店留聯（同上 + 客戶簽名欄 + 日期），中間 `hr.tear-line` 虛線裁切（✂ 沿此線撕開），各半高 133mm，html2pdf.js 存為 PDF |
| | | **維修單 `repair_workorder.html`**（新增）：A4 正式維修單 — 店家抬頭、客戶/設備/故障描述/檢測診斷四區段，零件報價明細表（品名/產品編號/數量/單價/小計），費用摘要（零件合計/工資/總計 NT$），五點注意事項（報價確認/額外費用通知/30日取件/30日保固/資料備份），客戶簽名確認欄，html2pdf.js 存為 PDF |
| | | **工單號碼格式**：`RO-{店碼}{YYYYMMDD}-{NNN}`，店碼依技術人員所屬門市（FY/TZ/DY/OW），每日每店獨立流水號 |
| | | **新增 3 張資料表**：`repair_orders`（工單主表，含 customer_id / device_type / brand / model / symptom / diagnosis / repair_note / status / technician / labor_fee / parts_total / total_amount）、`repair_order_items`（零件明細）、`repair_phrases`（常用診斷短語） |
| | | **新增 9 支維修 API**：`POST /api/repair/create`（建立工單，狀態直接為「檢測中」避免競態條件）、`POST /api/repair/update`、`GET /api/repair/list`、`GET /api/repair/detail/<order_no>`、`DELETE /api/repair/delete/<order_no>`、`GET+POST /api/repair/phrases`、`GET /repair_receipt/<order_no>`、`GET /repair_workorder/<order_no>` |
| | | **維修工資統一品項 `SV-LABOR`**：系統啟動時自動建立（品名「維修工資」，分類「服務」，單位「次」），帶入銷貨後可透過工單設備類型區分維修貢獻 |
| | | **銷貨整合**：`sales_input.html` 新增「🔧 從維修單帶入」按鈕 + 搜尋 Modal（優先顯示「待取件」工單），選取後自動帶入客戶資訊、零件明細與工資（SV-LABOR） |
| | | **零件品名即時搜尋**：報價步驟零件表格新增品名模糊搜尋下拉，復用 `/api/products/search` |
| | | **技術人員唯讀**：維修技術人員欄位自動帶入登入使用者，不允許手動修改 |
| | | **門市資訊對照 `STORE_INFO`**：依工單號碼前綴（FY/TZ/DY/OW）帶入門市名稱與地址，用於收件單與維修單抬頭 |
| | | **競態條件修復**：建立工單 API 直接以「檢測中」狀態寫入，取消前端 fire-and-forget 狀態更新；`confirmStep1()` 對既有工單僅送出步驟 1 欄位，避免覆蓋已填寫的診斷/零件資料 |
| | | **帳號密碼修改功能**：base.html 側邊欄新增「修改密碼」Modal，支援舊密碼驗證 + 新密碼設定 + 確認密碼，新增 `POST /api/auth/change-password` API |
| | | **啟動畫面修復**：修正 splash screen 與登入遮罩的 z-index 衝突，確保啟動畫面顯示在最上層 |
| | | **條碼掃描支援**：銷貨輸入與報價輸入的產品編號欄位支援條碼掃描器直接輸入 |
| | | **系統規模**：66 張資料表、236 支 API 路由、9,529 行 app.py |
| v3.6 | 2026-04-06 | **故障檢測整合至維修作業** |
| | | **步驟 2 內嵌 AI 診斷輔助**：維修作業檢測診斷步驟新增可收合「✦ AI 診斷輔助」面板，技術人員描述故障 → oMLX 本地模型回覆診斷建議 → 匹配情境卡片點擊或「將最新回覆填入檢測結果」按鈕一鍵帶入工單 diagnosis 欄位 |
| | | **步驟 2 內嵌故障知識庫瀏覽**：新增可收合「📖 故障知識庫瀏覽」面板，左右分欄群組/情境介面 + 關鍵字搜尋，展開查看排查步驟/可能原因/檢測方式/處置建議，「填入檢測結果」按鈕直接帶入工單；知識庫首次展開時 lazy load，不影響頁面載入速度 |
| | | **故障檢測頁面停用**：`fault_diagnose.html` 不再作為獨立入口，`/fault_diagnose` 路由改為 redirect 至 `/repair_order`；`print_repair_report.html`（檢測結論單列印）同步停用，`/print/repair-report` 改為 redirect |
| | | **側邊欄精簡**：「維修檢測」群組移除「故障檢測」入口，僅保留「維修作業」與「維修知識庫」兩項；手機版「更多」面板同步移除 `/fault_diagnose` |
| | | **Flask 新增 redirect import**：`app.py` 引入 `redirect`，用於停用路由的重導向 |
| | | **系統規模**：66 張資料表、236 支 API 路由、9,531 行 app.py |
| v3.7 | 2026-04-06 | **維修作業更名 + 老闆刪除權限** |
| | | **全站更名**：「維修工單」統一更名為「維修作業」，涵蓋頁面標題、側邊欄入口、新建表單標題、銷貨輸入帶入按鈕文字 |
| | | **老闆刪除工單**：新增 `POST /api/repair/delete` API（老闆限定，role 驗證），前端工單詳情頁標題列新增紅色「刪除」按鈕（僅老闆角色可見），刪除前 confirm 確認，操作記入 audit_log |
| | | **系統規模**：66 張資料表、237 支 API 路由、9,560 行 app.py |

---

## 13. 附錄

### 13.1 班次代碼

| 代碼 | 說明 | 顏色（新系統） |
|------|------|---------------|
| 值 | 值班 | 綠色 #e8f4e8 / #3d7a3d |
| 早 | 早班 | 琥珀 rgba(250,191,19,.18) / #7a5500 |
| 晚 | 晚班 | 暖紫 rgba(120,90,155,.12) / #6a4090 |
| 全 | 全天 | 鋼藍 rgba(80,110,155,.15) / #3a5a8a |
| 休 | 休假 | 暖灰 rgba(107,95,82,.08) / #9a9188 |
| 特 | 特殊假別 | 棕橘 rgba(180,100,50,.14) / #7a4020 |

### 13.2 重要路徑

| 項目 | 路徑 |
|------|------|
| 新系統根目錄 | ~/srv/web-site/computershop-erp/ |
| Flask 主程式 | computershop-erp/app.py |
| 資料庫 | computershop-erp/db/company.db |
| 白皮書 | computershop-erp/ERP_v2_Whitepaper_v3.7.md |
| Parser 腳本 | ~/srv/parser/（禁止異動） |
| 舊系統（唯讀參考） | computershop-erp/old system/dashboard-site/ |
| Gunicorn Log | ~/srv/logs/erp_v2_*.log |

### 13.3 倉庫名稱對照

系統中倉庫名稱須與資料庫完全一致，以下為標準名稱與排序：

| 順序 | 標準名稱 | 說明 |
|------|----------|------|
| 1 | 豐原門市 | 豐原門市實體倉 |
| 2 | 潭子門市 | 潭子門市實體倉 |
| 3 | 大雅門市 | 大雅門市實體倉 |
| 4 | 業務部 | 業務部庫存 |
| 5 | 總公司倉庫 | 總公司中央倉（推薦備貨採購統一入庫處） |

### 13.4 系統自我檢查報告

完整檢查報告存於 `check-report.md`。截至 v1.1，所有 QA 發現問題均已修復。

---

*OpenClaw ERP v2 — © 2026 COSH 電腦舖 · 內部文件，勿對外流通*
