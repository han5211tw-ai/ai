# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

### API Keys

- Brave Search: `BSAz6EsFkdHLmy3W8UthuxKpCBTdoU5` — 已設定於 gateway 環境變數

### Company Database (唯讀)

**路徑:** `/Users/aiserver/srv/db/company.db` (SQLite)
**權限:** 唯讀 — 只能執行 `SELECT`，禁止 `INSERT`/`UPDATE`/`DELETE`

**核心資料表：**

| 表格 | 用途 | 關鍵欄位 |
|------|------|----------|
| `sales_history` | 銷貨明細 | `invoice_no`, `date`, `salesperson`, `product_name`, `quantity`, `price`, `amount`, `customer_id` |
| `customers` | 客戶主檔 | `customer_id`, `short_name`, `mobile`, `phone1`, `company_address` |
| `inventory` | 庫存 | `product_id`, `item_spec`, `warehouse`, `stock_quantity`, `unit_cost` |
| `staff_roster` | 班表 | `date`, `staff_name`, `location`, `shift_code` |
| `crm_tasks` | 待辦追蹤 | `invoice_no`, `customer_name`, `task_type`, `status` |
| `performance_metrics` | 績效 | `subject_name`, `target_amount`, `revenue_amount`, `achievement_rate` |
| `needs` | 請購單 | `item_name`, `quantity`, `requester`, `status` |
| `purchase` / `purchase_history` | 採購紀錄 | `vendor_name`, `item_name`, `quantity`, `unit_price` |
| `store_reviews` | 評論統計 | `store_name`, `review_count` |

### 資料查詢習慣

- **產品名稱**：一律顯示完整名稱（如「微軟 OFFICE 2024 家用盒裝版」），不可簡化，避免誤會

---

Add whatever helps you do your job. This is your cheat sheet.
