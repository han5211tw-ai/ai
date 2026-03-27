# ERP 營運系統 — 專案白皮書

**版本**: v4.1（AI 聊天機器人）
**最後更新**: 2026-03-26
**文件編號**: ERP-WP-002
**撰寫者**: Yvonne (AI Assistant)
**前版**: v3.2（暗色霓虹版，port 3000）

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
| **系統名稱** | COSH ERP 營運系統 |
| **版本** | v4.0（溫潤極簡版） |
| **前版** | v3.2（暗色霓虹版） |
| **重建開始** | 2026-03-21 |
| **系統定位** | 電腦舖零售業務管理與營運分析平台 |
| **目標用戶** | 老闆、門市主管、會計、業務員、門市人員 |
| **部署環境** | Mac mini 本地伺服器 + Cloudflare Tunnel |

### 1.2 v4.0 核心改變

v4.0 是一次完整的前端視覺重建，後端架構保持不變。核心改變包括：

- **設計語言**：從暗色霓虹（玻璃擬態）改為溫潤極簡（米白紙質質感）
- **Port**：3000 → 9000
- **認證方式**：username + password → 4 位 PIN 碼（以 `staff` 表為準）
- **字體系統**：Inter + JetBrains Mono → Noto Serif TC + Cormorant Garamond
- **目錄結構**：從 `~/.openclaw/workspace/dashboard-site/` 遷移至 `/Users/aiserver/srv/web-site/computershop-erp/電腦舖ERP系統/`
- **頁面總數**：30 頁（比 v3.2 多出 Phase 4 建檔/後台頁與 admin/ 管理頁）
- **AI 聊天機器人**（v4.1 新增）：本機 oMLX（Qwen3）SSE 串流、浮動視窗、多輪對話、對話記錄 DB

### 1.3 核心功能

- **業績分析**：部門/門市/個人多維度績效追蹤
- **銷售管理**：銷貨輸入、報價單、訂單管理
- **庫存管理**：即時庫存查詢、進貨追蹤、推薦備貨
- **需求表系統**：請購/調撥/新品申請流程
- **客戶管理**：客戶資料查詢、建立、待建檔中心
- **班表系統**：人員排班與查詢
- **督導評分**：門市四大類評核與追蹤
- **獎金計算**：薪資結構、業績提成、加給、目標達成
- **系統公告**：公告發布、排程、管理
- **後台管理**：員工管理、系統狀態、建檔管理
- **AI 助理**：本機 Qwen3 LLM、SSE 串流、多輪對話、全員可用

### 1.4 技術棧

| 層級 | 技術 |
|------|------|
| **前端** | HTML5, CSS3, JavaScript (Vanilla), 純 SVG 圖表 |
| **後端** | Python 3, Flask |
| **資料庫** | SQLite |
| **伺服器** | Gunicorn (port 9000) |
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
│                     Mac mini (aiserver)                         │
│  ┌─────────────────────┼────────────────────────────────────┐  │
│  │                     │                                    │  │
│  │  ┌──────────────────▼──────────────────┐               │  │
│  │  │        Gunicorn (Port 9000)         │               │  │
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
/Users/aiserver/srv/web-site/computershop-erp/
└── 電腦舖ERP系統/
    ├── app.py                     # Flask 主程式（DB 路徑、port 9000）
    ├── gunicorn.conf.py           # Gunicorn 設定（port 9000，gthread worker）
    ├── db/
    │   └── company.db             # SQLite 資料庫（唯讀）
    ├── shared/
    │   ├── global.css             # 全域樣式（溫潤極簡設計系統）
    │   ├── sidebar-nav.js         # 側邊欄導航（溫潤版）
    │   ├── auth_ui.js             # PIN 登入組件
    │   └── auth_ui.css            # 登入樣式（保留相容）
    │
    ├── index.html                 # 首頁（KPI + 日銷售圖 + 公告）
    ├── department.html            # 部門業績
    ├── store.html                 # 門市業績
    ├── personal.html              # 個人業績
    ├── business.html              # 業務業績
    ├── boss.html                  # 老闆控制台
    ├── needs_input.html           # 需求表（請購/調撥/新品）
    ├── query.html                 # 銷貨輸入
    ├── quote_input.html           # 報價單
    ├── inventory_query.html       # 庫存查詢
    ├── customer_search.html       # 客戶查詢
    ├── roster.html                # 班表
    ├── supervision_score.html     # 督導評分
    ├── monthly_report.html        # 月報表
    ├── recommended_products.html  # 推薦備貨（員工端）
    ├── bonus_personal.html        # 個人獎金
    ├── customer_create.html       # 新增客戶
    ├── product_create.html        # 新增產品
    ├── supplier_create.html       # 新增廠商
    ├── staging_center_v2.html     # 待建檔中心
    ├── Accountants.html           # 會計專區
    ├── staff_admin.html           # 員工管理
    ├── health_check.html          # 系統狀態
    └── admin/
        ├── bonus_rules.html              # 獎金規則設定
        ├── bonus_report.html             # 獎金總報表
        ├── announcement_management.html  # 公告管理
        └── recommended_products.html     # 推薦備貨管理（後台）

/Users/aiserver/srv/
├── db/
│   └── company.db               # SQLite 資料庫（來源 17MB+）
├── parser/                      # 資料解析腳本
│   ├── inventory_parser.py
│   ├── sales_parser_v22.py
│   ├── performance_parser.py
│   ├── google_reviews_parser.py
│   └── msi_inventory_report.py
├── sync/OneDrive/ai_source/     # OneDrive 同步
│   ├── roster/                  # 班表 Excel
│   ├── supervision/             # 督導評分
│   ├── feedback/                # 五星評論
│   └── backup/                  # 備份
└── logs/                        # 系統日誌
```

### 2.3 Flask 路由規則

```python
# app.py 關鍵設定
DB_PATH = os.environ.get('DB_PATH', './db/company.db')
STATIC_DIR = os.path.dirname(os.path.abspath(__file__))

# 靜態檔案 catch-all（讓所有 HTML 頁面可直接訪問）
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(STATIC_DIR, path)
```

---

## 3. 模組說明

### 3.1 核心模組架構

```
┌─────────────────────────────────────────────────────────────────┐
│                      COSH ERP v4.0                              │
├──────────────┬─────────────┬─────────────┬─────────────────────┤
│  銷售模組    │  庫存模組   │  客戶模組   │   報表模組          │
├──────────────┼─────────────┼─────────────┼─────────────────────┤
│ • 銷貨輸入   │ • 庫存查詢  │ • 客戶查詢  │ • 業績分析          │
│ • 報價單     │ • 需求表    │ • 客戶建立  │ • 班表查詢          │
│ • 需求/調撥  │ • 推薦備貨  │ • 待建檔中心│ • 督導評分          │
│              │ • 廠商管理  │             │ • 獎金計算          │
├──────────────┴─────────────┴─────────────┴─────────────────────┤
│                        管理後台                                 │
│  員工管理 ・ 公告管理 ・ 獎金規則 ・ 系統狀態 ・ 會計專區       │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     資料整合層                                  │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐                  │
│  │   Parser   │ │   Cron     │ │  OneDrive  │                  │
│  │   系統     │ │   排程     │ │   同步     │                  │
│  └────────────┘ └────────────┘ └────────────┘                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     資料儲存層                                  │
│              SQLite Database (company.db)                       │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 各模組詳細說明

#### 3.2.1 銷售模組 (Sales Module)

| 功能 | 說明 | 對應頁面 |
|------|------|----------|
| 銷貨輸入 | 新增銷貨單，支援客戶搜尋、產品搜尋 | `query.html` |
| 報價單 | 建立報價文件，定價/報價雙欄，有效期 | `quote_input.html` |
| 需求表 | 請購/調撥/新品申請（批次送出） | `needs_input.html` |

**API 端點**:
- `POST /api/sales/create` — 建立銷貨單
- `GET /api/sales/list` — 銷售列表
- `GET /api/sales/detail` — 銷售明細
- `POST /api/quote/create` — 建立報價單
- `POST /api/needs/batch` — 批次建立需求表

#### 3.2.2 庫存模組 (Inventory Module)

| 功能 | 說明 | 對應頁面 |
|------|------|----------|
| 庫存查詢 | 即時查詢各門市庫存、缺貨/偏低過濾 | `inventory_query.html` |
| 需求表 | 請購/調撥/新品申請 | `needs_input.html` |
| 推薦備貨（員工端） | 緊迫分級、一鍵建需求單 | `recommended_products.html` |
| 推薦備貨（管理後台） | 規則設定、批次建立需求單 | `admin/recommended_products.html` |
| 產品建立 | 新增產品、SKU 自動產生、毛利計算 | `product_create.html` |
| 廠商建立 | 新增廠商、聯絡人、付款條件 | `supplier_create.html` |

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
| 客戶查詢 | 搜尋客戶、交易紀錄雙欄 | `customer_search.html` |
| 客戶建立 | 個人/公司行號/VIP 三類型 | `customer_create.html` |
| 待建檔中心 | 客戶/產品/廠商未完成項目管理 | `staging_center_v2.html` |

**客戶資料來源**:
- `customers` — 既有客戶表（legacy）
- `customer_master` — 新客戶主檔（master）
- `customer_staging` — 待建檔/審核客戶

#### 3.2.4 業績模組 (Performance Module)

| 功能 | 說明 | 對應頁面 |
|------|------|----------|
| 部門業績 | 門市部/業務部績效（月/季/年） | `department.html` |
| 門市業績 | 各門市業績分析 | `store.html` |
| 個人業績 | 業務員排名與達成率 | `personal.html` |
| 業務部績效 | 業務員專屬報表 | `business.html` |
| 月報表 | KPI、日銷折線、門市比較、品類表 | `monthly_report.html` |

**業績計算邏輯**:
```
門市部總計 = 豐原門市 + 潭子門市 + 大雅門市 + 主管(莊圍迪)
業務部總計 = 鄭宇晉 + 梁仁佑 + 主管(萬書佑)
```

#### 3.2.5 班表模組 (Roster Module)

| 功能 | 說明 | 對應頁面 |
|------|------|----------|
| 本週班表 | 週視圖、門市篩選、班次圖例 | `roster.html` |
| 今日班表 | 顯示今日值班人員 | API 介面 |
| 班表匯入 | 從 Excel 匯入 | `roster_parser.py` |

**班次代碼**:

| 代碼 | 說明 | 時間 |
|------|------|------|
| 早 | 早班 | 10:00–18:00 |
| 晚 | 晚班 | 12:00–20:00 |
| 全 | 全班 | — |
| 值 | 值班 | — |
| 休 | 休假 | — |

#### 3.2.6 督導評分模組 (Supervision Module)

v4.0 改為四大類加權評分（v3.2 為 15 項目評分）。

| 功能 | 說明 | 對應頁面 |
|------|------|----------|
| 評分輸入 | 4 大類星星互動評分，總分換算 | `supervision_score.html` |
| 歷史記錄 | 歷史評分列表、月平均橫條圖 | `supervision_score.html` 右面板 |

**四大類評分（加權 100 分制）**:

| 類別 | 權重 | 說明 |
|------|------|------|
| 環境整潔 | 25% | 店面、倉庫整潔度 |
| 服務品質 | 30% | 服務態度、專業知識、銷售流程 |
| 商品陳列 | 25% | 商品擺設、標價、線材管理 |
| 作業流程 | 20% | 回覆速度、資訊完整、後續追蹤 |

**等級對應**:
- S（≥90）/ A（≥80）/ B（≥70）/ C（≥60）/ D

#### 3.2.7 獎金模組 (Bonus Module)

| 功能 | 說明 | 對應頁面 |
|------|------|----------|
| 個人獎金查詢 | 獎金拆解、達標進度、近半年走勢 | `bonus_personal.html` |
| 獎金規則設定 | 底薪/出勤/提成/加給/目標四大 tab | `admin/bonus_rules.html` |
| 獎金總報表 | 員工明細表、批次審核、匯出 CSV | `admin/bonus_report.html` |

**薪資結構**:
```
薪資合計 = 底薪 + 出勤獎金（全勤/遲到扣） + 業績提成 + 加給合計 + 服務品質獎金
```

**業績提成階梯**:

| 達成率 | 提成比率 |
|--------|----------|
| 未達 70% | 0% |
| 70%–85% | 0.8% |
| 85%–100% | 1.2% |
| 100%–120% | 1.8% |
| 超過 120% | 2.5% |

#### 3.2.8 推薦備貨模組 (Recommended Products)

| 功能 | 說明 | 對應頁面 |
|------|------|----------|
| 員工端推薦清單 | 緊迫分級、門市庫存、一鍵建需求 | `recommended_products.html` |
| 後台管理 | 推薦清單管理、規則設定、批次需求 | `admin/recommended_products.html` |

**緊迫等級**:
- 缺貨緊急（紅）/ 高需求（橘）/ 中需求（藍）/ 低需求（綠）

#### 3.2.9 系統管理模組 (Admin Module)

| 功能 | 說明 | 對應頁面 |
|------|------|----------|
| 老闆控制台 | 需求審核、今日班表、快速操作 | `boss.html` |
| 會計專區 | 損益摘要、應收帳款、帳齡分析 | `Accountants.html` |
| 員工管理 | 員工表格、PIN 管理、狀態切換 | `staff_admin.html` |
| 公告管理 | 新增/編輯/排程/置頂/刪除公告 | `admin/announcement_management.html` |
| 系統狀態 | 7 端點健檢、DB 統計、即時 log | `health_check.html` |
| 待建檔中心 | 客戶/產品/廠商待完成項目管理 | `staging_center_v2.html` |

#### 3.2.10 AI 聊天機器人模組（v4.1 新增）

| 功能 | 說明 | 實作位置 |
|------|------|----------|
| 浮動聊天視窗 | 右下角浮動按鈕，點擊展開 | `shared/chat-widget.js` |
| 多輪對話 | 完整 history 隨每次請求帶入 | chat-widget.js |
| SSE 串流 | 逐 token 即時渲染，舊版瀏覽器 fallback | chat-widget.js |
| 對話記錄 | 每輪寫入 `chat_logs` SQLite 資料表 | app.py `/api/chat` |
| Think 過濾 | 自動移除 `<think>…</think>` 思考區塊 | 前後端雙層過濾 |

**模型設定**:

| 項目 | 值 |
|------|----|
| 模型 | `Qwen3.5-9B-6bit` |
| API 端點 | `http://127.0.0.1:8001/v1/chat/completions` |
| API Key | `5211` |
| System Prompt | 內部 AI 助理，可回答任何問題（ERP 操作/業務/一般知識） |
| Session | `sessionStorage` 產生並持久化 `sessionId` |

**Session 物件（`_OMLX_SESSION`）**:
```python
_OMLX_SESSION = requests.Session()
_OMLX_SESSION.trust_env = False  # 避免 macOS 26 + Gunicorn fork crash
```

---

## 4. 頁面與功能清單

### 4.1 業績儀表板（Phase 2）

| 頁面名稱 | 檔案 | 用途 | 權限 |
|----------|------|------|------|
| 首頁 | `index.html` | 總覽、KPI、日銷售趨勢、公告 | 全員 |
| 部門業績 | `department.html` | 部門業績分析（月/季/年） | 全員 |
| 門市業績 | `store.html` | 門市業績分析 | 全員 |
| 個人業績 | `personal.html` | 個人業績排名、spotlight | 全員 |
| 業務部績效 | `business.html` | 業務員專屬報表 | 全員 |
| 老闆控制台 | `boss.html` | 需求審核、今日班表 | 老闆 |

### 4.2 表單操作（Phase 3）

| 頁面名稱 | 檔案 | 用途 | 權限 |
|----------|------|------|------|
| 銷貨輸入 | `query.html` | 新增銷貨單 | 全員 |
| 報價單 | `quote_input.html` | 建立報價，定價/報價雙欄 | 全員 |
| 需求表填寫 | `needs_input.html` | 請購/調撥/新品申請 | 全員 |

### 4.3 查詢類（Phase 3）

| 頁面名稱 | 檔案 | 用途 | 權限 |
|----------|------|------|------|
| 庫存查詢 | `inventory_query.html` | 庫存查詢、缺貨/偏低過濾 | 全員 |
| 客戶查詢 | `customer_search.html` | 客戶搜尋、交易記錄 | 全員 |
| 班表查詢 | `roster.html` | 本週班表、日力統計 | 全員 |

### 4.4 主管/管理（Phase 3）

| 頁面名稱 | 檔案 | 用途 | 權限 |
|----------|------|------|------|
| 督導評分 | `supervision_score.html` | 四大類評分、歷史記錄 | 主管 |
| 月報表 | `monthly_report.html` | 月度 KPI、各門市比較 | 全員 |
| 推薦備貨 | `recommended_products.html` | 商品補貨建議、一鍵需求 | 全員 |
| 個人獎金 | `bonus_personal.html` | 獎金查詢、達標進度 | 全員 |

### 4.5 建檔/後台（Phase 4）

| 頁面名稱 | 檔案 | 用途 | 權限 |
|----------|------|------|------|
| 新增客戶 | `customer_create.html` | 建立個人/公司/VIP 客戶 | 全員 |
| 新增產品 | `product_create.html` | 建立新品、SKU、毛利計算 | 主管 |
| 新增廠商 | `supplier_create.html` | 建立廠商、聯絡人 | 主管 |
| 待建檔中心 | `staging_center_v2.html` | 管理未完成的客戶/產品/廠商 | 主管 |
| 會計專區 | `Accountants.html` | 損益摘要、應收帳款 | 會計 |
| 員工管理 | `staff_admin.html` | 人員資料、PIN、狀態 | 老闆 |
| 系統狀態 | `health_check.html` | 健檢、DB 統計、log | 老闆 |

### 4.6 管理後台（admin/）

| 頁面名稱 | 檔案 | 用途 | 權限 |
|----------|------|------|------|
| 獎金規則設定 | `admin/bonus_rules.html` | 底薪/出勤/提成/加給/目標 | 老闆 |
| 獎金總報表 | `admin/bonus_report.html` | 全員獎金明細、批次審核 | 老闆/會計 |
| 公告管理 | `admin/announcement_management.html` | 公告 CRUD、排程、置頂 | 老闆 |
| 推薦備貨管理 | `admin/recommended_products.html` | 備貨清單規則、批次需求 | 老闆 |

### 4.7 共用組件 (Shared Components)

| 組件名稱 | 檔案 | 用途 |
|----------|------|------|
| PIN 登入組件 | `shared/auth_ui.js` + `auth_ui.css` | 4 位 PIN 統一登入介面 |
| 側邊欄導航 | `shared/sidebar-nav.js` | 溫潤版 RWD 選單 |
| 全域樣式 | `shared/global.css` | CSS 變數與基礎樣式 |
| AI 聊天機器人 | `shared/chat-widget.js` | 浮動聊天視窗，oMLX SSE 串流（v4.1 新增） |

引入方式（在任何頁面 `</body>` 前）：
```html
<!-- 根目錄頁面 -->
<script src="shared/chat-widget.js"></script>

<!-- admin/ 頁面 -->
<script src="../shared/chat-widget.js"></script>
```

> **注意**: v4.0 已移除 `global-background.js`、`global-background.css`、`modal-system.js`、`split-view.js`。

---

## 5. 資料庫結構

### 5.1 資料庫資訊

| 項目 | 內容 |
|------|------|
| **資料庫類型** | SQLite 3 |
| **來源路徑** | `/Users/aiserver/srv/db/company.db` |
| **v4.0 路徑** | `./db/company.db`（相對於 app.py）|
| **環境變數覆寫** | `DB_PATH`（測試/開發用） |
| **檔案大小** | ~18 MB |
| **備份策略** | 每日 04:00 自動備份 |

### 5.2 資料表清單

#### 5.2.1 核心業務表

| 資料表 | 用途 | 主要欄位 |
|--------|------|----------|
| `sales_history` | 銷貨歷史 | invoice_no, date, customer_id, salesperson, product_code, product_name, quantity, price, amount, profit |
| `inventory` | 庫存資料 | product_id, item_spec, warehouse, stock_quantity, unit_cost |
| `purchase_history` | 進貨歷史 | vendor_name, item_name, quantity, unit_price, date |
| `customers` | 客戶資料（legacy） | customer_id, short_name, mobile, phone1, company_address |
| `customer_master` | 客戶主檔 | customer_id, short_name, mobile, address, import_date |
| `customer_staging` | 待建檔客戶 | — |

#### 5.2.2 人員與排班表

| 資料表 | 用途 | 主要欄位 |
|--------|------|----------|
| `staff` | 員工主檔（v4.0 認證用） | id, name, staff_no, store, role, pin_hash, phone, join_date, is_active |
| `staff_roster` | 班表 | date, staff_name, location, shift_code |
| `staff_passwords` | 員工密碼（v3 legacy） | name, title, password_hash, created_at |

> **v4.0 認證說明**: `staff` 表的 `pin_hash`（4 位 PIN），`is_active=1` 才可登入。`erp_user` 存入 localStorage/sessionStorage。

#### 5.2.3 績效與評分表

| 資料表 | 用途 | 主要欄位 |
|--------|------|----------|
| `performance_metrics` | 績效指標 | subject_name, category, target_amount, revenue_amount, achievement_rate, margin_rate |
| `supervision_scores` | 督導評分（v4.0：四大類） | date, store_name, cleanliness, service_quality, display, workflow, total_score, grade |

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
| `system_announcements` | 系統公告 | title, content, type, status, pinned, targets, author, publish_at, expire_at |
| `notification_logs` | 通知記錄 | type, recipient, message_preview, status, error_message, created_at |
| `login_attempts` | 登入嘗試 | ip_address, failed_count, locked_until, last_attempt |
| `ops_events` | 系統事件 | event_type, source, actor, status, duration_ms, summary, error_code |
| `admin_audit_log` | 管理員操作 | admin_user, action, action_type, fix_code, affected_ids, created_at |
| `chat_logs` | AI 聊天記錄（v4.1） | session_id, user_message, bot_reply, created_at |
| `line_replies` | LINE 回覆表（v4.2） | reply_datetime, customer_line_name, inquiry_content, reply_store, reply_staff, is_resolved, created_at |

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

#### staff (員工主檔，v4.0 新增)

```sql
CREATE TABLE staff (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    staff_no TEXT UNIQUE,
    store TEXT,      -- 豐原/潭子/大雅/業務/總部
    role TEXT,       -- 老闆/主任/資深店員/店員/業務員/會計/兼職
    pin_hash TEXT,   -- bcrypt hash of 4-digit PIN
    phone TEXT,
    join_date TEXT,
    notes TEXT,
    is_active INTEGER DEFAULT 1
);
```

#### chat_logs（AI 聊天記錄，v4.1 新增）

```sql
CREATE TABLE IF NOT EXISTS chat_logs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT    NOT NULL,
    user_message TEXT    NOT NULL,
    bot_reply    TEXT    NOT NULL,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

> 資料表由 `app.py` 啟動時自動建立（`CREATE TABLE IF NOT EXISTS`）。

#### line_replies（LINE 回覆表，v4.2 新增）

```sql
CREATE TABLE IF NOT EXISTS line_replies (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    reply_datetime       DATETIME NOT NULL,
    customer_line_name   TEXT     NOT NULL,
    inquiry_content      TEXT     NOT NULL,
    reply_store          TEXT     NOT NULL,
    reply_staff          TEXT     NOT NULL,
    is_resolved          BOOLEAN  DEFAULT 0,
    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_line_replies_datetime ON line_replies(reply_datetime);
CREATE INDEX IF NOT EXISTS idx_line_replies_store ON line_replies(reply_store);
CREATE INDEX IF NOT EXISTS idx_line_replies_staff ON line_replies(reply_staff);
CREATE INDEX IF NOT EXISTS idx_line_replies_resolved ON line_replies(is_resolved);
```

> 用途：記錄 LINE 官方帳號客戶回覆紀錄，4/1 正式啟用。

---

## 6. API 規格

### 6.1 API 基礎資訊

| 項目 | 內容 |
|------|------|
| **Base URL** | `http://localhost:9000` |
| **協定** | HTTP/HTTPS（透過 Cloudflare Tunnel） |
| **格式** | JSON |
| **認證** | 部分 API 需傳入 `staff_id` 或 `admin` 參數 |
| **Fallback** | 所有頁面具備 `buildDemoData()` 離線展示模式 |

### 6.2 認證 API

#### POST /api/auth/verify
驗證員工 PIN 碼

**請求**:
```json
{
  "pin": "1234"
}
```

**回應**:
```json
{
  "success": true,
  "user": {
    "id": 1,
    "name": "陳芷涵",
    "store": "豐原",
    "role": "主任"
  }
}
```

### 6.3 銷售相關 API

#### GET /api/sales/daily
取得本季每日銷售（門市部 + 業務部疊加）

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
    { "product_code": "P001", "product_name": "產品名稱", "quantity": 2, "price": 5000 }
  ],
  "salesperson": "林榮祺"
}
```

### 6.4 業績相關 API

#### GET /api/performance/department
取得部門業績（參數：year, month, period_type）

#### GET /api/performance/store
取得門市業績

#### GET /api/performance/personal
取得個人業績排名

#### GET /api/performance/business
取得業務部績效

#### GET /api/reports/monthly
取得月報表（參數：year, month, store）

### 6.5 需求表 API

#### GET /api/needs/latest
取得最新待處理需求表

#### POST /api/needs/batch
批次建立需求表

#### POST /api/needs/purchase / transfer / arrive / complete / cancel
需求表流程狀態更新

#### POST /api/needs/from_recommendation
從推薦備貨建立需求單

#### POST /api/needs/batch_from_recommendation
批次從推薦備貨建立需求單

### 6.6 客戶相關 API

#### GET /api/customer/search?q=
搜尋客戶（姓名/電話/編號）

#### GET /api/customer/detail/<customer_id>
取得客戶詳細資料

#### GET /api/customers/recent
取得最近新增客戶

#### POST /api/customers/create
建立新客戶（個人/公司/VIP）

### 6.7 產品相關 API

#### GET /api/products/search?q=
搜尋產品

#### GET /api/product/info?code=
取得產品詳細資訊（含各倉庫庫存）

#### POST /api/products/create
建立新產品

#### GET /api/suppliers/list
取得廠商列表

#### POST /api/suppliers/create
建立新廠商

### 6.8 庫存相關 API

#### GET /api/inventory/search?q=
搜尋庫存

#### GET /api/inventory/list
取得庫存列表

#### GET /api/inventory/product/<product_id>
取得特定產品庫存

### 6.9 員工管理 API

#### GET /api/staff/list
取得員工列表

#### POST /api/staff/create
建立員工（含 PIN 設定）

#### POST /api/staff/<id>/update
更新員工資料

#### POST /api/staff/<id>/status
切換員工啟用/停用狀態

### 6.10 LINE 回覆表 API

#### GET /api/line-replies
取得 LINE 回覆紀錄列表

**參數**:
- `page`: 頁碼（預設 1）
- `per_page`: 每頁筆數（預設 20）
- `start_date`: 開始日期（YYYY-MM-DD）
- `end_date`: 結束日期（YYYY-MM-DD）
- `store`: 門市篩選
- `staff`: 人員篩選
- `is_resolved`: 結案狀態（true/false）
- `search`: 搜尋客戶名稱或內容

**回應**:
```json
{
  "success": true,
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "total_pages": 5
  }
}
```

#### POST /api/line-replies
新增 LINE 回覆紀錄

**請求**:
```json
{
  "reply_datetime": "2025-04-01T10:30:00",
  "customer_line_name": "客戶名稱",
  "inquiry_content": "提問內容",
  "reply_store": "潭子門市",
  "reply_staff": "張永承",
  "is_resolved": false
}
```

#### GET /api/line-replies/<id>
取得單筆回覆紀錄

#### PUT /api/line-replies/<id>
更新回覆紀錄

#### DELETE /api/line-replies/<id>
刪除回覆紀錄

#### GET /api/line-replies/stats/store/<store>
取得門市統計（回覆量、結案率）

#### GET /api/line-replies/stats/staff/<staff>
取得人員統計（處理量、結案率）

### 6.10 班表相關 API

#### GET /api/roster/weekly
取得本週班表

#### GET /api/roster/today
取得今日班表

### 6.11 督導評分 API

#### POST /api/supervision/submit
提交督導評分（四大類加權）

**請求**:
```json
{
  "store": "豐原",
  "cleanliness": 88,
  "service_quality": 92,
  "display": 85,
  "workflow": 90,
  "date": "2026-03-26",
  "notes": "備註"
}
```

#### GET /api/supervision/history?store=&limit=
取得歷史評分記錄

### 6.12 會計 API

#### GET /api/accounting/summary?year=&month=
取得月度財務摘要（損益、應收帳款、帳齡分析）

### 6.13 獎金相關 API

#### GET /api/bonus/personal?year=&month=&staff_id=
取得個人獎金詳情

#### POST /api/admin/bonus-rules
儲存獎金規則設定

#### GET /api/admin/bonus-report?year=&month=
取得全公司獎金報表

#### POST /api/admin/bonus-approve-all
批次核准待審核員工獎金

### 6.14 公告 API

#### GET /api/announcements/list
取得公告列表

#### POST /api/announcements/create
建立公告

#### POST /api/announcements/<id>
更新公告

#### DELETE /api/announcements/<id>
刪除公告

#### POST /api/announcements/<id>/pin
切換置頂狀態

### 6.15 推薦備貨 API

#### GET /api/admin/recommended-products
取得推薦備貨清單（含緊迫度分析）

#### POST /api/admin/recommendation-rules
儲存推薦規則

#### POST /api/recommended-products/order
從推薦備貨頁面建立需求單

**請求參數：**
```json
{
  "items": [{"product_id": 1, "quantity": 5}],
  "requester": "黃柏翰",
  "department": "豐原"
}
```

**回應：**
```json
{
  "success": true,
  "message": "成功建立 1 筆備貨需求",
  "needs": [{
    "item_name": "產品名稱",
    "product_code": "CP-001",
    "quantity": 5
  }]
}
```

**功能特性：**
- 自動檢查重複需求（同一天、相同產品、相同申請人）
- 成功後發送 Telegram 通知給老闆
- 支援多筆商品同時提交

### 6.16 待建檔 API

#### GET /api/staging/list
取得所有待完成的客戶/產品/廠商

#### POST /api/staging/<id>/complete
標記項目為已完成

### 6.17 健康檢查 API

#### GET /api/health
基礎健康檢查

#### GET /api/health/db
資料庫連線狀態

#### GET /api/health/db_stats
資料庫統計（各表記錄數、大小）

#### GET /api/health/version
系統版本資訊（Python, Flask, Gunicorn, SQLite, port）

#### GET /api/health/logs
最近系統日誌

### 6.18 AI 聊天 API（v4.1 新增）

#### POST /api/chat
接收對話訊息，以 SSE 串流回傳 AI 回應；串流結束後將對話寫入 `chat_logs`。

**請求**:
```json
{
  "messages": [
    { "role": "user", "content": "如何查詢庫存？" }
  ],
  "session_id": "sess_1234567890_abc123"
}
```

**回應**（`text/event-stream`）:
```
data: {"token": "您"}
data: {"token": "可以"}
data: {"token": "前往"}
...
data: [DONE]
```

**錯誤回應**:
```
data: {"error": "Connection refused"}
data: [DONE]
```

| 參數 | 類型 | 說明 |
|------|------|------|
| `messages` | array | OpenAI 格式對話陣列（`role` + `content`） |
| `session_id` | string | 前端 sessionStorage 產生的識別碼，用於 DB 分組 |

**注意事項**:
- System prompt 由後端固定注入，不需前端傳入
- `<think>…</think>` 在後端寫入 DB 前已過濾，前端亦做一次過濾
- 需要 Gunicorn `gthread` worker + `timeout=180`，`sync` worker 會讓串流被 SIGKILL

### 6.19 API 完整清單

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | /api/health | 健康檢查 |
| GET | /api/health/db | DB 狀態 |
| GET | /api/health/db_stats | DB 統計 |
| GET | /api/health/version | 版本資訊 |
| GET | /api/health/logs | 系統日誌 |
| POST | /api/auth/verify | 驗證 PIN |
| GET | /api/sales/daily | 每日銷售 |
| GET | /api/sales/daily/store | 門市部銷售 |
| GET | /api/sales/daily/by-store | 各門市銷售 |
| POST | /api/sales/create | 建立銷貨單 |
| GET | /api/sales/list | 銷售列表 |
| GET | /api/performance/department | 部門業績 |
| GET | /api/performance/store | 門市業績 |
| GET | /api/performance/personal | 個人業績 |
| GET | /api/performance/business | 業務部績效 |
| GET | /api/reports/monthly | 月報表 |
| GET | /api/roster/weekly | 本週班表 |
| GET | /api/roster/today | 今日班表 |
| GET | /api/store/supervision | 督導評分總覽 |
| POST | /api/supervision/submit | 提交評分 |
| GET | /api/supervision/history | 歷史評分 |
| GET | /api/needs/latest | 最新需求表 |
| GET | /api/needs/recent | 近期需求表 |
| GET | /api/needs/history | 需求表歷史 |
| POST | /api/needs/batch | 批次建立需求 |
| POST | /api/needs/cancel | 取消需求 |
| POST | /api/needs/purchase | 標記已採購 |
| POST | /api/needs/transfer | 標記已調撥 |
| POST | /api/needs/arrive | 標記已到貨 |
| POST | /api/needs/complete | 標記已完成 |
| POST | /api/needs/from_recommendation | 從推薦建立需求 |
| POST | /api/needs/batch_from_recommendation | 批次推薦需求 |
| GET | /api/customer/search | 搜尋客戶 |
| GET | /api/customer/detail/<id> | 客戶詳情 |
| GET | /api/customers/recent | 最近新增客戶 |
| POST | /api/customers/create | 建立客戶 |
| GET | /api/products/search | 搜尋產品 |
| GET | /api/product/info | 產品資訊 |
| POST | /api/products/create | 建立產品 |
| GET | /api/suppliers/list | 廠商列表 |
| POST | /api/suppliers/create | 建立廠商 |
| GET | /api/inventory/search | 搜尋庫存 |
| GET | /api/inventory/list | 庫存列表 |
| GET | /api/staff/list | 員工列表 |
| POST | /api/staff/create | 建立員工 |
| POST | /api/staff/<id>/update | 更新員工 |
| POST | /api/staff/<id>/status | 切換狀態 |
| GET | /api/accounting/summary | 會計摘要 |
| GET | /api/bonus/personal | 個人獎金 |
| POST | /api/admin/bonus-rules | 儲存獎金規則 |
| GET | /api/admin/bonus-report | 獎金報表 |
| POST | /api/admin/bonus-approve-all | 批次核准獎金 |
| GET | /api/announcements/list | 公告列表 |
| POST | /api/announcements/create | 建立公告 |
| POST | /api/announcements/<id> | 更新公告 |
| DELETE | /api/announcements/<id> | 刪除公告 |
| POST | /api/announcements/<id>/pin | 切換置頂 |
| GET | /api/admin/recommended-products | 推薦備貨清單 |
| POST | /api/admin/recommendation-rules | 儲存推薦規則 |
| GET | /api/staging/list | 待建檔列表 |
| POST | /api/staging/<id>/complete | 完成建檔 |
| GET | /api/system/announcements | 首頁公告 |
| GET | /api/google-reviews | Google 評論 |
| GET | /api/google-reviews/stats | 評論統計 |
| GET | /api/notification-status | 通知狀態 |
| **POST** | **/api/chat** | **AI 聊天串流（SSE，v4.1）** |
| GET | /api/line-replies | LINE 回覆列表（v4.2） |
| POST | /api/line-replies | 新增 LINE 回覆（v4.2） |
| GET | /api/line-replies/<id> | 取得單筆回覆（v4.2） |
| PUT | /api/line-replies/<id> | 更新回覆（v4.2） |
| DELETE | /api/line-replies/<id> | 刪除回覆（v4.2） |
| GET | /api/line-replies/stats/store/<store> | 門市統計（v4.2） |
| GET | /api/line-replies/stats/staff/<staff> | 人員統計（v4.2） |

---

## 7. UI/UX 設計說明

### 7.1 設計理念

**v4.0 設計核心——溫潤極簡**:

v4.0 捨棄 v3.2 的暗色霓虹/玻璃擬態風格，改採溫潤極簡美學。靈感來自日本文具的紙質觸感與台灣老字號的溫暖質地，以米白底色配合品牌黃強調，在視覺上減少疲勞感，並與 COSH 品牌個性更加貼近。

### 7.2 色彩系統

#### 頁面基礎色

| 色彩名稱 | 色碼 | CSS 變數 | 用途 |
|----------|------|----------|------|
| 頁面背景 | `#f5f0e8` | `--bg-page` | 所有頁面背景（米白） |
| Sidebar 背景 | `#eee8dd` | `--bg-sidebar` | 側邊欄（淺駝） |
| 卡片背景 | `#ffffff` | `--bg-card` | 卡片/面板白底 |
| 輸入框背景 | `#faf7f2` | `--bg-input` | 表單輸入框 |
| 邊框 | `#e0d8cc` | `--border` | 卡片邊框、分隔線 |

#### 文字色

| 色彩名稱 | 色碼 | 用途 |
|----------|------|------|
| 主要文字 | `#2c2720` | 標題、內文、數值 |
| 次要文字 | `#6b6158` | 說明文字、副標題 |
| 說明文字 | `#9a9188` | 提示、標籤、日期 |

#### 品牌強調色

| 色彩名稱 | 色碼 | 用途 |
|----------|------|------|
| 品牌黃 | `#FABF13` | 按鈕、強調、active 狀態 |
| 品牌黑 | `#231815` | 品牌黃按鈕上的文字色 |

#### 門市識別色（v4.0 重新定義）

| 門市 | v3.2 舊色碼 | v4.0 新色碼 | 說明 |
|------|-------------|-------------|------|
| 豐原 | `#ff9800` | `#d4780a` | 同色系，低彩度溫潤版 |
| 潭子 | `#9c27b0` | `#7b4fa0` | 同色系，低彩度溫潤版 |
| 大雅 | `#4caf50` | `#2d7a3a` | 同色系，低彩度溫潤版 |
| 業務 | — | `#1a5276` | 新增業務部識別色（深藍） |

#### 語意狀態色

| 色彩名稱 | 色碼 | 用途 |
|----------|------|------|
| 成功 | `#27ae60` | 確認、完成狀態 |
| 危險 | `#e74c3c` | 刪除、警告 |
| 警告 | `#e67e22` | 注意、高需求 |
| 資訊 | `#3498db` | 一般提示 |

### 7.3 字體系統

| 用途 | 字體 | 字重 | 說明 |
|------|------|------|------|
| 中文主要字體 | Noto Serif TC | 200, 300, 400 | 帶有人文書卷氣息 |
| 裝飾英文 | Cormorant Garamond | 300, 400 | 用於 logo 英文、頁首裝飾字 |
| 數值（等寬） | 繼承 Noto Serif TC | — | font-feature-settings: 'tnum' |

> **設計說明**: v3.2 使用無襯線 Inter + JetBrains Mono（科技感）；v4.0 改用細明體系 Noto Serif TC（人文感），以低字重（200–300）呈現輕盈質感。

### 7.4 PIN 登入組件 v4.0

**檔案**: `shared/auth_ui.js` + `auth_ui.css`

**設計特色**:
- 米白底色卡片，柔和陰影
- 品牌黃強調色（focus border、按鈕）
- 4 位 PIN 數字輸入（無 username 欄位）
- 依 `staff` 表 `is_active=1` 驗證
- 登入後將 `erp_user` 物件存入 localStorage/sessionStorage
- 不同角色可看到不同的 sidebar 選項

**使用方式**:
```javascript
// 每頁引入並呼叫
initSidebar('sidebar-placeholder', '../'); // admin/ 頁面路徑前綴為 '../'
requireAuth(); // 未登入自動顯示 PIN 輸入視窗
```

### 7.5 側邊欄導航 (sidebar-nav.js)

**設計特色**:
- 左側固定，背景 `#eee8dd`（淺駝）
- 摺疊/展開動畫
- 角色可見性控制（老闆/主任/會計/全員）
- 當前頁面高亮（品牌黃左 border）
- 分組：業績 / 操作 / 查詢 / 主管 / 建檔 / 管理後台

**admin/ 頁面注意事項**:
```javascript
initSidebar('sidebar-placeholder', '../'); // 路徑前綴需傳入 '../'
```

### 7.6 頁面布局規範

#### 標準頁面結構

```html
<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <title>頁面標題 — COSH ERP</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@200;300;400&family=Cormorant+Garamond:wght@300;400&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="shared/global.css">
  <style>
    body { display:flex; min-height:100vh; background:#f5f0e8; color:#2c2720; font-family:'Noto Serif TC',serif; }
    .main { flex:1; padding:2rem 2.5rem; overflow-y:auto; }
  </style>
</head>
<body>
  <div id="sidebar-placeholder"></div>
  <div class="main">
    <!-- 頁面內容 -->
  </div>
  <script src="shared/sidebar-nav.js"></script>
  <script src="shared/auth_ui.js"></script>
  <script>
    initSidebar('sidebar-placeholder');
    requireAuth();
    // ... 頁面邏輯
  </script>
</body>
</html>
```

### 7.7 元件尺寸規格

#### 按鈕（Button）

| 等級 | padding | border-radius | font-size | 適用場景 |
|------|---------|---------------|-----------|----------|
| 小型 | `0.25rem 0.65rem` | `6px` | `0.72rem` | 表格行內操作 |
| 標準 | `0.55rem 1.4rem` | `8px` | `0.85rem` | 主要操作按鈕 |
| 大型 | `0.7rem 2rem` | `8px` | `0.9rem` | 表單送出、主要 CTA |

**顏色語意**:
- 主要操作 → `background:#FABF13; color:#231815`
- 取消/次要 → `border:1px solid #e0d8cc; color:#6b6158; background:none`
- 危險 → `border:1px solid #e74c3c; color:#e74c3c`（hover 實心紅）

#### 輸入框（Input / Select / Textarea）

| 屬性 | 值 |
|------|----|
| `padding` | `0.55rem 0.8rem` |
| `border-radius` | `8px` |
| `font-size` | `0.85rem` |
| `border` | `1px solid #e0d8cc` |
| `background` | `#faf7f2` |
| `:focus border` | `#FABF13` |
| `:focus background` | `#ffffff` |

### 7.8 圖表設計

v4.0 全面使用純 SVG 或 CSS 自製圖表，不引入外部 Chart.js 等函式庫，以確保載入速度與離線相容性。

**常見圖表元件**:
- **橫條圖**: `<div>` + CSS `width` 百分比動畫（`transition:width .6s ease`）
- **折線圖**: 純 SVG `<polyline>` + `<circle>` 數據點（viewport 500px）
- **圓餅/環圖**: SVG `<circle>` + `stroke-dasharray`
- **迷你 sparkline**: 純 SVG 480×50 viewport 折線

**門市顏色**（圖表用，同識別色）:
- 豐原 `#d4780a` / 潭子 `#7b4fa0` / 大雅 `#2d7a3a` / 業務 `#1a5276`

### 7.9 API Fallback 模式

所有頁面必須能在伺服器不可用時正常展示：

```javascript
async function loadData() {
  try {
    const r = await fetch('/api/...');
    const data = await r.json();
    render(data);
  } catch (e) {
    render(buildDemoData()); // 內嵌假資料 fallback
  }
}
```

**原則**: `buildDemoData()` 要有代表性的假資料（含各種狀態、數值分佈），頁面需能完整展示所有功能。

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
| `google_reviews_parser.py` | Google 評論抓取 | 00:00 |
| `msi_inventory_report.py` | 微星庫存週報 | 每週一 12:00 |
| `roster_parser.py` | 班表資料匯入 | 10:55 |
| `performance_parser.py` | 績效資料匯入 | 11:00 |
| `supervision_parser.py` | 督導評分匯入 | 11:10 |
| `service_record_parser.py` | 服務記錄匯入 | 11:15 |
| `needs_parser.py` | 需求表同步 | 每 10 分鐘（9–21 點） |

### 8.2 Cron 排程

```bash
# 主要排程項目
04:00         數據備份 (auto_backup.sh)
05:00         記憶備份
06:00         系統自動重開機
10:30–11:15   Parser 批次執行
*/10 9-21     需求表同步（白天）
0 22-23,0-8   需求表同步（晚上）
00:00         Google 評論抓取
12:00 (週一)  微星庫存週報
```

### 8.3 備份策略

| 項目 | 時間 | 位置 |
|------|------|------|
| 資料庫備份 | 每日 04:00 | `~/srv/db/backups/` |
| 記憶檔備份 | 每日 05:00 | `~/srv/backup/` |
| OneDrive 同步 | 即時 | `~/srv/sync/OneDrive/` |

### 8.4 系統監控

**健康檢查端點（v4.0 強化版）**:
- `/api/health` — 基礎狀態
- `/api/health/db` — 資料庫連線
- `/api/health/db_stats` — 各表記錄數、DB 大小
- `/api/health/version` — Python/Flask/Gunicorn/SQLite 版本
- `/api/health/logs` — 最近 12 條日誌

**health_check.html 功能**:
- 7 端點自動健檢（`Promise.allSettled`）、延遲顯示
- 30 秒自動刷新
- 啟動以來 uptime 計數器

### 8.5 Gunicorn 設定（v4.1 更新）

AI 串流要求 Gunicorn 使用 `gthread` worker，`sync` worker 搭配短 timeout 會讓 SSE 串流被 SIGKILL 終止。

```python
# gunicorn.conf.py
worker_class = "gthread"   # 必須，SSE 串流用
threads     = 4
timeout     = 180          # 180s，讓 AI 串流有足夠時間完成
workers     = 4
bind        = "127.0.0.1:9000"
```

---

## 9. Telegram Bot 與通知

### 9.1 Bot 資訊

| 項目 | 內容 |
|------|------|
| **Bot 名稱** | 通知機器人 |
| **用途** | 需求表通知、庫存週報、系統告警 |

### 9.2 通知對象

| 類型 | 發送方式 | 接收對象 |
|------|----------|----------|
| 請購通知 | Telegram Bot | Alan（老闆） |
| 調撥通知 | Telegram Bot | 會計（黃環馥） |
| 系統告警 | Telegram Bot | Alan（老闆） |
| 微星週報 | Telegram Bot | Alan（老闆） |

### 9.3 群組

| 群組名稱 | 用途 |
|----------|------|
| 電腦舖工作群組 | 群組通知 |

### 9.4 通知格式範例

**需求表通知**:
```
📋 新請購單

產品：微軟 OFFICE 2024 家用盒裝版
數量：5
部門：豐原門市
填表人：林榮祺
時間：2026-03-26 10:30
```

**微星庫存週報**:
```
📊 微星庫存週報

統計日期：2026-03-24
總品項數：156
總庫存值：NT$ 2,450,000

（附 CSV 檔案）
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
| ERP v4.0 系統 | `/Users/aiserver/srv/web-site/computershop-erp/電腦舖ERP系統/` |
| 資料庫（來源） | `/Users/aiserver/srv/db/company.db` |
| 資料庫（v4.0 讀取） | `./db/company.db`（app.py 相對路徑） |
| Parser | `/Users/aiserver/srv/parser/` |
| 日誌 | `/Users/aiserver/srv/logs/` |
| OneDrive 同步 | `/Users/aiserver/srv/sync/OneDrive/ai_source/` |
| 備份 | `/Users/aiserver/srv/db/backups/` |

### 10.3 常用指令

```bash
# 啟動 ERP v4.0
cd /Users/aiserver/srv/web-site/computershop-erp/電腦舖ERP系統
gunicorn -c gunicorn.conf.py app:app

# 手動執行 Parser
cd /Users/aiserver/srv/parser
python3 inventory_parser.py
python3 sales_parser_v22.py

# 查看日誌
tail -f /Users/aiserver/srv/logs/app.log

# 資料庫備份
cp /Users/aiserver/srv/db/company.db /Users/aiserver/srv/db/backups/company_$(date +%Y%m%d).db

# 複製舊系統 .env（如需要 email 功能）
cp /Users/aiserver/.openclaw/workspace/dashboard-site/.env \
   /Users/aiserver/srv/web-site/computershop-erp/電腦舖ERP系統/.env
```

### 10.4 版本歷史

| 版本 | 日期 | 主要更新 |
|------|------|----------|
| v1.0 | 2026-02-20 | 系統初始建立 |
| v2.0 | 2026-03-01 | Admin Dashboard 完整功能 |
| v3.0 | 2026-03-16 | 系統正名 ERP、Google 評論自動化、獎金系統 |
| v3.1 | 2026-03-18 | 前端視覺優化：導入 CIS 品牌黃色系、修正選單搜尋 Bug |
| v3.2 | 2026-03-18 | 全系統色彩清掃（35 檔案）、按鈕/輸入框規格統一 |
| **v4.0** | **2026-03-21～26** | **完整前端重建：溫潤極簡設計系統、Noto Serif TC 字體、port 9000、PIN 認證、30 頁全數重建** |
| **v4.1** | **2026-03-26** | **AI 聊天機器人：oMLX Qwen3 SSE 串流、浮動視窗、多輪對話、chat_logs DB、Gunicorn gthread** |
| **v4.2** | **2026-03-27** | **LINE 回覆表：line_replies 資料表、列表/編輯頁面、6組 API、選單整合** |

### 10.5 v4.0 重建頁面統計

| 分類 | 頁面數 | 說明 |
|------|--------|------|
| 基礎建設（shared） | 4 | global.css, sidebar-nav.js, auth_ui.js, chat-widget.js |
| 業績儀表板 | 5 | index, department, store, personal, business |
| 控制台 | 1 | boss.html |
| 表單操作 | 3 | query, quote_input, needs_input |
| 查詢類 | 3 | inventory_query, customer_search, roster |
| 主管/管理 | 4 | supervision_score, monthly_report, recommended_products, bonus_personal |
| 建檔/後台 | 7 | customer_create, product_create, supplier_create, staging_center_v2, Accountants, staff_admin, health_check |
| 管理後台（admin/） | 4 | bonus_rules, bonus_report, announcement_management, recommended_products |
| 工作紀錄 | 2 | line_replies, line_replies_edit |
| **合計** | **32** | — |

### 10.6 聯絡資訊

| 項目 | 內容 |
|------|------|
| **系統管理員** | Alan（黃柏翰） |
| **AI 協作** | Yvonne（Cowork）|
| **ERP v4.0 網址** | http://localhost:9000 |
| **GitHub Repo** | https://github.com/han5211tw-ai/ai.git |

---

**文件結束**

*本文件由 Yvonne 自動生成，更新於 2026-03-27*
