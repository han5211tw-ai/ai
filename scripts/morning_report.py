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

# Telegram Bot 設定
# 使用 OpenClaw 內建通知機制，不透過 Bot Token 直接發送
# 由 OpenClaw cron job 呼叫時使用 message 工具發送
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
    """取得台中天氣"""
    try:
        result = subprocess.run(
            ['curl', '-s', 'wttr.in/Taichung?format=%l:+%c+%t+(體感+%f),+%w+風速,+%h+濕度,+%p+降雨機率'],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip()
    except:
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
    """取得科技新聞（使用輪替的預設內容，確保每天不同）"""
    from datetime import datetime
    
    # 根據日期選擇不同的新聞組合（確保每天不重複）
    day_of_year = datetime.now().timetuple().tm_yday
    
    # 多組新聞內容輪替
    news_collections = [
        # 組合 1: AI 主題
        [
            {"title": "NVIDIA Blackwell 架構顯卡正式出貨", "emoji": "🎮", "summary": "新一代 AI 顯卡效能翻倍，電腦硬體升級潮即將來臨！"},
            {"title": "AI PC 成為市場新寵", "emoji": "🤖", "summary": "內建 NPU 的處理器讓筆電也能跑 AI，換機需求看漲。"},
            {"title": "Intel Core Ultra 處理器降價", "emoji": "💻", "summary": "AI 筆電更親民，消費者換機意願提升！"}
        ],
        # 組合 2: 電競主題
        [
            {"title": "RTX 50 系列顯卡供貨穩定", "emoji": "🎮", "summary": "高階顯卡不再一卡難求，電競玩家升級好時機！"},
            {"title": "電競筆電市場持續成長", "emoji": "🏆", "summary": "高效能行動裝置需求增，高階機種銷量看漲。"},
            {"title": "DDR5 記憶體價格回穩", "emoji": "💾", "summary": "新平台裝機成本降低，整機銷售更有利潤空間。"}
        ],
        # 組合 3: 商用主題
        [
            {"title": "企業 AI 轉型加速", "emoji": "🤖", "summary": "商用電腦升級需求強勁，工作站級產品搶手。"},
            {"title": "遠端辦公設備更新潮", "emoji": "💻", "summary": "混合辦公模式成常態，筆電與週邊銷售增溫。"},
            {"title": "資安意識提升", "emoji": "🔒", "summary": "企業加強資安投資，商用軟體與服務需求增。"}
        ],
        # 組合 4: 產業動態
        [
            {"title": "半導體產業景氣回升", "emoji": "📈", "summary": "供應鏈恢復正常，電腦產品交期縮短。"},
            {"title": "面板價格觸底反彈", "emoji": "🖥️", "summary": "顯示器與筆電螢幕成本趨穩，終端售價更有競爭力。"},
            {"title": "SSD 固態硬碟大容量化", "emoji": "💾", "summary": "1TB 成為標準配備，消費者升級意願提高。"}
        ],
        # 組合 5: 消費趨勢
        [
            {"title": "開學季換機需求啟動", "emoji": "🎒", "summary": "學生族群採購高峰，文書與電競機種並進。"},
            {"title": "創作者市場崛起", "emoji": "🎨", "summary": "影音剪輯與設計需求增，高階筆電受青睞。"},
            {"title": "環保永續成選購考量", "emoji": "🌱", "summary": "節能標章與回收計畫影響消費決策。"}
        ]
    ]
    
    # 根據日期選擇新聞組合
    collection_index = day_of_year % len(news_collections)
    return news_collections[collection_index]

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
        message += f"\n{i}️⃣ {item['title']} {item['emoji']}\n{item['summary']}"
    
    message += f"""

---

🎯 今日小提醒

{quote}

祝今天順順利利，業績長紅！🦞✨
"""
    
    return message

def main():
    """主程式：生成晨報並輸出到 stdout"""
    print(f"🌅 生成晨報中... {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report = generate_report()
    return report

if __name__ == '__main__':
    report = main()
    print(report)
