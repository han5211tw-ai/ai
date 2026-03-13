#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微星庫存彙總表產生腳本
用法: python3 msi_inventory_report.py
自動抓取資料庫中最新的庫存日期
"""

import sqlite3
import csv
import sys
from datetime import datetime, timedelta
import os
import requests

# 資料庫路徑
DB_PATH = '/Users/aiserver/srv/db/company.db'
OUTPUT_DIR = '/Users/aiserver/.openclaw/workspace'

# Telegram 設定（與系統一致）
TELEGRAM_BOT_TOKEN = '8623161623:AAGWlwGjp0Vf3bzpiVgLltQFbcGFY4kpFxo'
TELEGRAM_CHAT_ID = '8545239755'  # 老闆個人

def get_inventory_by_date(report_date):
    """查詢指定日期的微星庫存資料"""
    
    if not os.path.exists(DB_PATH):
        print(f"錯誤：資料庫不存在 {DB_PATH}")
        return None
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 查詢微星硬體產品（排除 SO- 軟體類別）
    cursor.execute("""
        SELECT 
            product_id,
            item_spec,
            SUM(stock_quantity) as total_quantity
        FROM inventory 
        WHERE report_date = ? 
            AND product_id LIKE '%-MS-%'
            AND SUBSTR(product_id, 1, 2) != 'SO'
        GROUP BY product_id, item_spec
        ORDER BY 
            CASE SUBSTR(product_id, 1, 2)
                WHEN 'MB' THEN 1
                WHEN 'MP' THEN 2
                WHEN 'MI' THEN 3
                WHEN 'SD' THEN 4
                WHEN 'PO' THEN 5
                WHEN 'CO' THEN 6
                WHEN 'CA' THEN 7
                WHEN 'KB' THEN 8
                WHEN 'LC' THEN 9
                WHEN 'NB' THEN 10
                WHEN 'VG' THEN 11
                WHEN 'WA' THEN 12
                ELSE 13
            END,
            product_id
    """, (report_date,))
    
    results = cursor.fetchall()
    conn.close()
    
    return results

def get_available_dates():
    """取得資料庫中可用的庫存日期"""
    
    if not os.path.exists(DB_PATH):
        return []
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT report_date 
        FROM inventory 
        WHERE product_id LIKE '%-MS-%'
            AND SUBSTR(product_id, 1, 2) != 'SO'
        ORDER BY report_date DESC
        LIMIT 10
    """)
    
    dates = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    return dates

def generate_csv(report_date, data):
    """產生 CSV 檔案"""
    
    if not data:
        print(f"警告：{report_date} 沒有微星庫存資料")
        return None
    
    # 檔案名稱
    filename = f"msi_inventory_{report_date.replace('-', '')}_summary.csv"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    # 寫入 CSV
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        # 表頭
        writer.writerow(['產品編號', '產品名稱', '總庫存量'])
        # 資料
        for row in data:
            writer.writerow(row)
    
    return filepath

def print_category_summary(data):
    """印出各類別彙總"""
    
    categories = {
        'MB': '主機板',
        'MP': '滑鼠/滑鼠墊',
        'MI': '耳麥',
        'SD': 'SSD硬碟',
        'PO': '電源供應器',
        'CO': '散熱器',
        'CA': '機殼',
        'KB': '鍵鼠組合',
        'LC': '螢幕',
        'NB': '筆記型電腦',
        'VG': '顯示卡',
        'WA': '網通設備'
    }
    
    category_count = {}
    for row in data:
        prefix = row[0][:2]
        category_count[prefix] = category_count.get(prefix, 0) + 1
    
    print("\n各類別統計：")
    print("-" * 40)
    for prefix, name in categories.items():
        count = category_count.get(prefix, 0)
        if count > 0:
            print(f"  {prefix} ({name}): {count} 個產品")
    print("-" * 40)
    
    return category_count

def send_telegram_notification(filepath, report_date, total_count, category_count):
    """發送 Telegram 通知並傳送檔案"""
    
    # 構建訊息
    message = f"📦 微星庫存彙總表（{report_date}）\n\n"
    message += f"✅ 共 {total_count} 個硬體產品\n\n"
    message += "各類別統計：\n"
    
    categories = {
        'MB': '主機板',
        'MP': '滑鼠/滑鼠墊',
        'MI': '耳麥',
        'SD': 'SSD硬碟',
        'PO': '電源供應器',
        'CO': '散熱器',
        'CA': '機殼',
        'KB': '鍵鼠組合',
        'LC': '螢幕',
        'NB': '筆記型電腦',
        'VG': '顯示卡',
        'WA': '網通設備'
    }
    
    for prefix, name in categories.items():
        count = category_count.get(prefix, 0)
        if count > 0:
            message += f"• {name}: {count} 個\n"
    
    try:
        # 先發送文字訊息
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            print("\n📱 Telegram 文字通知已發送")
        else:
            print(f"\n⚠️ Telegram 文字通知發送失敗: {response.status_code}")
        
        # 再傳送檔案
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
        with open(filepath, 'rb') as f:
            files = {'document': f}
            payload = {
                'chat_id': TELEGRAM_CHAT_ID,
                'caption': f'微星庫存彙總表（{report_date}）'
            }
            response = requests.post(url, data=payload, files=files, timeout=30)
        
        if response.status_code == 200:
            print("📎 Telegram 檔案已傳送")
            return True
        else:
            print(f"⚠️ Telegram 檔案傳送失敗: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n⚠️ Telegram 發送失敗: {e}")
        return False

def get_latest_date():
    """取得資料庫中最新的庫存日期"""
    
    if not os.path.exists(DB_PATH):
        return None
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT MAX(report_date) 
        FROM inventory 
        WHERE product_id LIKE '%-MS-%'
            AND SUBSTR(product_id, 1, 2) != 'SO'
    """)
    
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None

def main():
    # 自動抓取最新的日期
    report_date = get_latest_date()
    
    if not report_date:
        print("錯誤：資料庫中沒有微星庫存資料")
        sys.exit(1)
    
    print(f"\n查詢微星庫存資料（最新）：{report_date}")
    print("=" * 50)
    
    # 查詢資料
    data = get_inventory_by_date(report_date)
    
    if data is None:
        sys.exit(1)
    
    if not data:
        print(f"\n{report_date} 沒有微星庫存資料")
        sys.exit(0)
    
    # 產生 CSV
    filepath = generate_csv(report_date, data)
    
    if filepath:
        print(f"\n✅ 成功產生庫存表！")
        print(f"   檔案：{filepath}")
        print(f"   產品數量：{len(data)} 個")
        
        # 印出各類別統計並取得統計資料
        category_count = print_category_summary(data)
        
        # 發送 Telegram 通知
        print("\n📱 正在發送 Telegram 通知...")
        send_telegram_notification(filepath, report_date, len(data), category_count)
    
    return filepath

if __name__ == '__main__':
    main()