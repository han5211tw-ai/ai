#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
晨間報告 - 每日 09:00 自動發送
內容：天氣、待請購清單、業績、排班、AI 新聞
"""

import sqlite3
import subprocess
import json
from datetime import datetime
import os

# 設定
DB_PATH = "/Users/aiserver/srv/db/company.db"
WEATHER_LOCATION = "豐原區"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = "8545239755"

def get_weather():
    """取得豐原區天氣"""
    try:
        result = subprocess.run(
            ['curl', '-s', f'wttr.in/{WEATHER_LOCATION}?format=%l:+%c+%t+(體感+%f),+%w+風,+%h+濕度'],
            capture_output=True, text=True, timeout=10
        )
        weather = result.stdout.strip()
        return weather if weather and "Unknown" not in weather else "天氣資訊暫時無法取得"
    except Exception as e:
        return f"天氣查詢失敗: {str(e)}"

def get_pending_needs():
    """取得待請購清單"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT item_name, quantity, requester, department, remark
        FROM needs
        WHERE status = '待處理' OR status IS NULL
        ORDER BY date DESC
        LIMIT 10
    """)
    
    results = cursor.fetchall()
    conn.close()
    return results

def get_performance():
    """取得各部門業績"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT category, subject_name, target_amount, revenue_amount, achievement_rate
        FROM performance_metrics
        ORDER BY 
            CASE category
                WHEN '公司' THEN 1
                WHEN '部門' THEN 2
                WHEN '門市' THEN 3
                WHEN '個人' THEN 4
            END,
            subject_name
    """)
    
    results = cursor.fetchall()
    conn.close()
    return results

def get_today_roster():
    """取得今日排班"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    cursor.execute("""
        SELECT location, staff_name, shift_code
        FROM staff_roster
        WHERE date = ?
        ORDER BY location, staff_name
    """, (today,))
    
    results = cursor.fetchall()
    conn.close()
    return results, today

def get_ai_news():
    """搜尋 AI 新聞"""
    try:
        # 使用 web_search 需要外部 API，這裡先簡化為手動搜尋結果
        # 實際上會由 agent 執行時使用 web_search 工具
        return None  # 由外部調用時填入
    except:
        return []

def format_report(weather, needs, performance, roster, roster_date):
    """格式化報告"""
    today_str = datetime.now().strftime('%Y年%m月%d日')
    
    report = f"📅 **晨間報告 - {today_str}**\n"
    report += "=" * 40 + "\n\n"
    
    # 天氣
    report += f"🌤️ **天氣資訊**\n"
    report += f"{weather}\n\n"
    
    # 待請購清單
    report += f"📋 **老闆控制台 - 待請購清單**\n"
    if needs:
        report += "| 品項 | 數量 | 申請人 | 部門 |\n"
        report += "|------|------|--------|------|\n"
        for item in needs:
            item_name = item[0] if item[0] else "未命名"
            item_name = item_name[:15] + "..." if len(item_name) > 15 else item_name
            report += f"| {item_name} | {item[1]} | {item[2] or '-'} | {item[3] or '-'} |\n"
    else:
        report += "✅ 目前無待處理請購項目\n"
    report += "\n"
    
    # 業績
    report += f"💰 **各部門/單位業績**\n"
    report += "| 類別 | 名稱 | 目標 | 實際 | 達成率 |\n"
    report += "|------|------|------|------|--------|\n"
    
    for row in performance:
        category, name, target, revenue, rate = row
        target_str = f"{target:,.0f}" if target else "-"
        revenue_str = f"{revenue:,.0f}" if revenue else "-"
        rate_str = f"{rate:.1f}%" if rate else "-"
        report += f"| {category} | {name} | {target_str} | {revenue_str} | {rate_str} |\n"
    report += "\n"
    
    # 排班
    report += f"👥 **今日排班 ({roster_date})**\n"
    if roster:
        current_location = None
        for row in roster:
            location, staff, shift = row
            if location != current_location:
                report += f"\n📍 {location}門市\n"
                current_location = location
            report += f"  • {staff} - {shift}\n"
    else:
        report += "今日無排班資料\n"
    report += "\n"
    
    return report

def main():
    """主程式"""
    print("🔄 產生晨間報告中...")
    
    # 收集資料
    weather = get_weather()
    needs = get_pending_needs()
    performance = get_performance()
    roster, roster_date = get_today_roster()
    
    # 格式化報告（不含新聞，新聞由 agent 處理）
    report = format_report(weather, needs, performance, roster, roster_date)
    
    return report

if __name__ == "__main__":
    result = main()
    print(result)
