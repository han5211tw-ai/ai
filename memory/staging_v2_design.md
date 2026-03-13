# 2026-02-27 - 待建檔系統 V2 設計

## 設計原則

### 核心原則
- **ERP/庫存表為唯一權威主檔**
- **待建檔只做「暫存 → 配對 → 回填到單據」**
- **客戶自動對照為主，商品人工處理為輔**

---

## 資料表設計

### staging_records（統一待建檔表）

| 欄位 | 說明 |
|------|------|
| id | 主鍵 |
| type | 'customer' 或 'product' |
| raw_input | 原始輸入（姓名或品名） |
| raw_code | 原始輸入編號 |
| raw_mobile | 原始手機號 |
| source_id | 來源單據 ID |
| source_type | 'needs' 或 'service_records' |
| requester | 申請人 |
| department | 部門 |
| store | 門市 |
| status | 'pending' / 'resolved' / 'needs_review' |
| resolved_code | 解析後的正式編號 |
| resolved_name | 解析後的正式名稱 |
| resolved_at | 解析時間 |
| resolver | 解析者（system / admin） |
| resolve_method | 'auto_mobile_exact' / 'manual' |
| audit_log | JSON 操作日誌 |

---

## 處理策略

### A) 客戶待建檔：自動對照回填（主流程）

**自動對照腳本** (`reconcile_customers.py`)：
1. 每天 ERP 客戶名單匯入完成後執行
2. 只處理 status='pending' 的客戶待建檔
3. 以 mobile（09 開頭 10 碼）做完全相等匹配
4. 命中唯一一筆則自動回填 customer_id
5. 例外標記為 needs_review

**匹配規則**：
- ✅ mobile 完全一致 → 自動回填
- ❌ mobile 空值/格式不合法 → needs_review
- ❌ mobile 命中多筆 → needs_review
- ❌ mobile 未命中 → 保留 pending

### B) 商品待建檔：全部人工逐筆處理

**原則**：
1. 一律保持 status='pending'
2. 不做自動合併、不做自動匹配
3. 人工審核時手動填入 product_code
4. 保留 original_name 不可覆蓋

---

## API 端點

```
GET    /api/staging/records?type=&status=    # 獲取待建檔列表
POST   /api/staging/resolve/<id>             # 人工解析
POST   /api/staging/reconcile                # 執行自動對照
```

---

## 後台頁面

**待建檔中心 V2**：`staging_center_v2.html`
- 分類顯示客戶/商品待建檔
- 支援人工解析（填入正式編號）
- 支援執行自動對照
- 顯示統計數據

---

## 檔案清單

| 檔案 | 說明 |
|------|------|
| `/srv/db/company.db` | staging_records 表 |
| `/srv/parser/reconcile_customers.py` | 客戶自動對照腳本 |
| `/dashboard-site/staging_center_v2.html` | 新待建檔中心後台 |
| `/dashboard-site/app.py` | API 端點 |

---

_記錄時間：2026-02-27 20:30_
_記錄者：Yvonne_
