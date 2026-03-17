# Purchase Request Manager

需求表管理系統 - 完整的請購/調撥/新品需求管理，四階段流程追蹤

## 功能特色

- 📝 **需求單管理** - 請購、調撥、新品三種類型
- 🔄 **四階段流程** - 待處理 → 已採購 → 已調撥 → 已完成
- ⏰ **30分鐘取消** - 提交後 30 分鐘內可取消
- 🔔 **自動通知** - 請購通知老闆、調撥通知會計
- ⚠️ **逾期提醒** - 自動提醒未收貨需求

## 快速開始

### 安裝

```bash
npx clawhub@latest install purchase-request-manager
```

### 設定

編輯 `~/.openclaw/skills/purchase-request-manager/config.json`：

```json
{
  "database": {
    "path": "/path/to/company.db"
  },
  "notifications": {
    "telegram": {
      "channels": {
        "purchase": "老闆_CHAT_ID",
        "transfer": "會計_CHAT_ID"
      }
    }
  }
}
```

### 使用範例

**提交請購：**
```
使用者：請購 10 台 RTX 4060
AI：✅ 單號 PR-20260317001 已建立，30分鐘內可取消
```

**查詢需求：**
```
使用者：查我的需求單
AI：📊 本月 3 筆 | 已完成 1 | 進行中 2
```

## 文件

詳細文件請見 [SKILL.md](SKILL.md)

## 授權

MIT License - 詳見 [LICENSE](LICENSE)

## 聯絡

- Email: ai@computershop.cc
- GitHub: https://github.com/computershop/purchase-request-manager
