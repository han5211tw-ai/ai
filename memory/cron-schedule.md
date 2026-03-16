# 排程任務

## Cron 時間表

| 時間 | 任務 | 腳本 | 說明 |
|------|------|------|------|
| 04:00 | 數據備份 | `auto_backup.sh` | |
| 05:00 | OpenClaw 記憶備份 | `backup-memory.sh` | |
| **06:00** | **系統重開機** | `shutdown -r now` | **新增：每天自動重開機** |
| 10:30 | 庫存模組 | `inventory_parser.py` | |
| 10:35 | 進貨模組 | `purchase_parser.py` | |
| **10:40** | **銷貨模組** | `sales_parser_v22.py` | **更新：v22 修正語法錯誤** |
| 10:45 | 客戶模組 | `customer_parser.py` | |
| 10:50 | 評論模組（舊） | `feedback_parser.py` | OneDrive 匯入，4/1 後停用 |
| **00:00** | **Google 評論抓取** | `google_reviews_parser.py` | **4/1 起：讀取 Gmail 通知信** |
| **12:00** | **微星庫存週報** | `msi_inventory_report.py` | **每週一：匯出微星庫存 CSV 到 Telegram** |
| 10:55 | 班表模組 | `roster_parser.py` | |
| 11:00 | 績效模組 | `performance_parser.py` | V7：目標表 + sales_history |
| ~~11:05~~ | ~~業績計算~~ | ~~`calculate_performance.py`~~ | ~~**已移除 (3/5)**~~ |
| 11:10 | 督導評分 | `supervision_parser.py` | |
| 11:15 | 服務記錄 | `service_record_parser.py` | |
| */10 9-21 * * * | 需求表模組 | `needs_parser.py` | **更新：白天每10分鐘** |
| 0 22-23,0-8 * * * | 需求表模組 | `needs_parser.py` | **更新：晚上每小時** |

## sudo 設定

**自動重開機需要 root 權限**，請確保 /etc/sudoers 包含：
```
aiserver ALL=(ALL) NOPASSWD: /sbin/shutdown
```

## 查看排程

```bash
crontab -l
```

## 排程規則

- **不重複執行**：確保長時間任務不會重複啟動
- **錯誤處理**：所有排程必須記錄錯誤日誌
- **資源釋放**：任務完成後釋放資料庫連線
