# Skill Specification: retail-erp-connector

## 概述

**名稱:** retail-erp-connector  
**版本:** 1.0.0  
**作者:** 電腦舖 (Computer Shop)  
**授權:** MIT  
**適用產業:** 電腦零售、3C 賣場、批發零售業  

**一句話描述:** 連接零售業 ERP 資料庫，讓 AI 助理能查庫存、查銷貨、查客戶、算業績。

---

## 功能清單

| 功能 | 指令範例 | 說明 |
|------|---------|------|
| **庫存查詢** | 「查 RTX 4060 庫存」 | 查詢產品在各倉庫的庫存量 |
| **產品搜尋** | 「找 Office 2024」 | 模糊搜尋產品名稱 |
| **銷貨紀錄** | 「查昨天銷貨」 | 查詢特定期間的銷貨明細 |
| **客戶查詢** | 「查客戶王小明」 | 查詢客戶基本資料與購買紀錄 |
| **業績計算** | 「這月業績多少」 | 計算個人/門市/部門業績與達成率 |
| **低庫存提醒** | 「哪些產品要補貨」 | 列出庫存低於安全量的產品 |

---

## 資料來源

**支援格式:**
- SQLite 資料庫 (`.db`)
- CSV 檔案 (透過 Parser 匯入)
- Excel 檔案 (`.xlsx`, `.xls`)

**預設資料表結構:**

```sql
-- 庫存表
CREATE TABLE inventory (
    product_id TEXT PRIMARY KEY,
    item_spec TEXT,
    warehouse TEXT,
    stock_quantity INTEGER,
    unit_cost REAL
);

-- 銷貨紀錄
CREATE TABLE sales_history (
    invoice_no TEXT,
    date TEXT,
    salesperson TEXT,
    product_name TEXT,
    quantity INTEGER,
    price REAL,
    amount REAL,
    customer_id TEXT
);

-- 客戶主檔
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    short_name TEXT,
    mobile TEXT,
    phone1 TEXT,
    company_address TEXT
);

-- 績效目標
CREATE TABLE performance_metrics (
    subject_name TEXT,
    target_amount REAL,
    revenue_amount REAL,
    achievement_rate REAL
);
```

---

## 安裝方式

### 方法一：ClawHub 安裝 (推薦)

```bash
npx clawhub@latest install retail-erp-connector
```

### 方法二：手動安裝

```bash
git clone https://github.com/computershop/retail-erp-connector.git
cd retail-erp-connector
openclaw skills install .
```

---

## 設定檔

**檔案位置:** `~/.openclaw/skills/retail-erp-connector/config.json`

```json
{
  "database": {
    "path": "/path/to/company.db",
    "type": "sqlite"
  },
  "parser": {
    "enabled": true,
    "schedule": {
      "inventory": "10:30",
      "sales": "10:40",
      "customers": "10:45"
    }
  },
  "notifications": {
    "telegram": {
      "enabled": true,
      "bot_token": "${TELEGRAM_BOT_TOKEN}",
      "chat_id": "${TELEGRAM_CHAT_ID}"
    }
  },
  "business_rules": {
    "low_stock_threshold": 5,
    "stores": ["豐原", "潭子", "大雅"],
    "departments": {
      "store": ["林榮祺", "林峙文", "劉育仕", "林煜捷", "張永承", "張家碩"],
      "business": ["鄭宇晉", "梁仁佑"]
    }
  }
}
```

---

## 環境變數

| 變數名稱 | 說明 | 必填 |
|---------|------|------|
| `ERP_DB_PATH` | 資料庫檔案路徑 | ✅ |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | ❌ |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID | ❌ |

---

## 使用範例

### 查庫存

**使用者:** 「查 RTX 4060 庫存」

**AI 回覆:**
```
📦 RTX 4060 庫存狀況

| 倉庫 | 數量 | 狀態 |
|------|------|------|
| 豐原 | 12 | ✅ 充足 |
| 潭子 | 3 | ⚠️ 偏低 |
| 大雅 | 0 | ❌ 缺貨 |

💡 建議：潭子門市可從豐原調撥 5 台
```

### 查業績

**使用者:** 「這個月業績」

**AI 回覆:**
```
📊 2026年3月 業績總覽

| 項目 | 目標 | 實際 | 達成率 |
|------|------|------|--------|
| 門市部 | 300萬 | 245萬 | 81.7% |
| 業務部 | 200萬 | 180萬 | 90.0% |
| 全公司 | 500萬 | 425萬 | 85.0% |

🎯 距離月底還有 14 天，需再衝 75 萬
```

---

## 排程自動化

**內建 Cron 任務:**

| 時間 | 任務 | 說明 |
|------|------|------|
| 10:30 | 庫存匯入 | 從 CSV/Excel 更新庫存 |
| 10:40 | 銷貨匯入 | 匯入前一日銷貨資料 |
| 10:45 | 客戶匯入 | 更新客戶主檔 |
| 17:00 | 低庫存檢查 | 自動發送補貨提醒 |

---

## 相依套件

```json
{
  "dependencies": {
    "openclaw": ">=1.0.0",
    "sqlite3": "^5.1.6",
    "pandas": "^2.0.0",
    "openpyxl": "^3.1.0"
  }
}
```

---

## 常見問題

### Q1: 資料庫格式不同怎麼辦？

**A:** 可以在 `config.json` 中設定欄位對應：

```json
{
  "schema_mapping": {
    "inventory": {
      "product_id": "品號",
      "item_spec": "規格",
      "stock_quantity": "庫存數量"
    }
  }
}
```

### Q2: 可以支援其他資料庫嗎？

**A:** 目前支援 SQLite，未來版本將支援 MySQL、PostgreSQL。

### Q3: 如何備份資料？

**A:** Skill 會自動在 `~/backups/` 建立每日備份。

---

## 版本紀錄

| 版本 | 日期 | 更新內容 |
|------|------|---------|
| 1.0.0 | 2026-03-17 | 初始版本，支援 SQLite + CSV 匯入 |

---

## 聯絡與支援

- **作者:** 電腦舖 (Computer Shop)
- **Email:** ai@computershop.cc
- **GitHub:** https://github.com/computershop/retail-erp-connector
- **文件:** https://docs.computershop.cc/retail-erp-connector

---

## 授權條款

MIT License - 詳見 LICENSE 檔案

---

_最後更新: 2026-03-17_
