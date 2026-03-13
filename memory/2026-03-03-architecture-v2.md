# 2026-03-03 架構圖 V2 重畫 - 盤點與交付

## 1️⃣ 盤點清單（基於實際程式碼）

### A. 頁面節點（Page Inventory）
| 頁面 | 路徑 | 使用 API |
|------|------|----------|
| needs_input.html | /needs_input.html | /api/auth/verify, /api/needs/batch, /api/needs/recent, /api/needs/cancel, /api/needs/complete |
| staging_center_v2.html | /staging_center_v2.html | /api/auth/verify, /api/staging/records, /api/staging/customer/approve, /api/staging/product/approve |
| admin.html | /admin.html | /api/auth/verify, /api/admin/table, /api/admin/audit/summary, /api/admin/audit/detail |
| staff_admin.html | /staff_admin.html | /api/auth/verify, /api/admin/staff/list, /api/admin/staff/update, /api/admin/staff/reset-password |
| roster_input.html | /roster_input.html | /api/auth/verify, /api/roster, /api/roster/batch |
| supervision_score.html | /supervision_score.html | /api/auth/verify, /api/supervision/score |
| service_record.html | /service_record.html | /api/auth/verify, /api/service-records |

### B. API 節點（Route Inventory）
| API 端點 | 方法 | 相關資料表 |
|----------|------|------------|
| /api/auth/verify | POST | staff, staff_passwords |
| /api/needs/batch | POST | needs, staging_records |
| /api/needs/recent | GET | needs |
| /api/needs/cancel | POST | needs, staging_records |
| /api/needs/complete | POST | needs |
| /api/staging/records | GET | staging_records, needs |
| /api/staging/customer/approve | POST | staging_records, customers |
| /api/staging/product/approve | POST | staging_records, products |
| /api/admin/table | GET | all tables |
| /api/admin/audit/summary | GET | admin_audit_log, needs, staging_records |
| /api/admin/audit/detail | GET | admin_audit_log |
| /api/admin/staff/list | GET | staff |
| /api/admin/staff/update | POST | staff, admin_audit_log |
| /api/roster | GET/POST | staff_roster |
| /api/supervision/score | GET/POST | supervision_scores |
| /api/service-records | GET/POST | service_records |

### C. DB 節點（Table Inventory）
| 資料表 | 用途 |
|--------|------|
| needs | 需求主表（含 TEMP-P/TEMP-C 標記、cancelled_at） |
| staging_records | 待建檔紀錄 |
| customers | 客戶主檔 |
| customer_staging | 客戶待建檔 |
| products | 產品主檔 |
| product_staging | 產品待建檔 |
| inventory | 庫存表 |
| purchase_history | 進貨歷史 |
| sales_history | 銷貨歷史 |
| staff | 員工主檔 |
| staff_passwords | 員工密碼 |
| staff_roster | 班表 |
| admin_audit_log | 操作紀錄 |
| ops_events | 系統事件 |

### D. Parser 節點
| Parser | 排程時間 | 資料表 |
|--------|----------|--------|
| inventory_parser.py | 10:30 | inventory, products |
| purchase_parser.py | 10:35 | purchase_history |
| sales_parser_v19.py | 10:40 | sales_history, products |
| customer_parser.py | 10:45 | customers |
| performance_parser.py | 11:00 | performance_metrics |

---

## 2️⃣ V2 重畫規則實現

### ✅ 線路完整性
- 每一條線都有「來源 → API → DB/服務」的完整路徑
- 不簡化為「頁面連 DB」
- 每條線標註實際 API 路徑

### ✅ 線條類型區分
| 類型 | 顏色 | 用途 |
|------|------|------|
| Read (GET) | 藍色 | 讀取資料 |
| Write (POST) | 橘色 | 寫入/更新 |
| Audit | 紅色 | 稽核檢查 |

### ✅ 補齊的關鍵資料流
1. **needs → staging**: TEMP-P/TEMP-C 產生 staging_records 的完整流程
2. **取消流程**: cancelled_at 對 staging 顯示的影響
3. **staging_center_v2**: /api/staging/records 讀取 staging + needs 條件
4. **admin 稽核**: /api/admin/audit/summary 查詢 A2/A3 邏輯
5. **Parser 匯入**: 每個 Parser 到對應資料表的線路

---

## 3️⃣ 資料流播放模式

### 控制面板功能
- ▶ Play / ⏸ Pause / ⟲ Reset
- 速度切換: 0.5x / 1x / 2x
- 流程選擇:
  - 新品 TEMP-P 流程
  - 客戶 TEMP-C 流程
  - 取消流程（紅色）

### 播放內容
- 光點沿線條跑動
- 節點發光（glow）
- 底部字幕顯示步驟說明
- 進度條顯示

---

## 4️⃣ 驗收證據

### 檔案資訊
```
$ ls -la architecture_map_v2.html
-rw-r--r--  1 aiserver  staff  35602 Mar  3 10:48

$ curl -I http://127.0.0.1:3000/architecture_map_v2.html
HTTP/1.1 200 OK ✓
```

### 節點統計
- Pages: 7 個
- APIs: 15 個
- DB Tables: 14 個
- Parsers: 5 個
- Links: 30+ 條（每條有實際端點對應）

### 快捷鍵
- `Space` - Play/Pause
- `R` - Reset
- `1` - 選擇 TEMP-P 流程
- `2` - 選擇 TEMP-C 流程
- `3` - 選擇取消流程

---

## 存取網址
http://localhost:3000/architecture_map_v2.html

**注意**: 舊版 v2 已被新版取代，新版包含完整拓撲與播放模式。
