# OpenClaw — ERP v2 系統白皮書

**電腦舖 COSH · 台中豐原／潭子／大雅**

| 項目 | 值 |
|------|---|
| 文件版本 | v1.6 |
| 系統代號 | OpenClaw |
| 服務端口 | Port 8800 |
| 最後更新 | 2026-04-03 |
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
| 前端頁面（templates/） | 49 個 |
| API 路由 | 165 個 |
| 資料庫資料表 | 57 張 |
| 後台管理頁面 | 4 個 |
| 程式碼行數（app.py） | 5,900+ 行 |
| 開發 Phase | 6 個 + QA 修正 + KPI 模組 + 財務模組 + 廠商管理 |

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
- **廠商管理**：廠商建檔、查詢、編輯，結構化帳期（結帳日 + 付款方式），進貨自動產生應付帳款與到期日計算

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
資料層（SQLite 3，WAL 模式，57 張表）
```

### 2.2 目錄結構

```
computershop-erp/
├── app.py                ← Flask 主程式（5,620+ 行）
├── gunicorn.conf.py      ← Gunicorn 設定（Port 8800）
├── .env                  ← 環境變數（DB_PATH、PORT）
├── ERP_v2_Whitepaper_v1.0.md  ← 本白皮書
├── templates/            ← 所有前端頁面（46 個）
│   ├── base.html         ← 母版（側邊欄 + 頂部 + 字體）
│   ├── kpi_review.html   ← KPI 考核總覽
│   ├── kpi_contribution.html ← 關鍵貢獻填報
│   ├── supplier_create.html  ← 廠商建檔
│   ├── supplier_search.html  ← 廠商查詢（含編輯）
│   ├── admin/            ← 後台管理頁面（4 個）
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
| 主字體 | Noto Serif TC 200/300（中文纖細體） |
| 數字裝飾字體 | Cormorant Garamond 300（英文數字） |
| 主背景色 | #f5f0e8（暖白） |
| 主文字色 | #2c2720（深墨） |
| 品牌黃 | #FABF13（僅 focus/active 使用） |
| 最大內容寬度 | 1,160px（寬螢幕兩側留白） |
| 手機斷點 | 768px / 480px |

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
| 輸入框 padding | 8px 12px（次要）/ 10px 14px（標準） |
| 輸入框 border-radius | 8–10px |
| 主要按鈕 | background: #2c2720, color: #f5f0e8, border-radius: 8px |
| 次要按鈕 | no background, border: rgba(107,95,82,.25) |
| 危險按鈕 | border/color: #8b3a3a（低調紅棕） |
| 卡片圓角 | 14–16px |
| Focus 光暈 | 0 0 0 3px rgba(250,191,19,.12) |

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

資料庫位於 `db/company.db`，採 SQLite 3 WAL 模式，共 57 張資料表，由外部 Parser 腳本自動維護核心業務資料。

### 5.2 資料表分組

| 分組 | 資料表 |
|------|--------|
| 核心業務 | sales_history, customers, customer_master, inventory, needs, purchase_history, products, suppliers, service_records, sales, sales_documents, sales_document_items |
| 人員 / 班表 | staff, staff_passwords, staff_roster, supervision_scores |
| 獎金 | bonus_rules, bonus_results, bonus_payments |
| 系統 / 管理 | system_announcements, notification_logs, login_attempts, boss_password, admin_audit_log, chat_logs, api_metrics, ops_events |
| 暫存 / 備份 | customer_staging, product_staging, staging_records, sales_history_deleted_backup, staging_records_backup |
| 財務管理 | finance_payables, finance_receivables, finance_transactions, finance_petty_cash, finance_petty_cash_log, finance_ledger |
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

由 sales_parser 自動匯入，亦提供 sales_input.html 手動輸入。

> **注意**：`invoice_no` 欄位存放的是民國曆日期（如 `1150326` = 民國115年3月26日），並非實際發票號碼。每個日期平均約 19 筆明細，逐筆存放。

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | INTEGER PK | 唯一識別（逐筆刪除用） |
| invoice_no | TEXT | 民國曆批次日期（非發票號碼） |
| date | TEXT | 銷售日期 |
| customer_id / customer_name | TEXT | 客戶資訊 |
| salesperson / salesperson_id | TEXT | 銷售人員 |
| product_code / product_name | TEXT | 商品資訊 |
| quantity, price, amount | INTEGER | 數量、單價、小計 |
| cost, profit, margin | REAL | 成本、毛利、毛利率（老闆/會計可見） |

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

共 49 個頁面，分六個 Phase 開發，QA 階段新增 3 個。所有頁面繼承 base.html 母版。

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

---

## 7. API 架構

### 7.1 認證機制

系統採用 JWT-less localStorage 認證，無需 Server Session。

- **登入**：員工編號 + 密碼 → `POST /api/auth/verify` → 寫入 localStorage
- **儲存格式**：`{ name, role, loginTime, expiresAt }`（key: `erp_v2_user`）
- **自動過期**：每天 21:00 過期（key: `erp_v2_exp`）
- **前端模式**：子頁面定義 `function onAppReady(user) {...}`，base.html 認證後自動呼叫

### 7.2 API 端點一覽

#### 銷售與業績

| 端點 | 方法 | 說明 |
|------|------|------|
| /api/sales/daily | GET | 每日銷售總覽（門市部 + 業務部） |
| /api/sales/list | GET | 銷貨紀錄分頁列表（支援 q, salesperson, page） |
| /api/sales/submit | POST | 手動新增銷貨單 |
| /api/sales/\<invoice_no\> | DELETE | 整批刪除（依民國曆批次日期） |
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
| /api/health | GET | 系統健康檢查 |

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
| 環境整潔（1–5 項） | 5 項 | 10 分 | 門市業績頁 |
| 人員表現（6–11 項） | 6 項 | 12 分 | 個人業績頁 |
| LINE 回覆（12–16 項） | 5 項 | 10 分 | 個人業績頁 |
| 合計 | 16 項 | 32 分 | 百分比 = 得分 ÷ 32 × 100 |

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

# 健康檢查
curl http://127.0.0.1:8800/api/health
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
| 白皮書 | computershop-erp/ERP_v2_Whitepaper_v1.6.md |
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
