# 2026-03-02 產品主檔合併記錄

## 執行內容

### 問題
- 存在兩個產品主檔表：`products` 和 `product_master`
- `product_master` 多一筆異常資料（`-14100`）

### 執行步驟

#### 1. 清理異常資料
```sql
DELETE FROM product_master WHERE product_code = '-14100';
```

#### 2. 修改使用 product_master 的程式

**match_product_staging.py**
- 修改：把 `SELECT ... FROM product_master` 改為 `SELECT ... FROM products`

**auto_add_new_products.py**
- 修改：把同步目標從 `product_master` 改為 `products`
- 新增過濾：排除 `product_code LIKE '-%'`（負數編號）

**sync_product_master.py**
- 修改：把同步目標從 `product_master` 改為 `products`
- 新增過濾：排除負數編號

#### 3. 標記 product_master 為棄用
```sql
ALTER TABLE product_master RENAME TO _deprecated_product_master;
```

### 結果

| 項目 | Before | After |
|------|--------|-------|
| products 筆數 | 3476 | 3476 |
| product_master 筆數 | 3477 | 0（已棄用）|
| 異常資料 `-14100` | 存在 | 已刪除 |

### 唯一主檔

現在只有 `products` 表作為唯一產品主檔：

```sql
SELECT 'products' as table_name, COUNT(*) as cnt FROM products;
-- 結果: 3476

SELECT '_deprecated_product_master' as table_name, COUNT(*) as cnt FROM _deprecated_product_master;
-- 結果: 3476（保留備份）
```

### 使用 products 的程式

- purchase_parser.py ✅
- inventory_parser.py ✅
- sales_parser.py ✅
- auto_add_new_products.py ✅（已更新）
- match_product_staging.py ✅（已更新）
- sync_product_master.py ✅（已更新）
