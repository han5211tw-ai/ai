# 電腦舖營運系統 - 推薦備貨商品功能白皮書

**版本**: 1.0  
**日期**: 2026-03-13  
**作者**: Yvonne  

---

## 1. 功能概述

### 1.1 目的
「推薦備貨商品」功能讓老闆/會計可以預先設定建議門市備貨的商品清單，門市/業務人員登入後可直接從清單中點選需要的數量，送出後自動轉為備貨需求單（needs）。

### 1.2 使用情境
- **老闆/會計**：管理推薦備貨商品清單，設定各商品的最小備貨量
- **門市/業務**：查看推薦清單，選擇需要備貨的商品與數量，一鍵送出需求

### 1.3 核心價值
- 統一備貨建議，避免遺漏熱銷商品
- 簡化需求單建立流程，提升效率
- 與現有備貨需求系統無縫整合

---

## 2. 系統架構

### 2.1 資料庫設計

#### 2.1.1 推薦商品分類表 (`recommended_categories`)
```sql
CREATE TABLE recommended_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,               -- 分類名稱
    sort_order INTEGER DEFAULT 0,     -- 排序
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2.1.2 推薦商品表 (`recommended_products`)
```sql
CREATE TABLE recommended_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER,              -- 分類ID
    item_name TEXT NOT NULL,          -- 項目名稱（對應 needs.item_name）
    product_code TEXT,                -- 產品編號（對應 needs.product_code）
    quantity INTEGER DEFAULT 1,       -- 最小備貨量（對應 needs.quantity）
    external_link TEXT,               -- 外部連結
    description TEXT,                 -- 說明
    is_active INTEGER DEFAULT 1,      -- 是否上架
    sort_order INTEGER DEFAULT 0,     -- 排序
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES recommended_categories(id)
);
```

**欄位對應關係**：

| 推薦商品表 | 需求表 (needs) | 說明 |
|-----------|---------------|------|
| `item_name` | `item_name` | 項目名稱 |
| `product_code` | `product_code` | 產品編號 |
| `quantity` | `quantity` | 數量（最小備貨量） |
| （送出時帶入） | `requester` | 申請人 |
| （送出時帶入） | `department` | 部門 |

### 2.2 API 設計

#### 2.2.1 分類管理 API

| 方法 | 端點 | 功能 |
|------|------|------|
| GET | `/api/recommended-categories` | 取得所有分類 |
| POST | `/api/recommended-categories` | 新增分類 |
| PUT | `/api/recommended-categories/{id}` | 更新分類 |
| DELETE | `/api/recommended-categories/{id}` | 刪除分類 |

#### 2.2.2 商品管理 API

| 方法 | 端點 | 功能 |
|------|------|------|
| GET | `/api/recommended-products` | 取得商品列表 |
| POST | `/api/recommended-products` | 新增商品 |
| PUT | `/api/recommended-products/{id}` | 更新商品 |
| DELETE | `/api/recommended-products/{id}` | 刪除商品 |
| POST | `/api/recommended-products/order` | 送出備貨需求 |

#### 2.2.3 送出備貨需求 API

**Request**:
```json
{
    "items": [
        {"product_id": 1, "quantity": 5},
        {"product_id": 2, "quantity": 3}
    ],
    "requester": "張家碩",
    "department": "豐原門市"
}
```

**Response**:
```json
{
    "success": true,
    "message": "成功建立 2 筆備貨需求",
    "needs": [
        {
            "need_no": "REC-20260313153000-1",
            "item_name": "羅技 G502 電競滑鼠",
            "product_code": "LOG-G502",
            "quantity": 5
        }
    ]
}
```

### 2.3 頁面設計

#### 2.3.1 後台管理頁面 (`/admin/recommended_products`)

**功能**：
- 分類管理（新增、編輯、刪除）
- 商品管理（新增、編輯、刪除、上架/下架）
- 從產品主檔搜尋自動帶入資料

**欄位說明**：
- **分類**：商品所屬分類
- **項目名稱**：對應需求表的 item_name
- **產品編號**：對應需求表的 product_code（從產品主檔搜尋帶入）
- **外部連結**：產品規格頁面連結
- **說明**：商品特色或注意事項
- **最小備貨量**：門市可選擇的最小數量
- **上架狀態**：是否顯示在前台

#### 2.3.2 前台選購頁面 (`/recommended_products`)

**功能**：
- 依分類瀏覽商品
- 點選數量（從最小備貨量開始累加）
- 一鍵送出備貨需求

**操作流程**：
1. 選擇分類標籤瀏覽商品
2. 點擊「+」按鈕增加數量
3. 底部顯示已選商品總數
4. 點擊「送出備貨需求」
5. 確認視窗顯示明細
6. 確認後建立需求單

---

## 3. 權限控制

### 3.1 角色權限表

| 角色 | 後台管理 | 前台選購 |
|------|---------|---------|
| 老闆 | ✅ | ✅（測試） |
| 會計 | ✅ | ✅（測試） |
| 門市工程師 | ❌ | ✅（未來開放） |
| 業務人員 | ❌ | ✅（未來開放） |

### 3.2 選單整合

在 `base.html` 選單中加入「備貨推薦」群組：
- 推薦備貨商品（前台）
- 商品管理（後台）

目前僅對「老闆」和「會計」角色顯示。

---

## 4. 資料流程

### 4.1 建立推薦商品流程

```
老闆/會計
    ↓
進入「商品管理」頁面
    ↓
點擊「新增商品」
    ↓
輸入產品名稱搜尋（從產品主檔）
    ↓
選擇搜尋結果 → 自動帶入編號與名稱
    ↓
設定最小備貨量、說明、連結
    ↓
儲存 → 寫入 recommended_products 表
```

### 4.2 送出備貨需求流程

```
門市/業務
    ↓
進入「推薦備貨商品」頁面
    ↓
瀏覽分類與商品
    ↓
點擊「+」增加數量（從最小備貨量開始）
    ↓
點擊「送出備貨需求」
    ↓
確認明細
    ↓
建立 needs 記錄：
    - need_no: REC-時間戳-商品ID
    - requester: 登入者姓名
    - department: 登入者部門
    - item_name: 推薦商品.item_name
    - product_code: 推薦商品.product_code
    - quantity: 選擇的數量
    - request_type: '請購'
    - purpose: '備貨'
    - status: '待審核'
    - source: 'recommended'
```

---

## 5. 技術實作

### 5.1 檔案結構

```
dashboard-site/
├── admin/
│   └── recommended_products.html    # 後台管理頁面
├── recommended_products.html        # 前台選購頁面
└── app.py                           # API 端點（已整合）
```

### 5.2 共用元件

- **模板**：`base.html`（共用側邊欄、登入驗證）
- **樣式**：使用現有 CSS 變數與元件風格
- **搜尋**：整合 `/api/product-master/search` 產品搜尋

### 5.3 資料庫整合

- 與 `needs` 資料表直接對應
- 無需額外轉換，送出時直接複製欄位值
- 需求單來源標記為 `'recommended'`，便於追蹤

---

## 6. 未來擴充

### 6.1 短期優化
- [ ] 商品圖片上傳功能
- [ ] 分類圖示設定
- [ ] 商品排序拖曳調整

### 6.2 中期功能
- [ ] 依門市別推薦不同商品
- [ ] 熱銷排行自動推薦
- [ ] 庫存連動（低庫存自動提示）

### 6.3 長期規劃
- [ ] 供應商整合（直接下單）
- [ ] 價格趨勢分析
- [ ] AI 智能推薦

---

## 7. 維護紀錄

| 日期 | 版本 | 變更內容 |
|------|------|---------|
| 2026-03-13 | 1.0 | 初版上線 |

---

## 附錄：相關 Git 提交

```
d5c5ef3 Add recommended products feature: backend admin, frontend page, APIs, and menu integration
3960130 Update recommended products: change model_no to product_code, add product search with auto-fill
de9e317 Align recommended_products schema with needs table: item_name, product_code, quantity, requester, department
```
