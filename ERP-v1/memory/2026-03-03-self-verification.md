# 2026-03-03 自我驗證報告

## 【一、欄位錯誤驗證】

### 1️⃣ 確認資料表沒有 customer_name 欄位
```sql
sqlite3 /Users/aiserver/srv/db/company.db "PRAGMA table_info(needs);"
```
結果：輸出中無 `customer_name` 欄位 ✓

### 2️⃣ 確認 staging/resolve API 已無 customer_name SQL
```bash
grep -RIn "customer_name" /Users/aiserver/.openclaw/workspace/dashboard-site --include="*.py" | grep "staging/resolve\|def resolve"
```
結果：resolve_staging_record 函數內無 SQL 使用 customer_name，僅剩註解說明 ✓

---

## 【二、狀態機驗證】

### A. 建立測試 staging
```sql
INSERT INTO staging_records (...) VALUES (...);
→ 新 ID: 199
```

初始狀態：
```
199|pending|驗證測試客戶
```

### B. API 呼叫手動解析
```bash
curl -X POST "http://127.0.0.1:3000/api/staging/resolve/199" \
  -d '{"resolved_code":"FY-VERIFY001","resolved_name":"驗證正式客戶"}'
```

輸出：
```json
{
    "success": true
}
```
✓ 無 customer_name 錯誤

### C. DB 驗證（必須為 resolved）
```sql
SELECT id, status, resolved_code FROM staging_records WHERE id=199;
```

結果：
```
199|resolved|FY-VERIFY001
```
✓ 狀態正確變為 resolved

### D. Pending 清單驗證
```sql
SELECT COUNT(*) FROM staging_records WHERE status='pending' AND id=199;
```

結果：
```
0
```
✓ 已解析資料不在 pending 清單

---

## 【三、API 層驗證】

### Pending View
```bash
curl "/api/staging/records?type=customer&view=pending"
```

結果：
- Records: 0 筆
- 無錯誤訊息

### Resolved View  
```bash
curl "/api/staging/records?type=customer&view=resolved"
```

結果：
- ID: 184, Status: resolved
- ID: 183, Status: resolved
- ID: 1, Status: resolved

---

## 【四、防回滾驗證】

### 執行 reconcile
```bash
curl -X POST "/api/staging/reconcile"
```

結果：
```json
{
    "success": true,
    "stats": {
        "auto_resolved": 0,
        "errors": 0,
        "needs_review": 0
    }
}
```

### 再查狀態
```sql
SELECT id, status, resolved_code FROM staging_records WHERE id=199;
```

結果：
```
199|resolved|FY-VERIFY001
```
✓ 狀態仍為 resolved，未被改回 pending

---

## 【結論】

| 驗證項目 | 結果 |
|----------|------|
| 無 customer_name SQL 錯誤 | ✅ 通過 |
| 手動解析成功 | ✅ 通過 |
| 狀態變更正確 | ✅ 通過 |
| Pending/Resolved 分離 | ✅ 通過 |
| 防回滾 | ✅ 通過 |
