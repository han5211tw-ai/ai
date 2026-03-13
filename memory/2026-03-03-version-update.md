# 2026-03-03 版本更新日誌

## 登入介面統一 - 小改版更新

### 更新項目

| 頁面 | 舊版本 | 新版本 | 更新內容 |
|------|--------|--------|----------|
| needs_input.html | 2.1 | **2.2** | 改用共用登入元件 auth_ui.js，統一登入流程與介面 |
| needs_input_v2.html | 2.0 | **2.1** | 改用共用登入元件 auth_ui.js，統一登入流程與介面 |
| service_record.html | 1.3 | **1.4** | 改用共用登入元件 auth_ui.js，統一登入流程與介面 |
| roster_input.html | 20250302-2200 | **20250303-0100** | 改用共用登入元件 auth_ui.js，統一登入流程與介面 |
| supervision_score.html | 1.1 | **1.2** | 改用共用登入元件 auth_ui.js，統一登入流程與介面 |
| admin.html | 1.0 | **1.1** | 改用共用登入元件 auth_ui.js，統一登入流程與介面 |

### 共用元件

**新增檔案：**
- `shared/auth_ui.css` - 登入介面樣式（使用 CSS 變數）
- `shared/auth_ui.js` - 登入邏輯與共用函數

**功能：**
- 統一的登入介面（Modal 樣式）
- 支援權限控制（staff / accountant / boss）
- 登入狀態儲存（sessionStorage / localStorage）
- 自動初始化與權限驗證

### 權限對應

| 頁面 | 最小權限 |
|------|---------|
| 需求表 (needs_input) | staff |
| 外勤服務 (service_record) | staff |
| 排班 (roster_input) | staff |
| 督導評分 (supervision_score) | accountant |
| 資料管理中心 (admin) | boss |

### 技術細節

1. 各頁面移除原有獨立登入表單
2. 統一引用 `shared/auth_ui.css` 與 `shared/auth_ui.js`
3. 使用 `requireLogin({ minRole, title, subtitle })` 進行驗證
4. 登入成功後自動顯示主內容區塊
5. 權限不足時顯示統一錯誤提示
