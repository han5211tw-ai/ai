# ERP 營運系統 - 專案白皮書

**版本**: v3.3
**最後更新**: 2026-03-23
**文件編號**: ERP-WP-001
**撰寫者**: Yvonne (AI Assistant)

---

## 目錄

1. [專案概述](#1-專案概述)
2. [系統架構](#2-系統架構)
3. [模組說明](#3-模組說明)
4. [頁面與功能清單](#4-頁面與功能清單)
5. [資料庫結構](#5-資料庫結構)
6. [API 規格](#6-api-規格)
7. [UI/UX 設計說明](#7-uiux-設計說明)
8. [工具與整合](#8-工具與整合)
9. [Telegram Bot 與通知](#9-telegram-bot-與通知)
10. [附錄](#10-附錄)

---

## 1. 專案概述

### 1.1 系統名稱與定位

| 項目 | 內容 |
|------|------|
| **系統名稱** | ERP 營運系統（原 Dashboard 營運系統） |
| **正名日期** | 2026-03-16 |
| **系統定位** | 電腦舖零售業務管理與營運分析平台 |
| **目標用戶** | 老闆、門市主管、會計、業務員、門市人員 |
| **部署環境** | Mac mini 本地伺服器 + Cloudflare Tunnel |

### 1.2 核心功能

- **業績分析**: 部門/門市/個人多維度績效追蹤
- **銷售管理**: 銷貨輸入、報價單、訂單管理
- **庫存管理**: 即時庫存查詢、進貨追蹤
- **需求表系統**: 請購/調撥/新品申請流程
- **客戶管理**: 客戶資料查詢、服務記錄
- **班表系統**: 人員排班與查詢
- **督導評分**: 門市評核與追蹤
- **獎金計算**: 銷售獎金規則與自動計算
- **系統公告**: 公告發布與管理

### 1.3 技術棧

| 層級 | 技術 |
|------|------|
| **前端** | HTML5, CSS3, JavaScript (Vanilla), Chart.js |
| **後端** | Python 3, Flask |
| **資料庫** | SQLite |
| **伺服器** | Gunicorn (正式環境) |
| **排程** | APScheduler, Cron |
| **通知** | Telegram Bot API |
| **郵件** | SMTP (Gmail) |
| **網路** | Cloudflare Tunnel |

---

## 2. 系統架構

### 2.1 實體架構圖

```
┌─────────────────────────────────────────────────────────────────┐
│                         使用者層                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │   老闆   │ │ 門市主管 │ │   會計   │ │ 業務員   │           │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘           │
└───────┼────────────┼────────────┼────────────┼─────────────────┘
        │            │            │            │
        └────────────┴────────────┴────────────┘
                         │
              ┌──────────┴──────────┐
              │   Cloudflare Tunnel │
              │  (HTTPS 反向代理)   │
              └──────────┬──────────┘
                         │
┌────────────────────────┼────────────────────────────────────────┐
│                     Mac mini (AI的Mac mini)                     │
│  ┌─────────────────────┼────────────────────────────────────┐  │
│  │                     │                                    │  │
│  │  ┌──────────────────▼──────────────────┐               │  │
│  │  │        Gunicorn (Port 3000)         │               │  │
│  │  │           Flask Application         │               │  │
│  │  └──────────────────┬──────────────────┘               │  │
│  │                     │                                   │  │
│  │  ┌──────────────────┼──────────────────┐               │  │
│  │  │                  │                  │               │  │
│  │  ▼                  ▼                  ▼               │  │
│  │ ┌────────┐    ┌──────────┐    ┌──────────────┐        │  │
│  │ │SQLite  │    │Telegram  │    │   Gmail      │        │  │
│  │ │Database│    │   Bot    │    │  (IMAP/SMTP) │        │  │
│  │ └────────┘    └──────────┘    └──────────────┘        │  │
│  │                                                        │  │
│  │  ┌────────────────────────────────────────────────┐   │  │
│  │  │         Parser Scripts (排程執行)              │   │  │
│  │  │  • inventory_parser.py                         │   │  │
│  │  │  • sales_parser_v22.py                         │   │  │
│  │  │  • performance_parser.py                       │   │  │
│  │  │  • google_reviews_parser.py                    │   │  │
│  │  └────────────────────────────────────────────────┘   │  │
│  │                                                        │  │
│  │  ┌────────────────────────────────────────────────┐   │  │
│  │  │         OneDrive Sync                          │   │  │
│  │  │  ~/srv/sync/OneDrive/ai_source/                │   │  │
│  │  └────────────────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

### 2.2 目錄結構

```
/Users/aiserver/
├── .openclaw/
│   └── workspace/                    # OpenClaw 工作區
│       ├── dashboard-site/           # ERP 系統主目錄
│       │   ├── app.py               # Flask 主程式
│       │   ├── *.html               # 頁面檔案
│       │   ├── shared/              # 共用資源
│       │   │   ├── auth_ui.js       # 登入組件 v2.0
│       │   │   ├── auth_ui.css      # 登入樣式
│       │   │   ├── global.css       # 全域樣式
│       │   │   └── sidebar-nav.js   # 側邊欄導航
│       │   ├── admin/               # 管理後台頁面
│       │   ├── templates/           # Jinja2 模板
│       │   └── gunicorn.conf.py     # Gunicorn 設定
│       ├── memory/                  # 記憶檔案
│       ├── skills/                  # OpenClaw Skills
│       └── docs/                    # 文件
│
├── srv/                             # 服務資料
│   ├── db/
│   │   └── company.db               # SQLite 資料庫 (17MB)
│   ├── parser/                      # 資料解析腳本
│   │   ├── inventory_parser.py
│   │   ├── sales_parser_v22.py
│   │   ├── performance_parser.py
│   │   ├── google_reviews_parser.py
│   │   └── msi_inventory_report.py
│   ├── sync/OneDrive/ai_source/     # OneDrive 同步
│   │   ├── roster/                  # 班表 Excel
│   │   ├── supervision/             # 督導評分
│   │   ├── feedback/                # 五星評論
│   │   └── backup/                  # 備份
│   └── logs/                        # 系統日誌
│
└── OneDrive/                        # OneDrive 主目錄
```

### 2.3 系統架構圖 V3

**檔案位置**: `dashboard-site/system_map_v3.html`

**設計特色**:
- 霓虹主題 (Cyan/Purple/Orange 漸層)
- 貝茲爾曲線連線 (Bezier Curves)
- 動態粒子背景
- Inter + JetBrains Mono 字體
- 玻璃擬態效果

---

## 3. 模組說明

### 3.1 核心模組架構

```
┌─────────────────────────────────────────────────────────────┐
│                      ERP 營運系統                            │
├─────────────┬─────────────┬─────────────┬─────────────────┤
│  銷售模組   │  庫存模組   │  客戶模組   │   報表模組      │
├─────────────┼─────────────┼─────────────┼─────────────────┤
│ • 銷貨輸入  │ • 庫存查詢  │ • 客戶查詢  │ • 業績分析      │
│ • 報價單    │ • 進貨管理  │ • 客戶新增  │ • 班表查詢      │
│ • 訂單管理  │ • 需求表    │ • 服務記錄  │ • 督導評分      │
│ • 銷售文件  │ • 調撥/請購 │ • 待辦追蹤  │ • 獎金計算      │
└─────────────┴─────────────┴─────────────┴─────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     資料整合層                               │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐              │
│  │   Parser   │ │   Cron     │ │  OneDrive  │              │
│  │   系統     │ │   排程     │ │   同步     │              │
│  └────────────┘ └────────────┘ └────────────┘              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     資料儲存層                               │
│              SQLite Database (company.db)                    │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 各模組詳細說明

#### 3.2.1 銷售模組 (Sales Module)

| 功能 | 說明 | 對應頁面 |
|------|------|----------|
| 銷貨輸入 | 新增銷貨單，支援客戶搜尋、產品搜尋 | `query.html` |
| 報價單 | 建立報價文件，可轉為訂單 | `quote_input.html` |
| 銷售文件 | 管理報價單/訂單/出貨單 | 文件列表頁 |
| 銷售查詢 | 查詢歷史銷售記錄 | API 介面 |

**API 端點**:
- `POST /api/sales/create` - 建立銷貨單
- `GET /api/sales/list` - 銷售列表
- `GET /api/sales/detail` - 銷售明細
- `POST /api/sales-doc/create` - 建立銷售文件

#### 3.2.2 庫存模組 (Inventory Module)

| 功能 | 說明 | 對應頁面 |
|------|------|----------|
| 庫存查詢 | 即時查詢各倉庫庫存 | `inventory_query.html` |
| 需求表 | 請購/調撥/新品申請 | `needs_input.html` |
| 進貨管理 | 進貨資料匯入與查詢 | API 介面 |
| 產品管理 | 產品資料維護 | `product_create.html` |

**需求表流程**:
```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  待處理  │ → │  已採購  │ → │  已調撥  │ → │  已完成  │
│ (員工填) │    │ (老闆批) │    │ (會計處) │    │ (到貨確認)│
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

#### 3.2.3 客戶模組 (Customer Module)

| 功能 | 說明 | 對應頁面 |
|------|------|----------|
| 客戶查詢 | 搜尋客戶基本資料 | `customer_search.html` |
| 客戶新增 | 建立新客戶資料 | `customer_create.html` |
| 服務記錄 | 記錄客戶服務事宜 | API 介面 |
| 待建檔中心 | 審核新客戶資料 | `staging_center_v2.html` |

**客戶資料來源**:
- `customers` - 既有客戶表 (legacy)
- `customer_master` - 新客戶主檔 (master)
- `customer_staging` - 待審核客戶

#### 3.2.4 業績模組 (Performance Module)

| 功能 | 說明 | 對應頁面 |
|------|------|----------|
| 部門業績 | 門市部/業務部績效 | `department.html` |
| 門市業績 | 各門市業績分析 | `store.html` |
| 個人業績 | 業務員排名與達成率 | `personal.html` |
| 業務部績效 | 業務員專屬報表 | `business.html` |

**業績計算邏輯**:
```
門市部總計 = 豐原門市 + 潭子門市 + 大雅門市 + 主管(莊圍迪)
業務部總計 = 鄭宇晉 + 梁仁佑 + 主管(萬書佑)
```

#### 3.2.5 班表模組 (Roster Module)

| 功能 | 說明 | 對應頁面 |
|------|------|----------|
| 本週班表 | 顯示本週排班 | `roster.html` |
| 今日班表 | 顯示今日值班人員 | API 介面 |
| 班表匯入 | 從 Excel 匯入 | `roster_parser.py` |

**班次代碼**:
| 代碼 | 說明 | 時間 |
|------|------|------|
| 早 | 早班 | 10:00-18:00 |
| 晚 | 晚班 | 12:00-20:00 |
| 全 | 全班 | - |
| 值 | 值班 | - |
| 休 | 休假 | - |

#### 3.2.6 督導評分模組 (Supervision Module)

| 功能 | 說明 | 對應頁面 |
|------|------|----------|
| 評分輸入 | 15項評分項目 | `supervision_score.html` |
| 評分總覽 | 各門市評分統計 | API 介面 |
| 評分明細 | 歷史評分記錄 | API 介面 |

**評分項目** (15項，每項滿分2分):
1. 出勤狀況
2. 服裝儀容
3. 服務態度
4. 專業知識
5. 銷售流程
6. 門面整潔
7. 店內清潔
8. 產品陳列
9. 線材管理
10. 倉庫整齊
11. 回覆速度
12. 回覆態度
13. 問題掌握
14. 資訊完整
15. 後續追蹤

#### 3.2.7 獎金模組 (Bonus Module)

| 功能 | 說明 | 對應頁面 |
|------|------|----------|
| 獎金規則 | 設定產品獎金 | `admin/bonus_rules.html` |
| 獎金計算 | 自動計算銷售獎金 | API 介面 |
| 獎金報表 | 獎金發放明細 | `admin/bonus_report.html` |
| 個人獎金 | 業務員獎金查詢 | `bonus_personal.html` |

**獎金類型**:
- `fixed` - 固定金額
- `percentage` - 銷售額百分比

#### 3.2.8 推薦備貨模組 (Recommended Products)

| 功能 | 說明 | 對應頁面 |
|------|------|----------|
| 分類管理 | 管理商品分類 | API 介面 |
| 商品管理 | 設定推薦商品 | `admin/recommended_products.html` |
| 前台選購 | 員工選購介面 | `recommended_products.html` |
| 一鍵送需求 | 直接產生需求表 | API 介面 |

#### 3.2.9 系統管理模組 (Admin Module)

| 功能 | 說明 | 對應頁面 |
|------|------|----------|
| 員工管理 | 人員資料維護 | `staff_admin.html` |
| 公告管理 | 系統公告發布 | `admin/announcement_management.html` |
| 健康檢查 | 系統狀態監控 | `health_check.html` |
| 系統架構 | 架構圖檢視 | `system_map_v3.html` |

---

## 4. 頁面與功能清單

### 4.1 前台頁面 (Public Pages)

| 頁面名稱 | 檔案 | 用途 | 權限 |
|----------|------|------|------|
| 首頁 | `index.html` | 總覽、每日銷售趨勢 | 全員 |
| 部門業績 | `department.html` | 部門業績分析 | 全員 |
| 門市業績 | `store.html` | 門市業績分析 | 全員 |
| 個人業績 | `personal.html` | 個人業績排名 | 全員 |
| 業務部績效 | `business.html` | 業務部專屬報表 | 全員 |
| 班表查詢 | `roster.html` | 本週班表 | 全員 |
| 客戶查詢 | `customer_search.html` | 客戶資料查詢 | 全員 |
| 庫存查詢 | `inventory_query.html` | 庫存查詢 | 全員 |
| 需求表填寫 | `needs_input.html` | 請購/調撥/新品 | 全員 |
| 銷貨輸入 | `query.html` | 新增銷貨單 | 全員 |
| 報價單 | `quote_input.html` | 建立報價 | 全員 |
| 督導評分 | `supervision_score.html` | 門市評分 | 主管 |
| 月報表 | `monthly_report.html` | 月度報表 | 全員 |
| 推薦備貨 | `recommended_products.html` | 商品選購 | 全員 |
| 個人獎金 | `bonus_personal.html` | 獎金查詢 | 全員 |

### 4.2 管理後台頁面 (Admin Pages)

| 頁面名稱 | 檔案 | 用途 | 權限 |
|----------|------|------|------|
| 老闆控制台 | `boss.html` | 總合控制台、需求表審核 | 老闆 |
| 門市主管控制台 | `Store_Manager.html` | 門市專用控制台 | 門市主管 |
| 會計專區 | `Accountants.html` | 會計專用看板 | 會計 |
| 員工管理 | `staff_admin.html` | 人員資料維護 | 老闆 |
| 公告管理 | `admin/announcement_management.html` | 公告發布管理 | 老闆 |
| 獎金規則 | `admin/bonus_rules.html` | 獎金規則設定 | 老闆 |
| 獎金報表 | `admin/bonus_report.html` | 獎金發放報表 | 老闆/會計 |
| 推薦商品管理 | `admin/recommended_products.html` | 推薦商品設定 | 老闆 |

| 健康檢查 | `health_check.html` | 系統狀態 | 老闆 |
| 系統架構圖 | `system_map_v3.html` | 架構視覺化 | 老闆 |

### 4.3 功能頁面 (Function Pages)

| 頁面名稱 | 檔案 | 用途 |
|----------|------|------|
| 客戶新增 | `customer_create.html` | 建立新客戶 |
| 產品新增 | `product_create.html` | 建立新產品 |
| 廠商新增 | `supplier_create.html` | 建立新廠商 |
| 待建檔中心 | `staging_center_v2.html` | 新客戶/新品審核 |
| 目標輸入 | `target_input.html` | 業績目標設定 |

### 4.4 共用組件 (Shared Components)

| 組件名稱 | 檔案 | 用途 |
|----------|------|------|
| 登入組件 v2.0 | `shared/auth_ui.js` + `auth_ui.css` | 統一登入介面 |
| 全域背景 | `shared/global-background.js` + `global-background.css` | 霓虹粒子背景 |
| 側邊欄導航 | `shared/sidebar-nav.js` | RWD 響應式選單 |
| 全域樣式 | `shared/global.css` | 共用 CSS |
| 模組系統 | `shared/modal-system.js` | 彈窗組件 |
| 分割視圖 | `shared/split-view.js` | 左右分割介面 |

---

## 5. 資料庫結構

### 5.1 資料庫資訊

| 項目 | 內容 |
|------|------|
| **資料庫類型** | SQLite 3 |
| **檔案路徑** | `/Users/aiserver/srv/db/company.db` |
| **檔案大小** | ~18 MB |
| **權限設定** | 唯讀 (SELECT only) |
| **備份策略** | 每日 04:00 自動備份 |

### 5.2 資料表清單

#### 5.2.1 核心業務表

| 資料表 | 用途 | 主要欄位 |
|--------|------|----------|
| `sales_history` | 銷貨歷史 | invoice_no, date, customer_id, salesperson, product_code, product_name, quantity, price, amount, profit |
| `inventory` | 庫存資料 | product_id, item_spec, warehouse, stock_quantity, unit_cost |
| `purchase_history` | 進貨歷史 | vendor_name, item_name, quantity, unit_price, date |
| `customers` | 客戶資料 | customer_id, short_name, mobile, phone1, company_address |
| `customer_master` | 客戶主檔 | customer_id, short_name, mobile, address, import_date |

#### 5.2.2 人員與排班表

| 資料表 | 用途 | 主要欄位 |
|--------|------|----------|
| `staff_roster` | 班表 | date, staff_name, location, shift_code |
| `staff_passwords` | 員工密碼 | name, title, password_hash, created_at |

#### 5.2.3 績效與評分表

| 資料表 | 用途 | 主要欄位 |
|--------|------|----------|
| `performance_metrics` | 績效指標 | subject_name, category, target_amount, revenue_amount, achievement_rate, margin_rate |
| `supervision_scores` | 督導評分 | date, store_name, attendance, appearance, service_attitude, ... (15項) |

#### 5.2.4 需求與流程表

| 資料表 | 用途 | 主要欄位 |
|--------|------|----------|
| `needs` | 需求表 | date, item_name, quantity, customer_code, department, requester, product_code, processed, processed_at, arrived_at |
| `service_records` | 服務記錄 | date, customer_code, customer_name, service_item, service_type, salesperson |

#### 5.2.5 評論與回饋表

| 資料表 | 用途 | 主要欄位 |
|--------|------|----------|
| `google_reviews` | Google 評論 | store_name, reviewer_name, review_date, star_rating, review_snippet, email_received_at |
| `google_reviews_stats` | 評論統計 | store_name, five_star, four_star, three_star, two_star, one_star, total_reviews, avg_rating |

#### 5.2.6 獎金與推薦表

| 資料表 | 用途 | 主要欄位 |
|--------|------|----------|
| `bonus_rules` | 獎金規則 | product_code, item_name, start_date, end_date, bonus_type, bonus_value, min_quantity |
| `bonus_results` | 獎金結果 | rule_id, salesperson, sale_date, product_code, quantity, revenue, bonus_amount, is_confirmed |
| `recommended_products` | 推薦商品 | category_id, product_code, item_name, quantity, requester, department |

#### 5.2.7 系統與日誌表

| 資料表 | 用途 | 主要欄位 |
|--------|------|----------|
| `system_announcements` | 系統公告 | title, content, level, is_active, is_pinned, created_by, created_at |
| `notification_logs` | 通知記錄 | type, recipient, message_preview, status, error_message, created_at |
| `login_attempts` | 登入嘗試 | ip_address, failed_count, locked_until, last_attempt |
| `ops_events` | 系統事件 | event_type, source, actor, status, duration_ms, summary, error_code |
| `admin_audit_log` | 管理員操作 | admin_user, action, action_type, fix_code, affected_ids, created_at |

### 5.3 詳細資料表結構

#### sales_history (銷貨歷史)

```sql
CREATE TABLE sales_history (
    invoice_no TEXT,
    date TEXT,
    customer_id TEXT,
    salesperson TEXT,
    product_code TEXT,
    product_name TEXT,
    quantity INTEGER,
    price INTEGER,
    amount INTEGER,
    cost INTEGER,
    profit INTEGER,
    margin_rate REAL
);
```

#### needs (需求表)

```sql
CREATE TABLE needs (
    date TEXT,
    item_name TEXT,
    quantity INTEGER,
    customer_code TEXT,
    department TEXT,
    requester TEXT,
    product_code TEXT,
    processed TEXT DEFAULT '待處理',
    processed_at DATETIME,
    arrived_at DATETIME,
    UNIQUE(date, item_name, quantity, requester, product_code)
);
```

#### performance_metrics (績效指標)

```sql
CREATE TABLE performance_metrics (
    subject_name TEXT,
    category TEXT,  -- '部門', '門市', '個人'
    target_amount REAL,
    revenue_amount REAL,
    profit_amount REAL,
    achievement_rate REAL,
    margin_rate REAL
);
```

---

## 6. API 規格

### 6.1 API 基礎資訊

| 項目 | 內容 |
|------|------|
| **Base URL** | `http://localhost:3000` |
| **協定** | HTTP/HTTPS (透過 Cloudflare Tunnel) |
| **格式** | JSON |
| **認證** | 部分 API 需傳入 `admin` 或 `requester` 參數 |

### 6.2 銷售相關 API

#### GET /api/sales/daily
取得本季每日銷售（門市部+業務部堆叠）

**回應**:
```json
[
  {
    "date": "2026-03-17",
    "store": 125000,
    "business": 45000,
    "total": 170000,
    "count": 12
  }
]
```

#### GET /api/sales/daily/store
取得本季每日銷售（僅門市部）

#### GET /api/sales/daily/by-store
取得各門市每日銷售明細

#### POST /api/sales/create
建立銷貨單

**請求**:
```json
{
  "customer_id": "C001",
  "items": [
    {
      "product_code": "P001",
      "product_name": "產品名稱",
      "quantity": 2,
      "price": 5000
    }
  ],
  "salesperson": "林榮祺"
}
```

### 6.3 業績相關 API

#### GET /api/performance/department
取得部門業績

**參數**:
- `year` (optional): 年份
- `month` (optional): 月份
- `period_type` (optional): `monthly`, `quarterly`, `yearly`

**回應**:
```json
{
  "departments": [
    {
      "name": "門市部",
      "target": 3000000,
      "revenue": 2500000,
      "profit": 500000,
      "achievement_rate": 0.83,
      "margin_rate": 0.20,
      "order_count": 150
    }
  ]
}
```

#### GET /api/performance/store
取得門市業績

#### GET /api/performance/personal
取得個人業績排名

#### GET /api/performance/business
取得業務部績效

### 6.4 需求表 API

#### GET /api/needs/latest
取得最新待處理需求表

#### POST /api/needs/batch
批次建立需求表

**請求**:
```json
{
  "items": [
    {
      "product_code": "P001",
      "product_name": "產品名稱",
      "quantity": 5,
      "department": "豐原門市",
      "requester": "林榮祺",
      "request_type": "請購"
    }
  ]
}
```

#### POST /api/needs/purchase
標記為已採購

#### POST /api/needs/transfer
標記為已調撥

#### POST /api/needs/arrive
標記為已到貨

#### POST /api/needs/complete
標記為已完成

#### POST /api/needs/cancel
取消需求表（30分鐘內）

### 6.5 客戶相關 API

#### GET /api/customer/search
搜尋客戶

**參數**:
- `q`: 搜尋關鍵字（姓名/電話/編號）

**回應**:
```json
{
  "customers": [
    {
      "customer_id": "C001",
      "short_name": "王小明",
      "mobile": "0912345678"
    }
  ]
}
```

#### GET /api/customer/detail/<customer_id>
取得客戶詳細資料

#### POST /api/customer/update
更新客戶資料

### 6.6 產品相關 API

#### GET /api/products/search
搜尋產品

**參數**:
- `q`: 搜尋關鍵字

#### GET /api/product/info
取得產品詳細資訊

**參數**:
- `code`: 產品編號

**回應**:
```json
{
  "product_code": "P001",
  "product_name": "微軟 OFFICE 2024 家用盒裝版",
  "vendor_name": "微軟",
  "unit_cost": 3200,
  "inventory": [
    {"warehouse": "豐原", "quantity": 15},
    {"warehouse": "潭子", "quantity": 8}
  ]
}
```

#### POST /api/product/create
建立新產品

### 6.7 庫存相關 API

#### GET /api/inventory/search
搜尋庫存

**參數**:
- `q`: 搜尋關鍵字

#### GET /api/inventory/list
取得庫存列表

#### GET /api/inventory/product/<product_id>
取得特定產品庫存

### 6.8 班表相關 API

#### GET /api/roster/weekly
取得指定日期所在週的班表（週日～週六）

**參數**:
- `date`（可選）：查詢基準日期，格式 `YYYY-MM-DD`。若未提供或格式錯誤，預設使用當天。

> **v3.3 Bug 修正**：原始實作忽略 `date` 參數，每次固定以 `datetime.now()` 計算本週範圍，導致前端無論選擇哪個日期都只能查看當週班表。v3.3 已修正為依傳入日期動態計算所屬週次。

**回應**:
```json
{
  "王小明": {
    "location": "豐原",
    "shifts": {
      "2026-03-16": "早班",
      "2026-03-17": "休",
      "2026-03-18": "早班"
    }
  }
}
```

#### GET /api/roster/today
取得今日班表

### 6.9 評論相關 API

#### GET /api/google-reviews
取得 Google 評論列表

**參數**:
- `store`: 門市名稱（可選）
- `limit`: 數量限制

#### GET /api/google-reviews/stats
取得評論統計

**回應**:
```json
{
  "豐原": {
    "five_star": 45,
    "four_star": 12,
    "total_reviews": 60,
    "avg_rating": 4.7
  }
}
```

### 6.10 督導評分 API

#### GET /api/store/supervision
取得評分總覽

#### GET /api/store/supervision/detail
取得評分明細

**參數**:
- `store`: 門市名稱
- `start_date`: 開始日期
- `end_date`: 結束日期

### 6.11 獎金相關 API

#### GET /api/bonus-rules
取得獎金規則列表

#### POST /api/bonus-rules
建立獎金規則

**請求**:
```json
{
  "product_code": "P001",
  "item_name": "產品名稱",
  "start_date": "2026-03-01",
  "end_date": "2026-03-31",
  "bonus_type": "fixed",
  "bonus_value": 500,
  "min_quantity": 1
}
```

#### POST /api/bonus-calculate
計算獎金

**請求**:
```json
{
  "year": 2026,
  "month": 3
}
```

#### GET /api/bonus-results
取得獎金計算結果

#### POST /api/bonus-results/batch-confirm
批次確認獎金

### 6.12 推薦商品 API

#### GET /api/recommended-categories
取得推薦分類

#### GET /api/recommended-products
取得推薦商品列表

#### POST /api/recommended-products/order
從推薦商品建立需求表

### 6.13 認證相關 API

#### POST /api/auth/verify
驗證員工密碼

**請求**:
```json
{
  "name": "林榮祺",
  "password": "密碼"
}
```

#### POST /api/boss/verify
驗證老闆密碼

#### POST /api/accountant/verify
驗證會計密碼

### 6.14 系統管理 API

#### GET /api/health
系統健康檢查

**回應**:
```json
{
  "status": "healthy",
  "database": "healthy",
  "timestamp": "2026-03-18 01:51:00"
}
```

#### GET /api/notification-status
通知系統狀態

#### GET /api/system/announcements
取得系統公告

#### GET /api/v1/admin/health
Admin 健康檢查（詳細）

#### POST /api/v1/admin/run-scripts
執行所有 Parser 腳本

#### POST /api/v1/admin/run-script
執行單一腳本

**請求**:
```json
{
  "script": "inventory_parser.py"
}
```

### 6.15 API 完整清單

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | /api/health | 健康檢查 |
| GET | /api/analysis/<type> | AI 分析結果 |
| GET | /api/sales/daily | 每日銷售 |
| GET | /api/sales/daily/store | 門市部銷售 |
| GET | /api/sales/daily/by-store | 各門市銷售 |
| POST | /api/sales/create | 建立銷貨單 |
| GET | /api/sales/list | 銷售列表 |
| GET | /api/sales/detail | 銷售明細 |
| GET | /api/performance/department | 部門業績 |
| GET | /api/performance/store | 門市業績 |
| GET | /api/performance/personal | 個人業績 |
| GET | /api/performance/business | 業務部績效 |
| GET | /api/roster/weekly | 本週班表 |
| GET | /api/roster/today | 今日班表 |
| GET | /api/store/reviews | 門市評論 |
| GET | /api/google-reviews | Google 評論 |
| GET | /api/google-reviews/stats | 評論統計 |
| GET | /api/store/supervision | 督導評分總覽 |
| GET | /api/store/supervision/detail | 評分明細 |
| GET | /api/needs/latest | 最新需求表 |
| GET | /api/needs/recent | 近期需求表 |
| GET | /api/needs/history | 需求表歷史 |
| POST | /api/needs/batch | 批次建立需求 |
| POST | /api/needs/cancel | 取消需求 |
| POST | /api/needs/purchase | 標記已採購 |
| POST | /api/needs/transfer | 標記已調撥 |
| POST | /api/needs/arrive | 標記已到貨 |
| POST | /api/needs/complete | 標記已完成 |
| POST | /api/needs/remark | 更新備註 |
| GET | /api/customer/search | 搜尋客戶 |
| GET | /api/customer/detail/<id> | 客戶詳情 |
| POST | /api/customer/update | 更新客戶 |
| GET | /api/customers/search | 客戶進階搜尋 |
| GET | /api/customers/list | 客戶列表 |
| GET | /api/products/search | 搜尋產品 |
| GET | /api/product/info | 產品資訊 |
| POST | /api/product/create | 建立產品 |
| GET | /api/inventory/search | 搜尋庫存 |
| GET | /api/inventory/list | 庫存列表 |
| GET | /api/inventory/product/<id> | 產品庫存 |
| GET | /api/service-records | 服務記錄列表 |
| POST | /api/service-records | 建立服務記錄 |
| GET | /api/service-records/detail | 服務記錄明細 |
| POST | /api/service-records/<id> | 更新服務記錄 |
| DELETE | /api/service-records/<id> | 刪除服務記錄 |
| GET | /api/bonus-rules | 獎金規則 |
| POST | /api/bonus-rules | 建立獎金規則 |
| PUT | /api/bonus-rules/<id> | 更新獎金規則 |
| DELETE | /api/bonus-rules/<id> | 刪除獎金規則 |
| POST | /api/bonus-calculate | 計算獎金 |
| GET | /api/bonus-results | 獎金結果 |
| POST | /api/bonus-results/batch-confirm | 批次確認獎金 |
| GET | /api/recommended-categories | 推薦分類 |
| POST | /api/recommended-categories | 建立分類 |
| GET | /api/recommended-products | 推薦商品 |
| POST | /api/recommended-products | 建立推薦商品 |
| POST | /api/recommended-products/order | 建立訂單 |
| GET | /api/system/announcements | 系統公告 |
| POST | /api/auth/verify | 驗證密碼 |
| POST | /api/boss/verify | 驗證老闆 |
| POST | /api/accountant/verify | 驗證會計 |
| GET | /api/notification-status | 通知狀態 |
| GET | /api/v1/admin/health | Admin 健康檢查 |
| POST | /api/v1/admin/run-scripts | 執行所有腳本 |
| POST | /api/v1/admin/run-script | 執行單一腳本 |

---

## 7. UI/UX 設計說明

### 7.1 設計理念

**核心原則**:
- **科技未來感**: 霓虹主題、玻璃擬態
- **清晰易讀**: 資訊層次分明、色彩對比適中
- **響應式設計**: 支援桌面與行動裝置
- **一致性**: 統一的視覺語言與互動模式

### 7.2 視覺風格

#### 色彩系統

色彩分為三層：**CIS 品牌色**（互動 UI 用）、**語意狀態色**（操作反饋用）、**系統功能色**（資料視覺化專用）。

v3.2 已完成全系統色彩清掃，將所有頁面 inline style 與 `<style>` 區塊中殘留的藍/青色系（`#00d4ff`、`#2196f3`、`#00bcd4`、`#38bdf8`、`#7c3aed` 等，共 35 個檔案 500+ 處）全數替換為品牌黃色系，達到視覺一致性。

**CIS 官方品牌色（互動 UI 用）**

| 顏色名稱 | 色碼 | CSS 變數 | 用途 |
|----------|------|----------|------|
| 品牌黃 | `#FABF13` | `--color-brand-primary` | 主要強調色、按鈕、focus ring、active 狀態 |
| 品牌黑 | `#231815` | `--color-brand-black` | 品牌黃按鈕上的文字色 |
| 品牌黃 10% | `rgba(250,191,19,0.10)` | `--color-brand-yellow-10` | active 背景、表格 header |
| 品牌黃 20% | `rgba(250,191,19,0.20)` | `--color-brand-yellow-20` | focus box-shadow |
| 品牌黃 30% | `rgba(250,191,19,0.30)` | `--color-brand-yellow-30` | hover border |

**語意狀態色（操作反饋專用，不隨品牌色更動）**

| 顏色名稱 | 色碼 | 用途 |
|----------|------|------|
| 成功綠 | `#22c55e → #16a34a` | 確認按鈕、成功狀態、到貨標記 |
| 危險紅 | `#ff6b6b → #c92a2a` | 刪除按鈕、警告狀態 |
| 中性灰 | `#64748b → #475569` | 取消按鈕、次要操作 |

**系統功能色（圖表 / 資料視覺化專用，不改動）**

| 顏色名稱 | 色碼 | CSS 變數 | 用途 |
|----------|------|----------|------|
| 科技青 | `#00d4ff` | `--color-accent-cyan` | 圖表、資料視覺化（保留備用） |
| 科技紫 | `#7b2cbf` | `--color-accent-purple` | 圖表（保留備用） |
| 主色橘 | `#ff9800` | — | 豐原門市圖表 |
| 主色紫 | `#9c27b0` | — | 潭子門市圖表 |
| 主色綠 | `#4caf50` | — | 大雅門市、成功狀態 |
| 警告黃 | `#ffc107` | `--color-status-warning` | 警告狀態 |

**背景與文字色**

| 顏色名稱 | 色碼 | CSS 變數 | 用途 |
|----------|------|----------|------|
| 背景深 | `#0a0a0a` | `--color-bg-primary` | 頁面背景 |
| 背景次 | `#1a1a2e` | `--color-bg-secondary` | Sidebar 背景 |
| 背景淺 | `#16213e` | `--color-bg-tertiary` | 卡片背景 |
| 文字白 | `#ffffff` | `--color-text-primary` | 主要文字 |
| 文字灰 | `#8892b0` | `--color-text-secondary` | 次要文字 |

#### 字體系統

> **CIS 指定字體**：中文 — 思源黑體 (Noto Sans CJK TC)；英文 — Calibri
> **系統現用字體**：系統介面以 `-apple-system / BlinkMacSystemFont / Microsoft JhengHei` 為主，與 CIS 精神一致（無襯線黑體）

| 用途 | 字體 | 大小 |
|------|------|------|
| 標題 | Inter | 24-32px |
| 內文 | Inter / Microsoft JhengHei | 最小 16px（防 iOS 縮放） |
| 數據 | JetBrains Mono | 18-24px |
| 程式碼 | JetBrains Mono | 12-14px |

### 7.3 登入組件 v2.0

**檔案**: `shared/auth_ui.js` + `auth_ui.css`

**設計特色**:
- 玻璃擬態效果 (backdrop-filter blur)
- 霓虹光暈動畫（品牌黃 `#FABF13` 漸層，v3.1 起由藍紫色系改為 CIS 品牌黃）
- 雙層旋轉裝飾圓環（外圈色：品牌黃 40% 透明）
- SVG 科技風格盾牌圖示（填色：品牌黃）
- 密碼顯示/隱藏切換
- 焦點動畫（鎖圖示變閃電）
- 登入按鈕：品牌黃漸層背景，文字色採品牌黑 `#231815`（符合 CIS 規範）

**使用方式**:
```javascript
import { showAuthModal, initAuthUI } from './shared/auth_ui.js';

// 初始化
initAuthUI({
  onLoginSuccess: (user) => {
    console.log('登入成功:', user);
  }
});

// 顯示登入視窗
showAuthModal({
  title: '門市主管登入',
  verifyUrl: '/api/auth/verify'
});
```

### 7.4 全域背景

**檔案**: `shared/global-background.js` + `global-background.css`

**效果**:
- 深色網格背景
- 浮動粒子動畫
- 漸層光暈裝飾
- 19 個頁面統一風格

### 7.5 RWD 響應式選單

**檔案**: `shared/sidebar-nav.js`

**功能**:
- 桌面版：左側固定側邊欄
- 行動版：漢堡選單 + 滑出抽屜
- 自動根據角色顯示對應選項
- 當前頁面高亮
- 選單關鍵字搜尋框（`#menuSearchInput`，v3.1 修正）

**v3.1 Bug 修正 — menuSearchInput**:

`sidebar-nav.js` 原本已有針對 `#menuSearchInput` 的鍵盤監聽邏輯，但 `base.html` 中從未定義對應的 HTML 元素，導致 `document.getElementById('menuSearchInput')` 回傳 `null`，造成前端 `TypeError` 錯誤，選單搜尋功能完全失效。

v3.1 已在 `base.html` Sidebar 中補上：

```html
<!-- 選單搜尋框 -->
<div style="padding: 8px 16px; flex-shrink: 0;">
    <input
        type="text"
        id="menuSearchInput"
        class="menu-search-input"
        placeholder="🔍 搜尋選單..."
        autocomplete="off"
    >
</div>
```

搜尋框 focus 樣式使用品牌黃 border（`#FABF13`）與品牌黃 20% box-shadow；字體大小設定 16px 以防 iOS 自動縮放。

### 7.6 頁面布局規範

#### 標準頁面結構
```html
<!DOCTYPE html>
<html>
<head>
  <title>頁面標題 | ERP 營運系統</title>
  <link rel="stylesheet" href="shared/global.css">
  <link rel="stylesheet" href="shared/auth_ui.css">
</head>
<body>
  <!-- 全域背景 -->
  <div id="global-background"></div>
  
  <!-- 側邊欄 -->
  <nav id="sidebar"></nav>
  
  <!-- 主要內容 -->
  <main class="main-content">
    <!-- 頁面內容 -->
  </main>
  
  <!-- 登入組件 -->
  <div id="auth-modal"></div>
  
  <script src="shared/global-background.js"></script>
  <script src="shared/sidebar-nav.js"></script>
  <script src="shared/auth_ui.js"></script>
</body>
</html>
```

### 7.7 元件尺寸規格（v3.2 統一標準）

v3.2 起全系統採用三段式按鈕尺寸與統一輸入框規格，以消除各頁面因 inline style 造成的大小不一問題。

#### 按鈕（Button）

| 等級 | padding | border-radius | font-size | 適用場景 |
|------|---------|---------------|-----------|----------|
| 小型 | `5px 12px` | `4px` | `13px` | 表格行內操作（編輯、刪除、確認） |
| 標準 | `10px 20px` | `8px` | `14px` | 頁面主要操作按鈕 |
| 大型 | `12px 28px` | `8px` | `15px` | 表單送出、主要 CTA |

**顏色語意對應**:
- 主要操作 → 品牌黃漸層 `linear-gradient(135deg, #FABF13 0%, #e6a800 100%)`，文字色 `#231815`
- 確認 / 成功 → 綠色漸層 `linear-gradient(135deg, #22c55e, #16a34a)`，文字色 `#fff`
- 刪除 / 危險 → 紅色漸層 `linear-gradient(135deg, #ff6b6b, #c92a2a)`，文字色 `#fff`
- 取消 / 次要 → 半透明灰 `rgba(100, 116, 139, 0.2)`，文字色 `#94a3b8`

#### 輸入框（Input / Select / Textarea）

| 屬性 | 值 |
|------|----|
| `padding` | `10px 14px` |
| `border-radius` | `8px` |
| `font-size` | `16px`（防 iOS 自動縮放） |
| `border` | `1px solid rgba(255,255,255,0.2)` |
| `:focus border` | `var(--color-brand-primary)` |
| `:focus box-shadow` | `0 0 0 3px var(--color-brand-yellow-20)` |

### 7.8 自訂游標（Custom Cursor）

**檔案**: `base.html`（內嵌 CSS + JS）

全系統採用「大圈套小圓點」雙層游標設計，小圓點即時跟隨滑鼠位置，外圈以 CSS transition 延遲追上，產生流暢的跟隨動態。

#### 元素結構

```html
<div class="cursor-dot" id="cursorDot"></div>
<div class="cursor-ring" id="cursorRing"></div>
```

#### 游標狀態與配色

| 狀態 | 觸發條件 | 小圓點顏色 | 外圈顏色 |
|------|----------|-----------|----------|
| 預設 | 一般移動 | 白色 `#FFFFFF` + 白色光暈 | `rgba(255,255,255,0.5)` |
| Hover | 懸停可點擊元素（`a`、`button`、`[onclick]` 等） | 青色 `#00d4ff` + 青色光暈 | `rgba(0,212,255,0.6)` |
| Click | 滑鼠按下瞬間 | 縮小 `scale(0.8)` | 縮小 `scale(0.9)` |
| Text | 懸停輸入框 | 白色細條（`2px × 20px`，仿文字游標） | 隱藏 |
| Disabled | 懸停 `disabled` 元素 | 紅色 `#f44336` + 紅色光暈 | `rgba(244,67,54,0.5)` 縮小 |

> **配色設計說明**：預設白色在深色背景上清晰可辨；Hover 改用系統既有的 `--color-accent-cyan`（`#00d4ff`）而非品牌黃，是因為品牌黃按鈕懸停時游標會與按鈕融合、難以辨識。青色與黃色形成互補對比，在任何背景色下皆清楚可見，形成白色（中性移動）→ 青色（可互動）的明確視覺語意。

#### 行動裝置

觸控裝置（`pointer: coarse`）自動停用自訂游標，恢復瀏覽器預設，避免殘影干擾。

### 7.9 圖表設計

**使用 Chart.js**，統一設定：

```javascript
Chart.defaults.color = '#8b92a8';
Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.1)';
Chart.defaults.font.family = 'Inter';
```

**門市顏色對應**:
- 豐原門市: `#ff9800` (橘色)
- 潭子門市: `#9c27b0` (紫色)
- 大雅門市: `#4caf50` (綠色)

---

## 8. 工具與整合

### 8.1 Parser 系統

**位置**: `/Users/aiserver/srv/parser/`

| 腳本 | 功能 | 排程時間 |
|------|------|----------|
| `inventory_parser.py` | 庫存資料匯入 | 10:30 |
| `purchase_parser.py` | 進貨資料匯入 | 10:35 |
| `sales_parser_v22.py` | 銷貨資料匯入 | 10:40 |
| `customer_parser.py` | 客戶資料匯入 | 10:45 |
| `google_reviews_parser.py` | Google 評論抓取 | 00:00 (4/1起) |
| `msi_inventory_report.py` | 微星庫存週報 | 每週一 12:00 |
| `roster_parser.py` | 班表資料匯入 | 10:55 |
| `performance_parser.py` | 績效資料匯入 | 11:00 |
| `supervision_parser.py` | 督導評分匯入 | 11:10 |
| `service_record_parser.py` | 服務記錄匯入 | 11:15 |
| `needs_parser.py` | 需求表匯入 | 每10分鐘 (9-21點) |

### 8.2 Cron 排程

```bash
# 查看排程
crontab -l

# 主要排程項目
04:00 - 數據備份 (auto_backup.sh)
05:00 - OpenClaw 記憶備份
06:00 - 系統自動重開機
10:30-11:15 - Parser 批次執行
*/10 9-21 * * * - 需求表同步 (白天)
0 22-23,0-8 * * * - 需求表同步 (晚上)
00:00 - Google 評論抓取 (4/1起)
12:00 (週一) - 微星庫存週報
```

### 8.3 備份策略

| 項目 | 時間 | 位置 |
|------|------|------|
| 資料庫備份 | 每日 04:00 | `~/srv/db/backups/` |
| 記憶檔備份 | 每日 05:00 | `~/srv/backup/` |
| OneDrive 同步 | 即時 | `~/srv/sync/OneDrive/` |

### 8.4 系統監控

**健康檢查端點**:
- `/api/health` - 基礎健康檢查
- `/api/v1/admin/health` - 詳細健康檢查
- `/admin/health` - 健康檢查頁面

**監控項目**:
- 資料庫連線狀態
- 通知發送成功率
- API 回應時間
- 資料新鮮度

---

## 9. Telegram Bot 與通知

### 9.1 Bot 資訊

| 項目 | 內容 |
|------|------|
| **Bot 名稱** | 通知機器人 |
| **Bot Token** | `8623161623:AAGWlwGjp0Vf3bzpiVgLltQFbcGFY4kpFxo` |
| **用途** | 需求表通知、庫存週報、系統告警 |

### 9.2 通知對象

| 類型 | 發送方式 | 接收對象 | Chat ID |
|------|----------|----------|---------|
| 請購通知 | Telegram Bot | Alan (老闆) | `8545239755` |
| 調撥通知 | Telegram Bot | 會計 (黃環馥) | `8203016237` |
| 系統告警 | Telegram Bot | Alan (老闆) | `8545239755` |
| 微星週報 | Telegram Bot | Alan (老闆) | `8545239755` |

### 9.3 群組

| 群組名稱 | Chat ID | 用途 |
|----------|---------|------|
| 電腦舖工作群組 | `-5232179482` | 群組通知 |

### 9.4 通知格式範例

**需求表通知**:
```
📋 新請購單

產品：微軟 OFFICE 2024 家用盒裝版
數量：5
部門：豐原門市
填表人：林榮祺
時間：2026-03-18 10:30
```

**微星庫存週報**:
```
📊 微星庫存週報

統計日期：2026-03-17
總品項數：156
總庫存值：NT$ 2,450,000

（附 CSV 檔案）
```

### 9.5 使用範例

```python
import requests

TELEGRAM_BOT_TOKEN = "8623161623:AAGWlwGjp0Vf3bzpiVgLltQFbcGFY4kpFxo"
TELEGRAM_CHAT_ID = "8545239755"

def send_telegram_message(message, file_path=None):
    if file_path:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
        with open(file_path, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': message}
            response = requests.post(url, files=files, data=data)
    else:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, data=data)
    return response
```

---

## 10. 附錄

### 10.1 組織架構

#### 門市部（主管：莊圍迪）
| 門市 | 人員 |
|------|------|
| 豐原門市 | 林榮祺、林峙文 |
| 潭子門市 | 劉育仕、林煜捷 |
| 大雅門市 | 張永承、張家碩 |

#### 業務部（主管：萬書佑）
| 職位 | 人員 |
|------|------|
| 主管 | 萬書佑 |
| 業務員 | 鄭宇晉、梁仁佑 |

### 10.2 重要檔案路徑

| 用途 | 路徑 |
|------|------|
| ERP 系統 | `~/.openclaw/workspace/dashboard-site/` |
| 資料庫 | `~/srv/db/company.db` |
| Parser | `~/srv/parser/` |
| 日誌 | `~/srv/logs/` |
| OneDrive 同步 | `~/srv/sync/OneDrive/ai_source/` |
| 備份 | `~/srv/backup/` |

### 10.3 常用指令

```bash
# 重啟 ERP 系統
cd ~/.openclaw/workspace/dashboard-site
./manage_gunicorn.sh restart

# 手動執行 Parser
cd ~/srv/parser
python3 inventory_parser.py
python3 sales_parser_v22.py

# 查看日誌
tail -f ~/srv/logs/app.log

# 資料庫備份
cp ~/srv/db/company.db ~/srv/db/backups/company_$(date +%Y%m%d).db

# Git 推送
cd ~/.openclaw/workspace
GIT_SSH_COMMAND="ssh -i ~/.ssh/github_deploy_key -o IdentitiesOnly=yes" git push origin main
```

### 10.4 版本歷史

| 版本 | 日期 | 主要更新 |
|------|------|----------|
| v1.0 | 2026-02-20 | 系統初始建立 |
| v2.0 | 2026-03-01 | Admin Dashboard 完整功能 |
| v3.0 | 2026-03-16 | 系統正名 ERP、Google 評論自動化、獎金系統 |
| v3.1 | 2026-03-18 | 前端視覺優化：導入 CIS 品牌黃色系（#FABF13）、修正選單搜尋 Bug（menuSearchInput）、全面 RWD 強化 |
| v3.2 | 2026-03-18 | 全系統色彩清掃（35 檔案 500+ 處藍青色 → 品牌黃）、按鈕三段式尺寸標準化、輸入框規格統一、非品牌漸層修正、側邊欄標題更新、清除廢棄 templates/ 目錄 |
| v3.3 | 2026-03-23 | 移除稽核儀表功能（admin.html 及相關 API）、調整推薦備貨與銷售獎金權限為全員可見、版本號更新為 2.0.3、安裝 Edge TTS 語音工具 |

### 10.5 聯絡資訊

| 項目 | 內容 |
|------|------|
| **系統管理員** | Alan (黃柏翰) |
| **AI 助理** | Yvonne |
| **Telegram Bot** | @alanhuangbot |
| **ERP 網址** | http://localhost:3000 |
| **GitHub Repo** | https://github.com/han5211tw-ai/ai.git |

---

**文件結束**

*本文件由 Yvonne 自動生成於 2026-03-23*