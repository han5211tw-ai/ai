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
