# Operations System Runbook
# 故障處理手冊

## 📋 概述

本文件提供 Operations System 常見故障的快速處理指南。
**目標**：任何人照此文件都能在 30 分鐘內完成修復。

---

## 🚨 故障狀況 1：前台送單失敗

### 徵狀
- 員工回報無法送出需求單
- 點擊「提交」後沒反應或顯示錯誤

### Step 1：查看 Log
```bash
# 檢查 Flask 日誌
tail -50 /tmp/flask.log

# 查看是否有 Python 例外
grep -i "error\|exception" /tmp/flask.log | tail -20
```

### Step 2：檢查資料庫連線
```bash
cd /Users/aiserver/srv/db
sqlite3 company.db ".tables"
# 若無回應，表示 DB 被鎖定或損壞
```

### Step 3：檢查 API 狀態
```bash
# 測試 API 是否運作
curl -s "http://localhost:3000/api/needs/recent?department=潭子門市&current_user=測試"
# 應回傳 JSON，若無則服務可能當掉
```

### Step 4：重啟服務（若需要）
```bash
# 1. 找出並停止舊服務
pkill -f "python3 app.py"

# 2. 等待 2 秒
sleep 2

# 3. 重新啟動
cd /Users/aiserver/.openclaw/workspace/dashboard-site
python3 app.py > /tmp/flask.log 2>&1 &

# 4. 驗證
sleep 3
curl -s "http://localhost:3000/api/auth/verify" -X POST \
  -H "Content-Type: application/json" \
  -d '{"password":"2218"}'
```

### Step 5：回滾（若重啟無效）
```bash
# 執行回滾腳本
/Users/aiserver/.openclaw/workspace/dashboard-site/rollback_to_previous.sh
```

---

## 🚨 故障狀況 2：Staging Pending 異常暴增

### 徵狀
- 待建檔中心發現大量 pending 項目
- 員工回報單據「消失」或狀態不對

### Step 1：檢查 Staging 狀態
```bash
cd /Users/aiserver/srv/db
sqlite3 company.db "
SELECT status, type, COUNT(*) as cnt
FROM staging_records
GROUP BY status, type;
"
```

### Step 2：檢查是否有 orphaned needs
```bash
sqlite3 company.db "
SELECT COUNT(*) as orphan_count
FROM needs n
LEFT JOIN staging_records s ON n.customer_staging_id = s.temp_customer_id
WHERE n.customer_staging_id IS NOT NULL AND s.id IS NULL;
"
```

### Step 3：使用 Admin 後台修正
1. 開啟 `https://dashboard.computershop.cc/admin.html`
2. 登入（黃柏翰帳號）
3. 查看「稽核儀表」
4. 依據 A1-A5 代碼執行對應修正

### Step 4：手動回填（若自動修正失敗）
```bash
# 找到 needs 已建立但 staging 未回填的項目
sqlite3 company.db "
SELECT n.id, n.customer_staging_id, s.resolved_code
FROM needs n
JOIN staging_records s ON n.customer_staging_id = s.temp_customer_id
WHERE s.status = 'resolved' AND n.customer_code = '';
"

# 手動執行 UPDATE（請謹慎）
sqlite3 company.db "
UPDATE needs
SET customer_code = (
    SELECT resolved_code FROM staging_records
    WHERE temp_customer_id = needs.customer_staging_id
)
WHERE customer_code = '' AND customer_staging_id IN (
    SELECT temp_customer_id FROM staging_records WHERE status = 'resolved'
);
"
```

---

## 🚨 故障狀況 3：A3 > 0（Needs 指到不存在的正式主檔）

### 徵狀
- 稽核報告顯示 A3 計數 > 0
- 需求單的客戶/產品編號無效

### Step 1：查看詳情
```bash
sqlite3 company.db "
SELECT n.id, n.customer_code, n.product_code, n.item_name
FROM needs n
LEFT JOIN customers c ON n.customer_code = c.customer_id
LEFT JOIN products p ON n.product_code = p.product_code
WHERE (n.customer_code != '' AND n.customer_code NOT LIKE 'TEMP-C-%' AND c.customer_id IS NULL)
   OR (n.product_code NOT LIKE 'TEMP-P-%' AND p.product_code IS NULL)
LIMIT 10;
"
```

### Step 2：決定處理方式
**選項 A：若為暫時編號錯誤**
- 使用 Admin 後台「編輯」功能修正編號

**選項 B：若為正式編號但主檔不存在**
- 建立缺失的主檔記錄，或
- 將 needs 的編號改為有效的暫時編號

### Step 3：使用 Admin 後台修正
1. 登入 Admin 後台
2. 點擊 A3 卡片查看明細
3. 逐筆修正編號

---

## 🚨 故障狀況 4：API 500 Error

### 徵狀
- 頁面顯示「系統錯誤」
- 瀏覽器 Console 看到 500

### Step 1：查看 Flask Log
```bash
tail -100 /tmp/flask.log | grep -A 5 "Error\|Exception"
```

### Step 2：檢查常見問題

**問：Import Error（找不到模組）**
```bash
# 重新安裝依賴
pip3 install flask flask-cors apscheduler
```

**問：Database Locked**
```bash
# 檢查是否有其他程序佔用 DB
lsof /Users/aiserver/srv/db/company.db

# 等待或重啟相關服務
```

**問：Syntax Error**
```bash
# 檢查 Python 語法
cd /Users/aiserver/.openclaw/workspace/dashboard-site
python3 -m py_compile app.py
```

### Step 3：回滾（若無法快速修復）
```bash
# 執行回滾
/Users/aiserver/.openclaw/workspace/dashboard-site/rollback_to_previous.sh

# 重啟服務
pkill -f "python3 app.py"
sleep 2
cd /Users/aiserver/.openclaw/workspace/dashboard-site
python3 app.py > /tmp/flask.log 2>&1 &
```

---

## 📞 緊急聯絡

若以上步驟都無法解決：
1. 記錄錯誤訊息和 Log
2. 聯絡技術負責人
3. 考慮暫時切換到備援系統（若有的話）

---

## 📁 重要檔案位置

| 檔案 | 路徑 |
|------|------|
| 主程式 | `/Users/aiserver/.openclaw/workspace/dashboard-site/app.py` |
| 資料庫 | `/Users/aiserver/srv/db/company.db` |
| 日誌 | `/tmp/flask.log` |
| 備份 | `/Users/aiserver/.openclaw/workspace/dashboard-site/backups/` |
| Deploy 腳本 | `/Users/aiserver/.openclaw/workspace/dashboard-site/deploy_switch_to_v2.sh` |
| Rollback 腳本 | `/Users/aiserver/.openclaw/workspace/dashboard-site/rollback_to_previous.sh` |

---

## ✅ 每日健康檢查

```bash
# 檢查服務狀態
curl -s "http://localhost:3000/api/admin/audit/summary?admin=黃柏翰" | python3 -m json.tool

# 檢查 A1-A5 計數
cd /Users/aiserver/srv/db
sqlite3 company.db "
SELECT 'A1' as code, COUNT(*) as cnt FROM (
    SELECT s.id FROM staging_records s
    JOIN needs n ON s.temp_customer_id = n.customer_staging_id
    WHERE s.status = 'resolved' AND n.customer_code = ''
)
UNION ALL
SELECT 'A3', COUNT(*) FROM (
    SELECT n.id FROM needs n
    LEFT JOIN customers c ON n.customer_code = c.customer_id
    WHERE n.customer_code != '' AND n.customer_code NOT LIKE 'TEMP-C-%' AND c.customer_id IS NULL
);
"
```

---

**建立時間**：2026-03-01
**版本**：1.0
**更新頻率**：每次重大變更後更新
