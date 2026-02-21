#!/opt/homebrew/bin/python3
from flask import Flask, jsonify, send_from_directory
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
            FROM sales_history WHERE date >= '2026-01-01'
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
        
        conn.close()
        
        # 更新結果
        analysis_results['department'] = "\n".join(dept_analysis)
        analysis_results['store'] = "\n".join(store_analysis)
        analysis_results['personal'] = "\n".join(personal_analysis)
        analysis_results['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        
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

# API: 本季每日銷售
@app.route('/api/sales/daily')
def get_daily_sales():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT date, SUM(amount) as daily_total 
        FROM sales_history 
        WHERE date >= '2026-01-01' AND date <= '2026-03-31' 
        GROUP BY date 
        ORDER BY date
    """)
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{'date': row['date'], 'amount': row['daily_total']} for row in rows])

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
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT subject_name, target_amount, revenue_amount, profit_amount, 
               achievement_rate, margin_rate
        FROM performance_metrics 
        WHERE category = '門市'
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

# API: 門市五星好評
@app.route('/api/store/reviews')
def get_store_reviews():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT store_name, review_count FROM store_reviews")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{'store': row['store_name'], 'reviews': row['review_count']} for row in rows])

# API: 個人業績
@app.route('/api/performance/personal')
def get_personal_performance():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT salesperson, SUM(amount) as total_sales, COUNT(*) as order_count
        FROM sales_history 
        WHERE date >= '2026-01-01'
        GROUP BY salesperson 
        ORDER BY total_sales DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    
    # 過濾掉不需要顯示的人員
    excluded_names = ['莊圍迪', '萬書佑', '黃柏翰']
    
    result = []
    rank = 1
    for row in rows:
        if row['salesperson'] in excluded_names:
            continue
        avg_price = row['total_sales'] // row['order_count'] if row['order_count'] > 0 else 0
        result.append({
            'rank': rank,
            'name': row['salesperson'],
            'total': row['total_sales'],
            'orders': row['order_count'],
            'avg': avg_price
        })
        rank += 1
    return jsonify(result)

# API: 當周班表
@app.route('/api/roster/weekly')
def get_weekly_roster():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT date, staff_name, location, shift_code 
        FROM staff_roster 
        WHERE date >= '2026-02-15' AND date <= '2026-02-21'
        ORDER BY date, location, staff_name
    """)
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
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT staff_name, location, shift_code 
        FROM staff_roster 
        WHERE date = '2026-02-21'
        ORDER BY location, staff_name
    """)
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{
        'name': row['staff_name'],
        'location': row['location'],
        'shift': row['shift_code']
    } for row in rows])

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

if __name__ == '__main__':
    print("🚀 營運看板 API 服務啟動中...")
    print("📊 請訪問: http://localhost:3000")
    print("🤖 每日 20:00 自動分析已啟動")
    print("-" * 50)
    app.run(host='0.0.0.0', port=3000, debug=False)