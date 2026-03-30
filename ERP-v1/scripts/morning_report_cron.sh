#!/bin/bash
# 晨間報告 Cron Wrapper
# 每天 09:00 執行

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export HOME="/Users/aiserver"

# 執行 Python 腳本取得基礎報告（不含新聞）
REPORT=$(python3 /Users/aiserver/.openclaw/workspace/scripts/morning_report.py 2>/dev/null | tail -n +2)

# 搜尋 AI 新聞
NEWS=$(curl -s "https://news.google.com/rss/search?q=AI+人工智慧&hl=zh-TW&gl=TW&ceid=TW:zh-Hant" | head -100)

# 發送到 Telegram
TELEGRAM_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
CHAT_ID="8545239755"

if [ -n "$TELEGRAM_TOKEN" ]; then
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
        -d "chat_id=${CHAT_ID}" \
        -d "text=${REPORT}" \
        -d "parse_mode=Markdown" \
        -d "disable_web_page_preview=true"
fi
