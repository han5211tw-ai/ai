#!/opt/homebrew/bin/python3
from flask import Flask, jsonify, send_from_directory, request
from health_check import get_health_status
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)
CORS(app)

DB_PATH = '/Users/aiserver/srv/db/company.db'
STATIC_DIR = '/Users/aiserver/.openclaw/workspace/dashboard-site'

# 儲存分析結果
analysis_results = {
    'department': '',
    'store': '',
    'business': '',
    'personal': '',
    'last_update': None
}

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def generate_analysis():
    """每天 20:00 執行的分析函數"""
    global analysis_results
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # ===== 部門分析 =====
        cursor.execute("""
            SELECT subject_name, target_amount, revenue_amount, achievement_rate, margin_rate
            FROM performance_metrics WHERE category = '部門'
        """)
        dept_rows = cursor.fetchall()
        
        dept_analysis = []
        for row in dept_rows:
            name = row['subject_name']
            achievement = row['achievement_rate'] * 100
            margin = row['margin_rate'] * 100
            gap = row['target_amount'] - row['revenue_amount']
            
            if achievement >= 80:
                status = "表現優秀"
            elif achievement >= 60:
                status = "進度正常"
            elif achievement >= 40:
                status = "需要加油"
            else:
                status = "警訊：進度嚴重落後"
            
            dept_analysis.append(f"• {name}：達成率 {achievement:.1f}%，毛利率 {margin:.1f}%，{status}。距離目標尚差 NT${gap:,.0f}。")
        
        # ===== 門市分析 =====
        cursor.execute("""
            SELECT subject_name, target_amount, revenue_amount, achievement_rate, margin_rate
            FROM performance_metrics WHERE category = '門市'
        """)
        store_rows = cursor.fetchall()
        
        store_analysis = []
        best_store = max(store_rows, key=lambda x: x['achievement_rate'])
        worst_store = min(store_rows, key=lambda x: x['achievement_rate'])
        
        for row in store_rows:
            name = row['subject_name']
            achievement = row['achievement_rate'] * 100
            margin = row['margin_rate'] * 100
            
            if row['subject_name'] == best_store['subject_name']:
                comment = "🏆 本季表現最佳"
            elif row['subject_name'] == worst_store['subject_name']:
                comment = "⚠️ 需加強業績推動"
            else:
                comment = "穩定發展中"
            
            store_analysis.append(f"• {name}：達成率 {achievement:.1f}%，毛利率 {margin:.1f}%。{comment}")
        
        # ===== 個人分析 =====
        cursor.execute("""
            SELECT salesperson, SUM(amount) as total_sales, COUNT(*) as order_count
            FROM sales_history 
            WHERE date >= '2026-01-01' 
              AND salesperson NOT IN ('Unknown', '莊圍迪', '萬書佑', '黃柏翰')
            GROUP BY salesperson ORDER BY total_sales DESC
        """)
        personal_rows = cursor.fetchall()
        
        personal_analysis = []
        if len(personal_rows) >= 3:
            top3 = personal_rows[:3]
            personal_analysis.append(f"🏆 前三名業務員：")
            for i, row in enumerate(top3, 1):
                avg = row['total_sales'] // row['order_count'] if row['order_count'] > 0 else 0
                personal_analysis.append(f"  {i}. {row['salesperson']}：NT${row['total_sales']:,.0f}（{row['order_count']}筆，均價 NT${avg:,.0f}）")
            
            # 找出單價最高的
            highest_avg = max(personal_rows, key=lambda x: x['total_sales']//x['order_count'] if x['order_count'] > 0 else 0)
            personal_analysis.append(f"\n💡 單價之王：{highest_avg['salesperson']}（平均 NT${highest_avg['total_sales']//highest_avg['order_count']:,.0f}/筆）")
        
        # 業務分析（不在門市班表中的業務員）
        cursor.execute("""
            SELECT DISTINCT staff_name FROM staff_roster 
            WHERE location IN ('豐原', '潭子', '大雅')
        """)
        store_staff = [row['staff_name'] for row in cursor.fetchall()]
        
        cursor.execute("""
            SELECT subject_name, target_amount, revenue_amount, profit_amount, achievement_rate, margin_rate
            FROM performance_metrics
            WHERE category = '個人' AND subject_name NOT IN ({placeholders})
        """.format(placeholders=','.join(['?' for _ in store_staff])), store_staff)
        business_rows = cursor.fetchall()
        
        business_analysis = ["💼 業務部總覽\n"]
        for row in business_rows:
            name = row['subject_name']
            target = row['target_amount']
            revenue = row['revenue_amount']
            achievement = row['achievement_rate'] * 100
            margin = row['margin_rate'] * 100
            
            if achievement >= 80:
                comment = "表現優秀！"
            elif achievement >= 60:
                comment = "達標，繼續加油！"
            elif achievement >= 40:
                comment = "接近目標，需要衝刺。"
            else:
                comment = "落後較多，需檢討改進。"
            
            business_analysis.append(f"• {name}：達成率 {achievement:.1f}%，毛利率 {margin:.1f}%。{comment}")
        
        # 更新結果
        analysis_results['department'] = "\n".join(dept_analysis)
        analysis_results['store'] = "\n".join(store_analysis)
        analysis_results['business'] = "\n".join(business_analysis)
        analysis_results['personal'] = "\n".join(personal_analysis)
        analysis_results['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        conn.close()
        print(f"✅ 分析完成：{analysis_results['last_update']}")
        
    except Exception as e:
        print(f"❌ 分析失敗：{e}")

# 初始化排程器
scheduler = BackgroundScheduler()
scheduler.add_job(generate_analysis, 'cron', hour=20, minute=0)
scheduler.start()

# 啟動時立即執行一次分析
generate_analysis()

@app.route('/')
def index():
    return send_from_directory(STATIC_DIR, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(STATIC_DIR, path)

# API: 分析結果
@app.route('/api/analysis/<type>')
def get_analysis(type):
    if type in analysis_results:
        return jsonify({
            'content': analysis_results[type],
            'last_update': analysis_results['last_update']
        })
    return jsonify({'error': 'Invalid type'}), 400

# API: 本季每日銷售（堆叠：門市部+業務部）
@app.route('/api/sales/daily')
def get_daily_sales():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 人員編制：門市部人員（豐原、潭子、大雅）
    store_staff = ['林榮祺', '林峙文', '劉育仕', '林煜捷', '張永承', '張家碩']
    
    # 獲取總銷售
    cursor.execute("""
        SELECT date, SUM(amount) as daily_total, COUNT(*) as daily_count
        FROM sales_history 
        WHERE date >= '2026-01-01' AND date <= '2026-03-31' 
        GROUP BY date 
        ORDER BY date
    """)
    total_rows = {row['date']: {'amount': row['daily_total'], 'count': row['daily_count']} for row in cursor.fetchall()}
    
    # 獲取門市部銷售（只計算門市人員，不含主管）
    placeholders = ','.join(['?' for _ in store_staff])
    cursor.execute(f"""
        SELECT date, SUM(amount) as daily_total
        FROM sales_history
        WHERE date >= '2026-01-01' AND date <= '2026-03-31'
        AND salesperson IN ({placeholders})
        GROUP BY date
        ORDER BY date
    """, store_staff)
    store_rows = {row['date']: row['daily_total'] for row in cursor.fetchall()}
    
    conn.close()
    
    # 合併數據：門市部 + 業務部（總計-門市部）
    result = []
    for date, total in total_rows.items():
        store_amount = store_rows.get(date, 0)
        business_amount = total['amount'] - store_amount
        result.append({
            'date': date,
            'store': store_amount,
            'business': business_amount,
            'total': total['amount'],
            'count': total['count']
        })
    
    return jsonify(result)

# API: 本季每日銷售（只含門市部）
@app.route('/api/sales/daily/store')
def get_daily_sales_store():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 獲取所有門市人員名單（曾在班表中出現的人員）
    cursor.execute("""
        SELECT DISTINCT staff_name FROM staff_roster 
        WHERE location IN ('豐原', '潭子', '大雅')
    """)
    store_staff = [row['staff_name'] for row in cursor.fetchall()]
    
    # 使用 LIKE 匹配（因為 sales_history 是全名，staff_roster 是名字）
    conditions = ' OR '.join([f"salesperson LIKE '%' || ? || '%'" for _ in store_staff])
    
    cursor.execute(f"""
        SELECT date, SUM(amount) as daily_total, COUNT(*) as daily_count
        FROM sales_history
        WHERE date >= '2026-01-01' AND date <= '2026-03-31'
        AND ({conditions})
        GROUP BY date
        ORDER BY date
    """, store_staff)
    
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{'date': row['date'], 'amount': row['daily_total'], 'count': row['daily_count']} for row in rows])

# API: 本季每日銷售（各門市明細）
@app.route('/api/sales/daily/by-store')
def get_daily_sales_by_store():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 獲取各門市的人員名單
    cursor.execute("""
        SELECT DISTINCT location, staff_name FROM staff_roster 
        WHERE location IN ('豐原', '潭子', '大雅')
    """)
    staff_by_store = {}
    for row in cursor.fetchall():
        if row['location'] not in staff_by_store:
            staff_by_store[row['location']] = []
        staff_by_store[row['location']].append(row['staff_name'])
    
    # 獲取所有日期
    cursor.execute("""
        SELECT DISTINCT date FROM sales_history 
        WHERE date >= '2026-01-01' AND date <= '2026-03-31'
        ORDER BY date
    """)
    dates = [row['date'] for row in cursor.fetchall()]
    
    result = []
    for date in dates:
        day_data = {'date': date, 'stores': {}}
        for store, staff_list in staff_by_store.items():
            conditions = ' OR '.join([f"salesperson LIKE '%' || ? || '%'" for _ in staff_list])
            cursor.execute(f"""
                SELECT SUM(amount) as total
                FROM sales_history
                WHERE date = ? AND ({conditions})
            """, [date] + staff_list)
            row = cursor.fetchone()
            day_data['stores'][store] = row['total'] or 0
        result.append(day_data)
    
    conn.close()
    return jsonify(result)

# API: 部門業績
@app.route('/api/performance/department')
def get_dept_performance():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT subject_name, target_amount, revenue_amount, profit_amount, 
               achievement_rate, margin_rate
        FROM performance_metrics 
        WHERE category = '部門'
    """)
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        'name': row['subject_name'],
        'target': row['target_amount'],
        'revenue': row['revenue_amount'],
        'profit': row['profit_amount'],
        'achievement_rate': row['achievement_rate'],
        'margin_rate': row['margin_rate']
    } for row in rows])

# API: 門市業績
@app.route('/api/performance/store')
def get_store_performance():
    from datetime import datetime
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 人員編制定義
    # 門市部：主管(莊圍迪) + 三個門市
    # 業務部：主管(萬書佑) + 兩位業務員
    store_staff = {
        '豐原': ['林榮祺', '林峙文'],
        '潭子': ['劉育仕', '林煜捷'],
        '大雅': ['張永承', '張家碩']
    }
    business_staff = ['鄭宇晉', '梁仁佑']  # 業務部業務員
    department_managers = ['莊圍迪', '萬書佑']  # 部門主管（不列入門市）
    
    # 動態計算到今天日期
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 從 sales_history 即時計算門市業績（只計算門市人員，不含主管）
    cursor.execute("""
        SELECT 
            salesperson,
            SUM(amount) as total_sales,
            SUM(profit) as total_profit
        FROM sales_history 
        WHERE date >= '2026-01-01' AND date <= ?
          AND salesperson NOT IN ('Unknown', '黃柏翰', '')
        GROUP BY salesperson
    """, (today,))
    rows = cursor.fetchall()
    
    # 按門市彙總（只包含門市人員）
    store_stats = {}
    for row in rows:
        name = row['salesperson']
        # 檢查此人屬於哪個門市
        for store_name, staff_list in store_staff.items():
            if name in staff_list:
                if store_name not in store_stats:
                    store_stats[store_name] = {'sales': 0, 'profit': 0}
                store_stats[store_name]['sales'] += row['total_sales']
                store_stats[store_name]['profit'] += row['total_profit'] or 0
                break
    
    # 獲取門市目標
    cursor.execute("""
        SELECT subject_name, target_amount
        FROM performance_metrics 
        WHERE category = '門市'
    """)
    target_rows = cursor.fetchall()
    target_map = {}
    for row in target_rows:
        # 去除"門市"後綴，只保留名稱
        name = row['subject_name'].replace('門市', '')
        target_map[name] = row['target_amount']
    
    conn.close()
    
    # 構建結果
    result = []
    for store_name in ['豐原', '潭子', '大雅']:
        stats = store_stats.get(store_name, {'sales': 0, 'profit': 0})
        sales = stats['sales']
        profit = stats['profit']
        target = target_map.get(store_name, 0)
        margin = profit / sales if sales > 0 else 0
        achievement = sales / target if target > 0 else 0
        
        result.append({
            'name': store_name,
            'target': target,
            'revenue': sales,
            'profit': profit,
            'achievement_rate': achievement,
            'margin_rate': margin
        })
    
    return jsonify(result)

# API: 門市五星好評
@app.route('/api/store/reviews')
def get_store_reviews():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT store_name, review_count FROM store_reviews")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{'store': row['store_name'], 'reviews': row['review_count']} for row in rows])

# API: 門市督導評分（本月）
@app.route('/api/store/supervision')
def get_store_supervision():
    from datetime import datetime
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 獲取本月日期範圍
    today = datetime.now()
    month_start = f"{today.year}-{today.month:02d}-01"
    
    # 計算每個門市本月的平均督導評分
    # 15項 × 3分 = 45分滿分，計算百分比
    cursor.execute("""
        SELECT 
            store_name,
            AVG(CAST(COALESCE(attendance, '0') AS FLOAT)) as avg_attendance,
            AVG(CAST(COALESCE(appearance, '0') AS FLOAT)) as avg_appearance,
            AVG(CAST(COALESCE(service_attitude, '0') AS FLOAT)) as avg_service,
            AVG(CAST(COALESCE(professional_knowledge, '0') AS FLOAT)) as avg_knowledge,
            AVG(CAST(COALESCE(sales_process, '0') AS FLOAT)) as avg_sales,
            AVG(CAST(COALESCE(storefront_cleanliness, '0') AS FLOAT)) as avg_storefront,
            AVG(CAST(COALESCE(store_cleanliness, '0') AS FLOAT)) as avg_cleanliness,
            AVG(CAST(COALESCE(product_display, '0') AS FLOAT)) as avg_display,
            AVG(CAST(COALESCE(cable_management, '0') AS FLOAT)) as avg_cable,
            AVG(CAST(COALESCE(warehouse_organization, '0') AS FLOAT)) as avg_warehouse,
            AVG(CAST(COALESCE(reply_speed, '0') AS FLOAT)) as avg_reply_speed,
            AVG(CAST(COALESCE(reply_attitude, '0') AS FLOAT)) as avg_reply_attitude,
            AVG(CAST(COALESCE(problem_grasp, '0') AS FLOAT)) as avg_problem,
            AVG(CAST(COALESCE(information_complete, '0') AS FLOAT)) as avg_info,
            AVG(CAST(COALESCE(follow_up, '0') AS FLOAT)) as avg_followup
        FROM supervision_scores 
        WHERE date >= ? AND date < date(?, '+1 month')
        GROUP BY store_name
    """, (month_start, month_start))
    
    rows = cursor.fetchall()
    
    # 獲取每個門市本月的督導次數
    cursor.execute("""
        SELECT 
            store_name,
            COUNT(DISTINCT date) as inspection_count
        FROM supervision_scores 
        WHERE date >= ? AND date < date(?, '+1 month')
        GROUP BY store_name
    """, (month_start, month_start))
    count_rows = cursor.fetchall()
    count_map = {row['store_name']: row['inspection_count'] for row in count_rows}
    
    conn.close()
    
    result = []
    for row in rows:
        # 計算總分（15項的平均值相加）
        total_avg = sum([
            row['avg_attendance'] or 0,
            row['avg_appearance'] or 0,
            row['avg_service'] or 0,
            row['avg_knowledge'] or 0,
            row['avg_sales'] or 0,
            row['avg_storefront'] or 0,
            row['avg_cleanliness'] or 0,
            row['avg_display'] or 0,
            row['avg_cable'] or 0,
            row['avg_warehouse'] or 0,
            row['avg_reply_speed'] or 0,
            row['avg_reply_attitude'] or 0,
            row['avg_problem'] or 0,
            row['avg_info'] or 0,
            row['avg_followup'] or 0
        ])
        # 30分滿分（15項×2分），計算百分比
        score_percentage = (total_avg / 30) * 100 if total_avg > 0 else 0
        store_name = row['store_name']
        
        result.append({
            'store': store_name,
            'score': round(score_percentage, 1),
            'inspection_count': count_map.get(store_name, 0)
        })
    
    return jsonify(result)

# API: 門市督導評分明細（本月詳細項目）
@app.route('/api/store/supervision/detail')
def get_store_supervision_detail():
    from datetime import datetime
    conn = get_db_connection()
    cursor = conn.cursor()
    
    today = datetime.now()
    month_start = f"{today.year}-{today.month:02d}-01"
    
    cursor.execute("""
        SELECT 
            store_name,
            AVG(CAST(COALESCE(attendance, '0') AS FLOAT)) as avg_attendance,
            AVG(CAST(COALESCE(appearance, '0') AS FLOAT)) as avg_appearance,
            AVG(CAST(COALESCE(service_attitude, '0') AS FLOAT)) as avg_service,
            AVG(CAST(COALESCE(professional_knowledge, '0') AS FLOAT)) as avg_knowledge,
            AVG(CAST(COALESCE(sales_process, '0') AS FLOAT)) as avg_sales,
            AVG(CAST(COALESCE(storefront_cleanliness, '0') AS FLOAT)) as avg_storefront,
            AVG(CAST(COALESCE(store_cleanliness, '0') AS FLOAT)) as avg_cleanliness,
            AVG(CAST(COALESCE(product_display, '0') AS FLOAT)) as avg_display,
            AVG(CAST(COALESCE(cable_management, '0') AS FLOAT)) as avg_cable,
            AVG(CAST(COALESCE(warehouse_organization, '0') AS FLOAT)) as avg_warehouse,
            AVG(CAST(COALESCE(reply_speed, '0') AS FLOAT)) as avg_reply_speed,
            AVG(CAST(COALESCE(reply_attitude, '0') AS FLOAT)) as avg_reply_attitude,
            AVG(CAST(COALESCE(problem_grasp, '0') AS FLOAT)) as avg_problem,
            AVG(CAST(COALESCE(information_complete, '0') AS FLOAT)) as avg_info,
            AVG(CAST(COALESCE(follow_up, '0') AS FLOAT)) as avg_followup
        FROM supervision_scores 
        WHERE date >= ? AND date < date(?, '+1 month')
        GROUP BY store_name
    """, (month_start, month_start))
    
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        result.append({
            'store': row['store_name'],
            'items': [
                {'name': '出勤狀況', 'score': round(row['avg_attendance'] or 0, 1)},
                {'name': '服裝儀容', 'score': round(row['avg_appearance'] or 0, 1)},
                {'name': '服務態度', 'score': round(row['avg_service'] or 0, 1)},
                {'name': '專業知識', 'score': round(row['avg_knowledge'] or 0, 1)},
                {'name': '銷售流程', 'score': round(row['avg_sales'] or 0, 1)},
                {'name': '門面整潔', 'score': round(row['avg_storefront'] or 0, 1)},
                {'name': '店內清潔', 'score': round(row['avg_cleanliness'] or 0, 1)},
                {'name': '產品陳列', 'score': round(row['avg_display'] or 0, 1)},
                {'name': '線材管理', 'score': round(row['avg_cable'] or 0, 1)},
                {'name': '倉庫整齊', 'score': round(row['avg_warehouse'] or 0, 1)},
                {'name': '回覆速度', 'score': round(row['avg_reply_speed'] or 0, 1)},
                {'name': '回覆態度', 'score': round(row['avg_reply_attitude'] or 0, 1)},
                {'name': '問題掌握', 'score': round(row['avg_problem'] or 0, 1)},
                {'name': '資訊完整', 'score': round(row['avg_info'] or 0, 1)},
                {'name': '後續追蹤', 'score': round(row['avg_followup'] or 0, 1)}
            ]
        })
    
    return jsonify(result)

# API: 個人業績
@app.route('/api/performance/personal')
def get_personal_performance():
    from datetime import datetime
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 動態計算到今天日期
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 獲取所有人員銷售額和即時毛利率（從 sales_history 計算）
    cursor.execute("""
        SELECT 
            salesperson, 
            SUM(amount) as total_sales, 
            COUNT(*) as order_count,
            SUM(profit) as total_profit
        FROM sales_history 
        WHERE date >= '2026-01-01' AND date <= ?
          AND salesperson NOT IN ('Unknown', '黃柏翰', '')
          AND product_code IS NOT NULL 
          AND product_code != ''
          AND product_code LIKE '%-%'
        GROUP BY salesperson
        ORDER BY total_sales DESC
    """, (today,))
    sales_rows = cursor.fetchall()
    
    # 獲取個人目標（從 performance_metrics）
    cursor.execute("""
        SELECT subject_name, target_amount
        FROM performance_metrics 
        WHERE category = '個人'
    """)
    perf_rows = cursor.fetchall()
    target_map = {row['subject_name']: row['target_amount'] for row in perf_rows}
    
    conn.close()
    
    # 過濾掉不需要顯示的人員（主管不列入個人排名）
    excluded_names = ['莊圍迪', '萬書佑', 'Unknown']
    
    result = []
    rank = 1
    for row in sales_rows:
        name = row['salesperson']
        if name in excluded_names:
            continue
        
        total_sales = row['total_sales']
        order_count = row['order_count']
        total_profit = row['total_profit'] or 0
        avg_price = total_sales // order_count if order_count > 0 else 0
        
        # 即時計算毛利率
        margin = total_profit / total_sales if total_sales > 0 else 0
        
        # 獲取目標
        target = target_map.get(name, 0)
        achievement = total_sales / target if target > 0 else 0
        
        result.append({
            'rank': rank,
            'name': name,
            'total': total_sales,
            'orders': order_count,
            'avg': avg_price,
            'target': target,
            'achievement_rate': achievement,
            'margin_rate': margin
        })
        rank += 1
    
    return jsonify(result)

# API: 業務員績效（業務部：鄭宇晉、梁仁佑）
@app.route('/api/performance/business')
def get_business_performance():
    from datetime import datetime
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 業務部人員列表
    business_staff = ['鄭宇晉', '梁仁佑']
    
    # 動態計算到今天日期
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 獲取業務員即時績效（從 sales_history 計算）
    placeholders = ','.join(['?' for _ in business_staff])
    cursor.execute(f"""
        SELECT 
            salesperson,
            SUM(amount) as total_sales,
            SUM(profit) as total_profit
        FROM sales_history 
        WHERE date >= '2026-01-01' AND date <= ?
          AND salesperson IN ({placeholders})
        GROUP BY salesperson
    """, [today] + business_staff)
    
    sales_rows = cursor.fetchall()
    
    # 獲取業務員目標
    cursor.execute("""
        SELECT subject_name, target_amount
        FROM performance_metrics 
        WHERE category = '個人' AND subject_name IN ('鄭宇晉', '梁仁佑')
    """)
    target_rows = cursor.fetchall()
    target_map = {row['subject_name']: row['target_amount'] for row in target_rows}
    
    conn.close()
    
    result = []
    for row in sales_rows:
        name = row['salesperson']
        sales = row['total_sales']
        profit = row['total_profit'] or 0
        target = target_map.get(name, 0)
        margin = profit / sales if sales > 0 else 0
        achievement = sales / target if target > 0 else 0
        
        result.append({
            'name': name,
            'target': target,
            'revenue': sales,
            'achievement_rate': achievement,
            'margin_rate': margin
        })
    
    return jsonify(result)

# API: 當周班表 (週日開始)
@app.route('/api/roster/weekly')
def get_weekly_roster():
    from datetime import datetime, timedelta
    
    today = datetime.now()
    sunday = today - timedelta(days=(today.weekday() + 1) % 7)  # 本週日
    saturday = sunday + timedelta(days=6)  # 本週六
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT date, staff_name, location, shift_code 
        FROM staff_roster 
        WHERE date >= ? AND date <= ?
        ORDER BY date, location, staff_name
    """, (sunday.strftime('%Y-%m-%d'), saturday.strftime('%Y-%m-%d')))
    rows = cursor.fetchall()
    conn.close()
    
    staff_weekly = {}
    for row in rows:
        name = row['staff_name']
        date = row['date']
        if name not in staff_weekly:
            staff_weekly[name] = {'location': row['location'], 'shifts': {}}
        staff_weekly[name]['shifts'][date] = row['shift_code']
    
    return jsonify(staff_weekly)

# API: 今日班表
@app.route('/api/roster/today')
def get_today_roster():
    from datetime import datetime
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT staff_name, location, shift_code 
        FROM staff_roster 
        WHERE date = ?
        ORDER BY location, staff_name
    """, (today_str,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        'name': row['staff_name'],
        'location': row['location'],
        'shift': row['shift_code']
    } for row in rows])

# API: 最新需求表（只顯示尚未處理，依照日期排序）
@app.route('/api/needs/latest')
def get_latest_needs():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 獲取查詢參數：type=all/請購/調撥，預設顯示全部
    filter_type = request.args.get('type', 'all')

    # 獲取所有尚未處理的需求，依照日期排序（最新的在前）
    # 處理多種未處理標記：'False', '0.0', '', NULL
    if filter_type == '調撥':
        # 只顯示調撥（排除已取消和已完成）
        cursor.execute("""
            SELECT id, date, item_name, quantity, customer_code, department,
                   requester, vendor_delivery, vendor_name, main_wh_stock,
                   processed, status, product_code, remark, purpose, request_type, transfer_from
            FROM needs
            WHERE (processed = 'False' OR processed = '0.0' OR processed = '' OR processed IS NULL)
              AND request_type = '調撥'
              AND (status IS NULL OR status = '' OR status = '待處理')
            ORDER BY date DESC, id DESC
            LIMIT 50
        """)
    elif filter_type == '請購':
        # 只顯示請購（包含 NULL 和空值，排除已取消和已完成）
        cursor.execute("""
            SELECT id, date, item_name, quantity, customer_code, department,
                   requester, vendor_delivery, vendor_name, main_wh_stock,
                   processed, status, product_code, remark, purpose, request_type, transfer_from
            FROM needs
            WHERE (processed = 'False' OR processed = '0.0' OR processed = '' OR processed IS NULL)
              AND (request_type = '請購' OR request_type IS NULL OR request_type = '')
              AND (status IS NULL OR status = '' OR status = '待處理')
            ORDER BY date DESC, id DESC
            LIMIT 50
        """)
    else:
        # 預設：顯示全部（請購 + 調撥，排除已取消和已完成）
        cursor.execute("""
            SELECT id, date, item_name, quantity, customer_code, department,
                   requester, vendor_delivery, vendor_name, main_wh_stock,
                   processed, status, product_code, remark, purpose, request_type, transfer_from
            FROM needs
            WHERE (processed = 'False' OR processed = '0.0' OR processed = '' OR processed IS NULL)
              AND (status IS NULL OR status = '' OR status = '待處理')
            ORDER BY date DESC, id DESC
            LIMIT 50
        """)
    rows = cursor.fetchall()
    
    if not rows:
        conn.close()
        return jsonify({'date': None, 'items': []})
    
    # 獲取最新日期用於顯示
    latest_date = rows[0]['date'] if rows else None
    
    result_items = []
    for row in rows:
        product_code = row['product_code'] if row['product_code'] else ''
        
        # 如果有產品編號，從庫存表查詢產品名稱
        display_name = row['item_name']
        if product_code:
            cursor.execute("""
                SELECT item_spec FROM inventory 
                WHERE product_id = ? 
                ORDER BY report_date DESC LIMIT 1
            """, (product_code,))
            inv_row = cursor.fetchone()
            if inv_row and inv_row['item_spec']:
                display_name = inv_row['item_spec']
            # 如果 Excel 沒有填產品名稱，但庫存表有，就用庫存表的
            elif (not display_name or display_name.strip() == '' or display_name == 'None') and inv_row and inv_row['item_spec']:
                display_name = inv_row['item_spec']
        
        # 查詢最後一次進貨價格與廠商名稱
        last_price = None
        last_vendor = None
        if product_code:
            cursor.execute("""
                SELECT price, supplier_name FROM purchase_history
                WHERE product_code = ?
                ORDER BY date DESC LIMIT 1
            """, (product_code,))
            price_row = cursor.fetchone()
            if price_row:
                last_price = price_row['price']
                last_vendor = price_row['supplier_name']
        
        # 查詢庫存分布（只顯示最新日期、庫存 > 0 的倉庫）
        stock_warehouses = []
        if product_code:
            # 先找最新日期
            cursor.execute("""
                SELECT MAX(report_date) as latest_date
                FROM inventory
                WHERE product_id = ?
            """, (product_code,))
            latest_row = cursor.fetchone()
            if latest_row and latest_row['latest_date']:
                # 只取最新日期的庫存（合併同一倉庫的數量）
                cursor.execute("""
                    SELECT warehouse, SUM(stock_quantity) as total_qty
                    FROM inventory
                    WHERE product_id = ? AND report_date = ? AND stock_quantity > 0
                    GROUP BY warehouse
                    ORDER BY warehouse
                """, (product_code, latest_row['latest_date']))
                stock_rows = cursor.fetchall()
                stock_warehouses = [{'warehouse': r['warehouse'], 'qty': r['total_qty']} for r in stock_rows]
        
        result_items.append({
            'id': row['id'],
            'date': row['date'],
            'item_name': row['item_name'],
            'display_name': display_name,
            'quantity': row['quantity'],
            'customer_code': row['customer_code'] if row['customer_code'] and row['customer_code'] not in ('nan', 'None', 'NaN') else '',
            'department': row['department'],
            'requester': row['requester'],
            'vendor_delivery': row['vendor_delivery'],
            'vendor_name': row['vendor_name'],
            'main_wh_stock': row['main_wh_stock'],
            'processed': row['processed'],
            'status': row['status'],
            'product_code': product_code,
            'last_price': last_price,
            'last_vendor': last_vendor,
            'stock_warehouses': stock_warehouses,
            'remark': row['remark'] if row['remark'] else '',
            'purpose': row['purpose'] if row['purpose'] else '備貨',
            'request_type': row['request_type'] if row['request_type'] else '請購',
            'transfer_from': row['transfer_from'] if row['transfer_from'] else ''
        })
    
    conn.close()
    
    return jsonify({
        'date': latest_date,
        'items': result_items
    })

# API: 總計數據
@app.route('/api/summary')
def get_summary():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT SUM(amount) FROM sales_history WHERE date >= '2026-01-01'")
    total_revenue = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(amount) FROM sales_history WHERE date = '2026-02-21'")
    today_revenue = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(DISTINCT date) FROM sales_history WHERE date >= '2026-01-01'")
    day_count = cursor.fetchone()[0] or 1
    avg_revenue = total_revenue // day_count
    
    cursor.execute("SELECT MAX(daily_total) FROM (SELECT date, SUM(amount) as daily_total FROM sales_history WHERE date >= '2026-01-01' GROUP BY date)")
    max_revenue = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return jsonify({
        'total': total_revenue,
        'today': today_revenue,
        'avg': avg_revenue,
        'max': max_revenue
    })

# API: 服務記錄統計（本季）
@app.route('/api/service-records/summary')
def get_service_records_summary():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 獲取本季日期範圍
    cursor.execute("""
        SELECT date, salesperson, COUNT(*) as count
        FROM service_records
        WHERE date >= '2026-01-01' AND date <= '2026-03-31'
        GROUP BY date, salesperson
    """)
    rows = cursor.fetchall()
    conn.close()
    
    # 統計各業務員筆數
    zhen_count = 0
    liang_count = 0
    
    for row in rows:
        salesperson = row['salesperson'] if row['salesperson'] else ''
        if '鄭宇晉' in salesperson:
            zhen_count += row['count']
        elif '梁仁佑' in salesperson:
            liang_count += row['count']
    
    return jsonify({
        'zhen_count': zhen_count,
        'liang_count': liang_count,
        'total_count': zhen_count + liang_count
    })

# 產品名稱映射表（用於沒有在 inventory 表中的服務類產品與組合品）
PRODUCT_NAME_MAP = {
    'SE-OU': '服務-其他',
    'SE-PC': '服務-電腦維修/檢測',
    'SE-NB': '服務-筆電維修',
    'SE-MB-0001': '服務-維修筆電主機板',
    'SE-NB-0002': '服務-維修筆電-其他',
    'PS-PC-001': '組合-電腦套組(初階)',
    'PS-PC-002': '組合-電腦套組(中階)',
    'PS-PC-003': '組合-電腦套組(高階)',
    'PS-PC-004': '組合-電腦套組(尊榮)',
    'PS-PC-005': '組合-電腦套組(特仕)',
    'PS-PC-006': '組合-電腦套組(商務)',
    'PS-PC-007': '組合-電腦套組(電競)',
    'PS-PC-008': '組合-電腦套組(工作站)',
    'SE-CO-0001': '服務-監控系統諮詢',
    'SE-PC-0001': '服務-電腦維修(保固內)',
}

def get_product_name(product_code, inventory_name=None):
    """獲取產品名稱，優先使用 inventory 表，其次使用映射表，最後回傳產品編號"""
    if inventory_name and inventory_name != product_code:
        return inventory_name
    if product_code in PRODUCT_NAME_MAP:
        return PRODUCT_NAME_MAP[product_code]
    return product_code

# API: 客戶搜尋（模糊比對姓名或手機）
@app.route('/api/customer/search')
def search_customer():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'found': False, 'message': '請輸入搜尋關鍵字'})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 模糊搜尋客戶（姓名或手機），上限50筆
    cursor.execute("""
        SELECT customer_id, short_name, phone1, mobile, company_address
        FROM customers
        WHERE short_name LIKE ? OR mobile LIKE ? OR phone1 LIKE ?
        ORDER BY short_name
        LIMIT 50
    """, (f'%{query}%', f'%{query}%', f'%{query}%'))
    
    customers = cursor.fetchall()
    
    if not customers:
        conn.close()
        return jsonify({'found': False, 'message': '找不到符合的客戶'})
    
    # 如果只有一筆，直接回傳詳細資料
    if len(customers) == 1:
        customer = customers[0]
        cursor.execute("""
            SELECT s.date, s.product_code, s.product_name, s.quantity, s.amount, s.salesperson,
                   i.item_spec as inventory_product_name
            FROM sales_history s
            LEFT JOIN (
                SELECT product_id, item_spec, MAX(report_date) as max_date
                FROM inventory
                GROUP BY product_id
            ) i ON s.product_code = i.product_id
            WHERE s.customer_name LIKE ? OR s.customer_id = ?
            ORDER BY s.date DESC
            LIMIT 20
        """, (f'%{customer["short_name"]}%', customer['customer_id']))
        purchases = cursor.fetchall()
        total_spent = sum(p['amount'] for p in purchases) if purchases else 0
        conn.close()
        
        return jsonify({
            'found': True,
            'multiple': False,
            'customer': {
                'customer_id': customer['customer_id'],
                'short_name': customer['short_name'],
                'phone1': customer['phone1'],
                'mobile': customer['mobile'],
                'address': customer['company_address']
            },
            'purchases': [{
                'date': p['date'],
                'product_code': p['product_code'],
                'product_name': get_product_name(p['product_code'], p['inventory_product_name']),
                'quantity': p['quantity'],
                'amount': p['amount'],
                'salesperson': p['salesperson']
            } for p in purchases],
            'total_spent': total_spent
        })
    
    # 多筆結果，回傳列表讓用戶選擇
    conn.close()
    return jsonify({
        'found': True,
        'multiple': True,
        'count': len(customers),
        'customers': [{
            'customer_id': c['customer_id'],
            'short_name': c['short_name'],
            'phone1': c['phone1'],
            'mobile': c['mobile']
        } for c in customers]
    })

# API: 獲取客戶總數
@app.route('/api/customer/count')
def get_customer_count():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM customers")
    result = cursor.fetchone()
    conn.close()
    return jsonify({'count': result['count']})

# API: 管理員健康檢查
@app.route('/api/v1/admin/health')
def admin_health_check():
    return jsonify(get_health_status())

# API: 查詢指定客戶詳細資料
@app.route('/api/customer/detail/<customer_id>')
def get_customer_detail(customer_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 查詢客戶基本資料
    cursor.execute("""
        SELECT customer_id, short_name, phone1, mobile, company_address
        FROM customers WHERE customer_id = ?
    """, (customer_id,))
    customer = cursor.fetchone()
    
    if not customer:
        conn.close()
        return jsonify({'found': False, 'message': '找不到該客戶'})
    
    # 查詢消費紀錄（直接使用 sales_history 的 product_name）
    cursor.execute("""
        SELECT s.date, s.product_code, s.product_name, s.quantity, s.amount, s.salesperson
        FROM sales_history s
        WHERE s.customer_id = ?
        ORDER BY s.date DESC
        LIMIT 20
    """, (customer['customer_id'],))
    purchases = cursor.fetchall()
    total_spent = sum(p['amount'] for p in purchases) if purchases else 0
    
    conn.close()
    
    return jsonify({
        'found': True,
        'customer': {
            'customer_id': customer['customer_id'],
            'short_name': customer['short_name'],
            'phone1': customer['phone1'],
            'mobile': customer['mobile'],
            'address': customer['company_address']
        },
        'purchases': [{
            'date': p['date'],
            'product_code': p['product_code'],
            'product_name': p['product_name'] or p['product_code'],
            'quantity': p['quantity'],
            'amount': p['amount'],
            'salesperson': p['salesperson']
        } for p in purchases],
        'total_spent': total_spent
    })

# API: 服務記錄詳細統計
@app.route('/api/service-records/detail')
def get_service_records_detail():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 本季日期範圍
    cursor.execute("""
        SELECT 
            date,
            salesperson,
            COUNT(*) as count,
            COUNT(DISTINCT customer_code) as unique_customers,
            SUM(CASE WHEN is_contract = 1 THEN 1 ELSE 0 END) as contract_count,
            SUM(CASE WHEN is_contract = 0 THEN 1 ELSE 0 END) as non_contract_count
        FROM service_records
        WHERE date >= '2026-01-01' AND date <= '2026-03-31'
        GROUP BY date, salesperson
        ORDER BY date DESC, salesperson
    """)
    daily_stats = cursor.fetchall()
    
    # 服務分類統計
    cursor.execute("""
        SELECT 
            service_type,
            COUNT(*) as count
        FROM service_records
        WHERE date >= '2026-01-01' AND date <= '2026-03-31'
        GROUP BY service_type
        ORDER BY count DESC
    """)
    service_type_stats = cursor.fetchall()
    
    # 客戶來源統計
    cursor.execute("""
        SELECT 
            customer_source,
            COUNT(*) as count
        FROM service_records
        WHERE date >= '2026-01-01' AND date <= '2026-03-31'
          AND customer_source IS NOT NULL AND customer_source != ''
        GROUP BY customer_source
        ORDER BY count DESC
    """)
    source_stats = cursor.fetchall()
    
    # 業務員本季總覽
    cursor.execute("""
        SELECT 
            salesperson,
            COUNT(*) as total_count,
            COUNT(DISTINCT customer_code) as unique_customers,
            SUM(CASE WHEN is_contract = 1 THEN 1 ELSE 0 END) as contract_count
        FROM service_records
        WHERE date >= '2026-01-01' AND date <= '2026-03-31'
        GROUP BY salesperson
        ORDER BY total_count DESC
    """)
    salesperson_summary = cursor.fetchall()
    
    conn.close()
    
    return jsonify({
        'daily_stats': [{
            'date': r['date'],
            'salesperson': r['salesperson'],
            'count': r['count'],
            'unique_customers': r['unique_customers'],
            'contract_count': r['contract_count'],
            'non_contract_count': r['non_contract_count']
        } for r in daily_stats],
        'service_types': [{
            'type': r['service_type'] or '未分類',
            'count': r['count']
        } for r in service_type_stats],
        'customer_sources': [{
            'source': r['customer_source'] or '未分類',
            'count': r['count']
        } for r in source_stats],
        'salesperson_summary': [{
            'salesperson': r['salesperson'],
            'total_count': r['total_count'],
            'unique_customers': r['unique_customers'],
            'contract_count': r['contract_count']
        } for r in salesperson_summary]
    })

# API: 密碼驗證
@app.route('/api/auth/verify', methods=['POST'])
def verify_password():
    data = request.get_json()
    password = data.get('password', '')
    
    if not password or len(password) != 4:
        return jsonify({'success': False, 'message': '密碼格式錯誤'})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, department FROM staff_passwords WHERE password = ?", (password,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return jsonify({
            'success': True,
            'name': row['name'],
            'department': row['department']
        })
    else:
        return jsonify({'success': False, 'message': '密碼錯誤'})

# API: 產品資訊查詢
@app.route('/api/product/info')
def get_product_info():
    code = request.args.get('code', '').strip()
    if not code:
        return jsonify({'found': False})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 查詢產品名稱（從庫存表）
    cursor.execute("""
        SELECT item_spec FROM inventory 
        WHERE product_id = ? 
        ORDER BY report_date DESC LIMIT 1
    """, (code,))
    name_row = cursor.fetchone()
    product_name = name_row['item_spec'] if name_row else code
    
    # 查詢各倉庫庫存（只取最新日期）
    cursor.execute("""
        SELECT warehouse, stock_quantity as qty
        FROM inventory
        WHERE product_id = ? 
          AND report_date = (
              SELECT MAX(report_date) FROM inventory WHERE product_id = ?
          )
          AND stock_quantity > 0
        ORDER BY warehouse
    """, (code, code))
    stock_rows = cursor.fetchall()
    
    stock_list = [{'warehouse': r['warehouse'], 'qty': r['qty']} for r in stock_rows]
    
    conn.close()
    
    return jsonify({
        'found': True,
        'product_code': code,
        'product_name': product_name,
        'stock': stock_list
    })

# API: 客戶編號查詢
@app.route('/api/customer/lookup')
def lookup_customer():
    code = request.args.get('code', '').strip()
    if not code:
        return jsonify({'found': False})

    conn = get_db_connection()
    cursor = conn.cursor()

    # 查詢客戶資料
    cursor.execute("""
        SELECT customer_id, short_name, mobile, phone1
        FROM customers
        WHERE customer_id = ? OR short_name LIKE ?
        LIMIT 1
    """, (code, f'%{code}%'))
    row = cursor.fetchone()
    conn.close()

    if row:
        return jsonify({
            'found': True,
            'customer_id': row['customer_id'],
            'customer_name': row['short_name'],
            'phone': row['mobile'] or row['phone1'] or ''
        })
    else:
        return jsonify({'found': False})


# API: 批次提交需求
@app.route('/api/needs/batch', methods=['POST'])
def create_needs_batch():
    data = request.get_json()
    items = data.get('items', [])
    
    if not items:
        return jsonify({'success': False, 'message': '無資料'})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    inserted = 0
    
    for item in items:
        try:
            purpose = item.get('purpose', '備貨')
            customer_code = item.get('customer_code', '')
            request_type = item.get('request_type', '請購')
            transfer_from = item.get('transfer_from', '') if request_type == '調撥' else ''

            cursor.execute("""
                INSERT INTO needs
                (date, product_code, quantity, customer_code, department,
                 requester, status, created_at, remark, purpose, request_type, transfer_from)
                VALUES (?, ?, ?, ?, ?, ?, '待處理', ?, ?, ?, ?, ?)
            """, (
                item['date'],
                item['product_code'],
                item['quantity'],
                customer_code if purpose == '客戶' else '',
                item['department'],
                item['requester'],
                now,
                item.get('remark', ''),
                purpose,
                request_type,
                transfer_from
            ))
            inserted += 1
        except Exception as e:
            print(f"匯入失敗: {e}")
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'count': inserted})

# API: 取得最近提交（30分鐘內可取消）
@app.route('/api/needs/recent')
def get_recent_needs():
    requester = request.args.get('requester', '')
    if not requester:
        return jsonify({'items': []})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 獲取該填表人的待處理或30分鐘內的已取消需求
    cursor.execute("""
        SELECT id, date, product_code, quantity, customer_code, remark, 
               status, created_at, purpose, request_type, transfer_from,
               (strftime('%s', 'now', 'localtime') - strftime('%s', created_at)) / 60 as minutes_ago
        FROM needs
        WHERE requester = ? 
          AND (status = '待處理' OR (status = '已取消' AND 
               (strftime('%s', 'now', 'localtime') - strftime('%s', created_at)) < 1800))
        ORDER BY created_at DESC
        LIMIT 10
    """, (requester,))
    
    rows = cursor.fetchall()
    
    items = []
    for row in rows:
        minutes_ago = row['minutes_ago'] if row['minutes_ago'] else 999
        can_cancel = (row['status'] == '待處理' and minutes_ago < 30)
        
        # 查詢產品名稱
        product_name = ''
        if row['product_code']:
            cursor.execute("""
                SELECT item_spec FROM inventory 
                WHERE product_id = ? 
                ORDER BY report_date DESC LIMIT 1
            """, (row['product_code'],))
            inv_row = cursor.fetchone()
            if inv_row:
                product_name = inv_row['item_spec']
        
        items.append({
            'id': row['id'],
            'date': row['date'],
            'product_code': row['product_code'],
            'product_name': product_name,
            'quantity': row['quantity'],
            'customer_code': row['customer_code'],
            'remark': row['remark'],
            'status': row['status'],
            'purpose': row['purpose'],
            'request_type': row['request_type'],
            'transfer_from': row['transfer_from'],
            'can_cancel': can_cancel
        })
    
    conn.close()
    return jsonify({'items': items})

# API: 取消需求（軟刪除）
@app.route('/api/needs/cancel', methods=['POST'])
def cancel_need():
    data = request.get_json()
    need_id = data.get('id')

    if not need_id:
        return jsonify({'success': False, 'message': '缺少ID'})

    conn = get_db_connection()
    cursor = conn.cursor()

    # 檢查是否在30分鐘內
    cursor.execute("""
        SELECT status,
               (strftime('%s', 'now', 'localtime') - strftime('%s', created_at)) / 60 as minutes_ago
        FROM needs WHERE id = ?
    """, (need_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return jsonify({'success': False, 'message': '找不到該筆資料'})

    if row['status'] != '待處理':
        conn.close()
        return jsonify({'success': False, 'message': '該筆資料無法取消'})

    if row['minutes_ago'] >= 30:
        conn.close()
        return jsonify({'success': False, 'message': '超過30分鐘，無法取消'})

    # 軟刪除：標記為已取消
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        UPDATE needs
        SET status = '已取消', cancelled_at = ?
        WHERE id = ?
    """, (now, need_id))

    conn.commit()
    conn.close()

    return jsonify({'success': True})


# API: 標記需求為已完成（供老闆/會計使用）
@app.route('/api/needs/complete', methods=['POST'])
def complete_need():
    data = request.get_json()
    need_id = data.get('id')

    if not need_id:
        return jsonify({'success': False, 'message': '缺少ID'})

    conn = get_db_connection()
    cursor = conn.cursor()

    # 檢查資料是否存在且狀態為待處理
    cursor.execute("""
        SELECT status FROM needs WHERE id = ?
    """, (need_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return jsonify({'success': False, 'message': '找不到該筆資料'})

    if row['status'] != '待處理':
        conn.close()
        return jsonify({'success': False, 'message': '該筆資料無法標記完成'})

    # 標記為已完成
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        UPDATE needs
        SET status = '已完成', completed_at = ?
        WHERE id = ?
    """, (now, need_id))

    conn.commit()
    conn.close()

    return jsonify({'success': True})


# API: 更新需求備註
@app.route('/api/needs/remark', methods=['POST'])
def update_need_remark():
    data = request.get_json()
    need_id = data.get('id')
    remark = data.get('remark', '')

    if not need_id:
        return jsonify({'success': False, 'message': '缺少ID'})

    conn = get_db_connection()
    cursor = conn.cursor()

    # 檢查資料是否存在
    cursor.execute("SELECT id FROM needs WHERE id = ?", (need_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return jsonify({'success': False, 'message': '找不到該筆資料'})

    # 更新備註
    cursor.execute("""
        UPDATE needs
        SET remark = ?
        WHERE id = ?
    """, (remark, need_id))

    conn.commit()
    conn.close()

    return jsonify({'success': True})


# API: 手動執行所有排程腳本（除了備份與重開機）
@app.route('/api/v1/admin/run-scripts', methods=['POST'])
def run_all_scripts():
    import subprocess
    import os
    
    parser_dir = '/Users/aiserver/srv/parser'
    log_dir = '/Users/aiserver/srv/logs'
    
    # 確保日誌目錄存在
    os.makedirs(log_dir, exist_ok=True)
    
    # 要執行的腳本列表（排除重開機）
    scripts = [
        ('inventory_parser.py', '庫存模組'),
        ('purchase_parser.py', '進貨模組'),
        ('sales_parser_v19.py', '銷貨模組'),
        ('customer_parser.py', '客戶模組'),
        ('feedback_parser.py', '評論模組'),
        ('roster_parser.py', '班表模組'),
        ('performance_parser.py', '績效模組'),
        ('calculate_performance.py', '業績計算'),
        ('supervision_parser.py', '督導評分表'),
        ('service_record_parser.py', '出勤服務記錄'),
        ('needs_parser.py', '需求表模組'),
        ('generate_ai_analysis.py', 'AI 業績分析'),
        ('auto_backup.sh', '數據備份')
    ]
    
    results = []
    
    for script_name, script_desc in scripts:
        script_path = os.path.join(parser_dir, script_name)
        log_path = os.path.join(log_dir, script_name.replace('.py', '.log').replace('.sh', '.log'))
        
        try:
            # 檢查腳本是否存在
            if not os.path.exists(script_path):
                results.append({
                    'script': script_desc,
                    'status': 'error',
                    'message': f'腳本不存在: {script_name}'
                })
                continue
            
            # 根據腳本類型選擇執行方式
            if script_name.endswith('.sh'):
                # Shell 腳本
                cmd = ['/bin/bash', script_path]
            else:
                # Python 腳本
                cmd = ['/opt/homebrew/bin/python3', script_path]
            
            # 執行腳本
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分鐘超時
            )
            
            if result.returncode == 0:
                results.append({
                    'script': script_desc,
                    'status': 'success',
                    'message': '執行成功'
                })
            else:
                results.append({
                    'script': script_desc,
                    'status': 'error',
                    'message': f'返回碼 {result.returncode}: {result.stderr[:100]}'
                })
                
        except subprocess.TimeoutExpired:
            results.append({
                'script': script_desc,
                'status': 'error',
                'message': '執行超時（超過5分鐘）'
            })
        except Exception as e:
            results.append({
                'script': script_desc,
                'status': 'error',
                'message': str(e)[:100]
            })
    
    return jsonify({
        'success': True,
        'results': results
    })


# API: 手動執行單個排程腳本
@app.route('/api/v1/admin/run-script', methods=['POST'])
def run_single_script():
    import subprocess
    import os
    
    data = request.get_json()
    script_desc = data.get('script_name', '')
    
    if not script_desc:
        return jsonify({'success': False, 'message': '缺少腳本名稱'})
    
    parser_dir = '/Users/aiserver/srv/parser'
    log_dir = '/Users/aiserver/srv/logs'
    
    # 腳本對照表
    scripts_map = {
        '庫存模組': ('inventory_parser.py', 'inventory_parser.log'),
        '進貨模組': ('purchase_parser.py', 'purchase_parser.log'),
        '銷貨模組': ('sales_parser_v19.py', 'sales_parser.log'),
        '客戶模組': ('customer_parser.py', 'customer_parser.log'),
        '評論模組': ('feedback_parser.py', 'feedback_parser.log'),
        '班表模組': ('roster_parser.py', 'roster_parser.log'),
        '績效模組': ('performance_parser.py', 'performance_parser.log'),
        '業績計算': ('calculate_performance.py', 'calculate_performance.log'),
        '督導評分表': ('supervision_parser.py', 'supervision_parser.log'),
        '出勤服務記錄': ('service_record_parser.py', 'service_record_parser.log'),
        '需求表模組': ('needs_parser.py', 'needs_parser.log'),
        'AI 業績分析': ('generate_ai_analysis.py', 'ai_analysis.log'),
        '數據備份': ('auto_backup.sh', 'backup.log')
    }
    
    if script_desc not in scripts_map:
        return jsonify({'success': False, 'message': f'未知的腳本: {script_desc}'})
    
    script_name, log_name = scripts_map[script_desc]
    script_path = os.path.join(parser_dir, script_name)
    
    # 檢查腳本是否存在
    if not os.path.exists(script_path):
        return jsonify({
            'success': False,
            'result': {
                'script': script_desc,
                'status': 'error',
                'message': f'腳本不存在: {script_name}'
            }
        })
    
    try:
        # 根據腳本類型選擇執行方式
        if script_name.endswith('.sh'):
            cmd = ['/bin/bash', script_path]
        else:
            cmd = ['/opt/homebrew/bin/python3', script_path]
        
        # 執行腳本
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5分鐘超時
        )
        
        if result.returncode == 0:
            return jsonify({
                'success': True,
                'result': {
                    'script': script_desc,
                    'status': 'success',
                    'message': '執行成功'
                }
            })
        else:
            return jsonify({
                'success': True,
                'result': {
                    'script': script_desc,
                    'status': 'error',
                    'message': f'返回碼 {result.returncode}'
                }
            })
            
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': True,
            'result': {
                'script': script_desc,
                'status': 'error',
                'message': '執行超時（超過5分鐘）'
            }
        })
    except Exception as e:
        return jsonify({
            'success': True,
            'result': {
                'script': script_desc,
                'status': 'error',
                'message': str(e)[:100]
            }
        })


if __name__ == '__main__':
    print("🚀 營運看板 API 服務啟動中...")
    print("📊 請訪問: http://localhost:3000")
    print("🤖 每日 20:00 自動分析已啟動")
    print("-" * 50)
    app.run(host='0.0.0.0', port=3000, debug=False)