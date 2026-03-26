# ERP AI 聊天機器人實作規格

## 模型設定
- **模型**: 本機 oMLX
- **模型名稱**: `Qwen3.5-9B-6bit`
- **API 端點**: `http://127.0.0.1:8001/v1/chat/completions`
- **API Key**: `5211`

## 回答範圍
不限，開放給內部員工使用，可回答 ERP 操作、業務問題、一般知識等所有問題。

---

## 後端（Python Flask）

### 1. 建立 Session（必要設定）
```python
import requests

_OMLX_SESSION = requests.Session()
_OMLX_SESSION.trust_env = False  # 必要！避免 macOS 26 + Gunicorn fork crash
```

### 2. API 路由
```python
@app.route('/api/chat', methods=['POST'])
def chat():
    """
    接收: { messages: [...], session_id: "..." }
    回傳: SSE 串流
    """
    pass
```

### 3. 串流處理
- 透過 SSE (Server-Sent Events) 串流回傳模型回應
- 串流結束後將完整對話寫入 SQLite

### 4. 資料庫寫入
**資料表**: `chat_logs`
| 欄位 | 型別 | 說明 |
|------|------|------|
| session_id | TEXT | 對話 session ID |
| user_message | TEXT | 使用者訊息 |
| bot_reply | TEXT | 機器人回覆 |
| created_at | DATETIME | 建立時間 |

### 5. System Prompt
```
你是公司內部 AI 助理，可以回答任何問題，包含 ERP 操作、業務流程、一般知識。
```

---

## 前端（浮動視窗）

### 1. UI 設計
- 右下角浮動機器人按鈕
- 點擊展開聊天視窗
- 支援多輪對話（完整 history 帶入）

### 2. Session 管理
- 使用 `sessionStorage` 產生 `sessionId`
- 每次請求帶入 `sessionId`

### 3. 串流支援偵測
```javascript
// 偵測 ReadableStream 支援
if (window.ReadableStream && resp.body) {
    // 使用串流
} else {
    // Fallback: resp.text() 一次解析
}
```

### 4. 思考區塊過濾
自動過濾 Qwen3 的 `<think>…</think>` 思考區塊，只顯示最終答案。

### 5. 輸入行為
- **Enter**: 換行
- **傳送按鈕**: 送出訊息
- 送出後自動清空輸入框

---

## Gunicorn 設定

**檔案**: `gunicorn.conf.py`

```python
worker_class = "gthread"
threads = 4
timeout = 180
```

⚠️ **重要**: sync worker + 短 timeout 會讓 SSE 串流被 SIGKILL，必須改成 gthread。

---

## 參考實作
官網已有類似架構，可參考其做法進行實作。
