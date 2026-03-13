# Operations System Runbook v2.0
# 可追溯 + 可定位觀測系統故障排查手冊

**目標**：任何人照此文件都能在 10 分鐘內定位問題根源。

---

## 🚨 快速診斷入口

開啟 Admin 後台：`https://dashboard.computershop.cc/admin.html`

查看三大區塊：
1. **FRESHNESS (資料新鮮度)** - 各資料源最新日期
2. **INGEST (匯入狀態)** - 昨日應有 vs 實際筆數
3. **CONSISTENCY (一致性)** - A1~A5 + 孤兒記錄

---

## 📊 症狀→排查路徑

### 症狀 1：需求表送不出去（前台員工回報）

**Step 1：確認 API 狀態**
```bash
# 檢查 API 是否存活
curl -s "http://localhost:3000/api/needs/recent?department=潭子門市&current_user=test"
```

**Step 2：查看 API 效能指標**
```sql
-- 查詢 /api/needs/batch 最近效能
SELECT 
    endpoint,
    COUNT(*) as calls,
    AVG(duration_ms) as avg_ms,
    MAX(duration_ms) as max_ms,
    SUM(error_count) as errors
FROM api_metrics
WHERE endpoint = '/api/needs/batch'
  AND ts > datetime('now', '-1 hour')
GROUP BY endpoint;
```

**Step 3：查看失敗事件**
```sql
-- 查詢最近失敗的送單事件
SELECT ts, actor, status, summary, error_code, error_stack, trace_id
FROM ops_events
WHERE event_type = 'NEEDS_SUBMIT'
  AND status = 'FAIL'
  AND ts > datetime('now', '-1 hour')
ORDER BY ts DESC;
```

**Step 4：查看追蹤詳情**
```bash
# 用 trace_id 追蹤完整流程
curl -s "http://localhost:3000/api/admin/trace/{trace_id}"
```

**處置**：
- API 回應慢 → 檢查資料庫連線、考慮重啟
- 大量 500 錯誤 → 立即回滾
- 單筆失敗 → 請員工重試

---

### 症狀 2：庫存查不到 / 顯示不正確

**Step 1：檢查 FRESHNESS**
```sql
-- 查看 inventory 最新日期
SELECT data_source, latest_business_date, lag_days, status
FROM freshness_cache
WHERE data_source = 'inventory';
```

**Step 2：檢查 INGEST**
```sql
-- 查看 inventory_parser 最後執行狀態
SELECT ts, source, status, summary, trace_id
FROM ops_events
WHERE source LIKE '%inventory%'
  AND event_type = 'IMPORT'
ORDER BY ts DESC
LIMIT 5;
```

**Step 3：檢查失敗原因**
```sql
-- 查看錯誤詳情
SELECT ts, summary, error_stack, details_json
FROM ops_events
WHERE source LIKE '%inventory%'
  AND status = 'FAIL'
ORDER BY ts DESC
LIMIT 1;
```

**處置**：
- lag_days > 0 → 手動執行 inventory_parser
- 有 FAIL 記錄 → 根據錯誤訊息修復後重跑
- 無記錄 → 檢查排程是否執行

---

### 症狀 3：整體狀態紅燈 (Overall FAIL)

**Step 1：確定哪個區塊導致**
```sql
-- 查看各區塊狀態
SELECT 
    (SELECT COUNT(*) FROM freshness_cache WHERE status = 'FAIL') as freshness_fail,
    (SELECT COUNT(*) FROM needs n 
     LEFT JOIN products p ON n.product_code = p.product_code 
     WHERE n.product_code != '' AND n.product_code NOT LIKE 'TEMP-P-%' AND p.product_code IS NULL) as a3_count,
    (SELECT COUNT(*) FROM api_metrics 
     WHERE ts > datetime('now', '-1 hour') AND error_count > 0) as api_errors;
```

**Step 2：根據區塊深入排查**

| 紅燈區塊 | 排查 SQL |
|---------|---------|
| FRESHNESS | `SELECT * FROM freshness_cache WHERE status = 'FAIL'` |
| INGEST | `SELECT * FROM ops_events WHERE event_type = 'IMPORT' AND status = 'FAIL' ORDER BY ts DESC LIMIT 5` |
| CONSISTENCY A3 | `SELECT n.id, n.product_code, n.item_name FROM needs n LEFT JOIN products p ON n.product_code = p.product_code WHERE p.product_code IS NULL LIMIT 20` |
| API | `SELECT endpoint, AVG(duration_ms) as avg_ms, SUM(error_count) as errors FROM api_metrics WHERE ts > datetime('now', '-1 hour') GROUP BY endpoint ORDER BY errors DESC` |

**處置**：
- FRESHNESS → 手動執行對應 parser
- INGEST → 根據錯誤訊息修復
- CONSISTENCY → 使用 Admin 後台「一鍵修正」
- API → 重啟服務或檢查資料庫

---

### 症狀 4：匯入缺資料（昨天資料沒進來）

**Step 1：查看 INGEST 狀態**
```sql
SELECT data_source, yesterday_count, latest_business_date, status
FROM freshness_cache
WHERE status IN ('FAIL', 'WARN');
```

**Step 2：查看最後一次成功/失敗**
```sql
-- 最後成功
SELECT ts, source, trace_id, summary
FROM ops_events
WHERE event_type = 'IMPORT' AND status = 'OK'
ORDER BY ts DESC LIMIT 1;

-- 最後失敗
SELECT ts, source, trace_id, summary, error_stack
FROM ops_events
WHERE event_type = 'IMPORT' AND status = 'FAIL'
ORDER BY ts DESC LIMIT 1;
```

**Step 3：確認是否為週末**
```sql
SELECT 
    datetime('now') as now,
    strftime('%w', 'now') as weekday,
    CASE strftime('%w', 'now')
        WHEN '0' THEN '週日' WHEN '1' THEN '週一' WHEN '2' THEN '週二'
        WHEN '3' THEN '週三' WHEN '4' THEN '週四' WHEN '5' THEN '週五'
        WHEN '6' THEN '週六'
    END as weekday_name;
```

**處置**：
- 週末進貨為 0 → 正常（非工作日），顯示為 WARN 不是 FAIL
- 工作日缺少 → 手動執行對應 parser
- 有 FAIL 記錄 → 根據錯誤訊息修復

---

### 症狀 5：數字對不起來（報表不一致）

**Step 1：確認資料日期**
```sql
-- 查看各表最新日期
SELECT 'sales' as source, MAX(date) as latest_date, COUNT(*) as total FROM sales_history
UNION ALL
SELECT 'purchase', MAX(date), COUNT(*) FROM purchase_history
UNION ALL
SELECT 'inventory', MAX(report_date), COUNT(*) FROM inventory;
```

**Step 2：檢查一致性問題**
```sql
-- A3: Needs 指到不存在的主檔
SELECT COUNT(*) as orphan_count FROM (
    SELECT n.id FROM needs n
    LEFT JOIN products p ON n.product_code = p.product_code
    WHERE n.product_code != '' AND n.product_code NOT LIKE 'TEMP-P-%' AND p.product_code IS NULL
);

-- A5: 同名產品多碼
SELECT product_name, COUNT(DISTINCT product_code) as code_count
FROM products
GROUP BY product_name
HAVING code_count > 1;
```

**處置**：
- 日期不一致 → 執行對應 parser 補齊
- A3/A5 問題 → 使用 Admin 後台「一鍵修正」

---

## 🔧 常用排查指令速查

### 查看最近事件
```sql
-- 所有事件
SELECT ts, event_type, source, status, summary, trace_id
FROM ops_events
WHERE ts > datetime('now', '-1 hour')
ORDER BY ts DESC;

-- 只看失敗
SELECT ts, event_type, source, summary, error_code, trace_id
FROM ops_events
WHERE status = 'FAIL'
  AND ts > datetime('now', '-1 hour')
ORDER BY ts DESC;
```

### 用 trace_id 追蹤
```sql
-- 查詢特定 trace_id 的所有事件
SELECT ts, event_type, source, status, summary, duration_ms
FROM ops_events
WHERE trace_id = 'YOUR_TRACE_ID'
ORDER BY ts;
```

### 查看 Parser 執行狀態
```sql
SELECT 
    source,
    COUNT(*) as runs,
    SUM(CASE WHEN status = 'OK' THEN 1 ELSE 0 END) as success,
    SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) as failed,
    MAX(CASE WHEN status = 'OK' THEN ts END) as last_success,
    MAX(CASE WHEN status = 'FAIL' THEN ts END) as last_fail
FROM ops_events
WHERE event_type = 'IMPORT'
  AND ts > datetime('now', '-24 hours')
GROUP BY source;
```

### 查看 API 效能
```sql
-- P50/P95 延遲
SELECT 
    endpoint,
    COUNT(*) as calls,
    AVG(duration_ms) as avg_ms,
    (SELECT duration_ms FROM api_metrics m2 
     WHERE m2.endpoint = m1.endpoint 
     ORDER BY duration_ms 
     LIMIT 1 OFFSET (SELECT COUNT(*)/2 FROM api_metrics WHERE endpoint = m1.endpoint)) as p50_ms
FROM api_metrics m1
WHERE ts > datetime('now', '-1 hour')
GROUP BY endpoint
ORDER BY calls DESC;
```

---

## 🔄 回滾條件與指令

### 何時應該回滾

| 狀況 | 回滾？ | 說明 |
|------|--------|------|
| 單一 API 偶發錯誤 | ❌ 否 | 可能是暫時問題，觀察即可 |
| 所有 API 500 錯誤 | ✅ 是 | 系統性問題，立即回滾 |
| Parser 執行失敗 | ❌ 否 | 修復後重跑即可 |
| DB locked/connection error | ✅ 是 | 可能是 migration 問題 |
| 資料嚴重不一致 | ⚠️ 評估 | 先備份再決定 |

### 回滾指令

```bash
# 1. 先備份當前狀態（重要！）
cd /Users/aiserver/.openclaw/workspace/dashboard-site
cp app.py app.py.$(date +%Y%m%d%H%M).pre_rollback
cp needs_input.html needs_input.html.$(date +%Y%m%d%H%M).pre_rollback

# 2. 執行回滾腳本
./rollback_to_previous.sh

# 3. 重啟服務
pkill -f "python3 app.py"
sleep 2
python3 app.py > /tmp/flask.log 2>&1 &

# 4. 驗證
sleep 3
curl -s "http://localhost:3000/api/health"

# 5. 記錄回滾事件
# （在 Admin 後台手動記錄，或執行以下 SQL）
# INSERT INTO ops_events (event_type, source, status, summary) 
# VALUES ('ROLLBACK', 'manual', 'OK', '回滾到上一版本');
```

---

## 📞 緊急聯絡

若 Runbook 無法解決問題：

1. **記錄以下資訊**：
   - 錯誤發生時間
   - 錯誤訊息截圖
   - trace_id（從 ops_events 查詢）
   - 最近 50 行 Flask log: `tail -50 /tmp/flask.log`

2. **聯絡技術負責人** 並提供上述資訊

---

## 📝 版本記錄

| 版本 | 日期 | 更新內容 |
|------|------|---------|
| v2.0 | 2026-03-01 | 新增 ops_events 追蹤、三區塊健康檢查、10分鐘定位流程 |
| v1.0 | 2026-02-28 | 初始版本 |

---

**維護者**：Yvonne  
**最後更新**：2026-03-01
