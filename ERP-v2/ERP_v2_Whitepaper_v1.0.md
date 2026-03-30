# OpenClaw — ERP v2 系統白皮書

**電腦舖 COSH · 台中豐原／潭子／大雅**

| 項目 | 值 |
|------|---|
| 文件版本 | v1.0 |
| 系統代號 | OpenClaw |
| 服務端口 | Port 8800 |
| 最後更新 | 2026-03-28 |
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
| 前端頁面（templates/） | 29 個 |
| API 路由 | 85+ 個 |
| 資料庫資料表 | 49 張 |
| 後台管理頁面 | 4 個 |
| 程式碼行數（app.py） | 3,023 行 |
| 開發 Phase | 6 個 |

### 1.3 核心功能

- **即時業績追蹤**：部門、門市、個人三層業績每日更新
- **需求表系統**：四階段流程管理（待處理 → 已採購 → 已調撥 → 已完成）
- **人員管理**：班表、督導評分、獎金計算完整串聯
- **後台管理**：員工、公告、獎金規則、推薦備貨一站式管理
- **LINE 客服**：回覆記錄管理，含結案追蹤
- **待建檔中心**：客戶暫存記錄與產品待建檔雙軌管理

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
資料層（SQLite 3，WAL 模式，49 張表）
```

### 2.2 目錄結構

```
computershop-erp/
├── app.py                ← Flask 主程式（3,023 行）
├── gunicorn.conf.py      ← Gunicorn 設定（Port 8800）
├── .env                  ← 環境變數（DB_PATH、PORT）
├── progress.md           ← 開發進度記錄
├── check-report.md       ← 自我檢查報告
├── templates/            ← 所有前端頁面
│   ├── base.html         ← 母版（側邊欄 + 頂部 + 字體）
│   ├── admin/            ← 後台管理頁面（4個）
│   └── ...（其餘 24 個頁面）
├── static/
│   ├── css/main.css      ← 全局樣式
│   └── js/
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

所有頁面統一引用以下色票，禁止寫死不相干的 hex 值。圖表色系與班別標籤允許功能性獨立色，但整體維持暖色調。

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

- 主內容最大寬度 1,160px，超出兩側自動留白（`max()` CSS 函數）
- 統計數字為第一視覺焦點：Cormorant Garamond + 2.5~2.6rem
- 公告、提示等次要資訊字體弱化，不搶主畫面
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

---

## 5. 資料庫設計

### 5.1 資料庫概覽

資料庫位於 `db/company.db`，採 SQLite 3 WAL 模式，共 49 張資料表，由外部 Parser 腳本自動維護核心業務資料，新系統僅讀取並在需求表、督導評分等必要場景寫入。

### 5.2 資料表分組

| 分組 | 資料表 |
|------|--------|
| 核心業務 | sales_history, customers, customer_master, inventory, needs, purchase_history, products, suppliers, service_records, sales, sales_documents, sales_document_items |
| 人員 / 班表 | staff, staff_passwords, staff_roster, supervision_scores |
| 獎金 | bonus_rules, bonus_results, bonus_payments |
| 系統 / 管理 | system_announcements, notification_logs, login_attempts, boss_password, admin_audit_log, chat_logs, api_metrics, ops_events |
| 暫存 / 備份 | customer_staging, product_staging, staging_records, sales_history_deleted_backup, staging_records_backup |
| 特殊功能 | google_reviews, google_reviews_stats, store_reviews, line_replies, recommended_products, recommended_categories, crm_tasks, finance_ledger |
| 目錄 / 快取 | product_categories, _deprecated_product_master, freshness_cache, performance_metrics, sqlite_sequence |

### 5.3 核心資料表說明

#### needs（需求表）

四階段流程核心。status 欄位記錄當前狀態，timestamps 追蹤各階段時間。

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | INTEGER PK | 自動遞增 |
| date | TEXT | 日期 YYYY-MM-DD |
| item_name | TEXT | 商品名稱 |
| quantity | INTEGER | 數量 |
| requester | TEXT | 填表人員 |
| department | TEXT | 部門 |
| status | TEXT | 待處理 / 已採購 / 已調撥 / 已完成 / 已取消 |
| product_code | TEXT | ERP 料號 |
| processed_at / arrived_at / cancelled_at | DATETIME | 各階段時間戳 |

#### sales_history（銷貨歷史）

由 sales_parser 自動匯入，新系統亦提供手動輸入入口（sales_input.html）。

| 欄位 | 型別 | 說明 |
|------|------|------|
| invoice_no | TEXT | 發票號碼（同張發票多行） |
| date | TEXT | 銷售日期 |
| customer_id / customer_name | TEXT | 客戶資訊 |
| salesperson / salesperson_id | TEXT | 銷售人員 |
| product_code / product_name | TEXT | 商品資訊 |
| quantity, price, amount | INTEGER | 數量、單價、小計 |
| cost, profit, margin | REAL | 成本、毛利、毛利率（老闆可見） |

#### line_replies（LINE 客服回覆）

| 欄位 | 型別 | 說明 |
|------|------|------|
| reply_datetime | TEXT | 回覆日期時間 |
| customer_line_name | TEXT | 客戶 LINE 顯示名稱 |
| inquiry_content | TEXT | 詢問內容 |
| reply_content | TEXT | 回覆內容 |
| reply_store / reply_staff | TEXT | 回覆門市 / 負責人員 |
| is_resolved | INTEGER | 0=未結案, 1=已結案 |

---

## 6. 頁面結構

共 29 個頁面，分六個 Phase 開發完成，按使用頻率排序。所有頁面繼承 base.html 母版，統一套用設計系統。

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

---

## 7. API 架構

### 7.1 認證機制

系統採用 JWT-less localStorage 認證，無需 Server Session。

- **登入**：員工編號 + 密碼 → `POST /api/auth/verify` → 寫入 localStorage
- **儲存格式**：`{ name, role, loginTime, expiresAt }`（key: `erp_v2_user`）
- **自動過期**：每天 21:00 過期（key: `erp_v2_exp`）
- **前端模式**：`onAppReady(user)` callback，確保認證後才載入資料

### 7.2 API 端點一覽

#### 銷售與業績

| 端點 | 方法 | 說明 |
|------|------|------|
| /api/sales/daily | GET | 每日銷售總覽（門市部 + 業務部） |
| /api/sales/list | GET | 銷貨紀錄分頁列表 |
| /api/sales/submit | POST | 手動新增銷貨單 |
| /api/sales/\<invoice_no\> | DELETE | 刪除銷貨單 |
| /api/performance/department | GET | 部門業績 |
| /api/performance/department/daily | GET | 部門每日趨勢 |
| /api/performance/store | GET | 門市業績 |
| /api/performance/personal | GET | 個人業績排名 |
| /api/performance/business | GET | 業務部績效 |

#### 需求表

| 端點 | 方法 | 說明 |
|------|------|------|
| /api/needs/latest | GET | 最新待處理需求 |
| /api/needs/batch | POST | 批次新增需求 |
| /api/needs/cancel | POST | 取消需求 |
| /api/needs/purchase | POST | 標記已採購 |
| /api/needs/transfer | POST | 標記已調撥 |
| /api/needs/arrive | POST | 批次到貨 |
| /api/needs/\<id\>/arrive | POST | 單筆到貨 |
| /api/needs/\<id\>/complete | POST | 完成需求 |
| /api/needs/overdue-arrival | GET | 逾期收貨提醒 |
| /api/needs/history | GET | 需求歷史紀錄 |
| /api/needs/recent | GET | 最近 14 天紀錄 |
| /api/needs/transfers | GET | 調撥列表 |

#### 客戶 / 庫存 / 班表

| 端點 | 方法 | 說明 |
|------|------|------|
| /api/customer/search | GET | 客戶搜尋 |
| /api/customer/detail/\<id\> | GET | 客戶詳細資料 + 購買紀錄 |
| /api/customers/search | GET | 客戶模糊搜尋（需求表用） |
| /api/inventory/list | GET | 庫存分頁列表 |
| /api/inventory/product/\<code\> | GET | 單品各倉庫存 |
| /api/products/search | GET | 產品搜尋（先查庫存，再 fallback products） |
| /api/roster/monthly | GET | 整月班表 |
| /api/roster/batch | POST | 批次儲存班表 |

#### 人員 / 督導 / 獎金

| 端點 | 方法 | 說明 |
|------|------|------|
| /api/staff/list | GET | 員工列表 |
| /api/staff/\<id\> | PUT | 更新員工資料（含密碼同步） |
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
| /api/system/announcements/all | GET | 全部公告（含未啟用） |
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
| /api/staging/list | GET | 暫存記錄列表 |
| /api/staging/\<id\>/resolve | PUT | 標記暫存記錄完成 |
| /api/staging/stats | GET | 各類型待處理數量 |
| /api/product-staging/list | GET | 產品待建檔列表 |
| /api/product-staging/\<id\>/resolve | PUT | 標記產品待建檔完成 |
| /api/boss/pending-needs | GET | 老闆待審核需求 |
| /api/boss/needs/\<id\>/status | POST | 更新需求狀態 |
| /api/boss/needs/\<id\>/notes | POST | 新增備註 |
| /api/store-manager/today | GET | 今日門市數據（班表+銷售+需求） |
| /api/store/reviews | GET | 門市評論統計 |
| /api/google-reviews | GET | Google 評論列表 |
| /api/summary | GET | 首頁摘要（需求+銷售+公告） |
| /api/health | GET | 系統健康檢查 |

---

## 8. 權限系統

### 8.1 角色定義

| 角色 | 英文代碼 | 主要權限範圍 |
|------|----------|-------------|
| 老闆 | 老闆 | 全部功能，含成本/毛利資訊 |
| 會計 | 會計 | 需求表處理、銷貨輸入、獎金報表、庫存 |
| 門市部主管 | 門市部主管 | 門市業績、督導評分、班表管理 |
| 業務部主管 | 業務部主管 | 業務部績效、業務員管理 |
| 門市工程師 | 工程師 | 需求表、班表查詢、客戶查詢 |
| 業務人員 | 業務人員 | 需求表、外勤服務紀錄、客戶查詢 |

### 8.2 敏感資訊控制

- 成本、毛利、毛利率欄位：僅老闆、會計可見（`canViewCost` flag）
- 刪除操作：需老闆/督導層級，前端按鈕依角色隱藏
- 老闆控制台、admin 頁面：僅老闆可存取，路由層直接過濾
- Password 欄位：API 從不回傳，由後端 `staff_passwords` 獨立管理

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

### 9.1 需求表四階段流程

| 階段 | 操作角色 | 動作 | 狀態 |
|------|----------|------|------|
| 1 | 所有員工 | 送出需求 | 待處理 |
| 2 | 老闆 | 按「已採購」 | 已採購 |
| 3 | 會計 | 按「已調撥」 | 已調撥（或直接到貨） |
| 4 | 申請人 | 按「已到貨」 | 已完成 |

取消規則：老闆可取消任意待處理需求；一般員工僅可取消自己的需求，且需在 30 分鐘內。

### 9.2 督導評分系統

督導評分採 16 項 32 分制，分三大類。評分人自動帶入登入者，不開放修改。

| 類別 | 項目數 | 總分 | 顯示位置 |
|------|--------|------|----------|
| 環境整潔（1–5 項） | 5 項 | 10 分 | 門市業績頁（store.html） |
| 人員表現（6–11 項） | 6 項 | 12 分 | 個人業績頁（personal.html） |
| LINE 回覆（12–16 項） | 5 項 | 10 分 | 個人業績頁 |
| 合計 | 16 項 | 32 分 | 百分比 = 得分 ÷ 32 × 100 |

### 9.3 銷售獎金系統

- `bonus_rules`：設定商品代碼、時間區間、獎金類型（固定金額 / 百分比）
- `bonus_calculate`：POST 日期範圍 → 交叉比對 sales_history → 寫入 bonus_results
- `bonus_results`：人員 + 商品 + 銷售額 + 獎金金額，可按月份 / 人員查詢

### 9.4 待建檔中心

系統設有兩個暫存機制：

- **staging_records**：客戶或產品輸入無法自動對應 ERP 編號時，自動建立待建檔記錄，type 為 `customer` 或 `product`
- **product_staging**：銷貨輸入時輸入的商品名稱無法對應 products 表，建立待人工確認記錄

管理員在 `staging_center_v2.html` 逐筆確認並標記完成後，系統從 `pending` 更新為 `resolved`。

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
| DB_PATH | db/company.db（相對路徑） | SQLite 資料庫路徑 |
| SECRET_KEY | openclaw-erp-v2-2026 | Flask 密鑰 |
| PORT | 8800 | 服務端口 |

### 10.3 啟動指令

```bash
# 進入新系統目錄
cd ~/srv/web-site/computershop-erp

# 啟動（開發模式）
python3 app.py

# 啟動（Gunicorn 生產模式）
gunicorn -c gunicorn.conf.py app:app

# 確認運行狀態
curl http://127.0.0.1:8800/api/health
```

### 10.4 日誌位置

- Access Log：`/Users/aiserver/srv/logs/erp_v2_access.log`
- Error Log：`/Users/aiserver/srv/logs/erp_v2_error.log`

### 10.5 絕對禁止事項

- `old system/` 資料夾：唯讀參考，禁止修改任何檔案
- Parser 腳本（`~/srv/parser/`）：禁止異動，任何修改都會影響自動匯入
- 資料庫本體：禁止手動刪除資料表或欄位
- Cron 排程：禁止修改，需先確認再調整

---

## 11. Parser 系統（參考）

Parser 系統獨立於新系統之外，位於 `~/srv/parser/`，共 11 支腳本，由 cron 自動排程執行。ERP v2 僅負責讀取 Parser 寫入的資料，不介入 Parser 本身。

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
| | | Phase 0：app.py / base.html / main.css / gunicorn 骨架 |
| | | Phase 1：首頁、需求表輸入、老闆控制台 |
| | | Phase 2：部門、門市、個人業績、業務部績效、月會報告 |
| | | Phase 3：門市主管控制台、會計專區、客戶/庫存/班表查詢 |
| | | Phase 4：服務紀錄、督導評分、班表輸入、銷貨輸入、目標管理 |
| | | Phase 5：後台管理中心（員工/公告/獎金/推薦備貨） |
| | | Phase 6：LINE 回覆、個人獎金、推薦選購、待建檔、系統架構圖 |
| | | 自我檢查完成，修正重複 API 路由（products/search） |
| | | 修正 Accountants / Store_Manager Bootstrap 色票不一致問題 |
| | | 全站表格補齊 overflow-x:auto 手機橫向捲動保護 |

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
| Parser 腳本 | ~/srv/parser/（禁止異動） |
| 舊系統（唯讀參考） | computershop-erp/old system/dashboard-site/ |
| Gunicorn Log | ~/srv/logs/erp_v2_*.log |

### 13.3 系統自我檢查報告

完整檢查報告存於 `check-report.md`，包含四個階段：功能完整性、視覺一致性、禁止項目確認、技術檢查。截至 v1.0，所有必修問題均已修復，建議項目依優先順序逐步處理。

---

*OpenClaw ERP v2 — © 2026 COSH 電腦舖 · 內部文件，勿對外流通*
