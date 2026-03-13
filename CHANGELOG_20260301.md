# 系統變更日誌 - 2026-03-01

## 概覽
今日完成 Admin Center 系統升級、UI 統一、以及資料庫結構優化。

---

## 一、資料管理中心 (admin.html) - v1.0

### 1.1 UI 統一優化
- ✅ 登入頁面標題簡化：移除 "Admin" 字樣
- ✅ 登入框位置調整：水平與垂直置中
- ✅ 背景色統一：`linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%)`
- ✅ 按鈕樣式統一：width: 100%, padding: 12px, border-radius: 8px

### 1.2 功能增強
- ✅ 加入版本號組件（右上角顯示）
- ✅ 版本號點擊可查看更新日誌
- ✅ Flask port 固定為 3000（禁止自動切換）

### 1.3 日誌版本
```
v1.0 - Admin Center UI統一
v0.9 - sales_history去重機制升級
v0.8 - 新增備份表、清理測試資料
v0.7 - Flask port固定為3000
v0.6 - 新增欄位、建立migration
v0.5 - 初始版本
```

---

## 二、請購調撥需求表 (needs_input.html) - v2.0

### 2.1 UI 統一優化
- ✅ 移除頁面頂部 h1 標題（登入時隱藏）
- ✅ 登入框標題簡化：移除 "🔐 請輸入密碼驗證" → "🛒 請購調撥需求表"
- ✅ 移除 "V2" 字樣
- ✅ 移除輸入框上方 "身分證後四碼" 標籤
- ✅ 按鈕文字統一："驗證" → "登入"
- ✅ 按鈕樣式統一：與資料管理中心一致
- ✅ 登入框位置：水平與垂直置中

### 2.2 日誌版本
```
v2.0 - UI統一：登入頁面簡化、移除V2字樣、按鈕樣式統一
v1.2 - staging_records補強
v1.1 - 代送門市下拉框調整
v1.0 - 初始版本
```

---

## 三、外勤服務紀錄表 (service_record.html)

### 3.1 UI 統一優化
- ✅ 移除頁面頂部 h1 標題
- ✅ 登入框標題簡化："業務部登入" → "📋 外勤服務紀錄"
- ✅ 移除輸入框上方 "身分證後四碼" 標籤
- ✅ input 樣式統一：移除 height:44px，padding 改為 10px 12px
- ✅ 按鈕樣式統一：與資料管理中心一致
- ✅ 登入框位置：水平與垂直置中

### 3.2 日誌版本
已與需求表共用版本號組件邏輯

---

## 四、資料庫結構變更 (company.db)

### 4.1 sales_history 表結構升級
```sql
-- 新增欄位
ALTER TABLE sales_history ADD COLUMN source_file TEXT;
ALTER TABLE sales_history ADD COLUMN source_row INTEGER;
ALTER TABLE sales_history ADD COLUMN import_key TEXT UNIQUE;
ALTER TABLE sales_history ADD COLUMN imported_at DATETIME DEFAULT (datetime('now','localtime'));
ALTER TABLE sales_history ADD COLUMN import_batch TEXT;

-- 移除舊索引
DROP INDEX idx_sales_unique;
```

### 4.2 Migration 腳本
- ✅ `migrate_sales_history_v2.py` - 添加 source_file/source_row 欄位

### 4.3 備份表
- ✅ `sales_history_deleted_backup` - 測試資料備份（28筆）

### 4.4 匯入腳本升級
- ✅ `sales_parser_v21.py` - 新版去重機制
- ✅ `sales_parser_v19.py` - 已更新為 V21 內容（排程器使用）

---

## 五、後端 API 修正 (app.py)

### 5.1 Flask 設定
- ✅ Port 固定為 3000
- ✅ Admin API 路由修正（移出 `if __name__ == '__main__':` 區塊）

### 5.2 Admin Center API
- ✅ `/api/admin/table` - 列表查詢
- ✅ `/api/admin/row` - 單筆查看（使用 id）

---

## 六、測試驗證項目

| 項目 | 狀態 |
|------|------|
| 同 CSV 匯入兩次（第二次 0 新增） | ✅ PASS |
| 相同內容不同行號（兩筆都寫入） | ✅ PASS |
| Admin Center 單筆查看 | ✅ PASS |
| 資料庫欄位完整性 | ✅ PASS |
| 備份表資料完整性 | ✅ PASS |
| 測試資料清理（28筆） | ✅ PASS |

---

## 七、檔案修改清單

### 前端頁面
1. `/dashboard-site/admin.html` - UI 統一、加入版本號
2. `/dashboard-site/needs_input.html` - UI 統一
3. `/dashboard-site/service_record.html` - UI 統一
4. `/dashboard-site/version-component.css` - 版本號樣式（共用）
5. `/dashboard-site/version-component.js` - 版本號邏輯（共用）

### 後端
6. `/dashboard-site/app.py` - Port 修正、API 路由修正

### 資料庫 Migration
7. `/srv/parser/migrate_sales_history_v2.py` - 欄位升級

### 匯入腳本
8. `/srv/parser/sales_parser_v21.py` - 新版去重機制
9. `/srv/parser/sales_parser_v19.py` - 排程器用（已更新）
10. `/srv/parser/sales_parser_v19_backup_*.py` - 備份檔案

---

## 八、排程器設定

```cron
40 10 * * * python3 sales_parser_v19.py
```

明日起自動使用新版去重機制。

---

## 九、已知限制

1. 舊資料的 `source_row` 保留了 migration 時的 `id` 值
2. 新匯入資料會使用實際 CSV 行號（1, 2, 3...）
3. 歸檔目錄：`/sales/archive/`

---

## 十、回滾方式

如需還原測試資料：
```sql
INSERT INTO sales_history 
SELECT * FROM sales_history_deleted_backup;
```

---

記錄時間：2026-03-01 22:30
記錄者：Yvonne

---

## 十一、導航列優化（追加）

### 11.1 修改內容
將以下頁面的導航列中，當前頁面的連結改為不可點擊的 span 元素：
- store.html (門市) - v1.1
- personal.html (個人) - v1.1
- business.html (業務) - v1.2
- department.html (部門) - v1.1
- Accountants.html (會計) - v1.2
- roster.html (班表) - v1.1
- customer_search.html (客戶) - v1.1

### 11.2 CSS 調整
為 `.nav span.active` 添加與 `.nav a.active` 相同的樣式，並設置 `cursor: default`

### 11.3 更新版本號
- 門市分析：v1.0 → v1.1
- 個人分析：v1.0 → v1.1
- 業務分析：v1.1 → v1.2
- 部門分析：v1.0 → v1.1
- 會計專區：v1.1 → v1.2
- 班表查詢：v1.0 → v1.1
- 客戶查詢：v1.0 → v1.1


---

## 十二、導航列優化 - 修正（追加）

### 12.1 修正內容
將當前頁面從導航列中**完全移除**（不只是改為不可點擊）：

| 頁面 | 移除項目 |
|------|----------|
| store.html (門市) | 🏬 門市 |
| personal.html (個人) | 🧑‍💼 個人 |
| business.html (業務) | 💼 業務 |
| department.html (部門) | 🏢 部門 |
| Accountants.html (會計) | 🧮 會計專區 |
| roster.html (班表) | 📅 班表 |
| customer_search.html (客戶) | 🔍 客戶 |

### 12.2 導航列現在顯示
- **store.html**: 首頁、部門、業務、個人、班表、客戶
- **personal.html**: 首頁、部門、門市、業務、班表、客戶
- **business.html**: 首頁、部門、門市、個人、班表、客戶
- **department.html**: 首頁、門市、業務、個人、班表、客戶
- **Accountants.html**: 首頁、部門、門市、業務、個人、班表、客戶、待建檔中心
- **roster.html**: 首頁、部門、門市、業務、個人、客戶
- **customer_search.html**: 首頁、部門、門市、業務、個人、班表


---

## 十三、班表匯入腳本停用（追加）

### 13.1 修改內容
- **停用 roster_parser.py 自動匯入**：因班表已改由前端直接輸入，不再需要從 Excel 檔案自動匯入
- **腳本狀態**：`roster_parser.py` → `roster_parser_DISABLED_20260302.py`
- **備份檔案**：`roster_parser_backup_20260302.py`

### 13.2 排程器調整
- 從 crontab 中移除 `55 10 * * * roster_parser.py` 排程
- 班表資料現在只透過前端 `roster_input.html` 頁面維護

### 13.3 資料狀態
- 現有 `staff_roster` 資料表保留（354筆排班紀錄）
- 未來新增/修改透過前端班表輸入頁面操作


---

## 十四、員工主檔系統（重大更新）

### 14.1 系統目標
建立集中式員工主檔管理系統，統一管理所有與員工相關的功能（登入、排班、績效、需求單、服務記錄等）。

### 14.2 資料庫設計

#### 新表：staff（員工主檔）
| 欄位 | 類型 | 說明 |
|------|------|------|
| staff_id | TEXT PRIMARY KEY | 員工編號（S0001...） |
| name | TEXT NOT NULL | 姓名 |
| title | TEXT | 職稱 |
| org_type | TEXT | HQ/DEPARTMENT/STORE/SALES |
| department | TEXT | 部門名稱 |
| store | TEXT | 門市名稱（可為 NULL） |
| role | TEXT | boss/accountant/manager/supervisor/staff/sales/engineer |
| phone | TEXT | 電話 |
| id_card | TEXT | 身分證字號 |
| birthday | TEXT | 生日 |
| is_active | INTEGER | 0=停用, 1=啟用 |
| password | TEXT | 登入密碼 |
| created_at | DATETIME | 建立時間 |
| updated_at | DATETIME | 更新時間 |

#### 索引
- idx_staff_name
- idx_staff_department
- idx_staff_store
- idx_staff_role
- idx_staff_active

### 14.3 API 清單

| 方法 | 路徑 | 功能 |
|------|------|------|
| GET | /api/admin/staff/list | 員工列表（含分頁/搜尋） |
| GET | /api/admin/staff/row | 單筆員工詳情 |
| POST | /api/admin/staff/create | 新增員工 |
| POST | /api/admin/staff/update | 更新員工資料 |
| POST | /api/admin/staff/reset-password | 重設密碼 |
| POST | /api/admin/staff/sync-from-staff-password | 同步舊表資料 |

### 14.4 前端頁面

#### staff_admin.html
- 員工列表表格（staff_id / 姓名 / 職稱 / 部門 / 門市 / 角色 / 狀態）
- 搜尋功能（staff_id / 姓名）
- 新增/編輯員工表單
- 啟用/停用功能（Soft Delete）
- 重設密碼功能
- 同步舊表資料按鈕
- 分頁功能

### 14.5 資料對應表

| 姓名 | staff_id | org_type | department | store | role |
|------|----------|----------|------------|-------|------|
| 劉育仕 | S0001 | STORE | 門市部 | 潭子門市 | engineer |
| 張家碩 | S0002 | STORE | 門市部 | 大雅門市 | engineer |
| 張永承 | S0003 | STORE | 門市部 | 大雅門市 | engineer |
| 林峙文 | S0004 | STORE | 門市部 | 豐原門市 | engineer |
| 林榮祺 | S0005 | STORE | 門市部 | 豐原門市 | engineer |
| 林煜捷 | S0006 | STORE | 門市部 | 潭子門市 | engineer |
| 梁仁佑 | S0007 | SALES | 業務部 | NULL | sales |
| 莊圍迪 | S0008 | STORE | 門市部 | NULL | manager |
| 萬書佑 | S0009 | SALES | 業務部 | NULL | manager |
| 鄭宇晉 | S0010 | SALES | 業務部 | NULL | sales |
| 黃柏翰 | S0011 | HQ | 總公司 | NULL | boss |
| 黃環馥 | S0012 | HQ | 總公司 | NULL | accountant |

### 14.6 版本號
- staff_admin.html: v1.0

### 14.7 上線切換策略

#### 第一階段（已完成）
- ✅ 在測試庫建立 staff 表
- ✅ 匯入 12 位員工資料
- ✅ 建立 Admin API
- ✅ 建立前端管理頁面
- ✅ 測試所有功能

#### 第二階段（待執行）
1. 備份 company.db
2. 執行 migrate_staff_master_production.py
3. 重啟 Flask 服務
4. 測試 staff_admin.html
5. 確認無誤後上線

#### 第三階段（未來）
- 修改既有登入流程，回傳 staff_id
- 統一系統內所有 requester 存儲為 staff_id
- 移除對 staff_password 表的依賴

### 14.8 交付檔案清單

1. `/srv/parser/migrate_staff_master.py` - 測試庫 migration
2. `/srv/parser/migrate_staff_master_production.py` - 正式庫 migration
3. `/dashboard-site/staff_admin_api.py` - API 參考實作
4. `/dashboard-site/staff_admin.html` - 前端管理頁面

