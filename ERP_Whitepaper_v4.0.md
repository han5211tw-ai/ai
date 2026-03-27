# ERP 營運系統專案白皮書

**文件版本**: v4.3  
**最後更新**: 2026-03-27 17:15  
**專案名稱**: 電腦舖 ERP 營運系統  
**系統版本**: V2.0.4  
**作者**: Yvonne (AI Assistant)  
**適用對象**: 系統管理員、開發人員、未來維護者

---

## 目錄

1. [專案概述](#1-專案概述)
2. [系統架構](#2-系統架構)
3. [技術棧](#3-技術棧)
4. [資料庫設計](#4-資料庫設計)
5. [前端頁面結構](#5-前端頁面結構)
6. [API 架構](#6-api-架構)
7. [Parser 系統](#7-parser-系統)
8. [權限與安全](#8-權限與安全)
9. [通知系統](#9-通知系統)
10. [排程任務](#10-排程任務)
11. [功能模組詳解](#11-功能模組詳解)
12. [部署與維運](#12-部署與維運)
13. [版本歷史](#13-版本歷史)
14. [附錄](#14-附錄)

---

## 1. 專案概述

### 1.1 專案背景

電腦舖 ERP 營運系統（原名 Dashboard 營運系統）是專為「電腦舖」零售門市設計的企業資源規劃系統。系統於 2026 年 2 月開始開發，歷經多次迭代，已成為整合銷售、庫存、人員、客戶管理的完整營運平台。

### 1.2 系統正名

- **原名稱**: Dashboard 營運系統
- **新名稱**: ERP 營運系統
- **正名日期**: 2026-03-16
- **對外名稱**: 電腦舖營運系統

### 1.3 系統統計

| 項目 | 數量 |
|------|------|
| 前端頁面 | 50 個 HTML 檔案 |
| API 端點 | 181 個路由 |
| 後端函數 | 205 個 Python 函數 |
| 資料庫表格 | 49 個資料表 |
| Parser 腳本 | 11 個自動化腳本 |
| 開發歷程 | 36 天 (2026-02-20 ~ 2026-03-27) |

### 1.4 核心價值

1. **即時業績追蹤**: 每日自動匯入銷售資料，即時計算部門/門市/個人績效
2. **需求表管理**: 四階段流程（待處理→已採購→已調撥→已完成）
3. **自動化營運**: Parser 自動匯入、Telegram 通知、排程報表
4. **資料視覺化**: Chart.js 圖表、系統架構圖、健康檢查儀表板

---

## 2. 系統架構

### 2.1 整體架構

```
使用者層 (老闆/門市/業務/會計)
    ↓
前端層 (HTML5 + JS + Chart.js)
    ↓
API 層 (Flask + Gunicorn)
    ↓
資料層 (SQLite3)
    ↓
資料來源 (OneDrive/Gmail/Telegram)
```

### 2.2 目錄結構

```
/Users/aiserver/
├── .openclaw/workspace/
│   └── dashboard-site/          # ERP 系統主目錄
│       ├── app.py               # Flask 主程式
│       ├── index.html           # 首頁
│       ├── admin.html           # 資料管理中心
│       ├── boss.html            # 老闆控制台
│       ├── Store_Manager.html   # 門市主管控制台
│       ├── Accountants.html     # 會計專區
│       ├── shared/              # 共用資源
│       │   ├── auth_ui.js       # 登入組件 v2.0
│       │   ├── auth_ui.css      # 登入樣式
│       │   └── admin_ui.css     # 管理介面樣式
│       ├── admin/               # 後台管理頁面
│       ├── backup/              # 備份檔案
│       └── system_map_v3.html   # 系統架構圖 V3
├── srv/
│   ├── db/
│   │   └── company.db           # SQLite 資料庫
│   ├── parser/                  # Parser 腳本
│   │   ├── inventory_parser.py
│   │   ├── sales_parser_v22.py
│   │   ├── performance_parser.py
│   │   ├── needs_parser.py
│   │   ├── google_reviews_parser.py
│   │   └── msi_inventory_report.py
│   └── sync/OneDrive/           # OneDrive 同步
│       └── ai_source/
│           ├── roster/          # 班表
│           ├── supervision/     # 督導評分
│           ├── feedback/        # 五星評論
│           └── backup/          # 備份
└── srv/web-site/computershop-web/  # 官網 (Port 8000)
```

### 2.3 系統架構圖 V3

- **檔案位置**: `dashboard-site/system_map_v3.html`
- **技術**: D3.js + GSAP
- **特性**: 霓虹主題、貝茲爾曲線、動態粒子、節點互動


---

## 3. 技術棧

### 3.1 前端技術

| 技術 | 用途 | 版本 |
|------|------|------|
| HTML5 | 頁面結構 | - |
| CSS3 | 樣式設計 | - |
| JavaScript (Vanilla) | 互動邏輯 | ES6+ |
| Chart.js | 資料視覺化 | v3.x |
| D3.js | 系統架構圖 | v7.x |
| GSAP | 動畫效果 | v3.x |

### 3.2 後端技術

| 技術 | 用途 | 版本 |
|------|------|------|
| Python | 後端語言 | 3.11+ |
| Flask | Web 框架 | 2.x |
| Gunicorn | WSGI 伺服器 | 20.x |
| SQLite3 | 資料庫 | 3.x |

### 3.3 外部服務

| 服務 | 用途 |
|------|------|
| OneDrive | 資料同步 (ai_source/) |
| Gmail | Google 商家評論通知 |
| Telegram Bot | 即時通知 (@alanhuangbot) |
| Cloudflare Tunnel | 外部存取 (選配) |

---

## 4. 資料庫設計

### 4.1 核心資料表

#### sales_history (銷貨歷史)
```sql
CREATE TABLE sales_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no TEXT,              -- 發票號碼
    date TEXT,                    -- 日期 (YYYY-MM-DD)
    customer_id TEXT,             -- 客戶編號
    salesperson TEXT,             -- 銷售人員
    product_code TEXT,            -- 產品代碼
    product_name TEXT,            -- 產品名稱
    quantity INTEGER,             -- 數量
    price INTEGER,                -- 單價
    amount INTEGER,               -- 金額
    cost INTEGER,                 -- 成本
    profit INTEGER,               -- 利潤
    profit_rate REAL,             -- 毛利率
    source_file TEXT,             -- 來源檔案
    source_row INTEGER,           -- 原始行號
    import_key TEXT               -- 匯入鍵值
);
```

#### customers (客戶主檔)
```sql
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    short_name TEXT,              -- 簡稱
    full_name TEXT,               -- 全名
    mobile TEXT,                  -- 手機
    phone1 TEXT,                  -- 電話1
    phone2 TEXT,                  -- 電話2
    company_address TEXT,         -- 公司地址
    contact_person TEXT,          -- 聯絡人
    tax_id TEXT,                  -- 統編
    email TEXT,                   -- 信箱
    notes TEXT                    -- 備註
);
```

#### inventory (庫存)
```sql
CREATE TABLE inventory (
    product_id TEXT,
    item_spec TEXT,               -- 產品規格
    warehouse TEXT,               -- 倉庫
    stock_quantity INTEGER,       -- 庫存數量
    unit_cost REAL,               -- 單位成本
    record_date TEXT,             -- 記錄日期
    PRIMARY KEY (product_id, warehouse)
);
```

#### needs (需求表)
```sql
CREATE TABLE needs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,                    -- 日期
    item_name TEXT,               -- 產品名稱
    quantity INTEGER,             -- 數量
    customer_code TEXT,           -- 客戶編號/需求用途
    department TEXT,              -- 需求部門
    requester TEXT,               -- 填表人員
    product_code TEXT,            -- 產品編號
    status TEXT DEFAULT '待處理',  -- 狀態
    processed_at DATETIME,        -- 處理時間
    arrived_at DATETIME,          -- 到貨時間
    cancelled_at DATETIME,        -- 取消時間
    UNIQUE(date, item_name, quantity, requester, product_code)
);
```

#### staff_roster (班表)
```sql
CREATE TABLE staff_roster (
    date TEXT,
    staff_name TEXT,
    location TEXT,                -- 門市
    shift_code TEXT,              -- 班次代碼
    PRIMARY KEY (date, staff_name)
);
```

#### supervision_scores (督導評分)
```sql
CREATE TABLE supervision_scores (
    date TEXT,
    store_name TEXT,
    employee_name TEXT,           -- 員工姓名（人員表現項目）
    -- 環境整潔（1-5項）
    storefront REAL,              -- 門面整潔
    store_interior REAL,          -- 店內清潔
    product_display REAL,         -- 產品陳列
    cable_management REAL,        -- 線材管理
    warehouse REAL,               -- 倉庫整齊
    -- 人員表現（6-11項）
    attendance REAL,              -- 出勤狀況
    appearance REAL,              -- 服裝儀容
    service_attitude REAL,        -- 服務態度
    professionalism REAL,         -- 專業知識
    sales_process REAL,           -- 銷售流程
    work_attitude REAL,           -- 工作態度
    total_score REAL,             -- 總分（22分制）
    percentage REAL,              -- 百分比分數
    issues TEXT,                  -- 發現問題
    suggestions TEXT,             -- 改善建議
    PRIMARY KEY (date, store_name, employee_name)
);
```

### 4.2 擴充資料表

| 資料表 | 用途 |
|--------|------|
| google_reviews | Google 商家評論 |
| google_reviews_stats | 評論統計快取 |
| bonus_rules | 銷售獎金規則 |
| bonus_results | 獎金計算結果 |
| recommended_products | 推薦備貨商品 |
| system_announcements | 系統公告 |
| notification_logs | 通知發送記錄 |
| service_records | 外勤服務紀錄 |
| staging_records | 待建檔資料 |
| products | 產品主檔 |
| purchase_history | 進貨歷史 |
| crm_tasks | CRM 待辦 |
| line_reply_templates | LINE 回覆範本 |
| supervision_scores | 督導評分紀錄 |

### 4.3 資料庫路徑

```
主資料庫: /Users/aiserver/srv/db/company.db
備份位置: ~/srv/sync/OneDrive/ai_source/backup/
權限設定: 唯讀 (SELECT only)
```


---

## 5. 前端頁面結構

### 5.1 頁面分類

| 類別 | 頁面 | 說明 |
|------|------|------|
| **首頁/總覽** | index.html | 每日銷售趨勢、公告欄、待處理需求 |
| **業績分析** | department.html | 部門業績分析 |
| | store.html | 門市業績分析 |
| | personal.html | 個人業績排名 |
| | business.html | 業務部績效 |
| | monthly_report.html | 月會報告 |
| **控制台** | boss.html | 老闆控制台 |
| | Store_Manager.html | 門市主管控制台 |
| | Accountants.html | 會計專區 |
| | admin.html | 資料管理中心 |
| **功能頁面** | needs_input.html | 需求表輸入 |
| | customer_search.html | 客戶查詢 |
| | service_record.html | 外勤服務紀錄 |
| | sales_input.html | 銷貨輸入 |
| | roster.html | 班表查詢 |
| | roster_input.html | 班表輸入 |
| | supervision_score.html | 督導紀錄表 |
| | staging_center_v2.html | 待建檔中心 |
| | target_input.html | 業績目標管理 |
| | line_replies.html | LINE 回覆表 |
| | line_replies_edit.html | LINE 回覆編輯 |
| **後台管理** | admin/announcement_management.html | 公告管理 |
| | admin/recommended_products.html | 推薦備貨商品 |
| | admin/bonus_rules.html | 獎金規則管理 |
| | admin/bonus_report.html | 獎金報表 |
| | staff_management.html | 員工管理 |
| **其他** | system_map_v3.html | 系統架構圖 V3 |
| | bonus_personal.html | 個人獎金查詢 |
| | recommended_products.html | 推薦備貨選購 |

### 5.2 共用元件

#### 登入組件 v2.0
- **檔案**: `shared/auth_ui.js`, `shared/auth_ui.css`
- **特性**: 玻璃擬態設計、霓虹光暈動畫、旋轉圓環裝飾、自動過期機制

#### 全域背景
- **檔案**: `shared/global-background.css`, `shared/global-background.js`
- **套用頁面**: 19 個主要頁面
- **效果**: 網格背景 + 漸層色彩 + 浮動粒子

#### 側邊欄導航
- **檔案**: `base.html` (模板)
- **特性**: 響應式選單、權限控制顯示、當前頁面高亮

### 5.3 視覺設計規範

#### 顏色主題
```css
:root {
    --primary-bg: #0a0a0a;
    --secondary-bg: #1a1a2e;
    --accent-cyan: #00d4ff;
    --accent-purple: #9c27b0;
    --accent-orange: #ff9800;
    --accent-yellow: #ffc107;
    --accent-green: #4caf50;
    --text-primary: #ffffff;
    --text-secondary: rgba(255,255,255,0.7);
}
```

#### 部門顏色
| 部門/門市 | 顏色代碼 |
|-----------|----------|
| 門市部 | `#00d4ff` |
| 業務部 | `#ffc107` |
| 豐原門市 | `#ff9800` |
| 潭子門市 | `#9c27b0` |
| 大雅門市 | `#4caf50` |

---

## 6. API 架構

### 6.1 API 分類

#### 銷售相關
| API | 方法 | 說明 |
|-----|------|------|
| `/api/sales/daily` | GET | 每日銷售（門市部+業務部）|
| `/api/sales/daily/store` | GET | 每日銷售（僅門市部）|
| `/api/sales/daily/by-store` | GET | 各門市明細 |

#### 績效相關
| API | 方法 | 說明 |
|-----|------|------|
| `/api/performance/department` | GET | 部門績效 |
| `/api/performance/store` | GET | 門市績效 |
| `/api/performance/personal` | GET | 個人績效排名 |
| `/api/performance/business` | GET | 業務部績效 |

#### 需求表相關
| API | 方法 | 說明 |
|-----|------|------|
| `/api/needs/latest` | GET | 最新需求表（待處理）|
| `/api/needs/history` | GET | 需求歷史紀錄 |
| `/api/needs/batch` | POST | 批次新增需求 |
| `/api/needs/cancel` | POST | 取消需求 |
| `/api/needs/complete` | POST | 完成需求 |
| `/api/needs/purchase` | POST | 標記已採購 |
| `/api/needs/transfer` | POST | 標記已調撥 |
| `/api/needs/arrive` | POST | 標記已到貨 |
| `/api/needs/overdue-arrival` | GET | 逾期收貨提醒 |

#### 客戶相關
| API | 方法 | 說明 |
|-----|------|------|
| `/api/customer/search` | GET | 客戶搜尋 |
| `/api/customer/detail/<id>` | GET | 客戶詳細資料 |

#### 班表相關
| API | 方法 | 說明 |
|-----|------|------|
| `/api/roster/weekly` | GET | 本週班表 |
| `/api/roster/today` | GET | 今日班表 |
| `/api/roster/monthly` | GET | 整月班表 |

#### 系統相關
| API | 方法 | 說明 |
|-----|------|------|
| `/api/system/announcements` | GET/POST | 系統公告管理 |
| `/api/health` | GET | 系統健康檢查 |
| `/api/store/reviews` | GET | 門市評論統計 |
| `/api/google-reviews` | GET | Google 評論列表 |
| `/api/google-reviews/stats` | GET | Google 評論統計 |
| `/api/line/replies` | GET/POST | LINE 回覆管理 |
| `/api/line/categories` | GET | LINE 分類列表 |
| `/api/store/employees` | GET | 店別員工列表 |
| `/api/store/supervision` | GET | 門市督導評分 |
| `/api/personal/supervision` | GET | 個人督導評分 |
| `/api/supervision/score` | POST | 督導評分存檔 |

### 6.2 認證機制

系統採用 **JWT-less Session Auth**:

1. **登入流程**:
   - 使用者輸入員工編號 + 密碼
   - 驗證成功 → 寫入 localStorage
   - 儲存: `{name, role, loginTime, expiresAt}`

2. **自動過期**:
   - 每天晚上 9 點自動登出
   - 超過 24 小時強制重新登入

### 6.3 API 安全原則

- **資料庫唯讀**: 僅允許 SELECT
- **參數驗證**: 所有輸入參數經過型別檢查
- **SQL 注入防護**: 使用參數化查詢
- **錯誤處理**: 統一錯誤回傳格式


---

## 7. Parser 系統

### 7.1 Parser 列表

| 腳本 | 功能 | 排程時間 | 資料來源 |
|------|------|----------|----------|
| `inventory_parser.py` | 庫存匯入 | 10:30 | OneDrive/inventory/ |
| `purchase_parser.py` | 進貨匯入 | 10:35 | OneDrive/purchase/ |
| `sales_parser_v22.py` | 銷貨匯入 | 10:40 | OneDrive/sales/ |
| `customer_parser.py` | 客戶匯入 | 10:45 | OneDrive/customer/ |
| `feedback_parser.py` | 五星評論匯入 | 10:50 | OneDrive/feedback/ |
| `google_reviews_parser.py` | Google 評論抓取 | 00:00 | Gmail API |
| `roster_parser.py` | 班表匯入 | 10:55 | OneDrive/roster/ |
| `performance_parser.py` | 績效匯入 | 11:00 | OneDrive/performance/ |
| `supervision_parser.py` | 督導評分匯入 | 11:10 | OneDrive/supervision/ |
| `service_record_parser.py` | 服務記錄匯入 | 11:15 | OneDrive/service/ |
| `needs_parser.py` | 需求表匯入 | 每10分鐘 | OneDrive/needs/ |
| `msi_inventory_report.py` | 微星庫存週報 | 每週一 12:00 | 資料庫 |

### 7.2 資料格式規範

#### 銷貨 CSV 格式
- **編碼**: Big5/CP950
- **格式**: 無標題列
- **日期**: 民國曆 (1150101 = 2026/01/01)
- **解析**: 從右向左取 6 個欄位

#### 檔案命名規則
| 類型 | 命名模式 | 範例 |
|------|----------|------|
| 銷貨 | 業務銷退貨資料YYYYMMDD.csv | 業務銷退貨資料20260327.csv |
| 進貨 | 進退貨資料瀏覽YYYYMMDD.csv | 進退貨資料瀏覽20260327.csv |
| 庫存 | 產品現有庫存表YYYYMMDD.csv | 產品現有庫存表20260327.csv |

---

## 8. 權限與安全

### 8.1 角色定義

| 角色 | 權限範圍 |
|------|----------|
| 老闆 | 全部功能 |
| 會計 | 需求表處理、獎金報表、庫存查看 |
| 門市部主管 | 門市相關數據、督導評分 |
| 業務部主管 | 業務相關數據 |
| 門市工程師 | 需求表、班表、客戶查詢 |
| 業務人員 | 需求表、外勤服務紀錄、客戶查詢 |

### 8.2 權限控制機制

#### 前端控制
```javascript
const menuPermissions = {
    '老闆控制台': ['老闆'],
    '會計專區': ['老闆', '會計'],
    '需求表': ['老闆', '會計', '門市工程師', '業務人員'],
    '銷售獎金': ['老闆', '會計', '門市工程師', '業務人員', '門市部主管', '業務部主管']
};
```

### 8.3 資料安全

- **資料庫唯讀**: 生產環境僅開放 SELECT
- **敏感資料**: 成本、利潤僅老闆可見
- **登入過期**: 24 小時自動登出

---

## 9. 通知系統

### 9.1 Telegram Bot 設定

- **Bot 名稱**: @alanhuangbot
- **Token**: `8623161623:AAGWlwGjp0Vf3bzpiVgLltQFbcGFY4kpFxo`
- **Chat ID**:
  - Alan (老闆): `8545239755`
  - 會計 (黃環馥): `8203016237`

### 9.2 通知類型

| 類型 | 觸發條件 | 接收者 |
|------|----------|--------|
| 請購通知 | 員工提交請購單 | Alan |
| 調撥通知 | 員工提交調撥單 | 會計 |
| 微星週報 | 每週一 12:00 | Alan |
| 系統告警 | 服務異常 | Alan |
| 逾期提醒 | 需求單逾期未收貨 | 相關人員 |

---

## 10. 排程任務

### 10.1 Cron 時間表

```bash
# 系統維護
0 4 * * * /Users/aiserver/srv/parser/auto_backup.sh
0 5 * * * /Users/aiserver/.openclaw/workspace/.pi/backup-memory.sh
0 6 * * * sudo /sbin/shutdown -r now

# 資料匯入
30 10 * * * python3 inventory_parser.py
35 10 * * * python3 purchase_parser.py
40 10 * * * python3 sales_parser_v22.py
45 10 * * * python3 customer_parser.py
50 10 * * * python3 feedback_parser.py
0 0 * * * python3 google_reviews_parser.py

# 班表與績效
55 10 * * * python3 roster_parser.py
0 11 * * * python3 performance_parser.py
10 11 * * * python3 supervision_parser.py
15 11 * * * python3 service_record_parser.py

# 需求表（高頻率）
*/10 9-21 * * * python3 needs_parser.py
0 22-23,0-8 * * * python3 needs_parser.py

# 微星週報
0 12 * * 1 python3 msi_inventory_report.py
```

---

## 11. 功能模組詳解

### 11.1 需求表系統

#### 四階段流程
| 階段 | 角色 | 動作 | 狀態 |
|------|------|------|------|
| 1 | 員工 | 送出需求 | 待處理 |
| 2 | 老闆 | 按「已採購」 | 已採購 |
| 3 | 會計 | 按「已調撥」 | 已調撥 |
| 4 | 員工 | 按「已到貨」 | 已完成 |

#### 權限規則
| 角色 | 可取消範圍 |
|------|-----------|
| 老闆 | 任何待處理需求 |
| 會計 | 任何調撥需求 |
| 一般員工 | 自己的需求（30分鐘內）|

### 11.2 業績計算邏輯

#### 門市部計算
- **豐原門市**: 林榮祺 + 林峙文
- **潭子門市**: 劉育仕 + 林煜捷
- **大雅門市**: 張永承 + 張家碩
- **門市部總計**: 三個門市人員 + 主管（莊圍迪）

#### 業務部計算
- **業務員**: 鄭宇晉 + 梁仁佑
- **業務部總計**: 業務員 + 主管（萬書佑）

### 11.3 督導評分系統

#### 評分結構（v4.3）

| 類別 | 項目 | 編號 | 滿分 |
|------|------|------|------|
| **環境整潔** | 門面整潔 | 1 | 2分 |
| | 店內清潔 | 2 | 2分 |
| | 產品陳列 | 3 | 2分 |
| | 線材管理 | 4 | 2分 |
| | 倉庫整齊 | 5 | 2分 |
| **人員表現** | 出勤狀況 | 6 | 2分 |
| | 服裝儀容 | 7 | 2分 |
| | 服務態度 | 8 | 2分 |
| | 專業知識 | 9 | 2分 |
| | 銷售流程 | 10 | 2分 |
| | 工作態度 | 11 | 2分 |
| **總計** | **11項** | | **22分** |

#### 評分顯示
- **門市頁面 (store.html)**: 顯示環境整潔 1-5 項
- **個人頁面 (personal.html)**: 顯示人員表現 6-11 項
- **總分計算**: 得分 ÷ 22 × 100 = 百分比（例如 18/22 = 82%）

#### 工作態度細項（檢查重點）
- 主動性：主動協助同事、主動回報問題
- 責任感：對工作負責、不推卸責任
- 配合度：配合公司政策、配合主管指示
- 學習意願：願意學習新知識、接受指導

### 11.4 銷售獎金系統

#### 資料表
- `bonus_rules`: 獎金規則（商品、時間、獎金類型）
- `bonus_results`: 計算結果（人員、商品、數量、獎金）

#### 計算邏輯
- 檢查時間區間
- 檢查商品匹配
- 檢查數量門檻
- 計算：固定金額 × 數量 或 銷售額 × 百分比

### 11.5 Google 商家評論系統

#### 運作流程
```
顧客留評論 → Google 寄通知 → 腳本解析 → 寫入資料庫 → 頁面顯示
```

#### 資料表
- `google_reviews`: 單筆評論明細
- `google_reviews_stats`: 門市統計快取

### 11.6 LINE 回覆表系統

#### 功能說明
- 管理 LINE 官方帳號的常見回覆範本
- 支援分類管理（產品詢問、售後服務、活動資訊等）
- 提供關鍵字搜尋功能
- 可新增、編輯、刪除回覆內容

#### 頁面結構
| 頁面 | 功能 |
|------|------|
| line_replies.html | 回覆列表、搜尋、分類篩選 |
| line_replies_edit.html | 新增/編輯回覆內容 |

#### 資料表
```sql
CREATE TABLE line_reply_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT,                -- 分類
    keywords TEXT,                -- 關鍵字（逗號分隔）
    title TEXT,                   -- 標題
    content TEXT,                 -- 回覆內容
    created_at DATETIME,
    updated_at DATETIME
);
```


---

## 12. 部署與維運

### 12.1 啟動指令

```bash
# 進入目錄
cd /Users/aiserver/.openclaw/workspace/dashboard-site

# 重啟 Gunicorn
./manage_gunicorn.sh restart

# 或手動啟動
pkill -f gunicorn
gunicorn -c gunicorn.conf.py app:app
```

### 12.2 常用維護指令

```bash
# 查看排程
crontab -l

# 手動執行 Parser
cd /Users/aiserver/srv/parser
python3 sales_parser_v22.py

# 資料庫備份
cp /Users/aiserver/srv/db/company.db ~/backup/company_$(date +%Y%m%d).db

# 查看系統狀態
curl http://localhost:3000/api/health
```

### 12.3 日誌位置

```
Parser 日誌: ~/srv/logs/
Gunicorn 日誌: dashboard-site/logs/
系統日誌: /var/log/system.log
```

---

## 13. 版本歷史

### V2.0.4 (2026-03-27)
- 督導紀錄表重構 v4.3
- 環境整潔與人員表現分開顯示
- 新增工作態度評分項目
- 評分改為 0/1/2 分制
- LINE 回覆表功能上線
- 白皮書 v4.3 更新

### V2.0.3 (2026-03-27)
- 需求表取消後重打 Bug 修復
- ERP AI 聊天機器人上線

### V2.0.2 (2026-03-23)
- 每日晨報自動化系統
- 推薦備貨商品權限開放
- 銷售獎金頁面開放
- 移除稽核儀表功能

### V2.0.1 (2026-03-18)
- 系統架構圖 V3
- 官網 Deploy Key 設定
- ERP Repo 重新命名

### V2.0.0 (2026-03-16)
- Google 商家五星評論自動化
- 微星庫存週報
- 系統正名 ERP
- 推薦備貨商品功能
- 銷售獎金計算功能

### V1.2.0 (2026-03-08)
- RWD 響應式選單
- 銷貨系統修正
- 權限系統修復

### V1.1.0 (2026-03-04)
- 系統架構 V3
- 登入組件 v2.0
- 員工管理功能
- 系統公告功能

### V1.0.0 (2026-03-01)
- Admin Center 系統升級
- 三頁面 UI 統一
- 版本號管理

---

## 14. 附錄

### 14.1 人員編制

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

### 14.2 班次代碼

| 代碼 | 說明 |
|------|------|
| 早 | 早班 (10:00-18:00) |
| 晚 | 晚班 (12:00-20:00) |
| 全 | 全班 |
| 值 | 值班 |
| 休 | 休假 |

### 14.3 重要檔案路徑

| 檔案 | 路徑 |
|------|------|
| 主程式 | `/Users/aiserver/.openclaw/workspace/dashboard-site/app.py` |
| 資料庫 | `/Users/aiserver/srv/db/company.db` |
| 系統架構圖 | `/Users/aiserver/.openclaw/workspace/dashboard-site/system_map_v3.html` |
| Parser 腳本 | `/Users/aiserver/srv/parser/` |
| 記憶檔案 | `/Users/aiserver/.openclaw/workspace/memory/` |

### 14.4 聯絡資訊

- **系統管理員**: Yvonne (AI Assistant)
- **Telegram Bot**: @alanhuangbot
- **系統網址**: http://localhost:3000
- **GitHub Repo**: https://github.com/han5211tw-ai/ERP

---

## 文件資訊

- **建立日期**: 2026-03-27
- **文件大小**: 約 15 KB
- **頁數**: 14 章節
- **維護者**: Yvonne

_本文件為 ERP 營運系統的完整技術文件，供未來系統重建、維護、擴充參考使用。_

