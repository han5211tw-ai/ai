# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

### API Keys

- Brave Search: `BSAkRFXkBoZ3j1lnCsAVA7wXJpCZu9z` — 設定於環境變數 `export BRAVE_API_KEY="..."

### TTS (sherpa-onnx)

**類型:** 本地離線文字轉語音（免費，無需 API key）
**模型:** vits-melo-tts-zh_en（中文+英文，支援中英混合）
**路徑:** `~/.openclaw/tools/sherpa-onnx-tts/`

**環境變數設定:**
```bash
export SHERPA_ONNX_RUNTIME_DIR="$HOME/.openclaw/tools/sherpa-onnx-tts/runtime"
export SHERPA_ONNX_MODEL_DIR="$HOME/.openclaw/tools/sherpa-onnx-tts/vits-melo-tts-zh_en"
```

**使用方法:**
```bash
$SHERPA_ONNX_RUNTIME_DIR/bin/sherpa-onnx-offline-tts \
  --vits-model="$SHERPA_ONNX_MODEL_DIR/model.onnx" \
  --vits-lexicon="$SHERPA_ONNX_MODEL_DIR/lexicon.txt" \
  --vits-tokens="$SHERPA_ONNX_MODEL_DIR/tokens.txt" \
  --output-filename="output.wav" "要轉換的文字"
```

**測試結果:** ✅ 2026-03-11 安裝成功，支援中文與英文混合朗讀

---

### Yvonne 專用 Email

**用途:** 郵件收發、通知發送、郵件整理任務
**信箱:** `ai@computershop.cc`
**類型:** Gmail 體系（Google Workspace）
**應用程式密碼:** `wegc emle glvo vjhq`

**使用方式:**
- IMAP/SMTP 協定
- 應用程式密碼用於第三方郵件客戶端（如 himalaya、Python smtplib）
- 一般密碼登入 Gmail 網頁版

**注意事項:**
- 應用程式密碼僅顯示一次，已記錄於此
- 用於自動化郵件任務時請使用應用程式密碼而非一般密碼

### Company Database (唯讀)

**路徑:** `/Users/aiserver/srv/db/company.db` (SQLite)
**權限:** 唯讀 — 只能執行 `SELECT`，禁止 `INSERT`/`UPDATE`/`DELETE`

**核心資料表：**

| 表格 | 用途 | 關鍵欄位 |
|------|------|----------|
| `sales_history` | 銷貨明細 | `invoice_no`, `date`, `salesperson`, `product_name`, `quantity`, `price`, `amount`, `customer_id` |
| `customers` | 客戶主檔 | `customer_id`, `short_name`, `mobile`, `phone1`, `company_address` |
| `inventory` | 庫存 | `product_id`, `item_spec`, `warehouse`, `stock_quantity`, `unit_cost` |
| `staff_roster` | 班表 | `date`, `staff_name`, `location`, `shift_code` |
| `crm_tasks` | 待辦追蹤 | `invoice_no`, `customer_name`, `task_type`, `status` |
| `performance_metrics` | 績效 | `subject_name`, `target_amount`, `revenue_amount`, `achievement_rate` |
| `needs` | 請購單 | `item_name`, `quantity`, `requester`, `status` |
| `purchase` / `purchase_history` | 採購紀錄 | `vendor_name`, `item_name`, `quantity`, `unit_price` |
| `store_reviews` | 評論統計 | `store_name`, `review_count` |

### 資料查詢習慣

- **產品名稱**：一律顯示完整名稱（如「微軟 OFFICE 2024 家用盒裝版」），不可簡化，避免誤會
- **資料呈現**：查詢結果一律使用 Markdown 表格呈現，清晰易讀

---

### Dashboard 網頁伺服器

**正式環境使用 Gunicorn**，不是 Flask 開發伺服器。

**重啟指令:**
```bash
cd /Users/aiserver/.openclaw/workspace/dashboard-site
./manage_gunicorn.sh restart
```

**重要提醒:**
- 修改 `app.py` 後必須重啟 Gunicorn 才能生效
- 開發時不要誤用 `python3 app.py` 或 Flask 內建伺服器
- Gunicorn 設定檔: `gunicorn.conf.py`

---

### 通知機器人 (Telegram Bot)

**正式名稱:** 通知機器人  
**用途:** 需求表通知、微星庫存週報、系統告警  
**Bot Token:** `8623161623:AAGWlwGjp0Vf3bzpiVgLltQFbcGFY4kpFxo`  
**Chat ID:** `8545239755` (Alan)

---

### 需求表通知對象

| 類型 | 發送方式 | 接收對象 | Chat ID |
|------|----------|----------|---------|
| 請購 | 通知機器人 | Alan (老闆) | `8545239755` |
| 調撥 | 通知機器人 | 會計 (黃環馥) | `8203016237` |

### Telegram 群組

| 群組名稱 | Chat ID | 用途 |
|----------|---------|------|
| 電腦舖工作群組 | `-5232179482` | 未來同仁加入後的群組通知 |

**使用方式:**
```python
import requests

TELEGRAM_BOT_TOKEN = "8623161623:AAGWlwGjp0Vf3bzpiVgLltQFbcGFY4kpFxo"
TELEGRAM_CHAT_ID = "8545239755"

def send_telegram_message(message, file_path=None):
    if file_path:
        # 傳送檔案
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
        with open(file_path, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': message}
            response = requests.post(url, files=files, data=data)
    else:
        # 傳送文字
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
        response = requests.post(url, data=data)
    return response
```

**相關腳本:**
- `msi_inventory_report.py` - 微星庫存週報
- `app.py` - 需求表通知 (調撥/請購)

---

### GitHub Deploy Key

**Repo:** `https://github.com/han5211tw-ai/ai.git`  
**Key 位置:** `~/.ssh/github_deploy_key` (ed25519)  
**設定日期:** 2026-03-16

**Push 指令:**
```bash
cd /Users/aiserver/.openclaw/workspace
GIT_SSH_COMMAND="ssh -i ~/.ssh/github_deploy_key -o IdentitiesOnly=yes" git push origin main
```

---

Add whatever helps you do your job. This is your cheat sheet.
