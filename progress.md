# 前端視覺優化進度追蹤
> 任務：OpenClaw ERP 前端視覺優化（方案 B：保留暗色科技感 + 導入 CIS 品牌黃）
> 建立日期：2026-03-18
> 色系依據：COSH 電腦舖品牌識別手冊（品牌黃 #FABF13、品牌黑 #231815）

---

## ✅ 已完成步驟

### 步驟 1-2：文件閱讀與分析（完成）
- 閱讀 ERP_Whitepaper_v3.0.md 及 CIS 品牌識別手冊
- 擷取色票：品牌黃 #FABF13、品牌黑 #231815
- 確認修改範圍：global.css、auth_ui.css、base.html

---

### 步驟 3：CSS 變數色票建立（完成）
**修改檔案：** `shared/global.css`

新增 CIS 色票變數（`:root` 區塊）：
- `--color-brand-primary: #FABF13`（CIS 輔助黃）
- `--color-brand-black: #231815`（CIS 品牌黑）
- `--color-brand-yellow-10/20/30`（透明度系列）
- `--shadow-glow`、`--shadow-glow-hover`：改為品牌黃光暈
- `--color-bg-active`：改為黃 10% 透明底
- `--color-border-accent`、`--color-border-focus`：改為品牌黃

保留備用：
- `--color-accent-cyan: #00d4ff`（圖表/資料視覺化專用）
- `--color-accent-purple: #7b2cbf`（同上）

---

### 步驟 4：統一按鈕樣式（完成）
**修改檔案：** `shared/global.css`

- `.btn-primary`：品牌黃漸層（#FABF13 → #e6a800），文字色改為品牌黑
- `.btn-primary:hover`：品牌黃 glow
- `.btn-primary:active`：新增 active 狀態
- `.btn-save`：同 primary
- `.btn-secondary:active`：新增品牌黃 active 狀態
- `.btn-danger`：保持紅色，補上 active 狀態

---

### 步驟 5：統一輸入框 / 選單樣式（完成）
**修改檔案：** `shared/global.css`

- `.form-input:focus`：品牌黃 border + 黃 20% box-shadow
- `.form-input:hover`：黃 30% border hover 效果
- `.form-field input/select/textarea:focus`：同上
- 所有輸入框字體：`max(var(--font-size-md), 16px)`（防 iOS 自動縮放）
- 加上 `-webkit-appearance: none`（移除 iOS 預設樣式）

---

### 步驟 6：修復手機版跑版（完成）
**修改檔案：** `shared/global.css`、`base.html`

- `body`：加上 `overflow-x: hidden; max-width: 100vw`
- `.content-workspace`：加上 `overflow-x: hidden; max-width: 100%`
- `.main-content`：加上 `max-width: 100%; overflow-x: hidden`
- 新增 `.table-responsive`：`overflow-x: auto; -webkit-overflow-scrolling: touch`
- 手機版（<768px）：表格加 `min-width: 600px`、表單欄位 `min-width: 100%`

---

### 步驟 7：修正 menuSearchInput 缺失 Bug（完成）
**修改檔案：** `base.html`

- 在 sidebar 中補上缺失的 `<input id="menuSearchInput">` HTML 元素
- 搜尋框字體大小：16px（防 iOS 縮放）
- focus 樣式：品牌黃 border + 黃 20% glow

---

### 步驟 8：全面 RWD breakpoint 調整（完成）
**修改檔案：** `base.html`（base template 層統一處理）

- 手機版 < 768px：表格可橫向滾動
- 表單欄位手機版全寬
- 輸入框 `max-width: 100%` 保護

---

### 步驟 3b：auth_ui.css 品牌色更新（完成）
**修改檔案：** `shared/auth_ui.css`

- `:root` 色票：全面改用品牌黃
- 登入背景光暈：改為黃色漸層
- 旋轉外圈：改為品牌黃 40% 透明
- 盾牌圖示 / 鎖圖示：改為品牌黃
- 登入按鈕：品牌黃漸層，文字色改為品牌黑
- 輸入框 focus / 狀態點 / loading 文字：全改為品牌黃

---

### 步驟 3c：base.html 互動色更新（完成）
**修改檔案：** `base.html`

- Sidebar 選單 active 狀態：`#00d4ff` → `#FABF13`
- Logo 漸層：改為品牌黃
- User avatar 漸層：改為品牌黃
- 首頁按鈕（btn-home）：改為品牌黃
- 游標（dot + ring）：改為品牌黃 glow
- 粒子背景顏色：改為品牌黃

---

## 📁 修改的檔案清單

| 檔案 | 修改內容 |
|------|---------|
| `shared/global.css` | CSS 變數、按鈕、輸入框、表格、overflow 保護 |
| `shared/auth_ui.css` | 登入元件全面品牌黃化 |
| `base.html` | Sidebar 色彩、Logo、游標、粒子、menuSearchInput 補上、RWD 保護 |

## 🎨 色票對照

| 用途 | 舊色 | 新色 |
|------|------|------|
| 主要強調色 | `#00d4ff` (cyan) | `#FABF13` (CIS 品牌黃) |
| 主要漸層 | cyan → purple | `#FABF13 → #e6a800` |
| 按鈕文字 | white | `#231815` (CIS 品牌黑) |
| 圖表/視覺化 | 保留 `#00d4ff` | 保留 `#00d4ff` (不動) |

## ✅ 完成狀態：全部步驟已完成
