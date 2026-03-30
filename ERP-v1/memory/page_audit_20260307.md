# 全站 42 個頁面檢查報告

## 檢查時間：2026-03-07 23:30

## 統計摘要

| 問題類型 | 數量 |
|---------|------|
| 總頁面數 | 42 |
| 重複 container | 10 個頁面 |
| 重複 script | 18 個頁面 |
| 未使用 CSS 變數 | 31 個頁面 |

---

## 頁面狀態詳情

### ✅ 已完成（使用 CSS 變數）

| 頁面 | 行數 | 備註 |
|------|------|------|
| inventory_query.html | 558 | 已移除重複 JS |
| query.html | 103 | 簡化完成 |
| service_record.html | 935 | CSS 變數化 |
| target_input.html | 497 | 已移除重複 JS |

### ⚠️ 需要處理

#### 高優先（重複 script + 未使用 CSS 變數）

| 頁面 | 行數 | 問題 |
|------|------|------|
| customer_create.html | 1471 | 重複 container(2)、重複 script(2) |
| product_create.html | 1307 | 重複 container(2)、重複 script(3) |
| purchase_input.html | 1504 | 重複 container(2)、重複 script(3) |
| supplier_create.html | 1140 | 重複 container(2)、重複 script(3) |
| roster_input.html | 820 | 重複 script(2) |
| sales_input.html | 1140 | 重複 container(2) |
| sales_input_new.html | 1113 | 重複 container(2) |
| staff_admin.html | 1124 | 重複 container(2)、重複 script(2) |
| staff_management.html | 835 | 重複 container(2)、重複 script(2) |
| monthly_report.html | 823 | 重複 container(2)、重複 script(2) |

#### 中優先（只有重複 script）

| 頁面 | 行數 | 問題 |
|------|------|------|
| Accountants.html | 908 | 重複 script(2) |
| base.html | 599 | 重複 script(2) |
| boss.html | 1027 | 重複 script(2) |
| needs_input_v1_202603010303.html | 1697 | 重複 script(2) |
| needs_input_v1_backup.html | 1697 | 重複 script(2) |
| needs_input_v1_deprecated.html | 810 | 重複 script(2) |
| needs_input_v2_full.html | 477 | 重複 script(2) |
| system_map.html | 1113 | 重複 script(2) |
| system_map_v3.html | 1398 | 重複 script(2) |
| test_announcement.html | 95 | 重複 script(2) |

#### 低優先（只有未使用 CSS 變數）

| 頁面 | 行數 |
|------|------|
| Store_Manager.html | 765 |
| admin.html | 2264 |
| app_shell.html | 352 |
| app_shell_test.html | 532 |
| business.html | 626 |
| customer_search.html | 402 |
| department.html | 318 |
| index.html | 572 |
| needs_input.html | 725 |
| needs_input_v2_complete.html | 473 |
| personal.html | 363 |
| quote_input.html | 442 |
| roster.html | 538 |
| staging_center_v2.html | 431 |
| store.html | 417 |
| supervision_score.html | 586 |
| supplier_portal.html | 201 |
| ui_components_demo.html | 145 |

---

## 建議處理順序

### 第一階段（核心頁面）
1. sales_input.html - 最複雜，需仔細測試
2. purchase_input.html - 進貨核心功能
3. product_create.html - 產品建檔
4. customer_create.html - 客戶建檔
5. supplier_create.html - 廠商建檔

### 第二階段（管理頁面）
6. staff_admin.html
7. staff_management.html
8. monthly_report.html
9. roster_input.html

### 第三階段（其他頁面）
10. 剩餘 18 個頁面分批處理

---

## 備份位置

`/dashboard-site/backup/` - 所有頁面在更新前都已備份

---

維護者：Yvonne
最後更新：2026-03-07 23:30
