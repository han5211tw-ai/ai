# 2026-03-02 TEMP 新品回歸驗證報告

## 測試目標
證明「新品需求單就算被按『已完成』，只要未取消且仍是 TEMP-P，就一定會在前台/後台待建檔中心顯示」。

## 測試資料

| 項目 | 值 |
|------|-----|
| needs_id | 14868 |
| staging_id | 197 |
| TEMP-P 編號 | TEMP-P-REGTEST-001 |
| item_name | [REGTEST_TEMP_P] 測試新品-SSD |

## SQL 證據

### 1. needs 查詢
```
id     product_code        product_staging_id  status  cancelled_at  item_name
-----  ------------------  ------------------  ------  ------------  -----------------------------
14868  TEMP-P-REGTEST-001  TEMP-P-REGTEST-001  待處理                [REGTEST_TEMP_P] 測試新品-SSD
```

### 2. staging_records 查詢
```
id   type     temp_product_id     status   created_at
---  -------  ------------------  -------  -------------------
197  product  TEMP-P-REGTEST-001  pending  2026-03-02 13:39:05
```

### 3. 關聯確認
```
source   id     product_staging_id  product_code        status
-------  -----  ------------------  ------------------  -------
needs    14868  TEMP-P-REGTEST-001  TEMP-P-REGTEST-001  待處理
staging  197    TEMP-P-REGTEST-001                      pending
```

## API 驗證結果

### B) 前台待建檔中心 (/api/staging/records?type=product)
```json
{
  "records": [
    {
      "id": 197,
      "temp_product_id": "TEMP-P-REGTEST-001",
      "needs_id": 14868,
      "needs_status": "待處理"
    }
  ],
  "stats": {"product_pending": 1, "customer_pending": 2}
}
```
✓ **找到測試資料**

### C) 後台待建檔中心 (/api/admin/table?name=staging_records)
```json
{
  "items": [
    {
      "id": 197,
      "temp_product_id": "TEMP-P-REGTEST-001",
      "needs_id": 14868,
      "needs_status": "待處理"
    }
  ],
  "total": 3
}
```
✓ **找到測試資料**

### D) 「已完成」不影響顯示
將 needs 更新為「已完成」後：
- 前台：✓ PASS - 仍看得到 TEMP-P-REGTEST-001 (needs_status: 已完成)
- 後台：✓ PASS - 仍看得到 TEMP-P-REGTEST-001 (needs_status: 已完成)

### E) 「取消」才會消失
將 needs 設定 cancelled_at 後：
- 前台：✓ PASS (已消失) - 筆數: 0
- 後台：✓ PASS (已消失) - 筆數: 2

### F) 稽核卡片 (A2)
- A2 計數: 0
- 說明：A2 只抓「已轉正式碼但 staging 仍 pending」的異常，TEMP-P 仍在待建檔階段，不屬於 A2

## 驗證結論

| 驗證點 | 結果 |
|--------|------|
| 未取消 + TEMP-P → 前台顯示 | ✅ PASS |
| 未取消 + TEMP-P → 後台顯示 | ✅ PASS |
| 已完成 → 仍顯示（不影響）| ✅ PASS |
| 取消 → 消失 | ✅ PASS |

## 清理
```sql
DELETE FROM needs WHERE item_name LIKE '%[REGTEST_TEMP_P]%';
DELETE FROM staging_records WHERE raw_input LIKE '%[REGTEST_TEMP_P]%';
```
✓ 清理完成

## 核心規則確認

顯示條件（以 needs 為準）：
- `cancelled_at IS NULL`（未取消）
- `product_code LIKE 'TEMP-P-%'`（仍為臨時編號）

不影響顯示：
- `needs.status`（pending/已完成/已處理 都不影響）
- `staging_records.status`（pending/resolved 都不影響）

消失條件：
- `cancelled_at IS NOT NULL`（已取消）
- `product_code NOT LIKE 'TEMP-P-%'`（已轉正式碼）
