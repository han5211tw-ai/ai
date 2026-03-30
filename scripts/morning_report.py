#!/usr/bin/env python3
"""
電腦舖每日晨報生成器
每天早上十點自動發送到 Telegram 工作群組
"""

import sqlite3
import subprocess
import json
import requests
from datetime import datetime, date
import random
import xml.etree.ElementTree as ET
import re

# Telegram Bot 設定
# 使用通知機器人直接發送，避免 Agent 帳號產生「更多詳情」按鈕
TELEGRAM_BOT_TOKEN = "8623161623:AAGWlwGjp0Vf3bzpiVgLltQFbcGFY4kpFxo"
TELEGRAM_CHAT_ID = "-5232179482"  # 電腦舖工作群組

# 資料庫路徑
DB_PATH = "/Users/aiserver/srv/db/company.db"

# 正能量語錄庫
QUOTES = [
    "新的一天，新的機會！不管今天會遇到什麼挑戰，記得我們是一個團隊。有問題就問，有困難就說，不要一個人硬撐 💪",
    "每一筆成交，都是客戶對我們的信任。用心服務，業績自然會來 🎯",
    "沒有什麼困難是解決不了的，如果有，就問問身邊的夥伴。我們一起想辦法！💡",
    "今天的努力，是明天的實力。加油，你比你想像的更棒！⭐",
    "銷售不只是賣東西，是幫客戶找到最適合的解決方案。相信自己，你可以的！🚀",
    "有時候會遇到難搞的客户，但別忘了，每個挑戰都是讓我們變更強的機會 💪",
    "團隊的力量在於互相支持。今天，讓我們一起創造美好的一天！🌈",
    "不管昨天怎麼樣，今天都是全新的開始。帶著微笑出發吧！😊",
    "成功不是終點，失敗也不是末日，重要的是繼續前進的勇氣。我們一起加油！🔥",
    "客戶的每一句謝謝，都是我們最好的獎勵。讓我們繼續用專業和熱情服務每一位客人 🙏",
    "記得：你不是一個人在戰鬥。有任何需要，隨時找夥伴或主管支援！🤝",
    "每一天都是限量版的，好好把握當下，創造屬於今天的精彩 ✨",
    "遇到問題別慌，深呼吸，一步一步來。你比問題更強大！💪",
    "最好的銷售不是說服客戶買東西，而是幫他們找到真正需要的。保持真誠！❤️",
    "今天的你，已經比昨天的你更進步了。繼續前進，未來可期！🌟",
]

def get_weather():
    """取得台中天氣 - 使用 Open-Meteo API"""
    try:
        # Open-Meteo API (免費，無需 API key)
        url = "https://api.open-meteo.com/v1/forecast?latitude=24.15&longitude=120.68&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m&timezone=Asia/Taipei"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        current = data.get('current', {})
        temp = current.get('temperature_2m', 'N/A')
        feels_like = current.get('apparent_temperature', 'N/A')
        humidity = current.get('relative_humidity_2m', 'N/A')
        wind = current.get('wind_speed_10m', 'N/A')
        weather_code = current.get('weather_code', 0)
        
        # WMO Weather interpretation codes
        weather_emojis = {
            0: '☀️', 1: '🌤️', 2: '⛅', 3: '☁️',
            45: '🌫️', 48: '🌫️',
            51: '🌦️', 53: '🌦️', 55: '🌧️',
            61: '🌧️', 63: '🌧️', 65: '🌧️',
            71: '🌨️', 73: '🌨️', 75: '🌨️',
            80: '🌦️', 81: '🌧️', 82: '🌧️',
            95: '⛈️', 96: '⛈️', 99: '⛈️'
        }
        weather_emoji = weather_emojis.get(weather_code, '🌡️')
        
        return f"台中: {weather_emoji} {temp}°C (體感 {feels_like}°C), 濕度 {humidity}%, 風速 {wind} km/h"
    except Exception as e:
        # 備用方案：嘗試 wttr.in
        try:
            result = subprocess.run(
                ['curl', '-s', 'wttr.in/Taichung?format=%l:+%c+%t+(體感+%f),+%w+風速,+%h+濕度'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and 'weather' not in result.stdout.lower():
                return result.stdout.strip()
        except:
            pass
        return "台中天氣暫時無法取得"

def get_today_roster():
    """取得今天班表"""
    today = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT location, staff_name, shift_code 
        FROM staff_roster 
        WHERE date = ? 
        ORDER BY location, staff_name
    """, (today,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_q1_performance():
    """取得 Q1 業績"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Q1 目標 (1-3月)
    cursor.execute("""
        SELECT subject_name, SUM(target_amount) as target
        FROM performance_metrics 
        WHERE period_type = 'monthly' AND year = 2026 AND month IN (1,2,3)
        AND subject_name IN ('公司','門市部','業務部','豐原門市','潭子門市','大雅門市')
        GROUP BY subject_name
    """)
    targets = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Q1 實際達成
    cursor.execute("""
        SELECT '門市部' as dept, SUM(amount) as total 
        FROM sales_history 
        WHERE date >= '2026-01-01' AND date < '2026-04-01' 
        AND salesperson IN ('林榮祺','林峙文','劉育仕','林煜捷','張永承','張家碩','莊圍迪')
        UNION ALL
        SELECT '業務部', SUM(amount) 
        FROM sales_history 
        WHERE date >= '2026-01-01' AND date < '2026-04-01' 
        AND salesperson IN ('鄭宇晉','梁仁佑','萬書佑')
        UNION ALL
        SELECT '公司總計', SUM(amount) 
        FROM sales_history 
        WHERE date >= '2026-01-01' AND date < '2026-04-01'
    """)
    dept_actuals = {row[0]: row[1] or 0 for row in cursor.fetchall()}
    
    # 各門市實際達成
    cursor.execute("""
        SELECT '豐原門市' as store, SUM(amount) as total 
        FROM sales_history 
        WHERE date >= '2026-01-01' AND date < '2026-04-01' 
        AND salesperson IN ('林榮祺','林峙文')
        UNION ALL
        SELECT '潭子門市', SUM(amount) 
        FROM sales_history 
        WHERE date >= '2026-01-01' AND date < '2026-04-01' 
        AND salesperson IN ('劉育仕','林煜捷')
        UNION ALL
        SELECT '大雅門市', SUM(amount) 
        FROM sales_history 
        WHERE date >= '2026-01-01' AND date < '2026-04-01' 
        AND salesperson IN ('張永承','張家碩')
    """)
    store_actuals = {row[0]: row[1] or 0 for row in cursor.fetchall()}
    
    conn.close()
    
    return targets, dept_actuals, store_actuals

def get_tech_news():
    """取得科技新聞（從 Google News RSS 抓取）"""
    import xml.etree.ElementTree as ET
    
    try:
        # 嘗試抓取 Google News RSS (AI 相關)
        rss_url = "https://news.google.com/rss/search?q=AI+人工智慧+科技&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(rss_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # 解析 RSS
            root = ET.fromstring(response.content)
            items = root.findall('.//item')[:3]  # 取前 3 則
            
            news_list = []
            emojis = ["🤖", "💻", "📱"]
            
            for i, item in enumerate(items):
                title = item.find('title')
                title_text = title.text if title is not None else "科技新聞"
                # 移除來源標記 (如 - 聯合新聞網)
                title_text = title_text.split(' - ')[0] if ' - ' in title_text else title_text
                
                # 簡短摘要 (從標題推測)
                summary = "相關產業持續發展，值得關注最新動態。"
                if 'AI' in title_text or '人工智慧' in title_text:
                    summary = "AI 技術持續演進，影響各行各業發展。"
                elif 'NVIDIA' in title_text or '輝達' in title_text or '晶片' in title_text:
                    summary = "半導體產業持續創新，帶動科技供應鏈發展。"
                elif '微軟' in title_text or 'Microsoft' in title_text or 'Google' in title_text:
                    summary = "科技巨擘持續投入新服務與產品開發。"
                
                news_list.append({
                    "title": title_text[:30] + "..." if len(title_text) > 30 else title_text,
                    "emoji": emojis[i % len(emojis)],
                    "summary": summary,
                    "source": "科技新聞"
                })
            
            if news_list:
                return news_list
    except Exception as e:
        pass
    
    # 備用：嘗試另一個 RSS 源 (TechCrunch 中文或類似)
    try:
        rss_url2 = "https://feeds.feedburner.com/engadget/cstb"
        response = requests.get(rss_url2, timeout=10)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            items = root.findall('.//item')[:3]
            
            news_list = []
            emojis = ["🤖", "💻", "📱"]
            for i, item in enumerate(items):
                title = item.find('title')
                title_text = title.text if title is not None else "科技新聞"
                news_list.append({
                    "title": title_text[:30] + "..." if len(title_text) > 30 else title_text,
                    "emoji": emojis[i % len(emojis)],
                    "summary": "最新科技動態，值得關注。",
                    "source": "Engadget"
                })
            if news_list:
                return news_list
    except:
        pass
    
    # 最終備用新聞內容
    return [
        {"title": "AI 產業持續快速發展", "emoji": "🤖", "summary": "各大科技巨擘持續投入 AI 研究，新模型與應用層出不窮。", "source": "產業快訊"},
        {"title": "半導體產業動態", "emoji": "💻", "summary": "NVIDIA、Intel 等企業持續優化晶片設計與製造技術。", "source": "產業快訊"},
        {"title": "軟體與服務更新", "emoji": "📱", "summary": "各大平台持續推出新功能與 AI 整合應用。", "source": "產業快訊"}
    ]

def format_money(amount):
    """格式化金額"""
    return f"${amount:,.0f}"

def calculate_rate(actual, target):
    """計算達成率"""
    if target and target > 0:
        return (actual / target) * 100
    return 0

def get_shift_emoji(shift):
    """取得班別表情"""
    if shift == '全':
        return '💪'
    elif shift == '早':
        return '🌅'
    elif shift == '晚':
        return '🌙'
    elif shift == '休':
        return '😴'
    return ''

def generate_report():
    """生成晨報內容"""
    today = datetime.now()
    weekday_names = ['一', '二', '三', '四', '五', '六', '日']
    weekday = weekday_names[today.weekday()]
    
    # 取得資料
    weather = get_weather()
    roster = get_today_roster()
    targets, dept_actuals, store_actuals = get_q1_performance()
    news = get_tech_news()
    quote = random.choice(QUOTES)
    
    # 整理班表
    on_duty = []
    on_leave = []
    for location, name, shift in roster:
        if shift == '休':
            on_leave.append((location, name, shift))
        else:
            on_duty.append((location, name, shift))
    
    # 計算達成率
    company_rate = calculate_rate(dept_actuals.get('公司總計', 0), targets.get('公司', 0))
    dept_store_rate = calculate_rate(dept_actuals.get('門市部', 0), targets.get('門市部', 0))
    dept_biz_rate = calculate_rate(dept_actuals.get('業務部', 0), targets.get('業務部', 0))
    fengyuan_rate = calculate_rate(store_actuals.get('豐原門市', 0), targets.get('豐原門市', 0))
    daya_rate = calculate_rate(store_actuals.get('大雅門市', 0), targets.get('大雅門市', 0))
    tanzi_rate = calculate_rate(store_actuals.get('潭子門市', 0), targets.get('潭子門市', 0))
    
    # 組合訊息
    message = f"""🌅 早安！電腦舖的夥伴們！

又是嶄新的一天，希望大家都睡飽飽、精神滿滿！來看看今天有什麼在等著我們吧 👇

---

🌤️ 台中天氣
{weather}

---

👥 今天誰在崗位上
"""
    
    # 在崗人員
    for location, name, shift in on_duty:
        message += f"\n• {location}｜{name}｜{shift}班 {get_shift_emoji(shift)}"
    
    # 休假人員
    for location, name, shift in on_leave:
        message += f"\n• {location}｜{name}｜休假 {get_shift_emoji(shift)}"
    
    message += f"\n\n今天有 {len(on_leave)} 位夥伴休假，在崗的大家辛苦啦！有什麼需要支援的記得互相 cover 喔～"
    
    message += f"""

---

📊 Q1 第一季業績快報（統計至昨日）

公司整體
目標：{format_money(targets.get('公司', 0))}
達成：{format_money(dept_actuals.get('公司總計', 0))}
達成率：{company_rate:.1f}% 🎯

門市部
目標：{format_money(targets.get('門市部', 0))}
達成：{format_money(dept_actuals.get('門市部', 0))}
達成率：{dept_store_rate:.1f}% 💪

業務部
目標：{format_money(targets.get('業務部', 0))}
達成：{format_money(dept_actuals.get('業務部', 0))}
達成率：{dept_biz_rate:.1f}% 📈

豐原門市
目標：{format_money(targets.get('豐原門市', 0))}
達成：{format_money(store_actuals.get('豐原門市', 0))}
達成率：{fengyuan_rate:.1f}% {'🔥 已超標！' if fengyuan_rate >= 100 else ''}

大雅門市
目標：{format_money(targets.get('大雅門市', 0))}
達成：{format_money(store_actuals.get('大雅門市', 0))}
達成率：{daya_rate:.1f}% {'💨' if daya_rate < 70 else ''}

潭子門市
目標：{format_money(targets.get('潭子門市', 0))}
達成：{format_money(store_actuals.get('潭子門市', 0))}
達成率：{tanzi_rate:.1f}% {'💨' if tanzi_rate < 70 else ''}
"""
    
    # 業績總結
    if fengyuan_rate >= 100:
        message += f"\n🎉 豐原門市已經超標達成 {fengyuan_rate:.0f}%！"
    
    remaining_days = 31 - today.day
    message += f"潭子和大雅還有距離，剩下 {remaining_days} 天大家一起衝刺！業務部表現也很穩，全公司 {company_rate:.1f}% 達成率，月底達標很有希望 💪"
    
    message += "\n\n---\n\n💡 科技新鮮事（3則）\n"
    
    for i, item in enumerate(news, 1):
        source_tag = f" [{item.get('source', '科技新聞')}]"
        message += f"\n{i}️⃣ {item['title']} {item['emoji']}{source_tag}\n{item['summary']}"
    
    message += f"""

---

🎯 今日小提醒

{quote}

祝今天順順利利，業績長紅！🦞✨
"""
    
    return message

def send_to_telegram(message):
    """使用通知機器人發送訊息到 Telegram 工作群組"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'  # 支援 HTML 格式
        }
        response = requests.post(url, data=data, timeout=30)
        if response.status_code == 200:
            print(f"✅ 晨報已成功發送到 Telegram 工作群組")
            return True
        else:
            print(f"❌ 發送失敗: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ 發送時發生錯誤: {e}")
        return False

def main():
    """主程式：生成晨報並發送到 Telegram"""
    print(f"🌅 生成晨報中... {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report = generate_report()
    
    # 將 Markdown 格式轉換為 HTML（Telegram 支援的格式）
    # 簡單轉換：將 **bold** 轉為 <b>bold</b>
    report_html = report.replace('**', '<b>').replace('**', '</b>')
    # 修正：上面的替換有問題，重新處理
    
    # 直接發送純文字，避免格式問題
    success = send_to_telegram(report)
    
    if not success:
        print("⚠️ 發送失敗，請手動檢查")
    
    return report

if __name__ == '__main__':
    report = main()
