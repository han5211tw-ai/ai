# DEVELOPMENT_RULES.md - 電腦舖 ERP 系統開發守則

> **最高準則：所有開發工作必須遵守本守則，違規視為未完成。**

---

## 1. 開發前強制步驟

### 1.1 必讀檢查清單
在任何開發工作開始前，必須：
- [ ] 讀取本 DEVELOPMENT_RULES.md 守則
- [ ] 確認目標頁面/功能的需求
- [ ] 檢查是否已有對應的 Macro 元件可用

### 1.2 禁止事項
- ❌ 直接手寫 HTML 表單元素（`<input>`、`<select>`、`<button>` 等）
- ❌ 使用內聯樣式（`style="..."`）
- ❌ 複製貼上舊頁面的非標準 UI 程式碼
- ❌ 建立新的 CSS 類別而不使用現有 Design Tokens

---

## 2. UI 規範標準

### 2.1 視覺設計系統

#### 色彩規範（CSS Variables）
```css
--color-primary: #00d4ff;        /* 主色：青色 */
--color-secondary: #7b2cbf;      /* 輔色：紫色 */
--color-bg-card: rgba(255,255,255,0.03);   /* 卡片背景 */
--color-border: rgba(255,255,255,0.1);     /* 邊框 */
--color-border-input: rgba(255,255,255,0.2); /* 輸入框邊框 */
--color-text-primary: #fff;       /* 主文字 */
--color-text-secondary: #8892b0;  /* 次要文字 */
--color-text-muted: #64748b;      /* 輔助文字 */
```

#### 間距規範
```css
--spacing-xs: 6px;
--spacing-sm: 10px;
--spacing-md: 15px;
--spacing-lg: 20px;
```

#### 圓角規範
```css
--radius-sm: 4px;   /* 小按鈕 */
--radius-md: 6px;   /* 輸入框、按鈕 */
--radius-lg: 8px;   /* 卡片 */
--radius-xl: 12px;  /* 大卡片 */
```

### 2.2 元件規範

所有表單元素必須使用 `macros.html` 提供的 Macro：

| 元素類型 | 禁止使用 | 必須使用 |
|:---|:---|:---|
| 文字輸入 | `<input type="text">` | `{{ input() }}` |
| 數字輸入 | `<input type="number">` | `{{ number() }}` |
| 金額輸入 | `<input type="number">` | `{{ money() }}` |
| 日期選擇 | `<input type="date">` | `{{ date() }}` |
| 下拉選單 | `<select>` | `{{ select() }}` |
| 多行文字 | `<textarea>` | `{{ textarea() }}` |
| 主要按鈕 | `<button class="btn">` | `{{ btn_primary() }}` |
| 次要按鈕 | `<button class="btn-secondary">` | `{{ btn_secondary() }}` |
| 危險按鈕 | `<button class="btn-danger">` | `{{ btn_danger() }}` |
| 資料表格 | `<table>` | `{{ table() }}` |
| 區塊卡片 | `<div class="card">` | `{{ section() }}` |

---

## 3. Jinja2 模板繼承規則

### 3.1 強制繼承結構

所有頁面必須繼承 `base.html`：

```jinja2
{% extends "base.html" %}

{% block title %}頁面標題 - 電腦舖{% endblock %}

{% block page_title %}頁面標題{% endblock %}

{% block styles %}
<!-- 頁面專屬 CSS -->
{% endblock %}

{% block content %}
<!-- 頁面內容 -->
{% endblock %}

{% block scripts %}
<!-- 頁面專屬 JavaScript -->
{% endblock %}
```

### 3.2 禁止事項

- ❌ 使用 `<!DOCTYPE html>`、`<html>`、`<head>`、`<body>` 標籤
- ❌ 載入 `auth_ui.css` 或 `auth_ui.js`（base.html 已處理）
- ❌ 定義 `* { margin: 0; }`、`body { ... }` 等全域樣式
- ❌ 使用 `<h1>` 作為頁面標題（使用 `{% block page_title %}`）

### 3.3 可選區塊

| 區塊 | 用途 | 必填 |
|:---|:---|:---:|
| `title` | 瀏覽器分頁標題 | ✅ |
| `page_title` | 頁面頂部標題 | ✅ |
| `styles` | 頁面專屬 CSS | 選填 |
| `content` | 主要內容 | ✅ |
| `scripts` | 頁面專屬 JS | 選填 |

---

## 4. auth_ui.js 登入組件規範

### 4.1 使用方式

base.html 已自動載入 `auth_ui.js`，頁面只需：

```javascript
// 檢查登入狀態
const user = await requireLogin();
if (!user) return;

// 使用使用者資訊
document.getElementById('userName').textContent = user.name;
document.getElementById('userDept').textContent = user.department;

// 登出
function logout() {
    authLogout();
}
```

### 4.2 禁止事項

- ❌ 自行建立登入表單 HTML
- ❌ 直接操作 `sessionStorage` 儲存登入狀態
- ❌ 使用 `auth_ui.css` 定義的 `.login-section`、`.login-box` 等類別

---

## 5. macros.html 調用規範

### 5.1 載入方式

在模板開頭載入需要的 Macro：

```jinja2
{% from "macros.html" import input, select, date, money, btn_primary, btn_secondary, section, table %}
```

或使用全部：

```jinja2
{% import "macros.html" as ui %}

{{ ui.input(...) }}
{{ ui.btn_primary(...) }}
```

### 5.2 常用 Macro 參考

#### 表單元素
```jinja2
{{ input(name='customer_name', label='客戶名稱', placeholder='請輸入客戶名稱', required=true) }}
{{ select(name='payment_type', label='付款方式', options=[
    {'value': 'cash', 'label': '現金'},
    {'value': 'transfer', 'label': '匯款'}
], required=true) }}
{{ date(name='order_date', label='訂單日期', required=true) }}
{{ money(name='amount', label='金額', value=0, required=true) }}
{{ textarea(name='memo', label='備註', rows=3) }}
```

#### 按鈕
```jinja2
{{ btn_primary(text='儲存', type='submit', icon='💾') }}
{{ btn_secondary(text='取消', onclick='history.back()') }}
{{ btn_danger(text='刪除', onclick='deleteItem()') }}
```

#### 佈局
```jinja2
{% call section(title='基本資料', icon='👤') %}
    <!-- 區塊內容 -->
{% endcall %}

{% call table(headers=['日期', '金額', '狀態']) %}
    <tr><td>...</td></tr>
{% endcall %}
```

### 5.3 尚未建立的 Macro

以下 Macro 待建立，暫時允許手寫（但必須符合 Design Tokens）：

- [ ] `data_table()` - 資料列表（含排序、分頁）
- [ ] `modal()` - 彈出視窗
- [ ] `tabs()` - 頁籤
- [ ] `chart()` - 圖表容器

---

## 6. 自我查核清單

### 6.1 開發完成前必檢查

- [ ] 所有表單元素使用 Macro（無手寫 `<input>`、`<select>`）
- [ ] 無內聯樣式（`style="..."`）
- [ ] 無重複 HTML 結構（`<!DOCTYPE>`、`<html>`、`<body>`）
- [ ] CSS 只使用頁面專屬類別（無全域 `*`、`html`、`body`）
- [ ] 已繼承 `base.html` 並正確使用 `{% block %}`

### 6.2 回報進度時必須聲明

```
本次修改已完全遵守 DEVELOPMENT_RULES.md 之規範：
- ✅ 所有 UI 元件使用 macros.html 標準 Macro
- ✅ 無手寫非標準 HTML/CSS
- ✅ 正確繼承 base.html
```

---

## 7. 違規處理

發現違規程式碼時：

1. **立即標記**：在回報中明確指出違規位置
2. **拒絕合併**：未修正前視為未完成
3. **主動重構**：發現舊頁面違規，主動排入重構清單

---

## 8. 版本記錄

| 日期 | 版本 | 變更內容 |
|:---|:---:|:---|
| 2026-03-07 | 1.0 | 初始版本發布 |

---

**確認簽署：**

我已完整閱讀並理解 DEVELOPMENT_RULES.md 之所有規範，
承諾未來所有開發工作將徹底遵守本守則。

簽署人：Yvonne  
日期：2026-03-07