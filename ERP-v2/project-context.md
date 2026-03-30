# OpenClaw ERP 重建 — 專案背景
## 關於這個專案
這是 COSH 電腦舖（台中豐原/大雅/潭子三門市）的內部 ERP 營運系統重建專案。
系統代號：OpenClaw（對外稱 ERP v2）
目標：在新目錄下全新重建前端，舊系統繼續運行不中斷。

## 關於我
- 姓名：Alan（黃柏翰）
- 身份：電腦舖老闆、系統開發者
- 技術棧：Flask、Jinja2、SQLite、gunicorn、macOS
- 溝通風格：直接、重點式、不需要過多說明

## 目錄結構
```
~/srv/web-site/computershop-erp/    ← 新系統根目錄
├── old system/dashboard-site/        ← 舊系統完整複製副本（唯讀，禁止修改）
├── templates/                        ← 新系統所有頁面放這裡
│   └── admin/                        ← 後台頁面
├── static/                           ← CSS、JS、圖片
│   ├── css/main.css
│   └── js/
├── db/                               ← 資料庫副本（每十分鐘備份一次）
├── app.py                            ← Flask 主程式
├── gunicorn.conf.py                  ← port 8800
├── .env                              ← 環境變數（DB_PATH 等）
├── progress.md                       ← 工作進度記錄
└── project-context.md                ← 本文件
```

## 系統現況
- 舊系統路徑：~/srv/web-site/computershop-erp/old system/dashboard-site/
- 舊系統 port：3000（持續運行，不能動）
- 資料庫：~/srv/web-site/computershop-erp/db/company.db（SQLite + WAL 模式）
- Parser 腳本：~/srv/parser/（11 支，完全不動）
- 白皮書：old system/dashboard-site/ERP_Whitepaper_v4.0.md

## 新系統規格
- 新系統目錄：~/srv/web-site/computershop-erp/
- 新系統 port：8800（測試用，穩定後切換上線）
- templates 目錄：~/srv/web-site/computershop-erp/templates/

## 舊系統參考原則
old system 資料夾是唯讀參考資料，用途如下：
- 理解每個頁面的功能與資料流
- 參考 API 路由與資料庫查詢邏輯
- 了解業務邏輯細節

參考方式：每次重建一個頁面前，先讀取 old system 中對應的舊頁面，
理解其功能後，用全新的視覺語言重新實作，不複製舊的樣式程式碼。

## 視覺定調（重點）
**核心美感：山中民宿、溫泉會館的從容感**

### 色系
```
背景：暖白 #f5f0e8
次要背景/分區：淺霧灰 #e8e2d8
主要文字：深墨色 #2c2720
次要文字：石灰色 #9a9188
細線/裝飾：淺棕 #6b5f52
Sidebar 背景：深墨 #2c2720（同主文字，對比像木框搭和紙）
品牌黃 #FABF13：只用於 focus ring、active 狀態
```

### 字體
- 中文：Noto Serif TC 200/300（纖細、有文人氣質）
- 英文裝飾：Cormorant Garamond 300
- 內文最小 16px（防 iOS 自動縮放）

### 按鈕設計原則
- 主要操作：膠囊形（border-radius: 999px），深墨底色
- 次要操作：無底色 + 細邊框膠囊形
- 危險操作：低調紅棕色，不用鮮豔紅色
- 品牌黃僅用於真正最重要的強調

### 整體空間感
- 大量留白，元素不擁擠
- 分區用細線或色塊輕描，不用粗邊框
- 資訊層次用字型大小與顏色深淺區分

### 輸入框
- padding: 10px 14px
- border-radius: 10px
- font-size: 16px
- border: 1px solid rgba(107,95,82,0.25)
- focus: 細線品牌黃 + 淡黃光暈

## 認證機制
- localStorage 存放 user 資訊：`erp_v2_user`
- 每天 21:00 自動過期：`erp_v2_exp`
- 角色來自 staff_passwords.title
- 老闆 / 會計：全權限

## 品牌核心
COSH = 讓你保持從容
官網主標：讓事情持續運作，讓你保持從容

## 絕對禁止
- 修改或刪除 old system/ 資料夾內任何檔案
- 動任何 Parser 腳本（~/srv/parser/）
- 動任何 Cron 排程
- 動資料庫本體
- 重啟伺服器（需先問我）
- 刪除任何檔案（需先問我）

## 工作方式
- 每次重建一個頁面前，先讀取 old system 對應的舊頁面理解功能
- 理解後用全新視覺語言實作，完成放入 templates/
- 每完成一個步驟立即存檔並更新 progress.md
- 遇到不確定的設計決策先問我
- 每步驟完成後回報，等我確認再繼續
