# Parser 系統

## Parser 腳本列表

| 腳本 | 功能 | 排程時間 | 備註 |
|------|------|----------|------|
| `inventory_parser.py` | 庫存資料匯入 | 10:30 | |
| `purchase_parser.py` | 進貨資料匯入 | 10:35 | |
| `sales_parser_v19.py` | 銷貨資料匯入 | 10:40 | 新格式（逐月匯入） |
| `customer_parser.py` | 客戶資料匯入 | 10:45 | |
| `feedback_parser.py` | 五星評論匯入（舊） | 10:50 | OneDrive 檔案匯入，4/1 後改用 `google_reviews_parser.py` |
| `google_reviews_parser.py` | Google 商家評論自動抓取 | 00:00（4/1 起） | 讀取 Gmail 通知信，解析寫入資料庫 |
| `roster_parser.py` | 班表資料匯入 | 10:55 | |
| `performance_parser.py` | 績效資料匯入 | 11:00 | V7：目標表 + sales_history |
| `calculate_performance.py` | 業績計算 | 11:05 | |
| `supervision_parser.py` | 督導評分匯入 | 11:10 | |
| `service_record_parser.py` | 服務記錄匯入 | 11:15 | |
| `needs_parser.py` | 需求表匯入 | 每10分鐘（9-21點）/ 每小時（21-9點） | 同步刪除版 |

## sales_parser_v19.py 新格式說明

### 檔案格式
- **編碼**：Big5
- **標題**：無（已移除「業務人員：」「客戶名稱：」等標題）
- **日期**：民國曆（1150101 = 2026/01/01）
- **欄位**：從右向左解析（處理產品名稱長度差異）

### 解析邏輯
1. 訂單行：日期 + 業務員編號/姓名 + 客戶編號/姓名
2. 產品行：產品編號 + 產品名稱 + 數量 + 單價 + 金額 + 成本 + 利潤 + 毛利率
3. 從右向左取6個欄位：數量、單價、金額、成本、利潤、毛利率

### 資料來源
- `~/srv/sync/OneDrive/ai_source/sales/銷貨YYYYMM.csv`
- 逐月匯入，累加不覆蓋

## performance_parser.py V7 說明

### 資料來源
- **目標**：`~/srv/sync/OneDrive/ai_source/performance/業績目標表.xlsx`
- **實際業績**：從 `sales_history` 即時計算

### 計算邏輯
- 門市部：三個門市人員 + 主管（莊圍迪）
- 業務部：業務員（鄭宇晉、梁仁佑）+ 主管（萬書佑）
- 個人：單獨計算

## needs_parser.py 說明

### 刪除邏輯
- 比對 Key：（日期, 產品編號/名稱, 數量, 填表人員）
- 優先用產品編號，沒有則用產品名稱
- 只刪除「待處理」狀態的資料

## 常用指令

```bash
# 手動執行 Parser
cd /Users/aiserver/srv/parser
python3 inventory_parser.py
python3 sales_parser_v19.py
python3 performance_parser.py
python3 needs_parser.py
```

## 日誌檔案

Parser 日誌位於:
- `~/srv/logs/`
