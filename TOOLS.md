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

### Cloudflare Tunnel (網路架構)

**用途:** 將 Mac mini 上的本地服務公開到網際網路，無需固定 IP 或開放 port
**服務商:** Cloudflare (免費方案)
**安裝位置:** Mac mini
**管理介面:** https://one.dash.cloudflare.com/

**目前透過 Cloudflare Tunnel 公開的服務:**
| 服務 | 本地位置 | 公開網址 |
|------|----------|----------|
| ERP 系統 | `localhost:3000` | `https://erp.你的domain.com` |
| 官網 | `localhost:8000` | `https://www.你的domain.com` |
| OpenClaw Gateway | `localhost:18789` | 可新增 subdomain |

**優點:**
- ✅ 免費固定網域（無需像 ngrok 付費）
- ✅ 自動 HTTPS (SSL 憑證由 Cloudflare 管理)
- ✅ 不需要開放路由器 port
- ✅ 適合 LINE Webhook、Telegram Bot 等需要固定 URL 的服務

**新增服務步驟:**
1. 登入 Cloudflare Zero Trust Dashboard
2. Networks → Tunnels → 選擇現有 Tunnel
3. 新增 Public Hostname:
   - Subdomain: `line` (或 `bot`, `webhook`)
   - Domain: 你的 domain
   - Type: HTTP
   - URL: `localhost:18789`
4. 在 LINE Developers Console 設定 Webhook URL: `https://line.你的domain.com/line/webhook`

**相關檔案:**
- `~/.cloudflared/config.yml` - Tunnel 設定檔
- `~/.cloudflared/cert.pem` - 認證檔案

---

### Telegram 工作群組 - Yvonne 權限規則

**適用範圍:** 電腦舖工作群組（以及其他未來可能加入的工作群組）

**群組裡可以執行的查詢:**
| 類型 | 範例 | 說明 |
|------|------|------|
| 庫存查詢 | 「RTX 4060 有沒有貨」 | 公開資訊 |
| 產品價格 | 「Office 2024 多少錢」 | 公開資訊 |
| 訂單狀態 | 「訂單 2025031501 好了嗎」 | 去識別化，只顯示狀態 |
| 營業額/業績 | 「今天業績多少」、「這月目標達成率」 | 已在 ERP 公開 |
| 客戶基本資料 | 「客戶王小明的電話」 | 公司政策允許 |

**群組裡不執行（請私聊 Alan）:**
| 類型 | 原因 |
|------|------|
| 毛利、利潤 | 敏感資訊，僅限老闆 |
| 成本相關數據 | 採購價、進貨成本 |
| 發送通知/郵件 | 需確認身份 |
| 修改任何設定 | 安全原則 |
| 執行任何寫入操作 | 資料庫唯讀政策 |

**回應方式:**
- 群組裡被 @ 或問到允許的問題 → 直接回答
- 問到不允許的問題 → 回覆「這個資訊請私聊 Alan 查詢」
- 不確定能否回答的問題 → 回覆「這個我需要確認一下，請稍等」

---

### ClawdHub CLI (OpenClaw Skill 管理工具)

**用途:** 搜尋、安裝、更新、發布 OpenClaw Agent Skills
**安裝日期:** 2026-03-17
**Registry:** https://clawdhub.com

**安裝指令:**
```bash
npm i -g clawdhub
npm i -g undici  # 需要額外安裝相依套件
```

**常用指令:**
```bash
# 搜尋 skill
clawdhub search "postgres"

# 安裝 skill
clawdhub install my-skill
clawdhub install my-skill --version 1.2.3

# 更新 skill
clawdhub update my-skill
clawdhub update --all

# 列出已安裝 skill
clawdhub list

# 發布 skill（需要登入）
clawdhub login
clawdhub publish ./my-skill --slug my-skill --name "My Skill" --version 1.0.0
```

**注意事項:**
- 預設安裝目錄: `./skills`
- 發布需要 `clawdhub login` 認證
- 可透過 `CLAWDHUB_REGISTRY` 環境變數指定其他 registry

**我們的 Skills:**
| Skill | 路徑 | 狀態 |
|-------|------|------|
| retail-erp-connector | `skills/retail-erp-connector/` | 規格完成，待實作 |
| purchase-request-manager | `skills/purchase-request-manager/` | 規格完成，待實作 |
| roster-performance-tracker | `skills/roster-performance-tracker/` | 規格完成，待實作 |
| google-reviews-automation | `skills/google-reviews-automation/` | 規格完成，待實作 |

---

Add whatever helps you do your job. This is your cheat sheet.
