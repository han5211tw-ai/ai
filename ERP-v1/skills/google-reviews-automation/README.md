# Google Reviews Automation

Google 商家評論自動化 - 自動抓取、統計、通知、報表

## 功能特色

- 📧 **Gmail 自動讀取** - 透過通知信間接取得評論
- 🔔 **即時通知** - 新評論 5-10 分鐘內 Telegram 通知
- ⚠️ **負評警報** - 3 星以下立即提醒
- 📊 **多門市支援** - 豐原/潭子/大雅分別統計
- 📈 **趨勢分析** - 評分變化圖表
- 📝 **回覆建議** - AI 生成回覆內容

## 快速開始

### 安裝

```bash
npx clawhub@latest install google-reviews-automation
```

### 設定

編輯 `~/.openclaw/skills/google-reviews-automation/config.json`：

```json
{
  "gmail": {
    "auth_method": "oauth2",
    "credentials_path": "~/.credentials/gmail_credentials.json"
  },
  "stores": [
    {"name": "豐原門市", "google_place_id": "ChIJ..."},
    {"name": "潭子門市", "google_place_id": "ChIJ..."}
  ]
}
```

### 使用範例

**查評論統計：**
```
使用者：這個月有幾則五星評論
AI：⭐ 本月 25 則評論，5 星佔比 80%
```

**最新評論：**
```
使用者：最新的 Google 評論
AI：📝 豐原門市 5 星 - 「服務很好，老闆很專業」
```

## 文件

詳細文件請見 [SKILL.md](SKILL.md)

## 授權

MIT License - 詳見 [LICENSE](LICENSE)

## 聯絡

- Email: ai@computershop.cc
- GitHub: https://github.com/computershop/google-reviews-automation
