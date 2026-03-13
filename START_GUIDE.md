# 手動啟動指南

## 問題原因
多個 Flask 進程衝突導致端口被佔用。

## 解決步驟

### 1. 終止所有 Python 進程
打開終端機，執行：
```bash
ps aux | grep python3 | grep -v grep
```
找到所有 python3 進程，然後：
```bash
kill -9 <PID>
```
（將 <PID> 替換為實際的進程 ID）

### 2. 確認端口已釋放
```bash
# 應該沒有 python3 進程顯示
ps aux | grep python3 | grep -v grep
```

### 3. 啟動 Flask 服務
```bash
cd /Users/aiserver/.openclaw/workspace/dashboard-site
python3 app.py
```

### 4. 測試 API
打開另一個終端機視窗：
```bash
# 測試資料庫監控
curl http://localhost:3000/api/admin/db/row-stats

# 測試 Admin 稽核
curl "http://localhost:3000/api/admin/audit/summary?admin=黃柏翰"
```

### 5. 訪問頁面
- 健康檢查：http://localhost:3000/admin/health.html
- Admin 後台：http://localhost:3000/admin.html

## 常見問題

Q: 如果端口 3000 被佔用？
A: 修改 app.py 最後一行：
```python
app.run(host='0.0.0.0', port=3001, debug=False)
```
然後使用 http://localhost:3001

## 注意事項
- 保持終端機開啟，Flask 服務會在背景運行
- 按 Ctrl+C 可以停止服務
