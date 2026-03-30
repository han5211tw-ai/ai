# Skill Specification: roster-performance-tracker

## 概述

**名稱:** roster-performance-tracker  
**版本:** 1.0.0  
**作者:** 電腦舖 (Computer Shop)  
**授權:** MIT  
**適用產業:** 零售業、連鎖店、多門市管理、需要班表與業績追蹤的企業  

**一句話描述:** 班表查詢、個人/門市/部門業績追蹤、達成率計算、督導評分管理，一站式績效管理系統。

---

## 功能清單

| 功能 | 指令範例 | 說明 |
|------|---------|------|
| **查班表** | 「這週班表」、「明天誰上班」 | 查詢個人或全體班表 |
| **今日出勤** | 「今天誰在豐原門市」 | 查詢特定門市今日人員 |
| **個人業績** | 「我這個月業績」 | 查詢個人目標、實際、達成率 |
| **門市業績** | 「豐原門市這週業績」 | 查詢門市整體表現 |
| **部門業績** | 「門市部這個月達成率」 | 查詢部門總合業績 |
| **排行榜** | 「這個月業績排名」 | 個人/門市排行榜 |
| **督導評分** | 「上個月督導評分」 | 查詢門市督導評分紀錄 |
| **業績預測** | 「月底能達標嗎」 | 根據目前進度預測達成率 |

---

## 資料表結構

```sql
-- 班表
CREATE TABLE staff_roster (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    staff_name TEXT NOT NULL,
    location TEXT NOT NULL,      -- 門市名稱
    shift_code TEXT,             -- 班次代碼
    shift_name TEXT,             -- 班次名稱（早班/晚班/全班）
    start_time TEXT,
    end_time TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 績效目標
CREATE TABLE performance_targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_type TEXT NOT NULL,  -- 'person' | 'store' | 'department'
    subject_name TEXT NOT NULL,  -- 人員/門市/部門名稱
    target_month TEXT NOT NULL,  -- YYYY-MM
    target_amount REAL NOT NULL, -- 目標金額
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(subject_type, subject_name, target_month)
);

-- 督導評分
CREATE TABLE supervision_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_name TEXT NOT NULL,
    score_date TEXT NOT NULL,
    total_score REAL,            -- 總分
    category_scores TEXT,        -- 各項分數 JSON
    evaluator TEXT,              -- 評分人
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 外勤服務紀錄
CREATE TABLE service_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    staff_name TEXT NOT NULL,
    customer_name TEXT,
    service_type TEXT,           -- 維修/安裝/諮詢
    location TEXT,
    description TEXT,
    status TEXT DEFAULT '完成',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 業績計算邏輯

### 門市部計算

```
門市部總業績 = 豐原門市 + 潭子門市 + 大雅門市 + 主管業績

豐原門市 = 林榮祺 + 林峙文
潭子門市 = 劉育仕 + 林煜捷
大雅門市 = 張永承 + 張家碩
門市部主管 = 莊圍迪
```

### 業務部計算

```
業務部總業績 = 鄭宇晉 + 梁仁佑 + 主管業績

業務部主管 = 萬書佑
```

### 個人績效計算

| 指標 | 計算方式 |
|------|---------|
| **目標業績** | 從 performance_targets 讀取 |
| **實際業績** | SUM(sales_history.amount) WHERE salesperson = ? |
| **達成率** | (實際 / 目標) × 100% |
| **毛利率** | SUM(利潤) / SUM(金額) × 100% |
| **單數** | COUNT(DISTINCT invoice_no) |
| **平均單價** | 實際業績 / 單數 |

---

## 安裝方式

### ClawHub 安裝

```bash
npx clawhub@latest install roster-performance-tracker
```

### 手動安裝

```bash
git clone https://github.com/computershop/roster-performance-tracker.git
cd roster-performance-tracker
openclaw skills install .
```

---

## 設定檔

**檔案位置:** `~/.openclaw/skills/roster-performance-tracker/config.json`

```json
{
  "database": {
    "path": "/path/to/company.db",
    "type": "sqlite"
  },
  "business_structure": {
    "departments": {
      "store": {
        "name": "門市部",
        "manager": "莊圍迪",
        "stores": {
          "豐原": ["林榮祺", "林峙文"],
          "潭子": ["劉育仕", "林煜捷"],
          "大雅": ["張永承", "張家碩"]
        }
      },
      "business": {
        "name": "業務部",
        "manager": "萬書佑",
        "staff": ["鄭宇晉", "梁仁佑"]
      }
    }
  },
  "performance_rules": {
    "calculation_method": "realtime",  -- realtime | daily_batch
    "target_period": "monthly",        -- monthly | weekly
    "commission_enabled": true,
    "commission_rates": {
      "base": 0.01,                    -- 1% 基本獎金
      "bonus_threshold": 1.0,          -- 達標才有獎金
      "bonus_rate": 0.02               -- 達標額外 2%
    }
  },
  "notifications": {
    "daily_report": {
      "enabled": true,
      "time": "18:00",
      "channel": "telegram"
    },
    "weekly_summary": {
      "enabled": true,
      "day": "sunday",
      "time": "20:00"
    },
    "target_alert": {
      "enabled": true,
      "threshold": 0.8  -- 低於 80% 提醒
    }
  },
  "parser": {
    "roster": {
      "enabled": true,
      "source_path": "~/srv/sync/OneDrive/ai_source/roster/",
      "schedule": "10:55"
    },
    "performance": {
      "enabled": true,
      "schedule": "11:00"
    },
    "supervision": {
      "enabled": true,
      "schedule": "11:10"
    }
  }
}
```

---

## 使用範例

### 查班表

**使用者:** 「這週班表」

**AI 回覆:**
```
📅 本週班表 (03/17 - 03/23)

| 日期 | 豐原門市 | 潭子門市 | 大雅門市 |
|------|---------|---------|---------|
| 一 | 林榮祺 早班 | 劉育仕 全班 | 張永承 晚班 |
| 二 | 林峙文 晚班 | 林煜捷 早班 | 張家碩 全班 |
| 三 | 林榮祺 全班 | 劉育仕 晚班 | 張永承 早班 |
| ... | ... | ... | ... |

💡 輸入「明天班表」查看明日詳細
```

### 查個人業績

**使用者:** 「我這個月業績」

**AI 回覆:**
```
📊 王小明 - 2026年3月 業績

| 指標 | 數值 | 狀態 |
|------|------|------|
| 目標業績 | 300,000 | - |
| 實際業績 | 245,000 | 🟡 |
| 達成率 | 81.7% | 需努力 |
| 毛利率 | 12.5% | ✅ |
| 單數 | 15 單 | - |
| 平均單價 | 16,333 | - |

📈 距離月底還有 14 天
🎯 需再衝 55,000 才能達標（日均 3,928）
```

### 查門市業績

**使用者:** 「豐原門市這個月業績」

**AI 回覆:**
```
🏪 豐原門市 - 2026年3月 業績

| 人員 | 目標 | 實際 | 達成率 | 排名 |
|------|------|------|--------|------|
| 林榮祺 | 150,000 | 135,000 | 90.0% | 🥇 |
| 林峙文 | 150,000 | 110,000 | 73.3% | 🥈 |
| **門市合計** | **300,000** | **245,000** | **81.7%** | - |

📊 門市達成率：81.7% (全公司排名第 2)
```

### 排行榜

**使用者:** 「這個月業績排名」

**AI 回覆:**
```
🏆 2026年3月 個人業績排行榜

| 排名 | 姓名 | 實際業績 | 達成率 |
|------|------|---------|--------|
| 🥇 | 鄭宇晉 | 320,000 | 106.7% |
| 🥈 | 林榮祺 | 135,000 | 90.0% |
| 🥉 | 梁仁佑 | 175,000 | 87.5% |
| 4 | 劉育仕 | 128,000 | 85.3% |
| 5 | 張永承 | 120,000 | 80.0% |
| ... | ... | ... | ... |

💪 加油！你目前排名第 6
```

### 督導評分

**使用者:** 「上個月督導評分」

**AI 回覆:**
```
📋 2026年2月 督導評分

| 門市 | 總分 | 整潔 | 陳列 | 服務 | 庫存 | 評分人 |
|------|------|------|------|------|------|--------|
| 豐原 | 92 | 18 | 19 | 19 | 18 | 莊圍迪 |
| 潭子 | 88 | 17 | 18 | 18 | 17 | 莊圍迪 |
| 大雅 | 85 | 16 | 17 | 18 | 16 | 莊圍迪 |

🥇 本月最佳：豐原門市 (92分)
```

---

## 業績預測功能

**使用者:** 「月底能達標嗎」

**AI 回覆:**
```
🔮 業績預測分析

【目前狀況】
- 時間進度：53% (16/30 天)
- 業績進度：48% (245,000/500,000)
- 落後：5%

【預測結果】
- 按目前速度：月底可達 462,000 (達成率 92.4%)
- 要達標需：每日平均 18,214 (目前 15,312)

【建議】
⚠️ 需提升每日業績 19% 才能達標
💡 可考慮：推促銷活動、加強客戶追蹤
```

---

## 排程自動化

**內建 Cron 任務：**

| 時間 | 任務 | 說明 |
|------|------|------|
| 10:55 | 班表匯入 | 從 Excel 更新本週班表 |
| 11:00 | 績效計算 | 重新計算個人/門市/部門業績 |
| 11:10 | 督導評分匯入 | 更新評分資料 |
| 18:00 | 日報發送 | 發送當日業績快報 |
| 每週日 20:00 | 週報發送 | 本週績效總結 |
| 每月 25 日 | 達標提醒 | 提醒未達標人員衝刺 |

---

## 報表功能

### 支援報表類型

| 報表 | 週期 | 內容 |
|------|------|------|
| **日報** | 每日 | 當日業績、達成率、排名變化 |
| **週報** | 每週 | 本週業績、趨勢圖、最佳表現 |
| **月報** | 每月 | 完整月報、獎金計算、排行榜 |
| **班表** | 每週 | 下週班表、休假統計 |
| **督導評分** | 每月 | 各門市評分明細、改善建議 |

---

## 相依套件

```json
{
  "dependencies": {
    "openclaw": ">=1.0.0",
    "sqlite3": "^5.1.6",
    "pandas": "^2.0.0",
    "openpyxl": "^3.1.0",
    "matplotlib": "^3.7.0",
    "python-telegram-bot": "^20.0"
  }
}
```

---

## 常見問題

### Q1: 業績多久更新一次？

**A:** 預設每小時自動計算，也可手動觸發「重新計算業績」。

### Q2: 可以查歷史業績嗎？

**A:** 可以，支援查詢任意月份：「查去年12月業績」。

### Q3: 如何修改目標金額？

**A:** 需老闆權限，可說「設定王小明3月目標35萬」。

### Q4: 班表可以匯出嗎？

**A:** 可以，支援匯出 Excel 或 PDF：「匯出這週班表」。

### Q5: 督導評分誰可以輸入？

**A:** 預設只有主管和老闆可以輸入評分。

---

## 版本紀錄

| 版本 | 日期 | 更新內容 |
|------|------|---------|
| 1.0.0 | 2026-03-17 | 初始版本，班表、業績、督導評分、預測功能 |

---

## 聯絡與支援

- **作者:** 電腦舖 (Computer Shop)
- **Email:** ai@computershop.cc
- **GitHub:** https://github.com/computershop/roster-performance-tracker
- **文件:** https://docs.computershop.cc/roster-performance-tracker

---

## 授權條款

MIT License - 詳見 LICENSE 檔案

---

_最後更新: 2026-03-17_
