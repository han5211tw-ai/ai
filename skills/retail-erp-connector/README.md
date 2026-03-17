# Retail ERP Connector

零售業 ERP 連接器 - 讓 AI 助理能查庫存、查銷貨、查客戶、算業績

## 功能特色

- 📦 **庫存查詢** - 即時查詢各門市庫存狀況
- 💰 **銷貨紀錄** - 查詢歷史銷貨明細
- 👤 **客戶管理** - 客戶資料與購買紀錄查詢
- 📊 **業績計算** - 個人/門市/部門業績與達成率
- 🔔 **低庫存提醒** - 自動提醒補貨

## 快速開始

### 安裝

```bash
npx clawhub@latest install retail-erp-connector
```

### 設定

編輯 `~/.openclaw/skills/retail-erp-connector/config.json`：

```json
{
  "database": {
    "path": "/path/to/company.db",
    "type": "sqlite"
  },
  "business_rules": {
    "low_stock_threshold": 5,
    "stores": ["豐原", "潭子", "大雅"]
  }
}
```

### 使用範例

**查庫存：**
```
使用者：查 RTX 4060 庫存
AI：📦 RTX 4060 庫存狀況 - 豐原: 12, 潭子: 3, 大雅: 0
```

**查業績：**
```
使用者：這個月業績
AI：📊 本月達成率 85%，需再衝 75 萬
```

## 文件

詳細文件請見 [SKILL.md](SKILL.md)

## 授權

MIT License - 詳見 [LICENSE](LICENSE)

## 聯絡

- Email: ai@computershop.cc
- GitHub: https://github.com/computershop/retail-erp-connector
