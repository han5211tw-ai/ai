#!/opt/homebrew/bin/python3
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)

DB_PATH = '/Users/aiserver/srv/db/company.db'
STATIC_DIR = '/Users/aiserver/.openclaw/workspace/dashboard-site'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return send_from_directory(STATIC_DIR, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(STATIC_DIR, path)

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
    result = []
    for i, row in enumerate(rows):
        avg_price = row['total_sales'] // row['order_count'] if row['order_count'] > 0 else 0
        result.append({
            'rank': i + 1,
            'name': row['salesperson'],
            'total': row['total_sales'],
            'orders': row['order_count'],
            'avg': avg_price
        })
    return jsonify(result)

# API: 當周班表
@app.route('/api/roster/weekly')
def get_weekly_roster():
    conn = get_db_connection()
    cursor = conn.cursor()
    # 本週日期：2/15 (週日) ~ 2/21 (週六)
    cursor.execute("""
        SELECT date, staff_name, location, shift_code 
        FROM staff_roster 
        WHERE date >= '2026-02-15' AND date <= '2026-02-21'
        ORDER BY date, location, staff_name
    """)
    rows = cursor.fetchall()
    conn.close()
    
    # 整理成每個人每週的班次
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
    
    # 本季總營收
    cursor.execute("SELECT SUM(amount) FROM sales_history WHERE date >= '2026-01-01'")
    total_revenue = cursor.fetchone()[0] or 0
    
    # 今日營收
    cursor.execute("SELECT SUM(amount) FROM sales_history WHERE date = '2026-02-21'")
    today_revenue = cursor.fetchone()[0] or 0
    
    # 平均日營收
    cursor.execute("SELECT COUNT(DISTINCT date) FROM sales_history WHERE date >= '2026-01-01'")
    day_count = cursor.fetchone()[0] or 1
    avg_revenue = total_revenue // day_count
    
    # 最高單日
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
    print("💻 資料即時從資料庫讀取")
    print("-" * 50)
    app.run(host='0.0.0.0', port=3000, debug=False)