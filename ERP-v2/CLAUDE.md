# COSH ERP v2 — 開發規範

設計理念：山中民宿的從容感。所有視覺風格集中在 `static/css/main.css` 的 `:root` 變數。

## 字型規則

| 用途 | 寫法 | 禁止 |
|------|------|------|
| 中文正文 | `var(--font-serif)` | 不可寫 `'Noto Serif TC', serif` |
| 英文裝飾 | `var(--font-en)` | 不可寫 `'Cormorant Garamond', serif` |
| 等寬字體 | `var(--font-mono)` | 不可寫 `'Courier New', monospace` |

JS 內（如 Chart.js config）無法直接用 CSS 變數，請用：
```js
const _cs = getComputedStyle(document.documentElement);
const _fSerif = _cs.getPropertyValue('--font-serif').trim();
const _fEn    = _cs.getPropertyValue('--font-en').trim();
```

唯一例外：SVG `<text>` 的 inline `font-family` 屬性不支援 CSS 變數，可寫死。

## 字體大小

- 全域表單輸入（input / select / textarea）：`16px`（定義在 main.css）
- 頁面級 `.f-input` / `.f-select` / `.f-textarea`：`.84rem`
- 表格內緊湊輸入（`table input`, `table select`）：`.82rem`
- 彈窗編輯欄（`.edit-field input / select`）：`.84rem`
- 顯示用文字（`.empty-hint` 等非表單元素）：`.86rem` 可接受
- 禁止出現 `.86rem` 在任何表單控件上

## 字重

- 正文預設：`300`
- placeholder：`200`
- 強調：用數值 `600` 或 `700`，禁止寫 `font-weight: bold`

## 表單欄位交錯色

所有頁面表單使用 auto-fit grid。奇數位欄位暖米色、偶數位淺色：

- 奇數欄：`background: #f5f0e8`（即 `var(--bg)`）
- 偶數欄：`background: var(--bg-card, #faf8f4)`

因為 CSS specificity 問題（`.f-select` 0,1,0 勝 `select` 0,0,1，但 `.f-input` 0,1,0 輸 `input[type="date"]` 0,1,1），必須用 **ID selector** 逐欄位覆蓋：

```css
#fDate     { background: #f5f0e8; }        /* 奇數 */
#fCompany  { background: var(--bg-card); }  /* 偶數 */
#fOrderNo  { background: #f5f0e8; }        /* 奇數 */
```

新增頁面時，先確認第一個欄位是 input 還是 select，再決定奇偶起始。

## 色彩變數（禁止硬編碼）

| 變數 | 色碼 | 用途 |
|------|------|------|
| `--bg` | `#f5f0e8` | 主背景、奇數欄 |
| `--bg-card` | `#faf8f4` | 卡片、偶數欄 |
| `--bg-alt` | `#ede8e0` | sidebar 等次要背景 |
| `--text` | `#2c2720` | 主文字 |
| `--text-sub` | `#9a9188` | 次要文字 |
| `--brand` | `#FABF13` | 只用於 focus / active 狀態 |
| `--border` | `rgba(107,95,82,.15)` | 細線 |
| `--border-mid` | `rgba(107,95,82,.25)` | 稍粗線 |

## 新頁面 Checklist

建立新 template 時，依序確認：

1. 繼承 `base.html`（AI 助理、sidebar 自動載入）
2. 主佈局容器不設 `max-width`，寬度交由 `.content-area` 控制
3. 字型全部用 `var(--font-serif)` 等變數，不寫死字體名稱
4. 表單控件 font-size 用 `.84rem`，不用 `.86rem`
5. 交錯色用 ID selector 覆蓋，不靠 class
6. 顏色用 CSS 變數，不寫死 hex（`#f5f0e8` 等常用色直接用對應變數）
7. font-weight 用數值不用 `bold`
8. 按鈕樣式用 `btn-primary` / `btn-secondary` / `btn-danger`（定義在 main.css），不自訂
9. 按鈕圓角統一 `border-radius: 8px`（方形帶圓角），禁止使用 `999px`（藥丸形）
10. 狀態篩選 / 排序切換使用 **Segmented Control**（分組按鈕），不用膠囊標籤或底線式 Tab

## Segmented Control（分組按鈕）

用於狀態篩選、排序切換等場景（參考 `personal.html` 的期間 / 排序列）：

```css
.xxx-tabs {                                          /* 外框容器 */
  display: flex;
  border: 1px solid rgba(107,95,82,.2);
  border-radius: 8px;
  overflow: hidden;
  width: fit-content;
}
.xxx-tab {                                           /* 各按鈕 */
  padding: 7px 15px; font-size: .82rem; font-weight: 300;
  font-family: var(--font-serif); letter-spacing: .04em;
  background: none; border: none; color: var(--accent);
  cursor: pointer; transition: background .15s;
}
.xxx-tab + .xxx-tab { border-left: 1px solid rgba(107,95,82,.2); }
.xxx-tab.active { background: var(--text); color: var(--bg); }
```

禁止使用：膠囊式（`border-radius: 20px` 獨立按鈕）或底線式（`border-bottom` 指示器）做狀態篩選。

## 手機版樣式規則

所有手機版樣式一律寫在 `@media (max-width: 767px)` 區塊內，**禁止修改現有的桌機版樣式規則**，只能在媒體查詢內新增。

- 頁面級手機樣式寫在各 template 的 `<style>` 內，用 `@media (max-width: 767px) { ... }`
- 全站共用的手機樣式寫在 `main.css` 的媒體查詢區塊
- 桌機版（≥ 768px）使用左側側邊欄，手機版（< 768px）使用底部導覽列（定義在 `base.html`）
- 底部導覽列固定五個入口：首頁、需求、庫存、待處理、更多

## 頁面佈局寬度

所有操作頁面的主佈局容器（如 `.xx-layout`）**禁止設 `max-width`**（用 `none` 或不寫）。
寬度由 `base.html` 的 `.content-area` 統一控制（內距居中，最大內寬 1160px）。

唯一例外：`print_letter.html` 等列印專用模板可保留固定寬度（A4 排版需要）。

## 銷貨單號規則

格式：`{店碼}-{YYYYMMDD}-{NNN}`（西元年，三位流水號）

合併規則：**同日期 + 同業務 + 同客戶 = 同一張銷貨單號**

店碼對照（依業務員所屬門市）：

| 門市 | 店碼 | 業務員 |
|------|------|--------|
| 豐原 | FY | 林榮祺、林峙文、莊圍迪 |
| 潭子 | TZ | 劉育仕、林煜捷 |
| 大雅 | DY | 張永承、張家碩 |
| 業務部 | OW | 張芯瑜、梁仁佑、鄭宇晉、萬書佑、黃柏翰、黃環馥、黎名燁 |

未知業務員預設 OW。SL（神岡）已停用。

## 後端注意事項

### ok() 回傳格式

`ok()` helper 回傳 `{success: true, **kwargs}`，kwargs 在頂層，**不是** 巢狀在 `data` 下。

### HTTP 請求（macOS 26 + Python 3.14 + Gunicorn）

在 Gunicorn worker 中使用 `requests` 庫，**必須**在 module level 建立 Session 並關閉系統代理偵測，否則 macOS 26 會觸發 SIGKILL：

```python
import requests as _requests_lib
_OMLX_SESSION = _requests_lib.Session()
_OMLX_SESSION.trust_env = False   # ← 關鍵：避免系統代理偵測導致 crash
```

禁止在 function 內 `import requests` 或建立新 Session。

### AI 助手（oMLX 本地模型）

- API：`http://127.0.0.1:8001/v1`（OpenAI 相容格式）
- 模型：`gemma-4-e4b-it-8bit`
- API Key：`5211`
- 前端浮動對話框定義在 `base.html`，所有角色可見
- 後端路由：`/api/ai/chat`，使用 `_OMLX_SESSION.post()` + `timeout=120`

## 資料庫

生產資料庫路徑為 `db/company.db`（根目錄的 `company.db` 是空的，不要用）。

## 建議售價自動帶入

報價（quote_input）與銷貨（sales_input）選擇商品時，單價自動帶入 `Math.round(cost * 1.2)`。

判斷欄位是否為空必須用 `!priceEl.value || priceEl.value === '0'`，因為 `addRow()` 預設 `price=0`，HTML input 的 value 是字串 `"0"`（truthy），單純 `!value` 會誤判為已填寫。

## 檔案結構

```
db/company.db          ← 生產資料庫（SQLite WAL mode）
static/css/main.css    ← 唯一全域樣式來源
templates/base.html    ← 共用骨架（sidebar + AI 助理 + 頁腳）
templates/*.html       ← 各功能頁面，{% extends "base.html" %}
templates/admin/*.html ← 管理後台頁面
```
