# Skill Specification: google-reviews-automation

## 概述

**名稱:** google-reviews-automation  
**版本:** 1.0.0  
**作者:** 電腦舖 (Computer Shop)  
**授權:** MIT  
**適用產業:** 有 Google 商家檔案的店家、重視線上評價的企業  

**一句話描述:** 自動抓取 Google 商家五星評論，解析通知信，統計評分趨勢，即時掌握店面口碑。

---

## 功能清單

| 功能 | 指令範例 | 說明 |
|------|---------|------|
| **評論統計** | 「這個月有幾則五星評論」 | 統計特定期間評論數量 |
| **評分趨勢** | 「最近評分趨勢」 | 查看評分變化圖表 |
| **最新評論** | 「最新的 Google 評論」 | 查看最新收到的評論 |
| **門市比較** | 「哪家門市評分最高」 | 多門市評分比較 |
| **負評提醒** | 「有沒有負評」 | 自動偵測 1-3 星評論並提醒 |
| **週報發送** | 「發送評論週報」 | 自動生成並發送評論統計 |
| **匯出報表** | 「匯出這個月評論」 | 匯出 Excel/CSV 報表 |

---

## 運作原理

```
Google 商家 → 新評論通知信 → Gmail
                                    ↓
                              [自動讀取]
                                    ↓
                         解析郵件內容（評分、內容、時間）
                                    ↓
                         寫入資料庫 + 發送 Telegram 通知
```

**資料來源：**
- Google 商家檔案的新評論通知信（寄到 Gmail）
- 透過 Gmail API 或 IMAP 讀取
- 解析郵件 HTML 內容，提取評論資訊

---

## 資料表結構

```sql
-- Google 評論主表
CREATE TABLE google_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id TEXT UNIQUE,           -- Google 評論唯一 ID
    store_name TEXT NOT NULL,        -- 門市名稱
    reviewer_name TEXT,              -- 評論者名稱
    reviewer_id TEXT,                -- 評論者 ID（去識別化）
    rating INTEGER NOT NULL,         -- 評分 1-5 星
    review_text TEXT,                -- 評論內容
    review_date TEXT,                -- 評論日期
    review_time TEXT,                -- 評論時間
    source_email_id TEXT,            -- 來源郵件 ID
    reply_text TEXT,                 -- 商家回覆內容
    reply_date TEXT,                 -- 回覆日期
    status TEXT DEFAULT 'new',       -- new | replied | flagged
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 評論統計表（每日彙整）
CREATE TABLE review_daily_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_name TEXT NOT NULL,
    stat_date TEXT NOT NULL,
    total_reviews INTEGER DEFAULT 0,
    five_star INTEGER DEFAULT 0,
    four_star INTEGER DEFAULT 0,
    three_star INTEGER DEFAULT 0,
    two_star INTEGER DEFAULT 0,
    one_star INTEGER DEFAULT 0,
    average_rating REAL,
    UNIQUE(store_name, stat_date)
);

-- 通知記錄表
CREATE TABLE review_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id TEXT,
    notification_type TEXT,          -- 'telegram' | 'email'
    recipient TEXT,
    message TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 郵件解析邏輯

### Gmail 通知信格式

Google 商家新評論通知信包含：
- 評論者名稱
- 評分（1-5 星）
- 評論內容
- 評論時間
- 門市名稱

### 解析流程

```python
1. 連接 Gmail (IMAP/API)
2. 搜尋未讀的 Google 通知信
   - Subject: "You have a new review on Google"
   - From: "Google My Business"
3. 解析郵件 HTML
4. 提取：評論者、評分、內容、時間、門市
5. 寫入資料庫
6. 標記郵件為已讀
7. 發送 Telegram 通知
```

---

## 安裝方式

### ClawHub 安裝

```bash
npx clawhub@latest install google-reviews-automation
```

### 手動安裝

```bash
git clone https://github.com/computershop/google-reviews-automation.git
cd google-reviews-automation
openclaw skills install .
```

---

## 設定檔

**檔案位置:** `~/.openclaw/skills/google-reviews-automation/config.json`

```json
{
  "database": {
    "path": "/path/to/company.db",
    "type": "sqlite"
  },
  "gmail": {
    "auth_method": "oauth2",  -- oauth2 | app_password
    "credentials_path": "~/.credentials/gmail_credentials.json",
    "token_path": "~/.credentials/gmail_token.json",
    "search_query": "from:noreply@google.com subject:'new review'",
    "check_interval": "1h"
  },
  "stores": [
    {
      "name": "豐原門市",
      "google_place_id": "ChIJ...",
      "notification_channel": "telegram"
    },
    {
      "name": "潭子門市",
      "google_place_id": "ChIJ...",
      "notification_channel": "telegram"
    },
    {
      "name": "大雅門市",
      "google_place_id": "ChIJ...",
      "notification_channel": "telegram"
    }
  ],
  "notifications": {
    "telegram": {
      "enabled": true,
      "bot_token": "${TELEGRAM_BOT_TOKEN}",
      "channels": {
        "new_review": "8545239755",      -- 新評論通知給老闆
        "negative_review": "8545239755", -- 負評立即通知
        "weekly_report": "-5232179482"   -- 週報發到群組
      }
    },
    "alert_threshold": {
      "negative_rating": 3,  -- 3 星以下立即通知
      "daily_summary": true  -- 每日統計
    }
  },
  "reports": {
    "weekly": {
      "enabled": true,
      "day": "monday",
      "time": "09:00"
    },
    "monthly": {
      "enabled": true,
      "day": 1,
      "time": "10:00"
    }
  }
}
```

---

## 使用範例

### 查評論統計

**使用者:** 「這個月有幾則五星評論」

**AI 回覆:**
```
⭐ Google 商家評論統計 - 2026年3月

| 門市 | 總評論 | 5星 | 4星 | 3星 | 2星 | 1星 | 平均分 |
|------|--------|-----|-----|-----|-----|-----|--------|
| 豐原 | 12 | 10 | 2 | 0 | 0 | 0 | 4.8 ⭐ |
| 潭子 | 8 | 6 | 1 | 1 | 0 | 0 | 4.6 ⭐ |
| 大雅 | 5 | 4 | 0 | 1 | 0 | 0 | 4.6 ⭐ |
| **合計** | **25** | **20** | **3** | **2** | **0** | **0** | **4.7** |

🎉 本月 5 星評論佔比 80%！
```

### 最新評論

**使用者:** 「最新的 Google 評論」

**AI 回覆:**
```
📝 最新 Google 評論

📍 豐原門市 - 3 小時前
⭐⭐⭐⭐⭐ (5/5)
👤 王小明
💬 「服務很好，老闆很專業，價格也公道。買的 RTX 4060 跑遊戲很順！」

---

📍 潭子門市 - 昨天
⭐⭐⭐⭐ (4/5)
👤 陳小姐
💬 「整體不錯，只是等貨時間比較久。不過品質沒問題。」

💡 輸入「回覆潭子-陳小姐」可協助撰寫回覆
```

### 負評提醒

**自動通知：**
```
⚠️ 負評提醒！

📍 大雅門市 - 剛剛
⭐⭐ (2/5)
👤 李先生
💬 「態度不好，問問題愛理不理」

🔴 建議盡快回覆處理
💬 輸入「建議回覆」查看建議回覆內容
```

### 評分趨勢

**使用者:** 「最近評分趨勢」

**AI 回覆:**
```
📈 Google 評分趨勢 (近 6 個月)

| 月份 | 豐原 | 潭子 | 大雅 | 平均 |
|------|------|------|------|------|
| 2025/10 | 4.5 | 4.3 | 4.2 | 4.3 |
| 2025/11 | 4.6 | 4.4 | 4.3 | 4.4 |
| 2025/12 | 4.7 | 4.5 | 4.4 | 4.5 |
| 2026/01 | 4.8 | 4.6 | 4.5 | 4.6 |
| 2026/02 | 4.8 | 4.7 | 4.6 | 4.7 |
| 2026/03 | 4.8 | 4.6 | 4.6 | 4.7 |

📊 趨勢：整體穩定上升 🟢
🏆 最佳門市：豐原 (4.8)
```

---

## 自動通知機制

### 即時通知

| 觸發條件 | 通知對象 | 內容 |
|---------|---------|------|
| 新 5 星評論 | 老闆 | 評論摘要 + 感謝提醒 |
| 新 4 星評論 | 老闆 | 評論摘要 |
| 新 3 星評論 | 老闆 | 評論摘要 + 建議回覆 |
| 新 1-2 星評論 | 老闆（立即）| 評論摘要 + 緊急提醒 |

### 定時報告

| 報告 | 時間 | 內容 |
|------|------|------|
| **日報** | 每日 21:00 | 當日新評論統計 |
| **週報** | 每週一 09:00 | 本週評論分析、趨勢圖 |
| **月報** | 每月 1 日 10:00 | 完整月報、門市比較 |

---

## 回覆建議功能

**使用者:** 「建議回覆潭子-陳小姐」

**AI 回覆:**
```
💬 建議回覆內容：

「陳小姐您好，感謝您的回饋！

關於等貨時間較長的部分，我們深感抱歉。
由於近期 RTX 4060 供貨較為緊張，
我們會持續跟廠商確認到貨時間，
並在第一時間通知您。

如有任何問題，歡迎隨時與我們聯繫。
再次感謝您的支持！

潭子門市 敬上」

---

✅ 已複製到剪貼簿
📋 可直接貼到 Google 商家後台回覆
```

---

## 排程自動化

**內建 Cron 任務：**

| 時間 | 任務 | 說明 |
|------|------|------|
| 每小時 | 檢查新郵件 | 讀取 Gmail 新評論通知 |
| 每日 21:00 | 日報發送 | 當日評論統計 |
| 每週一 09:00 | 週報發送 | 本週評論分析 |
| 每月 1 日 10:00 | 月報發送 | 完整月報 |
| 每日 00:00 | 統計彙整 | 更新每日統計表 |

---

## 相依套件

```json
{
  "dependencies": {
    "openclaw": ">=1.0.0",
    "sqlite3": "^5.1.6",
    "pandas": "^2.0.0",
    "google-auth": "^2.22.0",
    "google-auth-oauthlib": "^1.0.0",
    "google-auth-httplib2": "^0.1.1",
    "google-api-python-client": "^2.95.0",
    "beautifulsoup4": "^4.12.0",
    "python-telegram-bot": "^20.0"
  }
}
```

---

## 常見問題

### Q1: 需要 Google API 金鑰嗎？

**A:** 不需要。透過 Gmail 通知信間接取得，無需直接呼叫 Google Places API。

### Q2: 多久會同步一次？

**A:** 預設每小時檢查一次 Gmail，新評論通常在 5-10 分鐘內通知。

### Q3: 可以回覆評論嗎？

**A:** 目前只能提供回覆建議，實際回覆需到 Google 商家後台操作。

### Q4: 歷史評論能匯入嗎？

**A:** 可以，透過 Google Takeout 匯出評論資料，再批次匯入。

### Q5: 多個門市怎麼區分？

**A:** 透過 Gmail 篩選器，將不同門市的評論通知寄到不同標籤或資料夾。

---

## 版本紀錄

| 版本 | 日期 | 更新內容 |
|------|------|---------|
| 1.0.0 | 2026-03-17 | 初始版本，Gmail 解析、統計、通知、報表 |

---

## 聯絡與支援

- **作者:** 電腦舖 (Computer Shop)
- **Email:** ai@computershop.cc
- **GitHub:** https://github.com/computershop/google-reviews-automation
- **文件:** https://docs.computershop.cc/google-reviews-automation

---

## 授權條款

MIT License - 詳見 LICENSE 檔案

---

_最後更新: 2026-03-17_
