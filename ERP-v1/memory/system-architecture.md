# 系統架構

## 主機環境

- **作業系統**: macOS (Darwin)
- **主機**: AI的Mac mini
- **使用者**: aiserver
- **Shell**: zsh

## 目錄結構

```
/Users/aiserver/
├── .openclaw/
│   └── workspace/          # OpenClaw 工作區
│       ├── dashboard-site/ # 看板網站
│       ├── memory/         # 記憶檔案
│       ├── AGENTS.md
│       ├── BOOTSTRAP.md
│       ├── HEARTBEAT.md
│       ├── IDENTITY.md
│       ├── MEMORY.md
│       ├── SOUL.md
│       ├── TOOLS.md
│       └── USER.md
├── srv/
│   ├── db/
│   │   └── company.db      # SQLite 資料庫
│   ├── parser/             # Parser 腳本
│   └── sync/OneDrive/      # OneDrive 同步目錄
│       └── ai_source/
│           ├── roster/     # 班表
│           ├── supervision/# 督導評分
│           ├── feedback/   # 五星評論
│           └── backup/     # 備份
└── OneDrive/               # OneDrive 主目錄
```

## 核心檔案

| 檔案 | 用途 |
|------|------|
| `SOUL.md` | AI 核心人格定義 |
| `USER.md` | 使用者資訊 |
| `IDENTITY.md` | AI 身份設定 |
| `TOOLS.md` | 工具與 API 設定 |
| `AGENTS.md` | 工作區規則 |

## Gunicorn 服務管理

| 服務名稱 | Port | 路徑 | 用途 | 管理方式 |
|---------|------|------|------|---------|
| com.dashboard.gunicorn | 3000 | `~/.openclaw/workspace/dashboard-site/` | ERP v1 (舊系統) | launchctl |
| com.computershop.erpv2 | 8800 | `~/srv/web-site/computershop-erp/` | ERP v2 (新系統) | launchctl |
| com.computershop.website | 8000 | `~/srv/web-site/computershop-web/` | 電腦舖官網 | launchctl |
| com.computershop.student-chat | 329 | `~/srv/web-site/student-chat/` | 學生 AI 聊天室 | launchctl |

### 其他服務

| 服務 | Port | 用途 | 管理方式 |
|------|------|------|---------|
| oMLX | 8001 | 本地 AI 模型 (Qwen3.5-9B-6bit) | 獨立運行 |

### 管理指令

```bash
# 查看狀態
launchctl list | grep -E "(dashboard|computershop)"

# 啟動/停止/重啟
launchctl start com.dashboard.gunicorn         # ERP v1 (3000)
launchctl start com.computershop.erpv2         # ERP v2 (8800)
launchctl start com.computershop.website       # 官網 (8000)
launchctl start com.computershop.student-chat  # 學生聊天室 (329)

launchctl stop com.dashboard.gunicorn
launchctl stop com.computershop.erpv2
launchctl stop com.computershop.website
launchctl stop com.computershop.student-chat
```

### 設定檔位置

- `~/Library/LaunchAgents/com.dashboard.gunicorn.plist`
- `~/Library/LaunchAgents/com.computershop.erpv2.plist`
- `~/Library/LaunchAgents/com.computershop.website.plist`
- `~/Library/LaunchAgents/com.computershop.student-chat.plist`

## Dashboard 網站結構

```
dashboard-site/
├── app.py                    # Flask 主程式
├── index.html               # 首頁
├── admin.html               # 管理控制台
├── system_map_v3.html       # 系統架構圖 V3 (正式版)
├── system_map.html          # 系統架構圖 V2 (備份)
├── shared/
│   ├── auth_ui.js           # 登入組件 v2.0
│   ├── auth_ui.css          # 登入樣式 v2.0
│   └── admin_ui.css         # 管理介面樣式
└── [其他頁面...]
```

## 技術棧

| 層級 | 技術 |
|------|------|
| 前端 | HTML5, CSS3, JavaScript (Vanilla) |
| 後端 | Python Flask |
| 資料庫 | SQLite |
| 圖表 | Chart.js |
| 樣式 | 自定義 CSS + 玻璃擬態設計 |
