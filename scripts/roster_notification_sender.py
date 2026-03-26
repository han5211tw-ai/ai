#!/usr/bin/env python3
"""
排班開放通知發送腳本
每月24號中午12:00發送到電腦舖工作群組
"""

from datetime import datetime, date
import calendar
import requests

# Telegram Bot 設定
TELEGRAM_BOT_TOKEN = "8623161623:AAGWlwGjp0Vf3bzpiVgLltQFbcGFY4kpFxo"
TELEGRAM_CHAT_ID = "-5232179482"  # 電腦舖工作群組

def generate_roster_notification():
    """生成排班開放通知"""
    now = datetime.now()
    
    # 計算下個月的最後一天
    if now.month == 12:
        next_month = 1
        next_year = now.year + 1
    else:
        next_month = now.month + 1
        next_year = now.year
    
    last_day = calendar.monthrange(next_year, next_month)[1]
    
    month_names = ['', '1月', '2月', '3月', '4月', '5月', '6月', 
                   '7月', '8月', '9月', '10月', '11月', '12月']
    
    # 計算截止日（月底前一天）
    deadline_day = last_day - 1
    
    message = f"""📢 排班功能開放通知

各位夥伴好！

{next_year}年{month_names[next_month]}的班表排班功能已經開放！

📅 排班時間：
• 開放時間：每月24號 中午12:00
• 截止時間：{next_month}月{deadline_day}號 下午15:00

請各位在期限內完成排班，如有問題請聯繫主管。

祝工作順利！🦞"""
    
    return message

def send_telegram_message(message, chat_id=None):
    """發送 Telegram 訊息"""
    chat_id = chat_id or TELEGRAM_CHAT_ID
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()
        
        if result.get('ok'):
            print(f"✅ 通知發送成功")
            return True
        else:
            print(f"❌ 發送失敗: {result.get('description')}")
            return False
            
    except Exception as e:
        print(f"❌ 發送異常: {e}")
        return False

def main():
    """主程式：生成並發送通知"""
    print(f"🚀 排班開放通知發送中... {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 生成通知訊息
    message = generate_roster_notification()
    
    # 發送到 Telegram
    success = send_telegram_message(message)
    
    if success:
        print("✅ 排班開放通知已發送到電腦舖工作群組")
    else:
        print("❌ 通知發送失敗")
        exit(1)

if __name__ == '__main__':
    main()
