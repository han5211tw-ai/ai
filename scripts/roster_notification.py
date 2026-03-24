#!/usr/bin/env python3
"""
排班開放通知
每月24號中午12:00發送到電腦舖工作群組
"""

from datetime import datetime, date
import calendar

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

🔗 排班網址：http://localhost:3000/roster_input.html

祝工作順利！🦞"""
    
    return message

if __name__ == '__main__':
    print(generate_roster_notification())
