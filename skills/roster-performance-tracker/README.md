# Roster & Performance Tracker

班表與績效追蹤 - 班表查詢、個人/門市/部門業績追蹤、督導評分管理

## 功能特色

- 📅 **班表查詢** - 個人/全體/特定門市班表
- 📊 **三層業績** - 個人、門市、部門分別計算
- 🏆 **排行榜** - 即時排名，激勵競爭
- 📝 **督導評分** - 門店管理品質追蹤
- 🔮 **業績預測** - AI 預測月底能否達標
- 💰 **獎金計算** - 自動計算銷售獎金

## 快速開始

### 安裝

```bash
npx clawhub@latest install roster-performance-tracker
```

### 設定

編輯 `~/.openclaw/skills/roster-performance-tracker/config.json`：

```json
{
  "database": {
    "path": "/path/to/company.db"
  },
  "business_structure": {
    "departments": {
      "store": {
        "name": "門市部",
        "stores": ["豐原", "潭子", "大雅"]
      }
    }
  }
}
```

### 使用範例

**查班表：**
```
使用者：這週班表
AI：📅 本週班表 - 豐原: 林榮祺 早班, 潭子: 劉育仕 全班
```

**查業績：**
```
使用者：我這個月業績
AI：📊 達成率 81.7%，需再衝 55,000
```

## 文件

詳細文件請見 [SKILL.md](SKILL.md)

## 授權

MIT License - 詳見 [LICENSE](LICENSE)

## 聯絡

- Email: ai@computershop.cc
- GitHub: https://github.com/computershop/roster-performance-tracker
