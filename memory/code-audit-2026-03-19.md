# ERP 系統代碼審計報告

_執行日期：2026-03-19 17:15_  
_審計者：Yvonne_

---

## 📋 審計範圍

- **主程式**: `dashboard-site/app.py` (347KB)
- **觀測性模組**: `dashboard-site/observability.py` (24.6KB)
- **資料庫結構**: `company.db` (18 張表 + 視圖)
- **管理功能**: `admin_staff.py`, `staff_admin_api.py`

---

## ⚠️ 發現的問題

### 1. **SQL 注入風險（高優先級）**

#### 位置：`app.py` 第 **5739** 行

```python
cursor.execute(f"SELECT COUNT(*) as total FROM {table_name} WHERE {where_clause}", params)
```

**問題描述：**
- `table_name` 有白名單驗證 (`allowed_tables`)
- **但 `where_clause` 直接從用戶輸入構建，未做驗證**
- 可能被攻擊者利用注入惡意 SQL

**影響範圍：**
- `/api/admin/table` API（表查詢）
- 管理後台的分頁查詢功能

**風險等級：** 🔴 **中高**

---

#### 位置：`app.py` 第 **5811** 行

```python
cursor.execute(f"PRAGMA table_info({table_name})")
```

**問題描述：**
- `table_name` 有白名單驗證（`allowed_tables` 列表）
- 白名單包含：`['needs', 'staging_records', 'customers', 'products', 'inventory', 'purchase_history', 'sales_history', 'admin_audit_log', 'admin_tombstone', 'ops_events']`

**風險等級：** 🟡 **低**（有白名單保護，但仍是動態表名）

---

### 2. **格式化字串潛在風險**

以下位置使用了 f-string 構建 SQL（有後台驗證保護）：

| 行號 | 功能 | 風險等級 | 說明 |
|------|------|----------|------|
| 882 | 登入密碼檢查 | 🟡 低 | 後台驗證，表名固定 |
| 925 | 員工表單處理 | 🟡 低 | 後台驗證，表名固定 |
| 968 | 數據更新 | 🟡 低 | 後台驗證，表名固定 |
| 1664 | Admin 資料操作 | 🟡 低 | 後台驗證，表名固定 |
| 4870, 4886 | 數據修正 | 🟡 低 | 後台驗證，表名固定 |
| **5739** | **表查詢（where_clause）** | 🔴 **中** | **where_clause 未驗證** |
| 5811 | PRAGMA 查詢 | 🟡 低 | table_name 有白名單 |

---

## ✅ 系統優點

### 1. **資料庫設計優良**

```sql
-- 核心表結構（18 張表）
- sales_history: 銷貨明細
- inventory: 庫存管理
- customers: 客戶主檔
- products: 產品主檔
- needs: 需求單
- staging_records: Staging 機制
- ops_events: 事件追蹤
- admin_audit_log: 管理審計
- supervision_scores: 督導評分
- service_records: 服務紀錄
...
```

**優點：**
- ✅ 使用參數化查詢（`?` 綁定）
- ✅ 索引優化（多個 `CREATE INDEX`）
- ✅ 關聯完整（`FOREIGN KEY`、`UNIQUE` 約束）
- ✅ 審計欄位齊全（`created_at`, `updated_at`）

---

### 2. **完整的觀測性系統** (`observability.py`)

- ✅ 事件追蹤 (`ops_events`)
- ✅ 資料新鮮度檢查 (`freshness_cache`)
- ✅ 匯入狀態監控 (`ingest_status`)
- ✅ 資料一致性稽核 (`consistency_check`)
- ✅ API 效能指標 (`api_metrics`)

**所有 SQL 查詢使用參數化，無注入風險**

---

### 3. **權限管理健全**

- ✅ `@require_admin` 裝飾器保護管理 API
- ✅ `staff_passwords` 表管理權限
- ✅ `admin_audit_log` 記錄所有管理操作

---

### 4. **Staging 機制**

安全的主檔更新流程：
1. 資料先寫入 `staging_records`
2. 狀態 `pending` → `resolved`
3. Admin 確認後 `backfill` 到正式表

**優點：**
- ✅ 防止直接修改正式資料
- ✅ 完整的審計追蹤
- ✅ 支援回滾（`tombstone` 機制）

---

## 📊 系統架構檢查

| 項目 | 狀態 | 備註 |
|------|------|------|
| **資料庫** | ✅ 完整 | 18 張表 + 視圖，索引完善 |
| **Web 伺服器** | ✅ Gunicorn | 4 workers, Port 3000 |
| **排程任務** | ✅ launchd | 每日執行 Parser |
| **權限系統** | ✅ 健全 | 密碼驗證 + 審計日誌 |
| **觀測性** | ✅ 完整 | 事件追蹤 + 健康檢查 |
| **API 設計** | ✅ RESTful | JSON Response |

---

## 🎯 建議行動

### 立即處理：

1. **修復 SQL 注入風險**（第 5739 行）
   - 建立 `where_clause` 驗證函數
   - 只允許預定義的欄位和運算子
   - 或使用 ORM 風格的查詢构建器

### 長期改進：

1. **使用 ORM** - 可考慮 SQLAlchemy 減少 SQL 手寫
2. **增加自動化測試** - 單元測試 + 整合測試
3. **CI/CD 流程** - 代碼審查 + 靜態分析（`flake8`, `pylint`）
4. **日誌集中化** - 整合 `ops_events` 到外部監控系統

---

## 📁 相關檔案路徑

- **主程式**: `/Users/aiserver/.openclaw/workspace/dashboard-site/app.py`
- **觀測性**: `/Users/aiserver/.openclaw/workspace/dashboard-site/observability.py`
- **資料庫**: `/Users/aiserver/srv/db/company.db`
- **Gunicorn**: `/Users/aiserver/.openclaw/workspace/dashboard-site/gunicorn.conf.py`
- **Launchd**: `~/Library/LaunchAgents/com.dashboard.gunicorn.plist`

---

## 📌 總結

**整體評分：B+**

| 評分項目 | 得分 |
|----------|------|
| 功能完整性 | ⭐⭐⭐⭐⭐ |
| 資料庫設計 | ⭐⭐⭐⭐⭐ |
| 觀測性 | ⭐⭐⭐⭐⭐ |
| 權限管理 | ⭐⭐⭐⭐ |
| 代碼安全性 | ⭐⭐⭐ |
| 可維護性 | ⭐⭐⭐⭐ |

**關鍵問題：1 處 SQL 注入風險（where_clause 未驗證）**  
**處理建議：建立安全的查詢构建器，避免直接拼接用戶輸入**

---

_報告完成時間：2026-03-19 17:17_  
_審計版本：v1.0_
