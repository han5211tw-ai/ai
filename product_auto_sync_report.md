# 新品進貨自動寫入 products 主檔 - 行為確認報告

## 1️⃣ 是否會自動新增 products 主檔？

### 答案：**會，有兩層機制**

#### 機制 A：purchase_parser.py 直接寫入
**檔案位置**：`/Users/aiserver/srv/parser/purchase_parser.py` (約第 205 行)

```python
# ===== 自動補產品主檔 =====
if p_code and p_name and len(p_name) >= 2:
    # 1) 檢查是否已存在
    cursor.execute("SELECT product_name FROM products WHERE product_code = ?", (p_code,))
    existing = cursor.fetchone()
    
    if existing is None:
        # 新品：直接插入 products 表
        cursor.execute('''
            INSERT INTO products (product_code, product_name, created_at, updated_at, last_seen_at)
            VALUES (?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'), datetime('now', 'localtime'))
        ''', (p_code, p_name))
        print(f"      🆕 新增產品主檔: {p_code} - {p_name[:30]}...")
    else:
        # 已存在：允許更新品名
        ...
```

**處理邏輯**：
- ✅ 自動 INSERT 進 `products` 表
- ✅ 已存在時 UPDATE 品名
- ✅ 同時寫入 `purchase_history`

#### 機制 B：auto_add_new_products.py 補同步
**檔案位置**：`/Users/aiserver/srv/parser/auto_add_new_products.py`

```python
# 找出進貨表中有但 product_master 沒有的產品
SELECT DISTINCT 
    ph.product_code,
    ph.product_name
FROM purchase_history ph
LEFT JOIN product_master pm ON ph.product_code = pm.product_code
WHERE pm.product_code IS NULL
```

**用途**：補同步到 `product_master` 表

---

## 2️⃣ 是否有防止主檔污染機制？

### 檢查機制

| 檢查項 | 實作 | 說明 |
|--------|------|------|
| product_name 長度 | ✅ `len(p_name) >= 2` | 避免空值或單字 |
| product_code 存在 | ✅ `p_code is not None` | 必須有編號 |
| product_name 存在 | ✅ `p_name is not None` | 必須有名稱 |

### 沒有的檢查
- ❌ 沒有檢查 product_id 格式（如必須包含數字或特定長度）
- ❌ 沒有黑名單/白名單機制
- ❌ 沒有人工審核機制

---

## 3️⃣ 庫存查詢依賴關係

### 相依關係圖
```
purchase_history (進貨明細)
       │
       ▼
   products (主檔，自動建立)
       │
       ├── 提供 product_name 給 inventory_parser
       ├── 提供 product_name 給 sales_parser
       └── 提供 product_name 給 dashboard-site
```

### 風險說明
| 風險 | 說明 |
|------|------|
| Typo 新品 | 若進貨單有 typo，會自動建立錯誤產品 |
| 重複產品 | 不同廠商可能有相同 product_name 但不同 product_code |
| 主檔髒亂 | 沒有定期清理機制，無效產品會累積 |

---

## 4️⃣ 測試證據

### 測試項目：新品進貨自動同步

#### Before
```sql
SELECT COUNT(*) FROM products WHERE product_code = 'TEST-NEW-PRODUCT-001';
-- 結果: 0
```

#### 執行進貨匯入
```sql
INSERT INTO purchase_history (...) VALUES ('TEST-INV-001', ..., 'TEST-NEW-PRODUCT-001', '測試新品-001', ...);
```

#### 執行 auto_add_new_products.py
```
🆕 發現 2 個新品，正在加入產品主檔...
   + TEST-NEW-PRODUCT-001: 測試新品-001...
✅ 成功新增 2 個新品
```

#### After
```sql
SELECT product_code, product_name, category, unit 
FROM product_master 
WHERE product_code = 'TEST-NEW-PRODUCT-001';

-- 結果:
-- TEST-NEW-PRODUCT-001|測試新品-001|進貨商品|個
```

✅ **測試通過：新品會自動同步到 product_master**

---

## 總結

| 問題 | 答案 |
|------|------|
| 進貨新品會自動寫入 products？ | ✅ **會**，purchase_parser.py 直接 INSERT |
| 會報錯嗎？ | ❌ 不會，自動建立 |
| 有防污染機制？ | ⚠️ 只有基本檢查（名稱長度≥2），沒有格式驗證 |
| 庫存依賴 products？ | ✅ 會，inventory_parser 會查 products 表 |
| 會造成主檔缺失？ | ❌ 不會，會自動補上，但可能有多餘/錯誤資料 |
