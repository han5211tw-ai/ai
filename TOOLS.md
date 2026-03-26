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

### TTS (Edge TTS) - 預設語音工具

**類型:** Microsoft Edge 線上 TTS 服務（免費，需網路連線）
**安裝日期:** 2026-03-23
**版本:** 7.2.8
**安裝方式:** `pipx install edge-tts`

**預設語音:**
- **zh-TW-HsiaoChenNeural** (曉辰) - 台灣女生，溫暖自然，適合正式場合

**可用中文語音:**
| 語音 | 地區 | 性別 | 特色 |
|------|------|------|------|
| zh-TW-HsiaoChenNeural | 台灣 | 女 | 溫暖自然（預設）|
| zh-TW-HsiaoYuNeural | 台灣 | 女 | 活潑輕快 |
| zh-TW-YunJheNeural | 台灣 | 男 | 沉穩可靠 |
| zh-CN-XiaoxiaoNeural | 中國 | 女 | 新聞播報風格 |
| zh-HK-HiuGaaiNeural | 香港 | 女 | 粵語 |

**基本使用方法:**
```bash
# 基本語音合成
edge-tts --voice zh-TW-HsiaoChenNeural --text "你好" --write-media output.mp3

# 調整語速和音調
edge-tts --voice zh-TW-HsiaoChenNeural --rate "+20%" --pitch "+10Hz" --text "你好" --write-media output.mp3

# 生成字幕
edge-tts --voice zh-TW-HsiaoChenNeural --text "你好" --write-media output.mp3 --write-subtitles output.vtt

# 直接播放（使用 mpv）
edge-playback --voice zh-TW-HsiaoChenNeural --text "你好"
```

**列出所有語音:**
```bash
edge-tts --list-voices
edge-tts --list-voices | grep "zh-"  # 只顯示中文語音
```

**測試結果:** ✅ 2026-03-23 安裝成功，中文語音品質優秀

---

### TTS (sherpa-onnx) - 備用離線方案

**類型:** 本地離線文字轉語音（免費，無需 API key，無需網路）
**模型:** vits-melo-tts-zh_en（中文+英文，支援中英混合）
**路徑:** `~/.openclaw/tools/sherpa-onnx-tts/`
**狀態:** 備用方案，當 Edge TTS 無法使用時啟用

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

**Repo:** `https://github.com/han5211tw-ai/ERP.git`  
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

---

### OpenClaw Browser 自動化

**用途:** 控制瀏覽器進行網頁自動化操作、功能測試、資料抓取
**底層技術:** Playwright (Chrome/Firefox/Edge)
**設定日期:** 2026-03-18

**兩種連線方式:**

| 方式 | 參數 | 使用情境 |
|------|------|----------|
| **本機瀏覽器** | `profile="user"` | 連上已開啟的 Chrome，保留登入狀態 |
| **Chrome 擴充** | `profile="chrome-relay"` | 透過 Browser Relay 擴充功能 attach 特定分頁 |

**基本操作流程:**
```python
# 1. 檢查瀏覽器狀態
browser action="status" profile="user"

# 2. 列出所有分頁
browser action="tabs" profile="user"

# 3. 對特定分頁截圖/操作
browser action="snapshot" profile="user" targetId="<tab_id>"
browser action="click" profile="user" targetId="<tab_id>" ref="<element_ref>"
```

**實際測試記錄:**
- ✅ 2026-03-18 成功連上本機 Chrome (PID: 5133)
- ✅ 可讀取分頁列表、頁面結構、執行點擊操作
- ✅ 支援電腦舖官網 (computershop.shop) 自動化測試

**應用場景:**
- 網站功能自動化測試
- 登入流程驗證
- 表單填寫測試
- 視覺回歸測試（截圖比對）
- 競品價格監控

---

### Git LFS (Large File Storage)

**用途:** 管理 Git 倉庫中的大檔案（如 log 檔）
**安裝日期:** 2026-03-24
**版本:** 3.7.1

**安裝指令:**
```bash
brew install git-lfs
git lfs install
```

**設定追蹤檔案類型:**
```bash
# 追蹤所有 .log 檔案
git lfs track "*.log"

# 追蹤特定目錄下的大檔案
git lfs track "server/*.log"
```

**常用指令:**
```bash
git lfs status          # 查看 LFS 狀態
git lfs ls-files        # 列出被 LFS 管理的檔案
git lfs migrate info    # 查看倉庫中哪些檔案應該用 LFS
```

**目前設定:**
- 追蹤 `*.log` 檔案
- `.gitattributes` 已加入版本控制

---

### 電腦舖官網 (Website)

**本地路徑:** `~/srv/web-site/computershop-web/`
**GitHub Repo:** `https://github.com/han5211tw-ai/WEB.git`
**部署位置:** `/srv/web-site/computershop-web/` (生產環境)
**本地開發:** Port 8000

**Deploy Key:**
- **Key 位置:** `~/.ssh/cosh_deploy_key`
- **設定日期:** 2026-03-18
- **SSH Config:** `~/.ssh/config` 已設定 `Host github.com` 使用此金鑰

**常用指令:**
```bash
# Push 到 GitHub
cd ~/srv/web-site/computershop-web
git push origin main

# 測試 SSH 連線
ssh -T git@github.com
```

---

Add whatever helps you do your job. This is your cheat sheet.
