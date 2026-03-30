# Skill Specification: purchase-request-manager

## 概述

**名稱:** purchase-request-manager  
**版本:** 1.0.0  
**作者:** 電腦舖 (Computer Shop)  
**授權:** MIT  
**適用產業:** 零售業、批發業、需要進貨/調撥管理的企業  

**一句話描述:** 完整的請購/調撥/新品需求管理系統，四階段流程追蹤，自動通知，逾期提醒。

---

## 功能清單

| 功能 | 指令範例 | 說明 |
|------|---------|------|
| **提交需求單** | 「我要請購 10 台 RTX 4060」 | 建立請購單 |
| **調撥申請** | 「從豐原調 5 台筆電到潭子」 | 門市間調撥 |
| **新品申請** | 「申請新品 iPhone 16」 | 建立新品需求 |
| **查詢需求表** | 「查我的需求單」 | 查詢個人/部門需求單狀態 |
| **取消需求** | 「取消昨天那筆需求」 | 30 分鐘內可取消 |
| **逾期提醒** | 「哪些需求還沒到貨」 | 調撥 3 天/請購 5 天未收貨提醒 |
| **統計報表** | 「這個月請購統計」 | 依部門/人員/狀態統計 |

---

## 四階段流程

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ 待處理  │ → │ 已採購  │ → │ 已調撥  │ → │ 已完成  │
│ (NEW)   │    │ (BUY)   │    │ (MOVE)  │    │ (DONE)  │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
     ↑                                              │
     └──────────── 可取消 ──────────────────────────┘
                    (30分鐘內)
```

**狀態說明：**

| 狀態 | 顏色 | 說明 |
|------|------|------|
| 待處理 | 🟡 黃色 | 剛提交，等待處理 |
| 已採購 | 🔵 藍色 | 已下單採購，等待到貨 |
| 已調撥 | 🟣 紫色 | 已從其他門市調出 |
| 已完成 | 🟢 綠色 | 已收貨完成 |
| 已取消 | ⚪ 灰色 | 已取消（30分鐘內）|

---

## 資料表結構

```sql
-- 需求主表
CREATE TABLE needs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    product_code TEXT,
    product_name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    requester TEXT NOT NULL,
    request_type TEXT NOT NULL,  -- '請購' | '調撥' | '新品'
    transfer_from TEXT,          -- 調撥來源門市
    transfer_to TEXT,            -- 調撥目標門市
    customer_info TEXT,          -- 客戶編號或需求用途
    status TEXT DEFAULT '待處理', -- 狀態
    remark TEXT,                 -- 備註
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, product_code, quantity, requester)
);

-- 產品暫存表（新品用）
CREATE TABLE staging_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    suggested_vendor TEXT,
    estimated_cost REAL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 通知記錄表
CREATE TABLE notification_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    need_id INTEGER,
    notification_type TEXT,  -- 'telegram' | 'email'
    recipient TEXT,
    message TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 安裝方式

### ClawHub 安裝

```bash
npx clawhub@latest install purchase-request-manager
```

### 手動安裝

```bash
git clone https://github.com/computershop/purchase-request-manager.git
cd purchase-request-manager
openclaw skills install .
```

---

## 設定檔

**檔案位置:** `~/.openclaw/skills/purchase-request-manager/config.json`

```json
{
  "database": {
    "path": "/path/to/company.db",
    "type": "sqlite"
  },
  "business_rules": {
    "cancel_window_minutes": 30,
    "overdue_alert": {
      "transfer": 3,
      "purchase": 5
    },
    "stores": ["豐原", "潭子", "大雅"],
    "approval_required": {
      "amount_threshold": 50000,
      "roles": ["老闆", "主管"]
    }
  },
  "notifications": {
    "telegram": {
      "enabled": true,
      "bot_token": "${TELEGRAM_BOT_TOKEN}",
      "channels": {
        "purchase": "8545239755",      -- 請購通知給老闆
        "transfer": "8203016237",      -- 調撥通知給會計
        "general": "-5232179482"       -- 一般通知給群組
      }
    }
  },
  "parser": {
    "enabled": true,
    "source_path": "~/srv/sync/OneDrive/ai_source/needs/",
    "schedule": {
      "sync_interval": "10m"  -- 每10分鐘同步
    }
  }
}
```

---

## 使用範例

### 提交請購單

**使用者:** 「請購 10 台微星 RTX 4060，客戶張先生要」

**AI 回覆:**
```
✅ 需求單已建立

📋 單號：PR-20260317001
📅 日期：2026/03/17
📦 產品：微星 RTX 4060
🔢 數量：10
👤 申請人：王小明
📝 用途：客戶張先生
⏱️ 狀態：待處理

💡 30 分鐘內可輸入「取消 PR-20260317001」取消
```

### 調撥申請

**使用者:** 「從豐原調 5 台筆電到潭子，門市展示用」

**AI 回覆:**
```
✅ 調撥單已建立

📋 單號：TR-20260317002
📦 產品：筆記型電腦
🔢 數量：5
🏪 來源：豐原門市
🏪 目標：潭子門市
📝 用途：門市展示用
⏱️ 狀態：待處理

📢 已通知會計處理調撥
```

### 查詢需求單

**使用者:** 「查我這個月的需求單」

**AI 回覆:**
```
📊 王小明 - 2026年3月 需求單統計

| 單號 | 類型 | 產品 | 數量 | 狀態 | 日期 |
|------|------|------|------|------|------|
| PR-001 | 請購 | RTX 4060 | 10 | 🟢 已完成 | 03/15 |
| TR-002 | 調撥 | 筆電 | 5 | 🔵 已採購 | 03/16 |
| PR-003 | 請購 | iPhone 16 | 3 | 🟡 待處理 | 03/17 |

📈 本月共 3 筆 | 已完成 1 | 進行中 2
```

### 逾期提醒

**使用者:** 「哪些需求還沒到貨」

**AI 回覆:**
```
⚠️ 逾期需求提醒

| 單號 | 類型 | 產品 | 申請日 | 逾期天數 | 負責人 |
|------|------|------|--------|----------|--------|
| PR-005 | 請購 | 記憶體 DDR5 | 03/10 | 2 天 | 採購部 |
| TR-003 | 調撥 | 螢幕 27吋 | 03/12 | 2 天 | 會計 |

💡 已發送提醒通知給相關人員
```

---

## 通知機制

### 自動通知觸發條件

| 事件 | 通知對象 | 通知方式 |
|------|---------|---------|
| 新請購單 | 老闆 | Telegram |
| 新調撥單 | 會計 | Telegram |
| 狀態變更 | 申請人 | Telegram |
| 逾期提醒 | 負責人 + 老闆 | Telegram |
| 每日統計 | 管理群組 | Telegram |

### 通知範本

**請購通知：**
```
🛒 新請購單

產品：微星 RTX 4060
數量：10
申請人：王小明
用途：客戶張先生

請至 ERP 系統處理：http://erp.local/needs
```

**調撥通知：**
```
🚚 新調撥單

產品：筆記型電腦
數量：5
來源：豐原門市
目標：潭子門市

請安排調撥作業
```

---

## 排程自動化

**內建 Cron 任務：**

| 時間 | 任務 | 說明 |
|------|------|------|
| 每 10 分鐘 | 需求表同步 | 從 Excel/OneDrive 匯入新需求 |
| 每日 09:00 | 逾期檢查 | 檢查逾期需求並發通知 |
| 每日 17:00 | 日報統計 | 發送當日需求統計 |
| 每週一 09:00 | 週報統計 | 上週需求完成率報告 |

---

## 權限控制

| 角色 | 權限 |
|------|------|
| **一般員工** | 提交需求、查詢自己的需求、30分鐘內取消 |
| **門市主管** | 查詢部門需求、核准調撥 |
| **會計** | 處理調撥、更新狀態 |
| **老闆** | 全部權限、查看報表、設定規則 |

---

## 相依套件

```json
{
  "dependencies": {
    "openclaw": ">=1.0.0",
    "sqlite3": "^5.1.6",
    "pandas": "^2.0.0",
    "openpyxl": "^3.1.0",
    "python-telegram-bot": "^20.0"
  }
}
```

---

## 常見問題

### Q1: 30分鐘後還能取消嗎？

**A:** 不能。超過 30 分鐘需聯絡主管或老闆手動處理。

### Q2: 可以批次提交多個產品嗎？

**A:** 可以。支援一次提交多個品項：
```
請購：
1. RTX 4060 x 5
2. DDR5 32GB x 10
3. SSD 1TB x 3
```

### Q3: 如何修改已提交的需求？

**A:** 30 分鐘內取消重送，或聯絡主管修改。

### Q4: 調撥和請購的差別？

**A:** 
- **調撥**：門市間移動現有庫存，速度快（1-2天）
- **請購**：向廠商進貨，時間較長（3-7天）

---

## 版本紀錄

| 版本 | 日期 | 更新內容 |
|------|------|---------|
| 1.0.0 | 2026-03-17 | 初始版本，四階段流程、逾期提醒、通知機制 |

---

## 聯絡與支援

- **作者:** 電腦舖 (Computer Shop)
- **Email:** ai@computershop.cc
- **GitHub:** https://github.com/computershop/purchase-request-manager
- **文件:** https://docs.computershop.cc/purchase-request-manager

---

## 授權條款

MIT License - 詳見 LICENSE 檔案

---

_最後更新: 2026-03-17_
