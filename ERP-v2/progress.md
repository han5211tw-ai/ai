# ERP v2 重建進度

**系統代號**: OpenClaw
**新系統 Port**: 8800
**最後更新**: 2026-03-28

---

## 階段規劃

### Phase 0：基礎架構（先做，其他都依賴它）
| 項目 | 狀態 | 說明 |
|------|------|------|
| 目錄結構建立 | ⬜ 待開始 | templates/, static/css/, static/js/ |
| app.py 骨架 | ✅ 完成 | Flask + SQLite 連線 + 路由骨架 |
| base.html（母版） | ✅ 完成 | 側邊欄 + 頂部 + 字體 + 色系 |
| 登入機制（auth） | ✅ 完成 | localStorage + 角色權限 |
| .env 設定 | ✅ 完成 | DB 路徑、密碼等 |

### Phase 1：核心每日使用頁面（最高優先）
| 頁面 | 對應舊檔 | 狀態 | 說明 |
|------|----------|------|------|
| 首頁 | index.html | ✅ 完成 | 每日銷售趨勢、公告、待處理需求 |
| 需求表輸入 | needs_input.html | ✅ 完成 | 四階段流程核心 |
| 老闆控制台 | boss.html | ✅ 完成 | 待處理需求審核、業績總覽 |

### Phase 2：業績分析頁面
| 頁面 | 對應舊檔 | 狀態 | 說明 |
|------|----------|------|------|
| 部門業績 | department.html | ✅ 完成 | 門市部 vs 業務部 |
| 門市業績 | store.html | ✅ 完成 | 豐原/潭子/大雅 + 督導環境分 |
| 個人業績 | personal.html | ✅ 完成 | 個人排名 + 督導人員分 |
| 業務部績效 | business.html | ✅ 完成 | 業務員績效 + 服務記錄統計 |
| 月會報告 | monthly_report.html | ✅ 完成 | 上月報告，可切換月份，含列印 |

### Phase 3：控制台與查詢
| 頁面 | 對應舊檔 | 狀態 | 說明 |
|------|----------|------|------|
| 門市主管控制台 | Store_Manager.html | ✅ 完成 | 今日班表/業績/待處理需求 |
| 會計專區 | Accountants.html | ✅ 完成 | 調撥需求管理，到貨/完成操作 |
| 客戶查詢 | customer_search.html | ✅ 完成 | 搜尋+詳情+購買紀錄 |
| 庫存查詢 | inventory_query.html | ✅ 完成 | 倉庫篩選、分頁、各倉統計 |
| 班表查詢 | roster.html | ✅ 完成 | 月曆視圖，班別色系標示 |

### Phase 4：輸入頁面
| 頁面 | 對應舊檔 | 狀態 | 說明 |
|------|----------|------|------|
| 外勤服務紀錄 | service_record.html | ✅ 完成 | |
| 督導評分 | supervision_score.html | ✅ 完成 | 16項 32分制 |
| 班表輸入 | roster_input.html | ✅ 完成 | |
| 銷貨輸入 | sales_input.html | ✅ 完成 | 含產品搜尋、客戶搜尋、成本/毛利（老闆可見） |
| 業績目標管理 | target_input.html | ✅ 完成 | 門市/個人/部門/公司分群 |

### Phase 5：後台管理
| 頁面 | 對應舊檔 | 狀態 | 說明 |
|------|----------|------|------|
| 資料管理中心 | admin.html | ✅ 完成 | 功能入口 hub + 快速統計 |
| 員工管理 | staff_management.html | ✅ 完成 | 列表 + 編輯 + 密碼修改 |
| 公告管理 | admin/announcement_management.html | ✅ 完成 | 新增/停用/刪除，含置頂/類型/到期日 |
| 獎金規則 | admin/bonus_rules.html | ✅ 完成 | 新增/停用/刪除，固定金額或百分比 |
| 獎金報表 | admin/bonus_report.html | ✅ 完成 | 日期範圍計算，人員匯總+明細 |
| 推薦備貨（後台） | admin/recommended_products.html | ✅ 完成 | 分類管理 + 品項管理 |

### Phase 6：特殊功能頁面
| 頁面 | 對應舊檔 | 狀態 | 說明 |
|------|----------|------|------|
| LINE 回覆表 | line_replies.html | ✅ 完成 | 含新增/編輯/結案/刪除，篩選+分頁 |
| LINE 回覆編輯 | line_replies_edit.html | ✅ 完成 | 已合併至 line_replies.html |
| 個人獎金查詢 | bonus_personal.html | ✅ 完成 | 月份快選，按月分組顯示明細 |
| 推薦備貨選購 | recommended_products.html | ✅ 完成 | 分類卡片選購，送出備貨需求 |
| 待建檔中心 | staging_center_v2.html | ✅ 完成 | 雙 Tab（暫存記錄/產品待建檔），標記完成 |
| 系統架構圖 | system_map_v3.html | ✅ 完成 | 四 Tab：頁面架構/API分組/資料庫/技術堆疊 |

---

## 資料庫 Tables（49張）

**核心業務**：sales_history, customers, customer_master, inventory, needs, purchase_history, products, suppliers, service_records, sales, sales_documents, sales_document_items

**人員/班表**：staff, staff_passwords, staff_roster, supervision_scores

**獎金**：bonus_rules, bonus_results, bonus_payments

**系統/管理**：system_announcements, notification_logs, login_attempts, boss_password, admin_audit_log, chat_logs, api_metrics, ops_events

**暫存/備份**：customer_staging, product_staging, staging_records, sales_history_deleted_backup

**特殊功能**：google_reviews, google_reviews_stats, store_reviews, line_replies, recommended_products, recommended_categories, crm_tasks, finance_ledger

---

## API 端點分組（181個路由）

| 分組 | 主要路由 |
|------|---------|
| 銷售 | /api/sales/daily, /api/sales/daily/store, /api/sales/daily/by-store |
| 績效 | /api/performance/department, store, personal, business |
| 需求表 | /api/needs/latest, batch, cancel, purchase, transfer, arrive, complete, history |
| 客戶 | /api/customer/search, detail, lookup, count, update |
| 班表 | /api/roster/weekly, today, monthly |
| 服務紀錄 | /api/service-records (GET/POST/DELETE) |
| 認證 | /api/auth/verify, boss/verify, accountant/verify |
| 公告 | /api/system/announcements |
| 老闆 | /api/boss/pending-needs, needs/status, needs/notes |
| 督導 | /api/store/supervision, personal/supervision, supervision/score |
| 推薦備貨 | /api/recommended-categories, recommended-products |
| 獎金 | /api/bonus-rules, bonus-calculate, bonus-results |
| LINE回覆 | /api/line-replies (CRUD) |
| 評論 | /api/google-reviews, store/reviews |
| 產品/供應商 | /api/products/list, supplier/list, purchase/list |
| AI聊天 | /api/chat |
| 系統 | /api/health, summary |

---

## 設計規範（快速參考）

```
背景：#f5f0e8
次要背景：#e8e2d8
主文字：#2c2720
次要文字：#9a9188
線條：#6b5f52
品牌黃：#FABF13（僅 focus/active）

字體：Noto Serif TC 200/300（中）/ Cormorant Garamond 300（英裝飾）
最小字體：16px
```

## 版面與資訊層級原則

**寬螢幕留白**
- 主內容約束在 1160px 以內，超出則兩側自動留白，畫面更集中
- 實作：`padding: 36px max(24px, calc((100% - 1160px) / 2))`
- top-bar 水平 padding 同步對齊，保持視覺一致

**資訊權重**
- 營收數字是第一視覺焦點：Cormorant Garamond 2.6rem+ 搭配寬字距
- 統計 label 用大寫淡色（text-light），與數字形成強弱對比
- 公告、提示等次要資訊用較小字體、弱化邊框，不搶主畫面

**版面節奏**
- 首頁排序：統計數字 → 圖表 → 待處理事項 → 公告（末尾，有資料才顯示）
- 圖表高度：主圖 340–360px，輔助圖 240–300px，讓閱讀更舒服
- 卡片 padding：統計卡 28–32px，圖表卡 30–32px（比一般內容卡更寬鬆）

**核心原則**
- 不增加元素，透過留白、間距與層級建立主次關係
- 讓使用者一眼掌握重點，減少視覺干擾

---

## 完成記錄

| 日期 | 項目 | 備註 |
|------|------|------|
| 2026-03-28 | 白皮書閱讀完成 | v4.3，49張表，181路由，~30頁面 |
| 2026-03-28 | 舊系統目錄盤點完成 | old system/dashboard-site/ |
| 2026-03-28 | 重建計畫產出 | 6個 Phase，依使用頻率排序 |
| 2026-03-28 | Phase 0 完成 | app.py / base.html / main.css / gunicorn.conf.py / .env / 404.html |
| 2026-03-28 | Phase 1 首頁完成 | index.html + 5 個 API（summary/sales/needs/arrive/overdue） |
| 2026-03-28 | Phase 1 需求表輸入完成 | needs_input.html + 7 個 API（customers/products/inventory/needs batch/recent/cancel/history） |
| 2026-03-28 | Phase 1 老闆控制台完成 | boss.html + 4 個 API（boss/pending-needs/purchase/status/notes） |
| 2026-03-28 | Phase 2 部門業績完成 | department.html + 2 個 API（performance/department + daily） |
| 2026-03-28 | Phase 2 門市業績完成 | store.html + 4 個 API（performance/store / store/reviews / google-reviews / store/supervision） |
| 2026-03-28 | Phase 2 個人業績完成 | personal.html + 2 個 API（performance/personal / personal/supervision） |
| 2026-03-28 | 登入 Bug 修正 | auth_verify 缺少 sp.department 欄位 → 500 錯誤已修復 |
| 2026-03-28 | Phase 2 業務部績效完成 | business.html + 2 個 API（performance/business / service-records/detail） |
| 2026-03-28 | Phase 2 月會報告完成 | monthly_report.html，預設上月，可切月份，含列印，六大區塊 |
| 2026-03-28 | Phase 3 全部完成 | Store_Manager / Accountants / customer_search / inventory_query / roster + 8 個新 API |
| 2026-03-28 | Phase 4 全部完成 | service_record / supervision_score / roster_input / target_input / sales_input + 8 個新 API |
| 2026-03-28 | Phase 5 全部完成 | admin / staff_management / announcement_management / bonus_rules / bonus_report / recommended_products + 17 個新 API |
| 2026-03-28 | 版面優化 | max-width 1160px 留白、統計數字層級提升、公告弱化移至末尾、圖表高度增加 |
| 2026-03-28 | Phase 6 APIs 新增 | line-replies CRUD、bonus-personal、staging/list+resolve、product-staging/list+resolve、staging/stats |
| 2026-03-28 | Phase 6 line_replies.html 完成 | LINE 客服回覆記錄，含篩選/分頁/新增/編輯/結案/刪除 |
| 2026-03-28 | Phase 6 bonus_personal.html 完成 | 個人獎金查詢，月份快選，按月分組明細 |
| 2026-03-28 | Phase 6 recommended_products.html 完成 | 推薦備貨選購，分類卡片，購物車式送出 needs |
| 2026-03-28 | Phase 6 staging_center_v2.html 完成 | 待建檔中心，暫存記錄+產品待建檔雙 Tab，標記完成 |
| 2026-03-28 | Phase 6 system_map_v3.html 完成 | 系統架構圖，四 Tab：頁面架構/API分組/資料庫/技術堆疊 |
| 2026-03-28 | Phase 6 全部完成 | 6 頁面，8 個 API，27 個頁面共完成 |
