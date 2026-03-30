| 2026-03-13 | v1.1 | 新增「推薦備貨商品」功能模組 |
| 2026-03-13 | v1.2 | 新增「銷售獎金計算」功能模組 |

---

## 12. 銷售獎金計算功能模組 (New in v1.2)

### 12.1 功能概述

「銷售獎金計算」功能讓老闆/會計可以設定特定商品在特定時間銷售的額外獎金規則，系統自動計算符合條件的銷售獎金，並提供確認與發放流程。

**核心價值**：
- 彈性設定獎金規則（商品+時間+獎金類型）
- 自動計算，減少人工錯誤
- 完整的確認與發放流程
- 與現有銷售資料無縫整合

### 12.2 資料庫設計

#### 12.2.1 獎金規則表 (`bonus_rules`)
```sql
CREATE TABLE bonus_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_name TEXT NOT NULL,          -- 規則名稱
    product_code TEXT,                -- 產品編號
    product_name TEXT,                -- 產品名稱關鍵字
    start_date DATE NOT NULL,         -- 開始日期
    end_date DATE NOT NULL,           -- 結束日期
    bonus_type TEXT DEFAULT 'fixed',  -- 獎金類型：fixed固定金額、percent百分比
    bonus_value REAL NOT NULL,        -- 獎金數值
    min_quantity INTEGER DEFAULT 1,   -- 最小數量門檻
    target_scope TEXT DEFAULT 'all',  -- 適用範圍
    target_codes TEXT,                -- 特定對象編號
    is_active INTEGER DEFAULT 1,      -- 是否啟用
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 12.2.2 獎金計算結果表 (`bonus_results`)
```sql
CREATE TABLE bonus_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id INTEGER,                  -- 對應規則ID
    period_start DATE,                -- 計算週期起日
    period_end DATE,                  -- 計算週期迄日
    salesperson_id TEXT,              -- 業務員編號
    salesperson_name TEXT,            -- 業務員名稱
    product_code TEXT,                -- 產品編號
    product_name TEXT,                -- 產品名稱
    sales_quantity INTEGER,           -- 銷售數量
    sales_amount REAL,                -- 銷售金額
    bonus_amount REAL,                -- 獎金金額
    invoice_nos TEXT,                 -- 相關銷貨單號
    status TEXT DEFAULT 'pending',    -- 狀態
    confirmed_by TEXT,
    confirmed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 12.3 API 設計

#### 12.3.1 規則管理 API

| 方法 | 端點 | 功能 |
|------|------|------|
| GET | `/api/bonus-rules` | 取得獎金規則列表 |
| POST | `/api/bonus-rules` | 新增獎金規則 |
| PUT | `/api/bonus-rules/{id}` | 更新獎金規則 |
| DELETE | `/api/bonus-rules/{id}` | 刪除獎金規則 |

#### 12.3.2 計算與查詢 API

| 方法 | 端點 | 功能 |
|------|------|------|
| POST | `/api/bonus-calculate` | 計算指定週期獎金 |
| GET | `/api/bonus-results` | 取得計算結果 |
| POST | `/api/bonus-results/{id}/confirm` | 確認單筆獎金 |
| POST | `/api/bonus-results/batch-confirm` | 批次確認獎金 |

### 12.4 頁面設計

#### 12.4.1 獎金規則管理頁面 (`/admin/bonus_rules`)

**功能**：
- 獎金規則列表（規則名稱、商品、時間區間、獎金類型）
- 新增/編輯/刪除規則
- 產品搜尋帶入（產品編號、產品名稱）
- 時間區間選擇
- 獎金類型（固定金額/百分比）
- 適用範圍設定

**欄位說明**：
- **規則名稱**：活動或規則名稱
- **產品編號**：指定商品的編號（唯讀，搜尋帶入）
- **產品名稱**：可手動輸入或搜尋帶入
- **時間區間**：規則生效的日期範圍
- **獎金類型**：固定金額（元/件）或銷售額百分比
- **獎金數值**：對應的獎金數字
- **最小數量門檻**：達成獎金的最小銷售數量
- **適用範圍**：全部人員或特定人員

#### 12.4.2 獎金報表頁面 (`/admin/bonus_report`)

**功能**：
- 選擇計算週期並執行計算
- 查詢條件篩選（日期、狀態）
- 統計摘要（總筆數、總銷售額、總獎金、待確認數）
- 獎金明細列表
- 單筆/批次確認
- 匯出 CSV 報表

#### 12.4.3 個人獎金查詢頁面 (`/bonus_personal`)

**功能**：
- 業務員查看自己的獎金記錄
- 日期範圍篩選
- 統計摘要
- 獎金明細列表

### 12.5 權限控制

| 角色 | 規則管理 | 獎金報表 | 個人查詢 |
|------|---------|---------|---------|
| 老闆 | ✅ | ✅ | ✅ |
| 會計 | ✅ | ✅ | ✅ |
| 門市/業務 | ❌ | ❌ | ⏳（未來開放） |

### 12.6 資料流程

```
老闆/會計
    ↓
進入「獎金規則管理」頁面
    ↓
新增獎金規則
    ↓
搜尋產品帶入編號與名稱
    ↓
設定時間區間、獎金類型、數值
    ↓
儲存規則

老闆/會計
    ↓
進入「獎金報表」頁面
    ↓
選擇計算週期
    ↓
點擊「開始計算」
    ↓
系統查詢 sales_history 表
    ↓
匹配符合規則的銷售記錄
    ↓
計算獎金金額
    ↓
儲存到 bonus_results 表
    ↓
顯示計算結果
    ↓
確認獎金記錄
```

### 12.7 獎金計算邏輯

```python
def calculate_bonus(sale, rule):
    # 檢查時間區間
    if not (rule.start_date <= sale.date <= rule.end_date):
        return 0
    
    # 檢查商品匹配
    if rule.product_code and sale.product_code != rule.product_code:
        return 0
    if rule.product_name and rule.product_name not in sale.product_name:
        return 0
    
    # 檢查數量門檻
    if sale.quantity < rule.min_quantity:
        return 0
    
    # 計算獎金
    if rule.bonus_type == 'fixed':
        return rule.bonus_value * sale.quantity
    elif rule.bonus_type == 'percent':
        return sale.amount * (rule.bonus_value / 100)
    
    return 0
```

### 12.8 相關檔案

```
dashboard-site/
├── admin/bonus_rules.html      # 獎金規則管理頁面
├── admin/bonus_report.html     # 獎金報表頁面
├── bonus_personal.html         # 個人獎金查詢頁面
└── app.py                      # API 端點
```

---

## 文件資訊
- **文件編號**: ERP-WP-001
- **版本**: v1.2
- **建立日期**: 2026-03-13
- **最後更新**: 2026-03-13
- **維護者**: Yvonne
- **審核者**: 黃柏翰

---

*本文件為電腦超市 ERP 系統的完整技術規格書，供系統管理、開發維護及未來擴充參考使用。*
