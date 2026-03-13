# 2026-02-27 - 銷貨資料匯入問題解決

## 📝 問題背景
- **時間**：2026-02-27 凌晨
- **問題**：銷貨資料匯入出現重複、退貨未計算、日期範圍錯誤等問題

---

## 🔧 核心問題與解決方案

### 1. 資料重複問題

**問題描述**：
- Parser V19 多次執行導致同一筆資料重複匯入
- 資料庫從 8,107 筆膨脹到 15,601 筆
- 總金額從 $51M 變成 $102M（翻倍）

**根本原因**：
1. 沒有防重複機制
2. Unique constraint 未正確設定（未包含 product_name）
3. 原始檔案中同一客戶的多個服務項目被誤判為重複

**解決方案**：

#### A. 資料層防護（Unique Constraint）
```sql
CREATE UNIQUE INDEX idx_sales_unique 
ON sales_history(
    date, 
    salesperson, 
    customer_name, 
    product_code, 
    product_name,  -- 關鍵：區分同一產品編號的不同服務項目
    quantity, 
    amount
);
```

**為什麼需要 product_name**：
- 客戶可能同一天購買同一產品編號（SE-PC）的多個服務
- 範例：代送修記憶體（$500）、維修費用（$800）、代送修硬碟（$500）
- 沒有 product_name 會誤判為重複

#### B. 流程層防護（檔案記錄）
```python
# Parser 記錄已匯入的檔案
IMPORT_LOG_PATH = os.path.join(HOME, "srv/logs/sales_import_log.txt")

def get_imported_files():
    """獲取已匯入的檔案列表"""
    # 檢查檔案是否已匯入
    
def log_imported_file(filepath):
    """記錄已匯入的檔案"""
    # 寫入日誌
```

---

### 2. 退貨處理問題

**問題描述**：
- Parser 過濾掉了負數記錄
- 退貨金額未從總業績中扣除
- 林榮祺 2/3 退貨 $91,890 未被計算

**根本原因**：
```python
# 錯誤碼 - 負數會被 isdigit() 判定為 False
'quantity': int(quantity) if quantity.isdigit() else 0,
'amount': int(amount) if amount.isdigit() else 0,
```

**解決方案**：
```python
# 正確碼 - 使用 lstrip('-') 處理負數
'quantity': int(quantity) if quantity and quantity.lstrip('-').isdigit() else 0,
'amount': int(amount) if amount and amount.lstrip('-').isdigit() else 0,
```

**驗證**：
- 修改後正確匯入 2/3 退貨記錄 6 筆
- 林榮祺總業績從 $1,467,932 修正為 $1,376,042（扣除 $91,890）

---

### 3. 每日增量模式管理

**現行模式**：
- 每天匯出前一天的資料（如：銷貨0226.csv）
- 檔案名稱：銷貨 + 月日（0226）
- 每月一個累計檔案：銷貨202602.csv（2/1-2/25）

**檔案命名規則**：
| 類型 | 檔名 | 內容 |
|------|------|------|
| 每日增量 | 銷貨0226.csv | 2/26 當天資料 |
| 每月累計 | 銷貨202602.csv | 2/1-2/25 完整資料 |

**Parser 處理邏輯**：
1. 檢查檔案是否已匯入（透過 import log）
2. 只匯入新檔案
3. 同一檔案不重複執行
4. Unique constraint 作為最後防線

---

## ✅ 最終狀態

### 資料庫狀態
```
總筆數：8,151 筆（含 2/26 的 33 筆）
日期範圍：2025-01-01 至 2026-02-26
總金額：約 $51M
```

### 資料正確性驗證
| 項目 | 結果 |
|------|------|
| 重複資料 | ✅ 已清除（unique constraint + 檔案記錄） |
| 退貨計算 | ✅ 正確扣除（負數記錄正確匯入） |
| 日期範圍 | ✅ 動態計算（API 使用 today 變數） |
| 防重複機制 | ✅ 雙重保險（流程層 + 資料層） |

---

## 📋 相關檔案

- **Parser**：`/Users/aiserver/srv/parser/sales_parser_v19.py`
- **備份**：`/Users/aiserver/srv/parser/sales_parser_v19.py.backup`
- **Import Log**：`/Users/aiserver/srv/logs/sales_import_log.txt`
- **資料庫**：`/Users/aiserver/srv/db/company.db`

---

## 🎯 關鍵學習

1. **Unique Constraint 設計**：必須包含所有能區分不同記錄的欄位（特別是 product_name）
2. **負數處理**：使用 `lstrip('-')` 而不是直接 `isdigit()`
3. **雙重防護**：流程防護（檔案記錄）+ 資料防護（unique constraint）
4. **每日增量模式**：需要檔案記錄機制防止重複執行

---

_記錄時間：2026-02-27_
_記錄者：Yvonne_
