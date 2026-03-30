# 資料庫結構

## 主要資料表

### sales_history (銷貨歷史)
| 欄位 | 類型 | 說明 |
|------|------|------|
| invoice_no | TEXT | 發票號碼 |
| date | TEXT | 日期 |
| customer_id | TEXT | 客戶編號 |
| salesperson | TEXT | 銷售人員 |
| product_code | TEXT | 產品代碼 |
| product_name | TEXT | 產品名稱 |
| quantity | INTEGER | 數量 |
| price | INTEGER | 單價 |
| amount | INTEGER | 金額 |

### staff_roster (班表)
| 欄位 | 類型 | 說明 |
|------|------|------|
| date | TEXT | 日期 |
| staff_name | TEXT | 人員姓名 |
| location | TEXT | 門市 |
| shift_code | TEXT | 班次代碼 |

### supervision_scores (督導評分)
| 欄位 | 類型 | 說明 |
|------|------|------|
| date | TEXT | 日期 |
| store_name | TEXT | 門市名稱 |
| attendance | REAL | 出勤狀況 |
| appearance | REAL | 服裝儀容 |
| service_attitude | REAL | 服務態度 |
| ... | ... | 共15項評分 |

### store_reviews (門市評論 - 舊版，4/1 後改用 google_reviews)
| 欄位 | 類型 | 說明 |
|------|------|------|
| record_date | TEXT | 記錄日期 |
| store_name | TEXT | 門市名稱 |
| review_count | INTEGER | 評論數量 |

### google_reviews (Google 商家評論 - 4/1 起使用)
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER | 主鍵 |
| store_name | TEXT | 門市名稱（豐原/潭子/大雅） |
| reviewer_name | TEXT | 評論者名稱 |
| review_date | DATE | 評論日期 |
| star_rating | INTEGER | 星等（1-5） |
| review_snippet | TEXT | 評論內容預覽 |
| email_subject | TEXT | 原始郵件主旨 |
| email_received_at | DATETIME | 收到通知時間 |
| processed_at | DATETIME | 處理時間 |
| parse_method | TEXT | 解析方式（regex/failed） |

### google_reviews_stats (評論統計快取)
| 欄位 | 類型 | 說明 |
|------|------|------|
| store_name | TEXT | 門市名稱（主鍵） |
| five_star | INTEGER | 五星數量 |
| four_star | INTEGER | 四星數量 |
| three_star | INTEGER | 三星數量 |
| two_star | INTEGER | 二星數量 |
| one_star | INTEGER | 一星數量 |
| total_reviews | INTEGER | 總評論數 |
| avg_rating | REAL | 平均分數 |
| updated_at | DATETIME | 更新時間 |

### needs (需求表)
| 欄位 | 類型 | 說明 |
|------|------|------|
| date | TEXT | 日期 |
| item_name | TEXT | 產品名稱 |
| quantity | INTEGER | 數量 |
| customer_code | TEXT | 客戶編號/需求用途 |
| department | TEXT | 需求部門 |
| requester | TEXT | 填表人員 |
| product_code | TEXT | 產品編號 |
| processed | TEXT | 處理狀態 |

### service_records (服務記錄)
| 欄位 | 類型 | 說明 |
|------|------|------|
| date | TEXT | 日期 |
| customer_code | TEXT | 客戶編號 |
| customer_name | TEXT | 客戶名稱 |
| service_item | TEXT | 服務事宜 |
| service_type | TEXT | 服務分類 |
| salesperson | TEXT | 業務員 |
| is_contract | BOOLEAN | 是否合約客戶 |

### recommended_products (推薦備貨商品)
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER | 主鍵 |
| category_id | INTEGER | 分類 ID |
| product_code | TEXT | 產品編號 |
| item_name | TEXT | 產品名稱 |
| quantity | INTEGER | 最小備貨量 |
| requester | TEXT | 預設填表人 |
| department | TEXT | 預設部門 |

### bonus_rules (銷售獎金規則)
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER | 主鍵 |
| product_code | TEXT | 產品編號 |
| item_name | TEXT | 產品名稱 |
| start_date | DATE | 開始日期 |
| end_date | DATE | 結束日期 |
| bonus_type | TEXT | 類型 (fixed/percentage) |
| bonus_value | REAL | 獎金數值 |
| min_quantity | INTEGER | 最小數量門檻 |
| applicable_to | TEXT | 適用對象 (all/specific) |

### bonus_results (獎金計算結果)
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER | 主鍵 |
| rule_id | INTEGER | 規則 ID |
| salesperson | TEXT | 業務員 |
| sale_date | DATE | 銷售日期 |
| product_code | TEXT | 產品編號 |
| quantity | INTEGER | 數量 |
| revenue | REAL | 銷售額 |
| bonus_amount | REAL | 獎金金額 |
| is_confirmed | BOOLEAN | 是否已確認 |

### notification_logs (通知發送記錄)
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER | 主鍵 |
| type | TEXT | 通知類型 |
| recipient | TEXT | 收件人 |
| message_preview | TEXT | 訊息預覽 |
| status | TEXT | 狀態 (success/failed) |
| error_message | TEXT | 錯誤訊息 |
| related_record | TEXT | 關聯記錄 |
| created_at | DATETIME | 建立時間 |

### system_announcements (系統公告)
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | INTEGER | 主鍵 |
| title | TEXT | 標題 |
| content | TEXT | 內容 |
| level | TEXT | 等級 (info/warning/urgent) |
| is_active | INTEGER | 是否生效 |
| is_pinned | INTEGER | 是否置頂 |
| created_by | TEXT | 建立者 |
| created_at | DATETIME | 建立時間 |
| expires_at | DATETIME | 過期時間 |

## 2026-03-05 更新

### needs 表格擴充（需求表流程優化）
| 欄位 | 類型 | 說明 |
|------|------|------|
| processed_at | DATETIME | 處理時間 |
| arrived_at | DATETIME | 到貨時間 |

## 資料庫路徑

```
/Users/aiserver/srv/db/company.db
```
