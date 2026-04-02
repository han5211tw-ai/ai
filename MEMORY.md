# MEMORY.md - Yvonne's Knowledge Index
_主索引檔案 - 快速查找與關鍵規則_

## 📚 主題分類索引

| 主題 | 檔案路徑 | 內容概要 |
|------|----------|----------|
| **系統架構** | [memory/system-architecture.md](memory/system-architecture.md) | 主機環境、目錄結構、核心檔案 |
| **資料來源** | [memory/data-sources.md](memory/data-sources.md) | OneDrive 資料夾、檔案格式 |
| **ERP 營運系統** | [memory/ERP-system.md](memory/ERP-system.md) | ERP 營運系統（原 Dashboard）、API、頁面結構 |
| **Parser 系統** | [memory/parser-system.md](memory/parser-system.md) | 所有 Parser 腳本、功能說明 |
| **資料庫** | [memory/database-schema.md](memory/database-schema.md) | 資料表結構、欄位定義 |
| **排程任務** | [memory/cron-schedule.md](memory/cron-schedule.md) | Cron 時間表、自動化流程 |
| **組織架構** | [memory/organization-rules.md](memory/organization-rules.md) | 門市結構、業績計算規則 |
| **外部服務** | [memory/external-services.md](memory/external-services.md) | Telegram、API 金鑰 |

---

## 🚨 關鍵規則（必須遵守）

詳見各分檔：
- [系統架構](memory/system-architecture.md)
- [資料安全](memory/data-sources.md#資料安全)
- [資料庫操作](memory/database-schema.md#資料庫操作)
- [排程任務](memory/cron-schedule.md#排程規則)

### 📋 工作記錄歸檔規則

- **MEMORY.md 主檔**只保留索引與關鍵規則，不存放詳細工作內容
- **每日工作** → 歸檔至 `memory/YYYY-MM-DD.md`
- **主題分類** → 歸檔至對應主題分檔（如 parser-system.md、dashboard-system.md 等）
- **對話總結** → 依照內容主題歸檔至對應分檔，不在主檔留存

### 💬 錯誤訊息處理規則

- **技術性錯誤訊息**（如 `Missing required parameter`、`Edit failed` 等）**不要發送到 Telegram**
- **只回報重要錯誤**：系統級故障、資料遺失、安全問題等
- 遇到技術錯誤時，自行修復或記錄到日誌即可，不要打擾用戶

### 🎨 前端開發規則（2026-03-27 確立）

**黃金法則**：所有新頁面必須繼承 `base.html`，使用共用樣式與元件。

| 規則 | 說明 |
|------|------|
| 模板 | 一律使用 Jinja2 `{% extends "base.html" %}` |
| 樣式 | 使用 `shared/global.css`，禁止獨立 CSS |
| 元件 | 側邊欄、登入驗證由系統提供 |
| 按鈕 | 使用 `.btn` 類別，禁止自定義樣式 |
| 路由 | 無副檔名（如 `/line_replies` 而非 `/line_replies.html`）|

**教訓**：v4.2 LINE 回覆表初期未遵守此規則，導致樣式不一致、登入機制不相容，需全面重寫。

---

## 📅 日誌檔案

| 日期 | 檔案 | 內容 |
|------|------|------|
| 2026-02-20 | `memory/2026-02-20.md` | 首次設定、Parser 建立 |
| 2026-02-21 | `memory/2026-02-21.md` | 看板完成、週報系統 |
| 2026-02-22 | `memory/2026-02-22.md` | 主管控制台、督導評分 |
| 2026-02-26 | `memory/2026-02-26.md` | 銷售系統重構、人員編制確認、自動化設定 |
| **2026-03-01** | **`memory/2026-03-01.md`** | **Admin Dashboard 完整功能上線** - 10個資料頁面、查看修復、UI調整、健康檢查修復 |
| 2026-03-02 | `memory/2026-03-02.md` | 待建檔中心與 A2 稽核排除已取消 needs |
| **2026-03-03** | **`memory/2026-03-03.md`** | **登入介面統一化、產品主檔合併、主管權限修正** |
| **2026-03-04** | **`memory/2026-03-04.md`** | **系統架構 V3、登入組件 v2.0、員工管理、系統公告** |
| 2026-03-05 | `memory/2026-03-05.md` | 需求表四階段流程、監控機制、權限密碼認證 |
| **2026-03-08** | **`memory/2026-03-08.md`** | **RWD 響應式選單、權限系統修復** |
| 2026-03-09 | `memory/2026-03-09.md` | 公告管理重構、逾期收貨提醒、Telegram 崩潰修復 |
| 2026-03-10 | `memory/2026-03-10.md` | 督導評分存檔修復 |
| 2026-03-11 | `memory/2026-03-11.md` | Yvonne 專用 Email、中文 TTS 安裝 |
| 2026-03-12 | `memory/2026-03-12.md` | 電腦舖官網部署 (Port 8000) |
| **2026-03-13** | **`memory/2026-03-13.md`** | **推薦備貨商品、銷售獎金計算功能** |
| **2026-03-16** | **`memory/2026-03-16.md`** | **Google 商家五星評論自動化、微星庫存週報、系統正名 ERP** |
| **2026-03-18** | **`memory/2026-03-18.md`** | **ERP 營運系統專案白皮書** - 完整技術文件 41.6KB |
| 2026-03-18 | `memory/2026-03-18.md` | 修復首頁「已到貨」按鈕、OpenClaw Browser 測試、官網 Deploy Key、ERP Repo 重新命名 |
| **2026-03-23** | **`memory/2026-03-23.md`** | **每日晨報自動化系統** - 每天早上十點自動發送天氣/班表/業績/新聞到 Telegram 工作群組 |
| **2026-03-26** | **`memory/2026-03-26.md`** | **ERP AI 聊天機器人** - oMLX Qwen3.5-9B-6bit、SSE 串流、即時資料庫查詢、推薦備貨修復 |
| 持續更新 | `memory/2026-MM-DD.md` | 每日工作記錄 |
| **2026-03-27** | **`memory/2026-03-27.md`** | **LINE 官方帳號回覆表** - 完整功能上線、前端開發規則確立、白皮書 v4.2 更新 |
| **2026-03-28** | **`memory/2026-03-28.md`** | **ERP v2 Step 5 完成** - 外勤服務紀錄、班表查詢、班表輸入（25頁完成） |
| 2026-03-29 | `memory/2026-03-29.md` | 晨報「更多詳情」按鈕修復 - 改由通知機器人直接發送，避免 Agent 帳號產生互動元素 |
| 2026-04-01 | `memory/2026-04-01.md` | 績效考核系統修正 - 業務同仁顯示、主管試算獎金、會計/主管 KPI 人工評分 |
| **2026-04-02** | **`memory/2026-04-02.md`** | **銷貨輸入編輯功能實作** - 取消 ERP-v2 同步、銷貨資料修正、完整編輯功能上線 |

---

## 🔍 快速查找

### 常見任務速查

**更新看板資料**
```bash
cd /Users/aiserver/srv/parser
python3 inventory_parser.py  # 庫存
python3 sales_parser.py      # 銷貨
python3 performance_parser.py # 績效
```

**重啟 Dashboard**
```bash
pkill -f "python3 app.py"
cd /Users/aiserver/.openclaw/workspace/dashboard-site
python3 app.py
```

**查看排程狀態**
```bash
crontab -l
```

---

## 📞 緊急聯絡

- **Telegram Bot**: @alanhuangbot
- **看板 URL**: http://localhost:3000
- **資料庫路徑**: `/Users/aiserver/srv/db/company.db`

---

_最後更新: 2026-04-02_
_維護者: Yvonne_
