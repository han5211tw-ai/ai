#!/bin/bash
# 外部監控腳本 - 檢查 Flask 是否存活
# 建議用 launchd 或 cron 每 5 分鐘執行一次

FLASK_URL="http://localhost:3000/api/health"
TELEGRAM_BOT_TOKEN="8623161623:AAGWlwGjp0Vf3bzpiVgLltQFbcGFY4kpFxo"
TELEGRAM_CHAT_ID="8545239755"
ALERT_FILE="/tmp/flask_down_alert_sent"

# Email 設定
EMAIL_HOST="smtp.gmail.com"
EMAIL_PORT="587"
EMAIL_USER="ai@computershop.cc"
EMAIL_PASSWORD="Nn121297069"
EMAIL_TO="alan@computershop.cc"

# 發送 Email 函數
send_email() {
    local subject="$1"
    local body="$2"
    
    python3 << EOF
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

try:
    msg = MIMEMultipart()
    msg['From'] = '$EMAIL_USER'
    msg['To'] = '$EMAIL_TO'
    msg['Subject'] = '$subject'
    
    body_html = '''
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6;">
        <h2 style="color: #d32f2f;">⚠️ 系統告警通知</h2>
        <div style="background: #f5f5f5; padding: 15px; border-radius: 5px;">
            ''' + '''$body''' + '''
        </div>
        <p style="color: #666; font-size: 0.9em;">
            時間：''' + os.popen('date "+%Y-%m-%d %H:%M:%S"').read().strip() + '''<br>
            系統：電腦舖營運系統
        </p>
    </body>
    </html>
    '''
    
    msg.attach(MIMEText(body_html, 'html'))
    
    server = smtplib.SMTP('$EMAIL_HOST', $EMAIL_PORT)
    server.starttls()
    server.login('$EMAIL_USER', '$EMAIL_PASSWORD')
    server.send_message(msg)
    server.quit()
    print("Email sent successfully")
except Exception as e:
    print(f"Email failed: {e}")
EOF
}

# 檢查 Flask 是否回應
if ! curl -s -f "$FLASK_URL" > /dev/null 2>&1; then
    # Flask 沒有回應
    if [ ! -f "$ALERT_FILE" ]; then
        # 還沒發送過告警，發送一次
        MESSAGE="🚨 <b>系統嚴重告警</b>%0A%0AFlask 服務無回應！%0APort 3000 可能已停止%0A%0A時間：$(date '+%Y-%m-%d %H:%M:%S')"
        
        curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
            -d "chat_id=$TELEGRAM_CHAT_ID" \
            -d "text=$MESSAGE" \
            -d "parse_mode=HTML" > /dev/null 2>&1
        
        # 發送 Email 告警
        send_email "[電腦舖系統告警] Flask 服務異常" "<p>Flask 服務無回應！</p><p>Port 3000 可能已停止，請立即檢查。</p>"
        
        # 記錄已發送告警
        touch "$ALERT_FILE"
        echo "[$(date)] Flask 無回應，已發送 Telegram + Email 告警" >> /tmp/monitor.log
    fi
else
    # Flask 正常回應
    if [ -f "$ALERT_FILE" ]; then
        # 之前發送過告警，現在恢復了，發送恢復通知
        MESSAGE="✅ <b>系統恢復</b>%0A%0AFlask 服務已恢復正常%0A%0A時間：$(date '+%Y-%m-%d %H:%M:%S')"
        
        curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
            -d "chat_id=$TELEGRAM_CHAT_ID" \
            -d "text=$MESSAGE" \
            -d "parse_mode=HTML" > /dev/null 2>&1
        
        # 發送 Email 恢復通知
        send_email "[電腦舖系統恢復] Flask 服務正常" "<p>Flask 服務已恢復正常</p><p>系統監控已恢復運作。</p>"
        
        # 移除告警記錄
        rm "$ALERT_FILE"
        echo "[$(date)] Flask 恢復，已發送 Telegram + Email 恢復通知" >> /tmp/monitor.log
    fi
fi
