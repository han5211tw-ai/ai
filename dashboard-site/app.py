#!/opt/homebrew/bin/python3
# 禁用 macOS 系統代理檢測，避免背景執行緒崩潰
import os
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

from flask import Flask, jsonify, send_from_directory, request, render_template, abort
from health_check import get_health_status
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from functools import wraps
import sqlite3
import json
import uuid
import time
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 載入環境變數（手動讀取 .env 檔案）
def load_env():
    """手動載入 .env 檔案"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

load_env()

# 匯入觀測系統
from observability import (
    log_event, get_last_event, get_events_summary,
    update_freshness_cache, get_freshness_status, get_ingest_status,
    get_consistency_status, get_api_performance, get_overall_health,
    record_api_metrics, get_debug_sql, is_workday, get_weekday_name
)

app = Flask(__name__,
    template_folder='/Users/aiserver/.openclaw/workspace/dashboard-site',
    static_folder='/Users/aiserver/.openclaw/workspace/dashboard-site'
)
app.config['TEMPLATES_AUTO_RELOAD'] = True
CORS(app)

DB_PATH = '/Users/aiserver/srv/db/company.db'
STATIC_DIR = '/Users/aiserver/.openclaw/workspace/dashboard-site'

# 共用函數：取得資料庫連線
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ============================================
# Admin 驗證裝飾器（統一權限檢查，所有 Admin API 共用）
# ============================================
def require_admin(f):
    """檢查是否為管理員 - 統一驗證入口"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin_user = request.args.get('admin') or request.headers.get('X-Admin-User')

        # DEBUG: 記錄收到的參數（僅記錄，不做轉碼）
        print(f"[DEBUG] require_admin: admin_user={repr(admin_user)}")

        if not admin_user:
            return jsonify({'success': False, 'message': '缺少管理員驗證'}), 401

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name, title FROM staff_passwords WHERE name = ?", (admin_user,))
        user = cursor.fetchone()
        conn.close()

        print(f"[DEBUG] Database result: {dict(user) if user else None}")

        if not user or (user['name'] != '黃柏翰' and user['title'] != '老闆'):
            return jsonify({'success': False, 'message': '無管理員權限'}), 403

        return f(*args, **kwargs)
    return decorated_function

# ============================================
# 老闆權限驗證裝飾器
# ============================================
def require_boss(f):
    """檢查是否為老闆 - 從請求中驗證使用者身份"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        data = request.get_json() or {}
        requester = data.get('requester') or request.headers.get('X-Requester')

        if not requester:
            return jsonify({'success': False, 'message': '缺少使用者驗證'}), 401

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name, title FROM staff_passwords WHERE name = ?", (requester,))
        user = cursor.fetchone()
        conn.close()

        if not user or user['title'] != '老闆':
            return jsonify({'success': False, 'message': '無老闆權限'}), 403

        return f(*args, **kwargs)
    return decorated_function

# 匯入並註冊 Staff Admin Blueprint
from admin_staff import admin_staff_bp
app.register_blueprint(admin_staff_bp)

# 為 Staff Blueprint 的所有路由統一添加 require_admin 裝飾器
for endpoint, func in app.view_functions.items():
    if endpoint.startswith('admin_staff.'):
        app.view_functions[endpoint] = require_admin(func)
STATIC_DIR = '/Users/aiserver/.openclaw/workspace/dashboard-site'

# 客戶資料來源切換開關（master=查 customer_master, legacy=查 customers）
# 預設為 legacy 直到 customer_master 補齊資料
CUSTOMER_SOURCE = os.environ.get('CUSTOMER_SOURCE', 'legacy')
print(f"[CONFIG] CUSTOMER_SOURCE = {CUSTOMER_SOURCE}")

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


# ========== 客戶資料同步機制 ==========

def get_customer_table_name():
    """根據 CUSTOMER_SOURCE 返回要查詢的表名"""
    return 'customer_master' if CUSTOMER_SOURCE == 'master' else 'customers'

def sync_customers_to_master(actor='system'):
    """
    【初始化】將 customers 的資料同步到 customer_master（一次性）
    這是為了將現有資料匯入到新的 master 表
    只做 INSERT（跳過已存在），不做 UPDATE/DELETE
    """
    start_time = time.time()

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 檢查 customers 是否有資料
        cursor.execute("SELECT COUNT(*) as count FROM customers")
        customers_count = cursor.fetchone()['count']

        if customers_count == 0:
            print("[INIT] customers 為空，無法初始化")
            return {'success': False, 'error': 'customers 表為空'}

        # 執行 INSERT：將 customers 資料匯入 customer_master
        cursor.execute("""
            INSERT OR IGNORE INTO customer_master
            (customer_id, short_name, mobile, mobile_raw, phone, address, import_date)
            SELECT
                customer_id,
                short_name,
                REPLACE(REPLACE(mobile, '-', ''), ' ', ''),
                mobile,
                phone1,
                company_address,
                DATE('now')
            FROM customers
            WHERE customer_id IS NOT NULL AND customer_id != ''
        """)

        inserted = cursor.rowcount
        conn.commit()

        duration_ms = int((time.time() - start_time) * 1000)

        # 記錄到 ops_events
        log_event(
            event_type='SYNC_INIT',
            source='sync_customers_to_master',
            actor=actor,
            status='OK',
            duration_ms=duration_ms,
            summary=f'初始化完成：匯入 {inserted} 筆到 customer_master',
            affected_rows=inserted,
            details={
                'source_count': customers_count,
                'inserted': inserted,
                'duration_ms': duration_ms
            }
        )

        conn.close()

        print(f"[INIT] 完成：從 customers 匯入 {inserted} 筆到 customer_master，耗時 {duration_ms}ms")
        return {
            'success': True,
            'synced': inserted,
            'source_count': customers_count,
            'duration_ms': duration_ms
        }

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)

        log_event(
            event_type='SYNC_INIT',
            source='sync_customers_to_master',
            actor=actor,
            status='FAIL',
            duration_ms=duration_ms,
            summary='初始化失敗: ' + error_msg,
            error_code='SYNC_ERROR',
            error_stack=error_msg
        )

        print(f"[INIT] 失敗: {error_msg}")
        return {'success': False, 'error': error_msg}


def sync_customers_from_master(actor='system'):
    """
    【未來同步】將 customer_master 的資料同步到 customers（單向同步）
    只做 UPSERT，不做 DELETE（保險鎖）
    """
    start_time = time.time()

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 檢查 customer_master 是否有資料
        cursor.execute("SELECT COUNT(*) as count FROM customer_master")
        master_count = cursor.fetchone()['count']

        if master_count == 0:
            print("[SYNC] customer_master 為空，跳過同步")
            return {'success': True, 'synced': 0, 'skipped': True}

        # 執行 UPSERT：將 master 資料同步到 customers
        cursor.execute("""
            INSERT INTO customers (customer_id, short_name, mobile, phone1, company_address, contact, updated_at)
            SELECT
                customer_id,
                short_name,
                mobile,
                phone,
                address,
                '',
                datetime('now', 'localtime')
            FROM customer_master
            WHERE customer_id NOT IN (SELECT customer_id FROM customers)
        """)

        inserted = cursor.rowcount

        # 更新已存在的記錄
        cursor.execute("""
            UPDATE customers SET
                short_name = (SELECT short_name FROM customer_master WHERE customer_master.customer_id = customers.customer_id),
                mobile = (SELECT mobile FROM customer_master WHERE customer_master.customer_id = customers.customer_id),
                phone1 = (SELECT phone FROM customer_master WHERE customer_master.customer_id = customers.customer_id),
                company_address = (SELECT address FROM customer_master WHERE customer_master.customer_id = customers.customer_id),
                updated_at = datetime('now', 'localtime')
            WHERE customer_id IN (SELECT customer_id FROM customer_master)
        """)

        updated = cursor.rowcount
        conn.commit()

        duration_ms = int((time.time() - start_time) * 1000)

        # 記錄到 ops_events
        log_event(
            event_type='SYNC',
            source='sync_customers_from_master',
            actor=actor,
            status='OK',
            duration_ms=duration_ms,
            summary=f'同步完成：新增 {inserted} 筆，更新 {updated} 筆',
            affected_rows=inserted + updated,
            details={
                'master_count': master_count,
                'inserted': inserted,
                'updated': updated,
                'duration_ms': duration_ms
            }
        )

        conn.close()

        print(f"[SYNC] 完成：新增 {inserted} 筆，更新 {updated} 筆，耗時 {duration_ms}ms")
        return {
            'success': True,
            'synced': inserted + updated,
            'inserted': inserted,
            'updated': updated,
            'duration_ms': duration_ms
        }

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)

        log_event(
            event_type='SYNC',
            source='sync_customers_from_master',
            actor=actor,
            status='FAIL',
            duration_ms=duration_ms,
            summary='同步失敗: ' + error_msg,
            error_code='SYNC_ERROR',
            error_stack=error_msg
        )

        print(f"[SYNC] 失敗: {error_msg}")
        return {'success': False, 'error': error_msg}


# ========== 慢查詢監控 ==========

def log_slow_query(endpoint, duration_ms, details=None):
    """記錄慢查詢（>200ms）到 admin_audit_log"""
    if duration_ms < 200:  # 只記錄超過 200ms 的查詢
        return

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 確保 admin_audit_log 表存在
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_user TEXT,
                action TEXT,
                action_type TEXT,
                fix_code TEXT,
                affected_ids TEXT,
                affected_count INTEGER,
                created_at DATETIME DEFAULT (datetime('now', 'localtime'))
            )
        """)

        cursor.execute("""
            INSERT INTO admin_audit_log (admin_user, action, action_type, fix_code, affected_ids)
            VALUES (?, ?, 'slow_query', ?, ?)
        """, ('system', endpoint, str(duration_ms), json.dumps(details) if details else None))

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[SlowQuery] 記錄失敗: {e}")


# ========== 防暴力破解：初始化與輔助函式 ==========

def init_login_attempts_table():
    """初始化登入嘗試記錄表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS login_attempts (
                ip_address TEXT PRIMARY KEY,
                failed_count INTEGER DEFAULT 0,
                locked_until DATETIME,
                last_attempt DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_locked_until ON login_attempts(locked_until)
        """)

        conn.commit()
        conn.close()
        print("✅ login_attempts 資料表已初始化")
    except Exception as e:
        print(f"⚠️ 初始化 login_attempts 表失敗: {e}")


def get_client_ip():
    """獲取客戶端真實 IP 位址"""
    # 優先檢查反向代理轉發的 IP
    if request.headers.get('X-Forwarded-For'):
        # X-Forwarded-For 可能包含多個 IP，取第一個
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        # 直接連線的 IP
        return request.remote_addr


def check_ip_locked(ip):
    """
    檢查該 IP 是否被鎖定

    Returns:
        tuple: (is_locked: bool, message: str)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT failed_count, locked_until
        FROM login_attempts
        WHERE ip_address = ?
    """, (ip,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return False, None

    # 檢查是否仍在鎖定期間
    if row['locked_until']:
        locked_until = datetime.fromisoformat(row['locked_until'])
        now = datetime.now()

        if now < locked_until:
            # 計算剩餘鎖定時間
            remaining = locked_until - now
            minutes = int(remaining.total_seconds() / 60)
            seconds = int(remaining.total_seconds() % 60)

            return True, f"⚠️ 登入失敗次數過多，此 IP 已被安全鎖定，請於 {minutes} 分 {seconds} 秒後再試。"
        else:
            # 鎖定已過期，自動解鎖（歸零）
            reset_login_attempts(ip)
            return False, None

    return False, None


def record_failed_login(ip):
    """
    記錄登入失敗，更新失敗次數

    Args:
        ip: 客戶端 IP 位址

    Returns:
        bool: 是否觸發鎖定
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    now = datetime.now().isoformat()

    # 查詢現有記錄
    cursor.execute("""
        SELECT failed_count FROM login_attempts WHERE ip_address = ?
    """, (ip,))
    row = cursor.fetchone()

    if row:
        # 更新現有記錄
        new_count = row['failed_count'] + 1

        if new_count >= 5:
            # 達到鎖定門檻，設定鎖定時間為 15 分鐘後
            locked_until = (datetime.now() + timedelta(minutes=15)).isoformat()
            cursor.execute("""
                UPDATE login_attempts
                SET failed_count = ?, locked_until = ?, last_attempt = ?
                WHERE ip_address = ?
            """, (new_count, locked_until, now, ip))
            conn.commit()
            conn.close()
            return True  # 已鎖定
        else:
            # 僅更新失敗次數
            cursor.execute("""
                UPDATE login_attempts
                SET failed_count = ?, last_attempt = ?
                WHERE ip_address = ?
            """, (new_count, now, ip))
    else:
        # 新增記錄
        cursor.execute("""
            INSERT INTO login_attempts (ip_address, failed_count, locked_until, last_attempt)
            VALUES (?, 1, NULL, ?)
        """, (ip, now))

    conn.commit()
    conn.close()
    return False  # 未鎖定


def reset_login_attempts(ip):
    """登入成功時重置該 IP 的嘗試記錄"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM login_attempts WHERE ip_address = ?
    """, (ip,))

    conn.commit()
    conn.close()


# 應用啟動時初始化資料表
init_login_attempts_table()


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

# 添加系統健康監控任務（每5分鐘檢查一次）
def health_monitor():
    """系統健康監控 - 檢查關鍵功能"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 檢查最近10分鐘的通知失敗
        cursor.execute("""
            SELECT COUNT(*) as failed_count
            FROM notification_logs
            WHERE status = 'failed'
            AND created_at >= datetime('now', '-10 minutes')
        """)
        failed_count = cursor.fetchone()['failed_count']

        # 檢查資料庫連線（簡單查詢）
        cursor.execute("SELECT 1")
        cursor.fetchone()

        conn.close()

        # 如果有通知失敗，發送告警
        if failed_count > 0:
            alert_msg = f"""⚠️ <b>系統告警</b>

最近 10 分鐘有 {failed_count} 筆通知發送失敗
請檢查 Telegram Bot 狀態

時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
            send_telegram_notification(alert_msg, TELEGRAM_CHAT_ID, notification_type='系統告警')
            # 同時發送 Email 告警
            send_email_alert(
                "Telegram 通知異常",
                f"<p>最近 10 分鐘有 <strong>{failed_count}</strong> 筆 Telegram 通知發送失敗</p>"
                f"<p>請檢查 Telegram Bot 狀態或網路連線</p>"
            )
            print(f"[HEALTH MONITOR] 檢測到 {failed_count} 筆通知失敗，已發送告警")
        else:
            print(f"[HEALTH MONITOR] 系統健康檢查通過 - {datetime.now().strftime('%H:%M:%S')}")

    except Exception as e:
        print(f"[HEALTH MONITOR] 健康檢查失敗: {e}")
        # 資料庫連線失敗也發送告警
        try:
            alert_msg = f"""🚨 <b>系統嚴重告警</b>

資料庫連線異常！
錯誤：{str(e)[:100]}

時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
            send_telegram_notification(alert_msg, TELEGRAM_CHAT_ID, notification_type='系統嚴重告警')
        except:
            pass
        # 同時發送 Email 告警
        send_email_alert(
            "資料庫連線異常",
            f"<p>系統健康檢查時發現資料庫連線異常</p>"
            f"<p>錯誤訊息：<code>{str(e)[:200]}</code></p>"
        )

scheduler.add_job(health_monitor, 'interval', minutes=5)
scheduler.start()

# 啟動時立即執行一次分析
generate_analysis()

@app.route('/')
def index():
    return render_template('index.html')

# 模板頁面路由（支援 .html 和無副檔名）
@app.route('/<path:page>.html')
def render_page_html(page):
    """渲染模板頁面（.html 版本）"""
    try:
        return render_template(f'{page}.html')
    except:
        return send_from_directory(STATIC_DIR, f'{page}.html')

@app.route('/<path:page>')
def render_page(page):
    """渲染模板頁面（無副檔名版本）"""
    # 排除 API 路徑和靜態檔案
    if page.startswith('api/') or page.startswith('static/'):
        abort(404)
    try:
        return render_template(f'{page}.html')
    except:
        return send_from_directory(STATIC_DIR, f'{page}.html')



# API: 健康檢查
@app.route('/api/health')
def health_check():
    """系統健康檢查端點"""
    try:
        # 檢查資料庫連線
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        conn.close()

        return jsonify({
            'status': 'healthy',
            'database': 'healthy',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'error',
            'error': str(e),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }), 500

# API: 分析結果
@app.route('/api/analysis/<type>')
def get_analysis(type):
    if type in analysis_results:
        return jsonify({
            'content': analysis_results[type],
            'last_update': analysis_results['last_update']
        })
    return jsonify({'error': 'Invalid type'}), 400

# API: 通知系統狀態
@app.route('/api/notification-status')
def get_notification_status():
    """檢查通知系統狀態"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 檢查最近 1 小時的通知記錄
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM notification_logs
            WHERE created_at >= datetime('now', '-1 hour')
            GROUP BY status
        """)
        rows = cursor.fetchall()
        conn.close()

        success_count = 0
        failed_count = 0
        for row in rows:
            if row['status'] == 'success':
                success_count = row['count']
            elif row['status'] == 'failed':
                failed_count = row['count']

        # 判斷狀態
        if failed_count == 0 and success_count > 0:
            telegram_status = 'healthy'
        elif failed_count > 0 and success_count > 0:
            telegram_status = 'warning'
        elif failed_count > 0:
            telegram_status = 'error'
        else:
            telegram_status = 'healthy'  # 沒有記錄也視為正常

        return jsonify({
            'telegram': telegram_status,
            'recent_success': success_count,
            'recent_failed': failed_count,
            'checked_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({
            'telegram': 'error',
            'error': str(e),
            'checked_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

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
    from datetime import datetime
    conn = get_db_connection()
    cursor = conn.cursor()

    # 取得查詢參數（支援 year, month, period_type）
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    period_type = request.args.get('period_type', 'quarterly')

    # 如果沒有指定年月，預設為本季
    if year is None:
        year = datetime.now().year
    if month is None:
        month = datetime.now().month

    # 計算日期範圍
    if period_type == 'monthly':
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-31"
    elif period_type == 'quarterly':
        quarter = (month - 1) // 3 + 1
        start_month = (quarter - 1) * 3 + 1
        end_month = quarter * 3
        start_date = f"{year}-{start_month:02d}-01"
        end_date = f"{year}-{end_month:02d}-31"
    else:  # yearly
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"

    # 從 sales_history 即時計算部門業績
    # 門市部：林榮祺、林峙文、劉育仕、林煜捷、張永承、張家碩
    # 業務部：鄭宇晉、梁仁佑
    cursor.execute("""
        SELECT
            CASE WHEN salesperson IN ('林榮祺', '林峙文', '劉育仕', '林煜捷', '張永承', '張家碩')
                 THEN '門市部'
                 WHEN salesperson IN ('鄭宇晉', '梁仁佑')
                 THEN '業務部'
            END as dept_name,
            SUM(amount) as revenue,
            SUM(profit) as profit,
            COUNT(*) as order_count
        FROM sales_history
        WHERE date >= ? AND date <= ?
          AND salesperson IN ('林榮祺', '林峙文', '劉育仕', '林煜捷', '張永承', '張家碩',
                              '鄭宇晉', '梁仁佑')
        GROUP BY dept_name
    """, (start_date, end_date))

    sales_rows = cursor.fetchall()

    # 從 performance_metrics 讀取目標
    if period_type == 'monthly':
        cursor.execute("""
            SELECT subject_name, target_amount
            FROM performance_metrics
            WHERE category = '部門'
              AND year = ?
              AND month = ?
              AND period_type = 'monthly'
        """, (year, month))
    elif period_type == 'quarterly':
        quarter = (month - 1) // 3 + 1
        start_month = (quarter - 1) * 3 + 1
        end_month = quarter * 3
        cursor.execute("""
            SELECT subject_name, SUM(target_amount) as target_amount
            FROM performance_metrics
            WHERE category = '部門'
              AND year = ?
              AND month >= ? AND month <= ?
              AND period_type = 'monthly'
            GROUP BY subject_name
        """, (year, start_month, end_month))
    else:  # yearly
        cursor.execute("""
            SELECT subject_name, SUM(target_amount) as target_amount
            FROM performance_metrics
            WHERE category = '部門'
              AND year = ?
              AND period_type = 'monthly'
            GROUP BY subject_name
        """, (year,))

    target_rows = cursor.fetchall()
    target_map = {row['subject_name']: row['target_amount'] for row in target_rows}

    conn.close()

    # 構建結果
    result = []
    for row in sales_rows:
        dept_name = row['dept_name']
        if not dept_name:
            continue

        revenue = row['revenue'] or 0
        profit = row['profit'] or 0
        target = target_map.get(dept_name, 0)

        result.append({
            'name': dept_name,
            'target': target,
            'revenue': revenue,
            'profit': profit,
            'order_count': row['order_count'],
            'achievement_rate': revenue / target if target > 0 else 0,
            'margin_rate': profit / revenue if revenue > 0 else 0,
            'year': year,
            'month': month,
            'period_type': period_type
        })

    return jsonify(result)

# API: 門市業績
@app.route('/api/performance/store')
def get_store_performance():
    from datetime import datetime
    conn = get_db_connection()
    cursor = conn.cursor()

    # 取得查詢參數（支援 year, month, period_type）
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    period_type = request.args.get('period_type', 'quarterly')

    # 如果沒有指定年月，預設為本季
    if year is None:
        year = datetime.now().year
    if month is None:
        month = datetime.now().month

    # 計算日期範圍
    if period_type == 'monthly':
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-31"
    elif period_type == 'quarterly':
        quarter = (month - 1) // 3 + 1
        start_month = (quarter - 1) * 3 + 1
        end_month = quarter * 3
        start_date = f"{year}-{start_month:02d}-01"
        end_date = f"{year}-{end_month:02d}-31"
    else:  # yearly
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"

    # 門市人員編制
    store_staff = {
        '豐原': ['林榮祺', '林峙文'],
        '潭子': ['劉育仕', '林煜捷'],
        '大雅': ['張永承', '張家碩']
    }

    # 從 sales_history 即時計算門市業績
    cursor.execute("""
        SELECT
            salesperson,
            SUM(amount) as revenue,
            SUM(profit) as profit,
            COUNT(*) as order_count
        FROM sales_history
        WHERE date >= ? AND date <= ?
          AND salesperson IN ('林榮祺', '林峙文', '劉育仕', '林煜捷', '張永承', '張家碩')
        GROUP BY salesperson
    """, (start_date, end_date))

    sales_rows = cursor.fetchall()

    # 按門市彙總
    store_stats = {}
    for row in sales_rows:
        name = row['salesperson']
        for store_name, staff_list in store_staff.items():
            if name in staff_list:
                if store_name not in store_stats:
                    store_stats[store_name] = {'revenue': 0, 'profit': 0, 'orders': 0, 'staff': []}
                store_stats[store_name]['revenue'] += row['revenue'] or 0
                store_stats[store_name]['profit'] += row['profit'] or 0
                store_stats[store_name]['orders'] += row['order_count']
                store_stats[store_name]['staff'].append(name)
                break

    # 從 performance_metrics 讀取目標
    if period_type == 'monthly':
        cursor.execute("""
            SELECT subject_name, target_amount
            FROM performance_metrics
            WHERE category = '門市'
              AND year = ?
              AND month = ?
              AND period_type = 'monthly'
        """, (year, month))
    elif period_type == 'quarterly':
        quarter = (month - 1) // 3 + 1
        start_month = (quarter - 1) * 3 + 1
        end_month = quarter * 3
        cursor.execute("""
            SELECT subject_name, SUM(target_amount) as target_amount
            FROM performance_metrics
            WHERE category = '門市'
              AND year = ?
              AND month >= ? AND month <= ?
              AND period_type = 'monthly'
            GROUP BY subject_name
        """, (year, start_month, end_month))
    else:  # yearly
        cursor.execute("""
            SELECT subject_name, SUM(target_amount) as target_amount
            FROM performance_metrics
            WHERE category = '門市'
              AND year = ?
              AND period_type = 'monthly'
            GROUP BY subject_name
        """, (year,))

    target_rows = cursor.fetchall()
    target_map = {row['subject_name'].replace('門市', ''): row['target_amount'] for row in target_rows}

    conn.close()

    # 構建結果
    result = []
    for store_name, stats in store_stats.items():
        revenue = stats['revenue']
        profit = stats['profit']
        target = target_map.get(store_name, 0)

        result.append({
            'store_name': store_name,
            'target': target,
            'revenue': revenue,
            'profit': profit,
            'order_count': stats['orders'],
            'achievement_rate': revenue / target if target > 0 else 0,
            'margin_rate': profit / revenue if revenue > 0 else 0,
            'salespeople': stats['staff']
        })

    return jsonify({'success': True, 'data': result, 'year': year, 'month': month, 'period_type': period_type})
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

# API: 門市督導評分（最近30天）
@app.route('/api/store/supervision')
def get_store_supervision():
    from datetime import datetime
    conn = get_db_connection()
    cursor = conn.cursor()

    # 獲取當月日期範圍
    today = datetime.now()
    date_start = f"{today.year}-{today.month:02d}-01"

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
        WHERE date >= ?
        GROUP BY store_name
    """, (date_start,))

    rows = cursor.fetchall()

    # 獲取每個門市本月的督導次數
    cursor.execute("""
        SELECT
            store_name,
            COUNT(DISTINCT date) as inspection_count
        FROM supervision_scores
        WHERE date >= ?
        GROUP BY store_name
    """, (date_start,))
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
    date_start = f"{today.year}-{today.month:02d}-01"

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
        WHERE date >= ?
        GROUP BY store_name
    """, (date_start,))

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

    # 取得查詢參數（支援 year, month, period_type）
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    period_type = request.args.get('period_type', 'quarterly')

    # 如果沒有指定年月，預設為本季
    if year is None:
        year = datetime.now().year
    if month is None:
        month = datetime.now().month

    # 計算日期範圍
    if period_type == 'monthly':
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-31"
    elif period_type == 'quarterly':
        quarter = (month - 1) // 3 + 1
        start_month = (quarter - 1) * 3 + 1
        end_month = quarter * 3
        start_date = f"{year}-{start_month:02d}-01"
        end_date = f"{year}-{end_month:02d}-31"
    else:  # yearly
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"

    # 過濾掉不需要顯示的人員（主管不列入個人排名）
    excluded_names = ['莊圍迪', '萬書佑', 'Unknown']

    # 從 sales_history 即時計算個人業績
    cursor.execute("""
        SELECT
            salesperson,
            SUM(amount) as revenue,
            SUM(profit) as profit,
            COUNT(*) as order_count
        FROM sales_history
        WHERE date >= ? AND date <= ?
          AND salesperson NOT IN ('莊圍迪', '萬書佑', 'Unknown', '黃柏翰', '')
          AND product_code IS NOT NULL
          AND product_code != ''
          AND product_code LIKE '%-%'
        GROUP BY salesperson
        ORDER BY revenue DESC
    """, (start_date, end_date))

    sales_rows = cursor.fetchall()

    # 從 performance_metrics 讀取目標
    if period_type == 'monthly':
        cursor.execute("""
            SELECT subject_name, target_amount
            FROM performance_metrics
            WHERE category = '個人'
              AND year = ?
              AND month = ?
              AND period_type = 'monthly'
        """, (year, month))
    elif period_type == 'quarterly':
        quarter = (month - 1) // 3 + 1
        start_month = (quarter - 1) * 3 + 1
        end_month = quarter * 3
        cursor.execute("""
            SELECT subject_name, SUM(target_amount) as target_amount
            FROM performance_metrics
            WHERE category = '個人'
              AND year = ?
              AND month >= ? AND month <= ?
              AND period_type = 'monthly'
            GROUP BY subject_name
        """, (year, start_month, end_month))
    else:  # yearly
        cursor.execute("""
            SELECT subject_name, SUM(target_amount) as target_amount
            FROM performance_metrics
            WHERE category = '個人'
              AND year = ?
              AND period_type = 'monthly'
            GROUP BY subject_name
        """, (year,))

    target_rows = cursor.fetchall()
    target_map = {row['subject_name']: row['target_amount'] for row in target_rows}

    conn.close()

    result = []
    rank = 1
    for row in sales_rows:
        name = row['salesperson']
        if name in excluded_names:
            continue

        revenue = row['revenue'] or 0
        profit = row['profit'] or 0
        orders = row['order_count'] or 0
        target = target_map.get(name, 0)
        avg = revenue // orders if orders > 0 else 0

        result.append({
            'rank': rank,
            'name': name,
            'total': revenue,
            'orders': orders,
            'avg': avg,
            'target': target,
            'achievement_rate': revenue / target if target > 0 else 0,
            'margin_rate': profit / revenue if revenue > 0 else 0,
            'year': year,
            'month': month,
            'period_type': period_type
        })
        rank += 1

    return jsonify(result)

# API: 業務員績效（業務部：鄭宇晉、梁仁佑）
@app.route('/api/performance/business')
def get_business_performance():
    from datetime import datetime
    conn = get_db_connection()
    cursor = conn.cursor()

    # 取得查詢參數（支援 year, month, period_type）
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    period_type = request.args.get('period_type', 'quarterly')

    # 如果沒有指定年月，預設為本季
    if year is None:
        year = datetime.now().year
    if month is None:
        month = datetime.now().month

    # 計算日期範圍
    if period_type == 'monthly':
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-31"
    elif period_type == 'quarterly':
        quarter = (month - 1) // 3 + 1
        start_month = (quarter - 1) * 3 + 1
        end_month = quarter * 3
        start_date = f"{year}-{start_month:02d}-01"
        end_date = f"{year}-{end_month:02d}-31"
    else:  # yearly
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"

    # 業務部人員列表
    business_staff = ['鄭宇晉', '梁仁佑']

    # 獲取業務員即時績效（從 sales_history 計算）
    placeholders = ','.join(['?' for _ in business_staff])
    cursor.execute(f"""
        SELECT
            salesperson,
            SUM(amount) as total_sales,
            SUM(profit) as total_profit
        FROM sales_history
        WHERE date >= ? AND date <= ?
          AND salesperson IN ({placeholders})
        GROUP BY salesperson
    """, [start_date, end_date] + business_staff)

    sales_rows = cursor.fetchall()

    # 獲取業務員目標（根據 period_type）
    if period_type == 'monthly':
        cursor.execute("""
            SELECT subject_name, target_amount
            FROM performance_metrics
            WHERE category = '個人' AND subject_name IN ('鄭宇晉', '梁仁佑')
              AND year = ? AND month = ? AND period_type = 'monthly'
        """, (year, month))
    elif period_type == 'quarterly':
        quarter = (month - 1) // 3 + 1
        start_month = (quarter - 1) * 3 + 1
        end_month = quarter * 3
        cursor.execute("""
            SELECT subject_name, SUM(target_amount) as target_amount
            FROM performance_metrics
            WHERE category = '個人' AND subject_name IN ('鄭宇晉', '梁仁佑')
              AND year = ? AND month >= ? AND month <= ? AND period_type = 'monthly'
            GROUP BY subject_name
        """, (year, start_month, end_month))
    else:  # yearly
        cursor.execute("""
            SELECT subject_name, SUM(target_amount) as target_amount
            FROM performance_metrics
            WHERE category = '個人' AND subject_name IN ('鄭宇晉', '梁仁佑')
              AND year = ? AND period_type = 'monthly'
            GROUP BY subject_name
        """, (year,))

    target_rows = cursor.fetchall()
    target_map = {row['subject_name']: row['target_amount'] for row in target_rows}

    conn.close()

    result = []
    for row in sales_rows:
        name = row['salesperson']
        sales = row['total_sales'] or 0
        profit = row['total_profit'] or 0
        target = target_map.get(name, 0)
        margin = profit / sales if sales > 0 else 0
        achievement = sales / target if target > 0 else 0

        result.append({
            'name': name,
            'target': target,
            'revenue': sales,
            'achievement_rate': achievement,
            'margin_rate': margin,
            'year': year,
            'month': month,
            'period_type': period_type
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

    try:
        # 獲取查詢參數：type=all/請購/調撥，預設顯示全部
        filter_type = request.args.get('type', 'all')

        # 獲取所有尚未處理的需求，依照日期排序（最新的在前）
        # 處理多種未處理標記：'False', '0.0', '', NULL
        if filter_type == '調撥':
            # 顯示調撥（包含待處理、已調撥，排除已取消和已完成）
            cursor.execute("""
                SELECT id, date, item_name, quantity, customer_code, department,
                       requester, vendor_delivery, vendor_name, main_wh_stock,
                       processed, status, product_code, remark, purpose, request_type, transfer_from
                FROM needs
                WHERE request_type = '調撥'
                  AND (status IS NULL OR status = '' OR status IN ('待處理', '已調撥'))
                  AND cancelled_at IS NULL
                  AND completed_at IS NULL
                ORDER BY date DESC, id DESC
                LIMIT 50
            """)
        elif filter_type == '請購':
            # 顯示請購（包含待處理、已採購，排除已取消和已完成）
            cursor.execute("""
                SELECT id, date, item_name, quantity, customer_code, department,
                       requester, vendor_delivery, vendor_name, main_wh_stock,
                       processed, status, product_code, remark, purpose, request_type, transfer_from
                FROM needs
                WHERE (request_type = '請購' OR request_type IS NULL OR request_type = '')
                  AND (status IS NULL OR status = '' OR status IN ('待處理', '已採購'))
                  AND cancelled_at IS NULL
                  AND completed_at IS NULL
                ORDER BY date DESC, id DESC
                LIMIT 50
            """)
        else:
            # 預設：顯示全部（請購 + 調撥，包含待處理、已採購、已調撥，排除已取消和已完成）
            cursor.execute("""
                SELECT id, date, item_name, quantity, customer_code, department,
                       requester, vendor_delivery, vendor_name, main_wh_stock,
                       processed, status, product_code, remark, purpose, request_type, transfer_from
                FROM needs
                WHERE (status IS NULL OR status = '' OR status IN ('待處理', '已採購', '已調撥'))
                  AND cancelled_at IS NULL
                  AND completed_at IS NULL
                ORDER BY date DESC, id DESC
                LIMIT 50
            """)

        rows = cursor.fetchall()

        if not rows:
            return jsonify({'date': None, 'items': []})

        # 獲取最新日期用於顯示
        latest_date = rows[0]['date'] if rows else None

        result_items = []
        for row in rows:
            product_code = row['product_code'] if row['product_code'] else ''

            # 產品名稱優先順序：1. needs.item_name 2. inventory.item_spec
            display_name = row['item_name'] if row['item_name'] else ''

            # 如果 needs 沒有產品名稱，或名稱看起來像編號，從庫存表查詢
            if product_code:
                cursor.execute("""
                    SELECT item_spec FROM inventory
                    WHERE product_id = ?
                    ORDER BY report_date DESC LIMIT 1
                """, (product_code,))
                inv_row = cursor.fetchone()
                if inv_row and inv_row['item_spec']:
                    # 如果 needs.item_name 是空的，或看起來像是編號（沒有中文字），就用庫存表的
                    has_chinese = display_name and any('\u4e00' <= char <= '\u9fff' for char in display_name)
                    if not display_name or not has_chinese:
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

            # 查詢客戶姓名
            customer_name = ''
            if row['customer_code'] and row['customer_code'] not in ('nan', 'None', 'NaN'):
                cursor.execute("""
                    SELECT short_name FROM customers
                    WHERE customer_id = ?
                    LIMIT 1
                """, (row['customer_code'],))
                cust_row = cursor.fetchone()
                if cust_row:
                    customer_name = cust_row['short_name']

            result_items.append({
                'id': row['id'],
                'date': row['date'],
                'item_name': row['item_name'],
                'display_name': display_name,
                'quantity': row['quantity'],
                'customer_code': row['customer_code'] if row['customer_code'] and row['customer_code'] not in ('nan', 'None', 'NaN') else '',
                'customer_name': customer_name,
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

        return jsonify({
            'date': latest_date,
            'items': result_items
        })
    except Exception as e:
        print(f"get_latest_needs 錯誤: {e}")
        return jsonify({'date': None, 'items': [], 'error': str(e)}), 500
    finally:
        conn.close()

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
    from datetime import datetime
    conn = get_db_connection()
    cursor = conn.cursor()

    # 取得查詢參數
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)

    # 計算當月日期範圍
    start_date = f"{year}-{month:02d}-01"
    end_date = f"{year}-{month:02d}-31"

    # 獲取各業務員服務筆數
    cursor.execute("""
        SELECT salesperson, COUNT(*) as total_count,
               SUM(CASE WHEN is_contract = 1 THEN 1 ELSE 0 END) as contract_count
        FROM service_records
        WHERE date >= ? AND date <= ?
        GROUP BY salesperson
    """, (start_date, end_date))

    salesperson_rows = cursor.fetchall()

    # 獲取服務分類統計
    cursor.execute("""
        SELECT service_type, COUNT(*) as count
        FROM service_records
        WHERE date >= ? AND date <= ?
        GROUP BY service_type
        ORDER BY count DESC
    """, (start_date, end_date))

    service_type_rows = cursor.fetchall()

    conn.close()

    # 構建回傳格式
    salesperson_summary = []
    for row in salesperson_rows:
        salesperson_summary.append({
            'salesperson': row['salesperson'],
            'total_count': row['total_count'],
            'contract_count': row['contract_count']
        })

    service_types = []
    for row in service_type_rows:
        service_types.append({
            'type': row['service_type'],
            'count': row['count']
        })

    return jsonify({
        'success': True,
        'year': year,
        'month': month,
        'salesperson_summary': salesperson_summary,
        'service_types': service_types
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

# API: 管理員健康檢查 - 使用 observability 作為唯一監控來源
@app.route('/api/v1/admin/health')
def admin_health_check():
    """統一健康檢查 API - Single Source of Truth"""
    from observability import get_overall_health
    result = get_overall_health()
    return jsonify(result)

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

# API: 密碼驗證（含防暴力破解機制）
@app.route('/api/auth/verify', methods=['POST'])
def verify_password():
    data = request.get_json()
    password = data.get('password', '')

    # 獲取客戶端 IP
    client_ip = get_client_ip()

    # 步驟 1：檢查 IP 是否被鎖定
    is_locked, lock_message = check_ip_locked(client_ip)
    if is_locked:
        return jsonify({'success': False, 'message': lock_message}), 403

    # 驗證密碼格式
    if not password or len(password) != 4:
        # 格式錯誤也算失敗
        record_failed_login(client_ip)
        return jsonify({'success': False, 'message': '密碼格式錯誤'})

    # 查詢資料庫驗證密碼（統一使用 staff 資料表）
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT name, department, title, is_active, store
        FROM staff
        WHERE password = ? AND is_active = 1
    ''', (password,))
    row = cursor.fetchone()
    conn.close()

    if row:
        # 步驟 2：登入成功，重置失敗記錄
        reset_login_attempts(client_ip)

        # 使用 store 作為顯示單位（如「大雅門市」），如果沒有或為'-'則使用 department
        display_unit = row['store'] if row['store'] and row['store'] != '-' else row['department']
        
        return jsonify({
            'success': True,
            'name': row['name'],
            'department': display_unit,
            'title': row['title']
        })
    else:
        # 步驟 3：密碼錯誤，記錄失敗
        is_now_locked = record_failed_login(client_ip)

        if is_now_locked:
            return jsonify({
                'success': False,
                'message': '⚠️ 登入失敗次數過多，此 IP 已被安全鎖定，請於 15 分鐘後再試。'
            }), 403
        else:
            return jsonify({'success': False, 'message': '密碼錯誤'})

# API: 老闆密碼驗證
@app.route('/api/boss/verify', methods=['POST'])
def verify_boss_password():
    data = request.get_json()
    password = data.get('password', '')

    if not password:
        return jsonify({'success': False, 'message': '請輸入密碼'})

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT password FROM boss_password WHERE id = 1')
    row = cursor.fetchone()
    conn.close()

    if row and row['password'] == password:
        return jsonify({'success': True, 'role': 'boss'})
    else:
        return jsonify({'success': False, 'message': '密碼錯誤'})

# API: 會計驗證（使用 staff_passwords）
@app.route('/api/accountant/verify', methods=['POST'])
def verify_accountant():
    data = request.get_json()
    name = data.get('name', '')
    password = data.get('password', '')

    if not name or not password:
        return jsonify({'success': False, 'message': '請輸入帳號密碼'})

    conn = get_db_connection()
    cursor = conn.cursor()

    # 驗證帳號密碼
    cursor.execute('''
        SELECT sp.name, sp.department, sp.title, s.is_active
        FROM staff_passwords sp
        JOIN staff s ON sp.name = s.name
        WHERE sp.name = ? AND sp.password = ?
    ''', (name, password))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({'success': False, 'message': '帳號或密碼錯誤'})

    if not row['is_active']:
        return jsonify({'success': False, 'message': '帳號已停用'})

    # 檢查是否為會計職位
    if '會計' not in row['title']:
        return jsonify({'success': False, 'message': '無會計權限'})

    return jsonify({
        'success': True,
        'role': 'accountant',
        'name': row['name'],
        'department': row['department'],
        'title': row['title']
    })

# API: 修改老闆密碼
@app.route('/api/boss/password', methods=['PUT'])
def update_boss_password():
    data = request.get_json()
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')

    if not old_password or not new_password:
        return jsonify({'success': False, 'message': '請輸入完整資訊'})

    if len(new_password) < 4:
        return jsonify({'success': False, 'message': '新密碼長度至少 4 碼'})

    conn = get_db_connection()
    cursor = conn.cursor()

    # 驗證舊密碼
    cursor.execute('SELECT password FROM boss_password WHERE id = 1')
    row = cursor.fetchone()

    if not row or row['password'] != old_password:
        conn.close()
        return jsonify({'success': False, 'message': '舊密碼錯誤'})

    # 更新密碼
    cursor.execute(
        'UPDATE boss_password SET password = ?, updated_at = datetime("now", "localtime") WHERE id = 1',
        (new_password,)
    )
    conn.commit()
    conn.close()

    return jsonify({'success': True})

# API: 產品資訊查詢
# API: 產品模糊搜尋
@app.route('/api/products/search')
def search_products():
    keyword = request.args.get('keyword', '').strip()

    if not keyword or len(keyword) < 2:
        return jsonify({'success': True, 'items': []})

    conn = get_db_connection()
    cursor = conn.cursor()

    # 從 products 表搜尋（最多 50 筆）
    cursor.execute("""
        SELECT product_code, product_name
        FROM products
        WHERE product_code LIKE ? OR product_name LIKE ?
        ORDER BY
            CASE WHEN product_code = ? THEN 0 ELSE 1 END,
            product_name
        LIMIT 50
    """, (f'%{keyword}%', f'%{keyword}%', keyword.upper()))

    rows = cursor.fetchall()
    conn.close()

    items = []
    for row in rows:
        items.append({
            'product_code': row['product_code'],
            'item_name': row['product_name']
        })

    return jsonify({'success': True, 'items': items})


@app.route('/api/product/info')
def get_product_info():
    code = request.args.get('code', '').strip()
    if not code:
        return jsonify({'found': False})

    conn = get_db_connection()
    cursor = conn.cursor()

    # 查詢產品名稱（從 products 表）
    cursor.execute("""
        SELECT product_name FROM products
        WHERE product_code = ?
    """, (code,))
    name_row = cursor.fetchone()

    if not name_row:
        return jsonify({'found': False, 'message': '產品不存在'})

    product_name = name_row['product_name']

    # 查詢該產品的最新報表日期
    cursor.execute("""
        SELECT MAX(report_date) FROM inventory WHERE product_id = ?
    """, (code,))
    latest_date_row = cursor.fetchone()
    latest_date = latest_date_row[0] if latest_date_row else None

    total_stock = 0
    stock_list = []

    if latest_date:
        # 查總庫存（所有倉庫加總，含0）
        cursor.execute("""
            SELECT SUM(stock_quantity) as total
            FROM inventory
            WHERE product_id = ? AND report_date = ?
        """, (code, latest_date))
        total_row = cursor.fetchone()
        total_stock = total_row['total'] if total_row and total_row['total'] else 0

        # 查有庫存的倉庫（只顯示 qty > 0）
        cursor.execute("""
            SELECT warehouse, stock_quantity as qty
            FROM inventory
            WHERE product_id = ? AND report_date = ? AND stock_quantity > 0
            ORDER BY warehouse
        """, (code, latest_date))
        stock_rows = cursor.fetchall()
        stock_list = [{'warehouse': r['warehouse'], 'qty': r['qty']} for r in stock_rows]

    # 查最新進貨資訊
    cursor.execute("""
        SELECT supplier_name, price, date
        FROM purchase_history
        WHERE product_code = ?
        ORDER BY date DESC, rowid DESC
        LIMIT 1
    """, (code,))
    purchase_row = cursor.fetchone()

    conn.close()

    result = {
        'found': True,
        'product_code': code,
        'product_name': product_name,
        'total_stock': total_stock,
        'stock': stock_list
    }

    # 庫存為空時添加提示
    if len(stock_list) == 0 and total_stock == 0:
        result['stock_note'] = '庫存報表未列出（可能為 0）'

    if purchase_row:
        result['last_supplier'] = purchase_row['supplier_name']
        result['last_purchase_price'] = purchase_row['price']
        result['last_purchase_date'] = purchase_row['date']

    return jsonify(result)

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


# API: 客戶模糊搜尋
@app.route('/api/customers/search')
def search_customers():
    """
    搜尋客戶 - 加強版
    支援：名稱模糊匹配、手機、電話、統編、客戶編號
    """
    keyword = request.args.get('keyword', '').strip()

    # 檢查 keyword 長度
    if len(keyword) < 2:
        return jsonify({'success': True, 'items': []})

    # 如果是純數字，至少 3 碼才查詢
    if keyword.isdigit() and len(keyword) < 3:
        return jsonify({'success': True, 'items': []})

    # 決定查詢哪張表
    source_table = get_customer_table_name()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 建立搜尋模式：支援部分匹配
        exact_pattern = f'%{keyword}%'
        # 移除空白後的模糊匹配（如「黃柏翰」匹配「黃柏翰有限公司」）
        fuzzy_pattern = f'%{keyword.replace(" ", "").replace(" ", "")}%'

        if source_table == 'customer_master':
            # 查詢 customer_master（加強版）
            cursor.execute("""
                SELECT
                    customer_id,
                    short_name,
                    mobile,
                    phone,
                    '' as contact,
                    address as company_address,
                    tax_id
                FROM customer_master
                WHERE short_name LIKE ?
                   OR short_name LIKE ?
                   OR mobile LIKE ?
                   OR phone LIKE ?
                   OR customer_id LIKE ?
                   OR tax_id LIKE ?
                ORDER BY
                    CASE WHEN short_name = ? THEN 0
                         WHEN short_name LIKE ? THEN 1
                         ELSE 2
                    END,
                    short_name
                LIMIT 20
            """, (exact_pattern, fuzzy_pattern, exact_pattern, exact_pattern,
                  exact_pattern, exact_pattern, keyword, exact_pattern))
        else:
            # 查詢 customers（舊版加強）
            cursor.execute("""
                SELECT customer_id, short_name, mobile, phone1, contact,
                       company_address, tax_id
                FROM customers
                WHERE short_name LIKE ?
                   OR short_name LIKE ?
                   OR mobile LIKE ?
                   OR phone1 LIKE ?
                   OR customer_id LIKE ?
                   OR tax_id LIKE ?
                ORDER BY
                    CASE WHEN short_name = ? THEN 0
                         WHEN short_name LIKE ? THEN 1
                         ELSE 2
                    END,
                    short_name
                LIMIT 20
            """, (exact_pattern, fuzzy_pattern, exact_pattern, exact_pattern,
                  exact_pattern, exact_pattern, keyword, exact_pattern))

        rows = cursor.fetchall()

        items = []
        for row in rows:
            items.append({
                'customer_id': row['customer_id'],
                'short_name': row['short_name'],
                'mobile': row['mobile'] or '',
                'phone': row['phone1'] if 'phone1' in row.keys() else (row['phone'] or ''),
                'contact': row['contact'] or '',
                'address': row['company_address'] or '',
                'tax_id': row['tax_id'] or ''
            })

        return jsonify({
            'success': True,
            'items': items,
            'source': CUSTOMER_SOURCE,
            'table': source_table
        })

    except Exception as e:
        print(f"[ERROR] search_customers failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()


# 用於追蹤最近提交的記錄（防止重複提交）
recent_submissions = {}

# API: 批次提交需求
@app.route('/api/needs/batch', methods=['POST'])
def create_needs_batch():
    import re

    start_time = time.time()
    trace_id = str(uuid.uuid4())[:16]

    data = request.get_json()
    items = data.get('items', [])
    requester = data.get('items', [{}])[0].get('requester', '') if items else ''
    department = data.get('items', [{}])[0].get('department', '') if items else ''

    # 防止重複提交：檢查 5 秒內是否有相同請求
    current_time = datetime.now()
    request_key = f"{requester}_{hash(str(items))}"

    if request_key in recent_submissions:
        last_submit_time = recent_submissions[request_key]
        if (current_time - last_submit_time).total_seconds() < 3:
            # 記錄重複提交事件
            log_event(
                event_type='NEEDS_SUBMIT',
                source='api:/api/needs/batch',
                actor=requester,
                status='FAIL',
                summary='重複提交被拒絕（3秒內）',
                trace_id=trace_id,
                details={'department': department, 'item_count': len(items), 'reason': 'duplicate_request'}
            )
            # 回傳 200 + 明確訊息，讓前端顯示黃色警告而非紅色錯誤
            return jsonify({'success': False, 'message': '資料已存在（3秒內重複提交），請確認後再試'}), 200

    # 記錄本次提交時間
    recent_submissions[request_key] = current_time

    # 清理過期的記錄（超過 60 秒的）
    expired_keys = [k for k, v in recent_submissions.items() if (current_time - v).total_seconds() > 60]
    for k in expired_keys:
        del recent_submissions[k]

    if not items:
        log_event(
            event_type='NEEDS_SUBMIT',
            source='api:/api/needs/batch',
            actor=requester,
            status='FAIL',
            summary='提交失敗：無資料',
            trace_id=trace_id
        )
        return jsonify({'success': False, 'message': '無資料'})

    # 後端驗證：檢查每筆資料
    for idx, item in enumerate(items, 1):
        product_code = item.get('product_code', '')
        product_name = item.get('product_name', '')
        is_new_product = item.get('is_new_product', False)

        # 驗證 product_name 不可為空
        if not product_name or product_name.strip() == '':
            log_event(
                event_type='NEEDS_SUBMIT',
                source='api:/api/needs/batch',
                actor=requester,
                status='FAIL',
                summary=f'第{idx}筆產品名稱為空',
                trace_id=trace_id,
                error_code='VALIDATION_ERROR'
            )
            return jsonify({'success': False, 'message': f'第{idx}筆：產品名稱不可為空'}), 400

        # 非新品時，驗證 product_code 格式
        if not is_new_product and product_code:
            if not re.match(r'^[A-Za-z0-9-]+$', product_code):
                log_event(
                    event_type='NEEDS_SUBMIT',
                    source='api:/api/needs/batch',
                    actor=requester,
                    status='FAIL',
                    summary=f'第{idx}筆產品編號格式錯誤',
                    trace_id=trace_id,
                    error_code='VALIDATION_ERROR'
                )
                return jsonify({'success': False, 'message': f'第{idx}筆：產品編號只能輸入英文、數字與連字號'}), 400

        # 新品時，product_name 必填已在上面驗證

        # 驗證：用途為「客戶」時，必須提供客戶資料
        purpose = item.get('purpose', '備貨')
        customer_code = item.get('customer_code', '')
        if purpose == '客戶' and not customer_code:
            log_event(
                event_type='NEEDS_SUBMIT',
                source='api:/api/needs/batch',
                actor=requester,
                status='FAIL',
                summary=f'第{idx}筆客戶資料缺失',
                trace_id=trace_id,
                error_code='VALIDATION_ERROR'
            )
            return jsonify({'success': False, 'message': f'第{idx}筆：用途為「客戶」時，必須填寫客戶資料'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # 開始 Transaction（第二防線：交易原子性）
    cursor.execute("BEGIN IMMEDIATE")

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    inserted = 0
    staging_records_created = []  # 記錄已建立的 staging 以便回滾
    new_customer_count = 0
    new_product_count = 0

    try:
        for item in items:
            purpose = item.get('purpose', '備貨')
            customer_code = item.get('customer_code', '')
            request_type = item.get('request_type', '請購')
            transfer_from = item.get('transfer_from', '') if request_type == '調撥' else ''
            product_name = item.get('product_name', '')

            # 取得 staging 相關欄位
            is_new_product = 1 if item.get('is_new_product') else 0
            is_new_customer = 1 if item.get('is_new_customer') else 0
            product_staging_id = item.get('product_staging_id')
            customer_staging_id = item.get('customer_staging_id')
            product_status = item.get('product_status', 'approved')
            customer_status = item.get('customer_status', 'approved')
            customer_mobile = item.get('customer_mobile', '')

            # 點2：新客戶 staging 處理（用手機去重）
            if is_new_customer and customer_mobile:
                try:
                    # 清理手機號碼
                    clean_mobile = customer_mobile.strip()
                    clean_mobile = re.sub(r'[^0-9]', '', clean_mobile)

                    # 驗證手機格式（點2：必須符合 ^09\d{8}$）
                    if re.match(r'^09\d{8}$', clean_mobile):
                        # 檢查是否已有同手機的 pending staging
                        cursor.execute("""
                            SELECT id, temp_customer_id, raw_input
                            FROM staging_records
                            WHERE type = 'customer'
                              AND raw_mobile = ?
                              AND status = 'pending'
                            ORDER BY created_at DESC
                            LIMIT 1
                        """, (clean_mobile,))
                        existing = cursor.fetchone()

                        if existing:
                            # 同手機已存在，更新 last_seen_at（點1）
                            cursor.execute("""
                                UPDATE staging_records
                                SET last_seen_at = datetime('now', 'localtime')
                                WHERE id = ?
                            """, (existing['id'],))

                            # 使用現有的 temp_customer_id
                            customer_staging_id = existing['temp_customer_id']

                            # 檢查是否同名不同（特殊標記）
                            input_name = item.get('customer_name', '').strip()
                            if existing['raw_input'] != input_name:
                                # 同手機不同姓名，加註記
                                if not item.get('remark'):
                                    item['remark'] = ''
                                item['remark'] += f'[同手機({clean_mobile})不同姓名待確認: {existing["raw_input"]} vs {input_name}]'
                                print(f"標記同手機不同姓名: {clean_mobile}")
                        else:
                            # 無現有記錄，建立新的 staging
                            # 點3：使用傳入的 temp_customer_id（前端產生的短 UUID）
                            if not customer_staging_id:
                                # 後備產生（理論上不應該發生）
                                import hashlib
                                hash_val = hashlib.md5(clean_mobile.encode()).hexdigest()[:8].upper()
                                customer_staging_id = f'TEMP-C-{hash_val}'

                            cursor.execute("""
                                INSERT INTO staging_records
                                (type, raw_input, raw_mobile, temp_customer_id, source_type,
                                 requester, department, status, created_at, last_seen_at)
                                VALUES (?, ?, ?, ?, 'needs', ?, ?, 'pending',
                                        datetime('now', 'localtime'), datetime('now', 'localtime'))
                            """, ('customer', item.get('customer_name', ''), clean_mobile,
                                  customer_staging_id, item['requester'], item['department']))
                    else:
                        print(f"手機格式錯誤，跳過 staging: {clean_mobile}")

                except Exception as e:
                    print(f"建立客戶 staging 失敗: {e}")

            # 點3：新品產品 staging 處理（每筆獨立，不去重）
            if is_new_product and product_staging_id and product_staging_id.startswith('TEMP-P-'):
                try:
                    # 檢查是否已存在（避免完全重複提交）
                    cursor.execute("""
                        SELECT id FROM staging_records
                        WHERE type = 'product' AND temp_product_id = ? AND status = 'pending'
                        LIMIT 1
                    """, (product_staging_id,))
                    existing_product = cursor.fetchone()

                    if not existing_product:
                        # 每筆新品都建立獨立的 staging（不去重）
                        cursor.execute("""
                            INSERT INTO staging_records
                            (type, raw_input, temp_product_id, source_type,
                             requester, department, status, created_at, last_seen_at)
                            VALUES (?, ?, ?, 'needs', ?, ?, 'pending',
                                    datetime('now', 'localtime'), datetime('now', 'localtime'))
                        """, ('product', product_name, product_staging_id,
                              item['requester'], item['department']))
                        print(f"建立產品 staging: {product_staging_id}")
                    else:
                        print(f"產品 staging 已存在: {product_staging_id}")

                except Exception as e:
                    print(f"建立產品 staging 失敗: {e}")

            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO needs
                    (date, product_code, item_name, quantity, customer_code, department,
                     requester, status, created_at, remark, purpose, request_type, transfer_from,
                     is_new_product, is_new_customer, product_staging_id, customer_staging_id,
                     product_status, customer_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, '待處理', ?, ?, ?, ?, ?,
                            ?, ?, ?, ?, ?, ?)
                """, (
                    item['date'],
                    item['product_code'],
                    product_name,
                    item['quantity'],
                    customer_code if purpose == '客戶' else '',
                    item['department'],
                    item['requester'],
                    now,
                    item.get('remark', ''),
                    purpose,
                    request_type,
                    transfer_from,
                    is_new_product,
                    is_new_customer,
                    product_staging_id,
                    customer_staging_id,
                    product_status,
                    customer_status
                ))
                if cursor.rowcount > 0:
                    inserted += 1
                else:
                    print(f"跳過重複資料: {product_name} ({item['date']})")
            except Exception as e:
                print(f"匯入失敗: {e}")
                # 發生錯誤時拋出例外，讓外層 catch 並執行 ROLLBACK
                raise e

        # 統計本次建立的 staging 數量
        product_staging_count = 0
        for item in items:
            if item.get('is_new_product') and item.get('product_staging_id'):
                product_staging_count += 1

    except Exception as e:
        # Transaction 失敗，執行 ROLLBACK
        conn.rollback()
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        print(f"Transaction 失敗，已回滾: {error_msg}")
        log_event(
            event_type='NEEDS_SUBMIT',
            source='api:/api/needs/batch',
            actor=requester,
            status='FAIL',
            summary='Transaction 失敗已回滾',
            duration_ms=duration_ms,
            trace_id=trace_id,
            error_code='TRANSACTION_ERROR',
            error_stack=error_msg,
            details={'department': department, 'item_count': len(items)}
        )
        conn.close()
        return jsonify({'success': False, 'message': f'提交失敗，系統已自動回滾: {error_msg}'}), 500

    total_items = len(items)
    response_data = {'success': True, 'count': inserted}

    # 如果有新客戶，回傳 customer_staging_id
    first_customer_staging_id = None
    for item in items:
        if item.get('is_new_customer') and item.get('customer_staging_id'):
            first_customer_staging_id = item.get('customer_staging_id')
            new_customer_count += 1
            break
    if first_customer_staging_id:
        response_data['customer_staging_id'] = first_customer_staging_id

    # 如果有新品，回傳 product_staging_count
    if product_staging_count > 0:
        response_data['product_staging_count'] = product_staging_count

    if inserted == 0:
        duration_ms = int((time.time() - start_time) * 1000)
        log_event(
            event_type='NEEDS_SUBMIT',
            source='api:/api/needs/batch',
            actor=requester,
            status='FAIL',
            summary='所有資料都已存在（重複提交）',
            duration_ms=duration_ms,
            trace_id=trace_id,
            affected_rows=0,
            details={'department': department, 'item_count': total_items}
        )
        conn.close()
        return jsonify({'success': False, 'message': '所有資料都已存在（重複提交），請確認後再試'}), 400
    elif inserted < total_items:
        duration_ms = int((time.time() - start_time) * 1000)
        response_data['message'] = f'成功新增 {inserted} 筆，{total_items - inserted} 筆因重複已跳過'
        log_event(
            event_type='NEEDS_SUBMIT',
            source='api:/api/needs/batch',
            actor=requester,
            status='OK',
            summary=f'部分成功：{inserted}/{total_items} 筆',
            duration_ms=duration_ms,
            trace_id=trace_id,
            affected_rows=inserted,
            details={
                'department': department,
                'total': total_items,
                'inserted': inserted,
                'skipped': total_items - inserted,
                'new_customer': new_customer_count,
                'new_product': product_staging_count
            }
        )
        # Transaction 成功，執行 COMMIT
        conn.commit()
        conn.close()
        return jsonify(response_data)
    else:
        if product_staging_count > 0:
            response_data['message'] = f'成功提交 {inserted} 筆，新品已送入待建檔中心（{product_staging_count}筆）'

        duration_ms = int((time.time() - start_time) * 1000)
        log_event(
            event_type='NEEDS_SUBMIT',
            source='api:/api/needs/batch',
            actor=requester,
            status='OK',
            summary=f'成功提交 {inserted} 筆',
            duration_ms=duration_ms,
            trace_id=trace_id,
            affected_rows=inserted,
            details={
                'department': department,
                'total': total_items,
                'new_customer': new_customer_count,
                'new_product': product_staging_count
            }
        )
        # Transaction 成功，執行 COMMIT
        conn.commit()
        conn.close()

        # 發送 Telegram 通知（背景執行，不阻塞回應）
        try:
            item_count = len(items)
            total_quantity = sum(int(item.get('quantity', 1)) for item in items)
            first_item = items[0] if items else {}
            product_name = first_item.get('product_name', '未知產品')
            request_type = first_item.get('request_type', '請購')
            transfer_from = first_item.get('transfer_from', '')

            # 依類型決定通知格式和發送對象
            if request_type == '調撥':
                telegram_msg = f"""🔄 <b>新調撥需求通知</b>

📅 日期：{now[:10]}
👤 填表人：{requester}
📍 部門：{department}
📦 產品：{product_name}
🔢 數量：{total_quantity} 個
📤 調撥來源：{transfer_from or '未指定'}

請至系統查看詳情"""
                # 調撥發送到會計個人（背景執行）
                import threading
                threading.Thread(
                    target=send_telegram_notification,
                    args=(telegram_msg, TELEGRAM_ACCOUNTANT_CHAT_ID, '調撥需求', None, 'needs'),
                    daemon=True
                ).start()
            else:
                telegram_msg = f"""🛒 <b>新採購需求通知</b>

📅 日期：{now[:10]}
👤 填表人：{requester}
📍 部門：{department}
📦 產品：{product_name}
🔢 數量：{total_quantity} 個

請至系統查看詳情"""
                # 請購發送到老闆個人（背景執行）
                import threading
                threading.Thread(
                    target=send_telegram_notification,
                    args=(telegram_msg, TELEGRAM_CHAT_ID, '請購需求', None, 'needs'),
                    daemon=True
                ).start()
        except Exception as e:
            print(f"Telegram 通知背景執行緒啟動失敗: {e}")

        return jsonify(response_data)


# API: 取得最近提交（30分鐘內可取消）
@app.route('/api/needs/recent')
def get_recent_needs():
    requester = request.args.get('requester', '')
    department = request.args.get('department', '')
    current_user = request.args.get('current_user', '')

    if not department:
        return jsonify({'items': []})

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 獲取同單位的待處理或30分鐘內的已取消需求
        cursor.execute("""
            SELECT id, date, product_code, quantity, customer_code, remark,
                   status, created_at, purpose, request_type, transfer_from, requester,
                   is_new_product, is_new_customer, product_status, customer_status,
                   (strftime('%s', 'now', 'localtime') - strftime('%s', created_at)) / 60 as minutes_ago
            FROM needs
            WHERE department = ?
              AND (status = '待處理' OR (status = '已取消' AND
                   (strftime('%s', 'now', 'localtime') - strftime('%s', created_at)) < 1800))
            ORDER BY created_at DESC
            LIMIT 20
        """, (department,))

        rows = cursor.fetchall()

        items = []
        for row in rows:
            minutes_ago = row['minutes_ago'] if row['minutes_ago'] else 999
            # 只能取消自己的，且狀態為待處理，且30分鐘內
            can_cancel = (row['status'] == '待處理' and minutes_ago < 30 and row['requester'] == current_user)

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

            # 根據 status 決定 status_type
            status_type = 'active'
            if row['status'] == '已取消':
                status_type = 'cancelled'
            elif row['status'] in ['已採購', '已調撥', '已到貨']:
                status_type = 'done'
            
            items.append({
                'id': row['id'],
                'date': row['date'],
                'product_code': row['product_code'],
                'product_name': product_name,
                'quantity': row['quantity'],
                'customer_code': row['customer_code'],
                'remark': row['remark'],
                'status': row['status'],
                'status_type': status_type,
                'purpose': row['purpose'],
                'request_type': row['request_type'],
                'transfer_from': row['transfer_from'],
                'requester': row['requester'],
                'can_cancel': can_cancel,
                'is_new_product': row['is_new_product'],
                'is_new_customer': row['is_new_customer'],
                'product_status': row['product_status'],
                'customer_status': row['customer_status']
            })

        return jsonify({'items': items})
    except Exception as e:
        print(f"get_recent_needs 錯誤: {e}")
        return jsonify({'items': [], 'error': str(e)}), 500
    finally:
        conn.close()

# API: 取消需求（軟刪除）
@app.route('/api/needs/cancel', methods=['POST'])
def cancel_need():
    data = request.get_json()
    need_id = data.get('id')
    current_user = data.get('current_user', '')
    is_boss = data.get('is_boss', False)
    is_accountant = data.get('is_accountant', False)
    requester = data.get('requester', '')

    if not need_id:
        return jsonify({'success': False, 'message': '缺少ID'})

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 驗證權限（如果宣稱是老闆或會計，必須驗證身份）
        if is_boss or is_accountant:
            if not requester:
                return jsonify({'success': False, 'message': '缺少使用者驗證'}), 401

            cursor.execute("SELECT name, title FROM staff_passwords WHERE name = ?", (requester,))
            user = cursor.fetchone()
            if not user:
                return jsonify({'success': False, 'message': '無效的使用者'}), 403

            if is_boss and user['title'] != '老闆':
                return jsonify({'success': False, 'message': '無老闆權限'}), 403
            if is_accountant and '會計' not in user['title']:
                return jsonify({'success': False, 'message': '無會計權限'}), 403

        # 檢查該筆資料
        cursor.execute("""
            SELECT status, requester, request_type,
                   (strftime('%s', 'now', 'localtime') - strftime('%s', created_at)) / 60 as minutes_ago
            FROM needs WHERE id = ?
        """, (need_id,))
        row = cursor.fetchone()

        if not row:
            return jsonify({'success': False, 'message': '找不到該筆資料'})

        # 老闆可以取消任何待處理的需求，無時間限制
        if is_boss:
            if row['status'] != '待處理':
                return jsonify({'success': False, 'message': '該筆資料無法取消'})
        # 會計可以取消任何調撥需求（不限於自己的）
        elif is_accountant:
            if row['request_type'] != '調撥':
                return jsonify({'success': False, 'message': '會計只能取消調撥需求'})
            if row['status'] != '待處理':
                return jsonify({'success': False, 'message': '該筆資料無法取消'})
        else:
            # 一般員工：檢查是否為本人、時間限制等
            if row['requester'] != current_user:
                return jsonify({'success': False, 'message': '只能取消自己的需求'})

            if row['status'] != '待處理':
                return jsonify({'success': False, 'message': '該筆資料無法取消'})

            if row['minutes_ago'] >= 30:
                return jsonify({'success': False, 'message': '超過30分鐘，無法取消'})

        # 軟刪除：標記為已取消
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            UPDATE needs
            SET status = '已取消', cancelled_at = ?
            WHERE id = ?
        """, (now, need_id))

        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(f"cancel_need 錯誤: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


# API: 取得需求歷史紀錄（支援分頁、篩選、搜尋）
@app.route('/api/needs/history')
def get_needs_history():
    """
    取得需求歷史紀錄
    Query params:
        - limit: 每頁筆數 (預設 50, 上限 500)
        - offset: 起始位置 (預設 0)
        - q: 搜尋關鍵字 (可選，搜尋 item_name/customer_code/requester/department)
        - status: 狀態篩選 (all/active/done/cancelled；預設 all)
        - date_from: 起始日期 (可選，格式 YYYY-MM-DD)
        - date_to: 結束日期 (可選，格式 YYYY-MM-DD)
        - include_cancelled: 是否包含已取消 (1/0，沒有 status 時預設 1)
        - scope: all (僅限管理員使用)
    """
    # 分頁參數
    limit = min(int(request.args.get('limit', 50)), 500)
    offset = int(request.args.get('offset', 0))

    # 篩選參數
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('q', '').strip()
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    include_cancelled = request.args.get('include_cancelled', '1') == '1'

    # 取得當前使用者（從登入 session）
    current_user = request.args.get('current_user', '') or request.headers.get('X-Current-User', '')
    department = request.args.get('department', '')
    scope = request.args.get('scope', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 檢查使用者權限
        can_view_all = False
        if current_user:
            cursor.execute("SELECT title FROM staff_passwords WHERE name = ?", (current_user,))
            user_info = cursor.fetchone()
            if user_info:
                title = user_info['title']
                # 檢查是否為管理員角色（包含老闆、主管、admin 等關鍵字）
                if any(keyword in title for keyword in ['老闆', '主管', 'Admin', 'admin']):
                    can_view_all = True

        # 建立 WHERE 條件
        where_clauses = []
        params = []

        # 如果有指定部門，按部門篩選（顯示同部門所有人）
        if department:
            where_clauses.append("department = ?")
            params.append(department)
        elif not can_view_all or scope != 'all':
            # 一般員工或非管理員請求 scope=all，限制為自己的資料
            if current_user:
                where_clauses.append("requester = ?")
                params.append(current_user)

        # 狀態篩選
        if status_filter == 'cancelled':
            where_clauses.append("cancelled_at IS NOT NULL")
        elif status_filter == 'active':
            where_clauses.append("cancelled_at IS NULL AND status != '已完成'")
        elif status_filter == 'done':
            where_clauses.append("cancelled_at IS NULL AND status = '已完成'")
        else:  # all
            if not include_cancelled:
                where_clauses.append("cancelled_at IS NULL")

        # 日期範圍
        if date_from:
            where_clauses.append("date >= ?")
            params.append(date_from)
        if date_to:
            where_clauses.append("date <= ?")
            params.append(date_to)

        # 搜尋關鍵字
        if search_query:
            where_clauses.append("""
                (item_name LIKE ? OR
                 customer_code LIKE ? OR
                 requester LIKE ? OR
                 department LIKE ? OR
                 product_code LIKE ?)
            """)
            search_pattern = f'%{search_query}%'
            params.extend([search_pattern] * 5)

        # 組合 WHERE
        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        # DEBUG: 記錄 SQL 和參數
        import sys
        print(f"[DEBUG] needs/history: user={current_user}, can_view_all={can_view_all}, scope={scope}", flush=True)
        print(f"[DEBUG] SQL: SELECT COUNT(*) as total FROM needs {where_sql}", flush=True)
        print(f"[DEBUG] params: {params}", flush=True)

        # 查詢總筆數
        count_sql = f"SELECT COUNT(*) as total FROM needs {where_sql}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()['total']

        # 查詢資料
        query_sql = f"""
            SELECT
                id, date, item_name, product_code, quantity,
                customer_code, department, requester, remark,
                status, cancelled_at, completed_at, created_at,
                purpose, request_type, is_new_customer, is_new_product
            FROM needs
            {where_sql}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        """
        cursor.execute(query_sql, params + [limit, offset])
        rows = cursor.fetchall()

        # 處理資料
        items = []
        for row in rows:
            # 判斷狀態類型
            if row['cancelled_at']:
                display_status = '已取消'
                status_type = 'cancelled'
            elif row['status'] == '已完成':
                display_status = '已完成'
                status_type = 'done'
            else:
                display_status = row['status'] or '待處理'
                status_type = 'active'

            items.append({
                'id': row['id'],
                'date': row['date'],
                'item_name': row['item_name'] or '',
                'product_code': row['product_code'] or '',
                'quantity': row['quantity'] or 0,
                'customer_code': row['customer_code'] or '',
                'department': row['department'] or '',
                'requester': row['requester'] or '',
                'remark': row['remark'] or '',
                'status': display_status,
                'status_type': status_type,
                'cancelled_at': row['cancelled_at'],
                'completed_at': row['completed_at'],
                'created_at': row['created_at'],
                'purpose': row['purpose'] or '備貨',
                'request_type': row['request_type'] or '請購',
                'is_new_customer': row['is_new_customer'],
                'is_new_product': row['is_new_product']
            })

        return jsonify({
            'success': True,
            'total': total,
            'items': items,
            'limit': limit,
            'offset': offset
        })

    except Exception as e:
        print(f"get_needs_history 錯誤: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


# API: 標記需求為已採購（供老闆使用）
@app.route('/api/needs/purchase', methods=['POST'])
def purchase_need():
    data = request.get_json()
    need_id = data.get('id')
    requester = data.get('requester')

    if not need_id:
        return jsonify({'success': False, 'message': '缺少ID'})

    # 權限檢查：必須是老闆
    if not requester:
        return jsonify({'success': False, 'message': '缺少使用者驗證'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 驗證是否為老闆
        cursor.execute("SELECT name, title FROM staff_passwords WHERE name = ?", (requester,))
        user = cursor.fetchone()
        if not user or user['title'] != '老闆':
            return jsonify({'success': False, 'message': '無老闆權限'}), 403

        # 檢查資料是否存在且狀態為待處理
        cursor.execute("""
            SELECT status, request_type FROM needs WHERE id = ?
        """, (need_id,))
        row = cursor.fetchone()

        if not row:
            return jsonify({'success': False, 'message': '找不到該筆資料'})

        if row['status'] != '待處理':
            return jsonify({'success': False, 'message': '該筆資料無法標記已採購'})

        # 標記為已採購
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            UPDATE needs
            SET status = '已採購', processed_at = ?
            WHERE id = ?
        """, (now, need_id))

        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(f"purchase_need 錯誤: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


# API: 標記需求為已調撥（供會計/老闆使用）
@app.route('/api/needs/transfer', methods=['POST'])
def transfer_need():
    data = request.get_json()
    need_id = data.get('id')
    requester = data.get('requester')

    if not need_id:
        return jsonify({'success': False, 'message': '缺少ID'})

    # 權限檢查：必須是會計或老闆
    if not requester:
        return jsonify({'success': False, 'message': '缺少使用者驗證'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 驗證是否為會計或老闆
        cursor.execute("SELECT name, title FROM staff_passwords WHERE name = ?", (requester,))
        user = cursor.fetchone()
        if not user or (user['title'] != '老闆' and '會計' not in user['title']):
            return jsonify({'success': False, 'message': '無權限執行調撥'}), 403

        # 檢查資料是否存在且狀態為待處理
        cursor.execute("""
            SELECT status, request_type FROM needs WHERE id = ?
        """, (need_id,))
        row = cursor.fetchone()

        if not row:
            return jsonify({'success': False, 'message': '找不到該筆資料'})

        if row['status'] != '待處理':
            return jsonify({'success': False, 'message': '該筆資料無法標記已調撥'})

        # 標記為已調撥
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            UPDATE needs
            SET status = '已調撥', processed_at = ?
            WHERE id = ?
        """, (now, need_id))

        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(f"transfer_need 錯誤: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


# API: 標記需求為已到貨（供員工使用，從已採購/已調撥→已完成）
@app.route('/api/needs/arrive', methods=['POST'])
def arrive_need():
    data = request.get_json()
    need_id = data.get('id')

    if not need_id:
        return jsonify({'success': False, 'message': '缺少ID'})

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 檢查資料是否存在且狀態為已採購或已調撥
        cursor.execute("""
            SELECT status FROM needs WHERE id = ?
        """, (need_id,))
        row = cursor.fetchone()

        if not row:
            return jsonify({'success': False, 'message': '找不到該筆資料'})

        if row['status'] not in ['已採購', '已調撥']:
            return jsonify({'success': False, 'message': '該筆資料尚未採購或調撥'})

        # 標記為已完成（已到貨即完成）
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            UPDATE needs
            SET status = '已完成', arrived_at = ?, completed_at = ?
            WHERE id = ?
        """, (now, now, need_id))

        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(f"arrive_need 錯誤: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


# API: 標記需求為已完成（供老闆/會計直接完成）
@app.route('/api/needs/complete', methods=['POST'])
def complete_need():
    data = request.get_json()
    need_id = data.get('id')

    if not need_id:
        return jsonify({'success': False, 'message': '缺少ID'})

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 檢查資料是否存在
        cursor.execute("""
            SELECT status FROM needs WHERE id = ?
        """, (need_id,))
        row = cursor.fetchone()

        if not row:
            return jsonify({'success': False, 'message': '找不到該筆資料'})

        if row['status'] in ['已完成', '已取消']:
            return jsonify({'success': False, 'message': '該筆資料已結案'})

        # 標記為已完成
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            UPDATE needs
            SET status = '已完成', completed_at = ?
            WHERE id = ?
        """, (now, need_id))

        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(f"complete_need 錯誤: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


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

    try:
        # 檢查資料是否存在
        cursor.execute("SELECT id FROM needs WHERE id = ?", (need_id,))
        row = cursor.fetchone()

        if not row:
            return jsonify({'success': False, 'message': '找不到該筆資料'})

        # 更新備註
        cursor.execute("""
            UPDATE needs
            SET remark = ?
            WHERE id = ?
        """, (remark, need_id))

        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(f"update_need_remark 錯誤: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


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


# API: 外勤服務紀錄 - 獲取列表
@app.route('/api/service-records')
def get_service_records():
    salesperson = request.args.get('salesperson', '')
    quarter = request.args.get('quarter', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT id, date, customer_code, customer_name, service_item,
               service_type, customer_source, is_contract, salesperson, store, updated_at,
               is_new_customer, customer_staging_id, customer_status
        FROM service_records
        WHERE 1=1
    """
    params = []

    if salesperson:
        query += " AND salesperson = ?"
        params.append(salesperson)

    if quarter:
        if quarter == 'Q1':
            query += " AND date >= '2026-01-01' AND date <= '2026-03-31'"
        elif quarter == 'Q2':
            query += " AND date >= '2026-04-01' AND date <= '2026-06-30'"
        elif quarter == 'Q3':
            query += " AND date >= '2026-07-01' AND date <= '2026-09-30'"
        elif quarter == 'Q4':
            query += " AND date >= '2026-10-01' AND date <= '2026-12-31'"

    query += " ORDER BY date DESC, id DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()

    result = []
    for row in rows:
        result.append({
            'id': row['id'],
            'date': row['date'],
            'customer_code': row['customer_code'],
            'customer_name': row['customer_name'],
            'service_item': row['service_item'],
            'service_type': row['service_type'],
            'customer_source': row['customer_source'],
            'is_contract': bool(row['is_contract']),
            'salesperson': row['salesperson'],
            'store': row['store'],
            'updated_at': row['updated_at']
        })

    conn.close()
    return jsonify({'success': True, 'items': result})


# API: 外勤服務紀錄 - 新增
@app.route('/api/service-records', methods=['POST'])
def create_service_record():
    data = request.get_json()

    records = data.get('records', [])
    if not records:
        return jsonify({'success': False, 'message': '沒有資料'})

    conn = get_db_connection()
    cursor = conn.cursor()

    inserted_count = 0
    for record in records:
        date = record.get('date')
        customer_code = record.get('customer_code', '')
        customer_name = record.get('customer_name', '')
        service_item = record.get('service_item', '')
        service_type = record.get('service_type', '')
        customer_source = record.get('customer_source', '')
        is_contract = 1 if record.get('is_contract') == '是' else 0
        salesperson = record.get('salesperson', '')
        store = record.get('store', '')

        # 檢查是否為新客戶
        is_new_customer = record.get('is_new_customer', False)
        customer_mobile = record.get('customer_mobile', '')
        customer_staging_id = None
        customer_status = 'approved'

        # 如果是新客戶，建立 staging 記錄
        if is_new_customer and customer_mobile:
            # 生成臨時客戶 ID
            temp_id = 'TEMP-C-' + datetime.now().strftime('%Y%m%d%H%M%S') + str(inserted_count)

            # 插入 staging_records
            cursor.execute("""
                INSERT INTO staging_records
                (type, raw_input, raw_mobile, temp_customer_id, source_type,
                 requester, department, status, created_at)
                VALUES (?, ?, ?, ?, 'service_record', ?, ?, 'pending', datetime('now', 'localtime'))
            """, ('customer', customer_name, customer_mobile, temp_id,
                  salesperson, '業務部'))

            # 獲取剛插入的 staging ID
            cursor.execute("SELECT last_insert_rowid()")
            customer_staging_id = cursor.fetchone()[0]
            customer_status = 'pending'

            # 使用臨時 ID 作為客戶編號
            customer_code = temp_id

        if service_type == '門市支援' and store:
            customer_name = store

        cursor.execute("""
            INSERT INTO service_records
            (date, customer_code, customer_name, service_item, service_type,
             customer_source, is_contract, salesperson, store, updated_at,
             is_new_customer, customer_staging_id, customer_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'), ?, ?, ?)
        """, (date, customer_code, customer_name, service_item, service_type,
              customer_source, is_contract, salesperson, store,
              1 if is_new_customer else 0, customer_staging_id, customer_status))

        # 獲取剛插入的 service_records ID
        cursor.execute("SELECT last_insert_rowid()")
        service_record_id = cursor.fetchone()[0]

        # 如果是新客戶，更新 staging_records 的 source_id
        if is_new_customer and customer_staging_id:
            cursor.execute("""
                UPDATE staging_records
                SET source_id = ?, source_type = 'service_record'
                WHERE id = ?
            """, (service_record_id, customer_staging_id))

        inserted_count += 1

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'count': inserted_count})


# API: 取得最近服務紀錄
@app.route('/api/service-records/recent')
def get_recent_service_records():
    """取得最近服務紀錄"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, date, customer_code, customer_name, service_item, service_type,
                   salesperson, store, is_new_customer
            FROM service_records
            ORDER BY date DESC, id DESC
            LIMIT 20
        """)

        records = [dict(row) for row in cursor.fetchall()]
        return jsonify({'success': True, 'records': records})

    except Exception as e:
        print(f"[ServiceRecord] 載入失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


# API: 外勤服務紀錄 - 刪除（只能刪除自己30天內的紀錄）
@app.route('/api/service-records/<int:record_id>', methods=['DELETE'])
def delete_service_record(record_id):
    data = request.get_json() or {}
    user_name = data.get('user_name', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 檢查紀錄是否存在且屬於該使用者且在30天內
    cursor.execute("""
        SELECT id, salesperson, date FROM service_records 
        WHERE id = ? AND salesperson = ? 
        AND date >= date('now', '-30 days')
    """, (record_id, user_name))
    
    record = cursor.fetchone()
    if not record:
        conn.close()
        return jsonify({'success': False, 'message': '只能刪除自己30天內的紀錄'}), 403
    
    cursor.execute("DELETE FROM service_records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': '紀錄已刪除'})


# API: 外勤服務紀錄 - 修改（只能修改自己30天內的紀錄）
@app.route('/api/service-records/<int:record_id>', methods=['PUT'])
def update_service_record(record_id):
    data = request.get_json() or {}
    user_name = data.get('user_name', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 檢查紀錄是否存在且屬於該使用者且在30天內
    cursor.execute("""
        SELECT id, salesperson, date FROM service_records 
        WHERE id = ? AND salesperson = ? 
        AND date >= date('now', '-30 days')
    """, (record_id, user_name))
    
    record = cursor.fetchone()
    if not record:
        conn.close()
        return jsonify({'success': False, 'message': '只能修改自己30天內的紀錄'}), 403
    
    # 更新欄位
    service_item = data.get('service_item', '')
    service_type = data.get('service_type', '')
    
    cursor.execute("""
        UPDATE service_records 
        SET service_item = ?, service_type = ?, updated_at = datetime('now', 'localtime')
        WHERE id = ?
    """, (service_item, service_type, record_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': '紀錄已更新'})


# API: 建立客戶待建檔
@app.route('/api/staging/customer', methods=['POST'])
def create_customer_staging():
    """建立客戶待建檔（使用 temp_customer_id 機制）"""
    data = request.json
    short_name = data.get('short_name', '').strip()
    mobile = data.get('mobile', '').strip()
    created_by = data.get('created_by', '').strip()
    department = data.get('department', '').strip()
    source_id = data.get('source_id')
    source_type = data.get('source_type', 'needs')

    if not short_name:
        return jsonify({'success': False, 'error': '客戶姓名不可為空'})

    if not mobile:
        return jsonify({'success': False, 'error': '手機號碼不可為空'})

    conn = get_db_connection()
    cursor = conn.cursor()

    # 產生 temp_customer_id
    today = datetime.now().strftime('%Y%m%d')
    cursor.execute(
        "SELECT COUNT(*) FROM staging_records WHERE temp_customer_id LIKE ?",
        (f'TEMP-{today}%',)
    )
    count = cursor.fetchone()[0] + 1
    temp_id = f'TEMP-{today}-{count:03d}'

    # 寫入 staging_records
    cursor.execute("""
        INSERT INTO staging_records
        (type, raw_input, raw_mobile, temp_customer_id, source_id, source_type,
         requester, department, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
    """, ('customer', short_name, mobile, temp_id, source_id, source_type,
          created_by, department, datetime.now().isoformat()))

    staging_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'staging_id': staging_id, 'temp_customer_id': temp_id})

# API: 建立商品待建檔
@app.route('/api/staging/product', methods=['POST'])
def create_product_staging():
    data = request.json
    product_name = data.get('product_name', '').strip()
    input_product_code = data.get('input_product_code', '').strip()
    requested_by = data.get('requested_by', '').strip()

    if not product_name:
        return jsonify({'success': False, 'error': '商品名稱不可為空'})

    conn = get_db_connection()
    cursor = conn.cursor()

    # 正規化商品編號
    normalized_code = input_product_code.upper().replace(' ', '') if input_product_code else None

    cursor.execute("""
        INSERT INTO product_staging (product_name, input_product_code, normalized_name, requested_by, status)
        VALUES (?, ?, ?, ?, 'pending')
    """, (product_name, input_product_code, normalized_code, requested_by))

    staging_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'staging_id': staging_id})

# API: 獲取待建檔列表
@app.route('/api/staging/list')
def get_staging_list():
    status = request.args.get('status', 'pending')
    type_filter = request.args.get('type', 'all')  # 'customer', 'product', 'all'

    conn = get_db_connection()
    cursor = conn.cursor()
    result = {'customers': [], 'products': []}

    if type_filter in ('all', 'customer'):
        cursor.execute("""
            SELECT * FROM customer_staging
            WHERE status = ?
            ORDER BY created_at DESC
        """, (status,))
        result['customers'] = [dict(row) for row in cursor.fetchall()]

    if type_filter in ('all', 'product'):
        cursor.execute("""
            SELECT * FROM product_staging
            WHERE status = ?
            ORDER BY created_at DESC
        """, (status,))
        result['products'] = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return jsonify({'success': True, 'data': result})

# API: 核准客戶待建檔
@app.route('/api/staging/customer/<int:staging_id>/approve', methods=['POST'])
def approve_customer_staging(staging_id):
    data = request.json
    erp_customer_id = data.get('erp_customer_id', '').strip()
    note = data.get('note', '').strip()

    if not erp_customer_id:
        return jsonify({'success': False, 'error': '請輸入 ERP 客戶編號'})

    conn = get_db_connection()
    cursor = conn.cursor()

    # 更新 staging 表
    cursor.execute("""
        UPDATE customer_staging
        SET status = 'approved', erp_customer_id = ?, note = ?
        WHERE id = ?
    """, (erp_customer_id, note, staging_id))

    # 更新對應的需求單
    cursor.execute("""
        UPDATE needs
        SET customer_status = 'approved', customer_code = ?
        WHERE customer_staging_id = ?
    """, (erp_customer_id, staging_id))

    conn.commit()
    conn.close()

    return jsonify({'success': True})

# API: 核准商品待建檔
@app.route('/api/staging/product/<int:staging_id>/approve', methods=['POST'])
def approve_product_staging(staging_id):
    data = request.json
    erp_product_code = data.get('erp_product_code', '').strip()
    note = data.get('note', '').strip()

    if not erp_product_code:
        return jsonify({'success': False, 'error': '請輸入 ERP 商品編號'})

    conn = get_db_connection()
    cursor = conn.cursor()

    # 更新 staging 表
    cursor.execute("""
        UPDATE product_staging
        SET status = 'approved', erp_product_code = ?, note = ?
        WHERE id = ?
    """, (erp_product_code, note, staging_id))

    # 更新對應的需求單
    cursor.execute("""
        UPDATE needs
        SET product_status = 'approved', product_code = ?
        WHERE product_staging_id = ?
    """, (erp_product_code, staging_id))

    conn.commit()
    conn.close()

    return jsonify({'success': True})

# API: 拒絕待建檔
@app.route('/api/staging/<type>/<int:staging_id>/reject', methods=['POST'])
def reject_staging(type, staging_id):
    data = request.json
    note = data.get('note', '').strip()

    conn = get_db_connection()
    cursor = conn.cursor()

    if type == 'customer':
        cursor.execute("""
            UPDATE customer_staging
            SET status = 'rejected', note = ?
            WHERE id = ?
        """, (note, staging_id))

        cursor.execute("""
            UPDATE needs
            SET customer_status = 'rejected'
            WHERE customer_staging_id = ?
        """, (staging_id,))
    else:
        cursor.execute("""
            UPDATE product_staging
            SET status = 'rejected', note = ?
            WHERE id = ?
        """, (note, staging_id))

        cursor.execute("""
            UPDATE needs
            SET product_status = 'rejected'
            WHERE product_staging_id = ?
        """, (staging_id,))

    conn.commit()
    conn.close()

    return jsonify({'success': True})


# API: 獲取需要人工審核的客戶列表
@app.route('/api/staging/customer/needs-review')
def get_customer_needs_review():
    """獲取狀態為 needs_review 的客戶待建檔列表"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.*,
               (SELECT GROUP_CONCAT(customer_id || ':' || short_name, ';')
                FROM customers m
                WHERE m.mobile = s.mobile) as potential_matches
        FROM customer_staging s
        WHERE s.status = 'needs_review'
        ORDER BY s.created_at ASC
    """)

    rows = cursor.fetchall()
    conn.close()

    items = []
    for row in rows:
        item = dict(row)
        # 解析 potential_matches
        if item.get('potential_matches'):
            matches = []
            for match_str in item['potential_matches'].split(';'):
                if ':' in match_str:
                    cid, name = match_str.split(':', 1)
                    matches.append({'customer_id': cid, 'short_name': name})
            item['potential_matches'] = matches
        else:
            item['potential_matches'] = []
        items.append(item)

    return jsonify({'success': True, 'items': items})


# API: 客戶人工匹配
@app.route('/api/staging/customer/<int:staging_id>/manual-match', methods=['POST'])
def manual_match_customer(staging_id):
    """
    人工匹配客戶待建檔

    請求參數:
    - master_customer_id: 選擇的 master 客戶 ID
    - operator: 操作人員
    """
    data = request.json
    master_customer_id = data.get('master_customer_id', '').strip()
    operator = data.get('operator', 'system').strip()

    if not master_customer_id:
        return jsonify({'success': False, 'error': '請選擇客戶'})

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 檢查 staging 資料
        cursor.execute("SELECT * FROM customer_staging WHERE id = ?", (staging_id,))
        staging = cursor.fetchone()

        if not staging:
            return jsonify({'success': False, 'error': 'Staging 資料不存在'})

        # 檢查客戶（使用 customers 表）
        cursor.execute("SELECT customer_id, short_name, mobile FROM customers WHERE customer_id = ?",
                      (master_customer_id,))
        master = cursor.fetchone()

        if not master:
            return jsonify({'success': False, 'error': 'Master 客戶不存在'})

        now = datetime.now().isoformat()
        reason = f'人工審核匹配 by {operator}: 選擇客戶 {master["short_name"]}({master_customer_id})'

        # 更新 staging
        cursor.execute("""
            UPDATE customer_staging
            SET status = 'synced',
                erp_customer_id = ?,
                match_reason = ?,
                matched_at = ?,
                audit_log = json_array(
                    IFNULL(json_extract(audit_log, '$'), json_array()),
                    json_object('timestamp', ?, 'action', 'MANUAL_MATCH',
                               'details', json_object('operator', ?, 'selected_customer_id', ?,
                                                     'selected_customer_name', ?))
                )
            WHERE id = ?
        """, (master_customer_id, reason, now, now, operator, master_customer_id,
              master['short_name'], staging_id))

        # 更新需求單
        cursor.execute("""
            UPDATE needs
            SET customer_code = ?,
                customer_status = 'synced'
            WHERE customer_staging_id = ?
        """, (master_customer_id, staging_id))

        affected_rows = cursor.rowcount

        conn.commit()

        return jsonify({
            'success': True,
            'staging_id': staging_id,
            'customer_id': master_customer_id,
            'customer_name': master['short_name'],
            'updated_needs': affected_rows
        })

    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()


# API: 獲取客戶列表（供人工匹配選擇）
@app.route('/api/customer-master/search')
def search_customer_master():
    """搜尋客戶（用於人工匹配時選擇）- 統一使用 customers 表"""
    keyword = request.args.get('keyword', '').strip()

    if not keyword or len(keyword) < 2:
        return jsonify({'success': True, 'items': []})

    conn = get_db_connection()
    cursor = conn.cursor()

    # 正規化手機號
    mobile_normalized = keyword.replace('-', '').replace(' ', '')
    if mobile_normalized.startswith('+886'):
        mobile_normalized = '0' + mobile_normalized[4:]

    cursor.execute("""
        SELECT customer_id, short_name, mobile, phone1 as phone
        FROM customers
        WHERE short_name LIKE ?
           OR mobile LIKE ?
           OR customer_id LIKE ?
        ORDER BY
            CASE WHEN mobile = ? THEN 0 ELSE 1 END,
            short_name
        LIMIT 20
    """, (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', mobile_normalized))

    rows = cursor.fetchall()
    conn.close()

    items = [{
        'customer_id': r['customer_id'],
        'short_name': r['short_name'],
        'mobile': r['mobile'],
        'mobile_raw': r['mobile_raw'],
        'phone': r['phone']
    } for r in rows]

    return jsonify({'success': True, 'items': items})


# API: 執行客戶自動匹配（呼叫 match_customer_staging.py）
@app.route('/api/staging/customer/run-match', methods=['POST'])
def run_customer_staging_match():
    """執行客戶待建檔自動匹配任務"""
    import subprocess
    import sys

    try:
        # 執行匹配腳本
        result = subprocess.run(
            [sys.executable, '/Users/aiserver/srv/parser/match_customer_staging.py'],
            capture_output=True,
            text=True,
            timeout=300  # 5分鐘超時
        )

        # 解析輸出（腳本會輸出統計結果）
        output = result.stdout

        # 簡單解析統計數字
        stats = {
            'total_pending': 0,
            'synced': 0,
            'needs_review': 0,
            'pending_remain': 0,
            'errors': 0
        }

        for line in output.split('\n'):
            if 'synced' in line and ':' in line:
                try:
                    stats['synced'] = int(line.split(':')[1].strip())
                except:
                    pass
            elif 'needs_review' in line and ':' in line:
                try:
                    stats['needs_review'] = int(line.split(':')[1].strip())
                except:
                    pass

        return jsonify({
            'success': True,
            'stats': stats,
            'output': output
        })

    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': '匹配任務超時'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ==================== 商品待建檔 API ====================

# API: 獲取需要人工審核的商品列表
@app.route('/api/staging/product/needs-review')
def get_product_needs_review():
    """獲取狀態為 needs_review 的商品待建檔列表"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM product_staging
        WHERE status = 'needs_review'
        ORDER BY created_at ASC
    """)

    rows = cursor.fetchall()
    conn.close()

    return jsonify({'success': True, 'items': [dict(row) for row in rows]})


# API: 商品人工匹配
@app.route('/api/staging/product/<int:staging_id>/manual-match', methods=['POST'])
def manual_match_product(staging_id):
    """
    人工匹配商品待建檔

    請求參數:
    - master_product_code: 選擇的 master 商品編號
    - operator: 操作人員
    """
    data = request.json
    master_product_code = data.get('master_product_code', '').strip()
    operator = data.get('operator', 'system').strip()

    if not master_product_code:
        return jsonify({'success': False, 'error': '請選擇商品'})

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 檢查 staging 資料
        cursor.execute("SELECT * FROM product_staging WHERE id = ?", (staging_id,))
        staging = cursor.fetchone()

        if not staging:
            return jsonify({'success': False, 'error': 'Staging 資料不存在'})

        # 檢查 master 商品
        cursor.execute("SELECT product_code, product_name FROM product_master WHERE product_code = ?",
                      (master_product_code,))
        master = cursor.fetchone()

        if not master:
            return jsonify({'success': False, 'error': 'Master 商品不存在'})

        now = datetime.now().isoformat()
        reason = f'人工審核匹配 by {operator}: 選擇商品 {master["product_name"]}({master_product_code})'

        # 更新 staging
        cursor.execute("""
            UPDATE product_staging
            SET status = 'synced',
                erp_product_code = ?,
                match_reason = ?,
                matched_at = ?,
                audit_log = json_array(
                    IFNULL(json_extract(audit_log, '$'), json_array()),
                    json_object('timestamp', ?, 'action', 'MANUAL_MATCH',
                               'details', json_object('operator', ?, 'selected_product_code', ?,
                                                     'selected_product_name', ?))
                )
            WHERE id = ?
        """, (master_product_code, reason, now, now, operator, master_product_code,
              master['product_name'], staging_id))

        # 更新需求單
        cursor.execute("""
            UPDATE needs
            SET product_code = ?,
                product_status = 'synced'
            WHERE product_staging_id = ?
        """, (master_product_code, staging_id))

        affected_rows = cursor.rowcount

        conn.commit()

        return jsonify({
            'success': True,
            'staging_id': staging_id,
            'product_code': master_product_code,
            'product_name': master['product_name'],
            'updated_needs': affected_rows
        })

    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()


# API: 獲取 Master 商品列表（供人工匹配選擇）
@app.route('/api/product-master/search')
def search_product_master():
    """搜尋 Master 商品（用於人工匹配時選擇）"""
    keyword = request.args.get('keyword', '').strip()

    if not keyword or len(keyword) < 2:
        return jsonify({'success': True, 'items': []})

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT product_code, product_name, category
        FROM product_master
        WHERE product_code LIKE ?
           OR product_name LIKE ?
        ORDER BY
            CASE WHEN product_code = ? THEN 0 ELSE 1 END,
            product_name
        LIMIT 20
    """, (f'%{keyword}%', f'%{keyword}%', keyword.upper()))

    rows = cursor.fetchall()
    conn.close()

    items = [{
        'product_code': r['product_code'],
        'product_name': r['product_name'],
        'category': r['category']
    } for r in rows]

    return jsonify({'success': True, 'items': items})


# API: 執行商品自動匹配（呼叫 match_product_staging.py）
@app.route('/api/staging/product/run-match', methods=['POST'])
def run_product_staging_match():
    """執行商品待建檔自動匹配任務"""
    import subprocess
    import sys

    try:
        # 執行匹配腳本
        result = subprocess.run(
            [sys.executable, '/Users/aiserver/srv/parser/match_product_staging.py'],
            capture_output=True,
            text=True,
            timeout=300  # 5分鐘超時
        )

        # 解析輸出（腳本會輸出統計結果）
        output = result.stdout

        # 簡單解析統計數字
        stats = {
            'total_pending': 0,
            'synced': 0,
            'needs_review': 0,
            'pending_remain': 0,
            'errors': 0
        }

        for line in output.split('\n'):
            if 'synced' in line and ':' in line:
                try:
                    stats['synced'] = int(line.split(':')[1].strip())
                except:
                    pass
            elif 'needs_review' in line and ':' in line:
                try:
                    stats['needs_review'] = int(line.split(':')[1].strip())
                except:
                    pass

        return jsonify({
            'success': True,
            'stats': stats,
            'output': output
        })

    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': '匹配任務超時'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ==================== 新待建檔系統 API (V2) ====================

@app.route('/api/staging/records')
def get_staging_records():
    """
    獲取待建檔記錄列表
    參數:
        type: customer|product|all (預設 all)
        view: pending|resolved|all (預設 pending)
            - pending: 只顯示未取消 + TEMP 編號（仍需建檔）
            - resolved: 只顯示未取消 + 已轉正式編號（已建檔）
            - all: 顯示全部（不分狀態）
    """
    type_filter = request.args.get('type', 'all')
    view = request.args.get('view', 'pending')

    conn = get_db_connection()
    cursor = conn.cursor()

    records = []

    # 根據 view 決定 WHERE 條件
    # 注意：同時檢查 staging_records.status 以處理資料不一致情況
    if view == 'pending':
        # 待處理：TEMP 編號 + 未取消 + staging 未解析
        product_where = "n.cancelled_at IS NULL AND n.product_code LIKE 'TEMP-P-%' AND sr.status != 'resolved'"
        customer_where = "n.cancelled_at IS NULL AND n.customer_code LIKE 'TEMP-C-%' AND sr.status != 'resolved'"
    elif view == 'resolved':
        # 已解析：staging 已解析 + 未取消
        product_where = "n.cancelled_at IS NULL AND sr.status = 'resolved'"
        customer_where = "n.cancelled_at IS NULL AND sr.status = 'resolved'"
    else:  # all
        product_where = "n.cancelled_at IS NULL"
        customer_where = "n.cancelled_at IS NULL"

    # 查詢商品
    if type_filter == 'product' or type_filter == 'all':
        cursor.execute(f"""
            SELECT DISTINCT
                sr.*,
                n.id as needs_id,
                n.status as needs_status,
                n.product_code,
                n.customer_code
            FROM needs n
            JOIN staging_records sr ON sr.temp_product_id = n.product_staging_id
            WHERE {product_where}
            ORDER BY sr.created_at DESC
        """, ())
        records.extend([dict(row) for row in cursor.fetchall()])

    # 查詢客戶
    if type_filter == 'customer' or type_filter == 'all':
        cursor.execute(f"""
            SELECT DISTINCT
                sr.*,
                n.id as needs_id,
                n.status as needs_status,
                n.product_code,
                n.customer_code
            FROM needs n
            JOIN staging_records sr ON sr.temp_customer_id = n.customer_staging_id
            WHERE {customer_where}
            ORDER BY sr.created_at DESC
        """, ())
        records.extend([dict(row) for row in cursor.fetchall()])

    # 統計：分開計算 pending 和 resolved（與 records 查詢使用相同條件：依 staging.status）
    cursor.execute("""
        SELECT
            -- Product pending (staging.status != 'resolved')
            (SELECT COUNT(DISTINCT sr.id)
             FROM needs n
             JOIN staging_records sr ON sr.temp_product_id = n.product_staging_id
             WHERE n.cancelled_at IS NULL
               AND sr.status != 'resolved'
            ) as product_pending,
            -- Product resolved today (staging.status = 'resolved' and updated today)
            (SELECT COUNT(DISTINCT sr.id)
             FROM needs n
             JOIN staging_records sr ON sr.temp_product_id = n.product_staging_id
             WHERE n.cancelled_at IS NULL
               AND sr.status = 'resolved'
               AND DATE(sr.updated_at) = DATE('now', 'localtime')
            ) as product_resolved,
            -- Customer pending (staging.status != 'resolved')
            (SELECT COUNT(DISTINCT sr.id)
             FROM needs n
             JOIN staging_records sr ON sr.temp_customer_id = n.customer_staging_id
             WHERE n.cancelled_at IS NULL
               AND sr.status != 'resolved'
            ) as customer_pending,
            -- Customer resolved today (staging.status = 'resolved' and updated today)
            (SELECT COUNT(DISTINCT sr.id)
             FROM needs n
             JOIN staging_records sr ON sr.temp_customer_id = n.customer_staging_id
             WHERE n.cancelled_at IS NULL
               AND sr.status = 'resolved'
               AND DATE(sr.updated_at) = DATE('now', 'localtime')
            ) as customer_resolved
    """)

    stats = dict(cursor.fetchone())
    conn.close()

    return jsonify({
        'success': True,
        'records': records,
        'stats': stats,
        'view': view,
        'type': type_filter
    })


@app.route('/api/staging/resolve/<int:record_id>', methods=['POST'])
def resolve_staging_record(record_id):
    """人工解析待建檔記錄"""
    data = request.json
    resolved_code = data.get('resolved_code', '').strip()
    resolved_name = data.get('resolved_name', '').strip()

    if not resolved_code:
        return jsonify({'success': False, 'error': '請輸入正式編號'})

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 獲取記錄資訊
        cursor.execute("SELECT * FROM staging_records WHERE id = ?", (record_id,))
        record = cursor.fetchone()

        if not record:
            return jsonify({'success': False, 'error': '記錄不存在'})

        # 更新記錄
        now = datetime.now().isoformat()
        cursor.execute("""
            UPDATE staging_records
            SET status = 'resolved',
                resolved_code = ?,
                resolved_name = ?,
                resolved_at = ?,
                resolver = 'admin',
                resolve_method = 'manual',
                updated_at = ?
            WHERE id = ?
        """, (resolved_code, resolved_name, now, now, record_id))

        # 更新來源單據
        if record['source_type'] == 'needs':
            if record['type'] == 'customer':
                # needs 表沒有 customer_name 欄位，只更新 customer_code
                cursor.execute("""
                    UPDATE needs
                    SET customer_code = ?, customer_status = 'resolved'
                    WHERE id = ?
                """, (resolved_code, record['source_id']))
            else:  # product
                cursor.execute("""
                    UPDATE needs
                    SET product_code = ?, product_status = 'resolved'
                    WHERE id = ?
                """, (resolved_code, record['source_id']))

        conn.commit()
        return jsonify({'success': True})

    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()


@app.route('/api/staging/reconcile', methods=['POST'])
def run_staging_reconcile():
    """執行客戶自動對照"""
    import subprocess
    import sys

    try:
        result = subprocess.run(
            [sys.executable, '/Users/aiserver/srv/parser/reconcile_customers.py'],
            capture_output=True,
            text=True,
            timeout=300
        )

        # 解析統計
        stats = {'auto_resolved': 0, 'needs_review': 0, 'errors': 0}
        for line in result.stdout.split('\n'):
            if '自動回填:' in line:
                try:
                    stats['auto_resolved'] = int(line.split(':')[1].strip())
                except:
                    pass
            elif '需人工審核:' in line:
                try:
                    stats['needs_review'] = int(line.split(':')[1].strip())
                except:
                    pass

        return jsonify({
            'success': True,
            'stats': stats,
            'output': result.stdout
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ==================== 督導評分表 API ====================

@app.route('/api/supervision/score', methods=['GET'])
def get_supervision_score():
    """查詢督導評分"""
    store_name = request.args.get('store', '').strip()
    date = request.args.get('date', '').strip()

    if not store_name or not date:
        return jsonify({'success': False, 'error': '店別和日期必填'})

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM supervision_scores
        WHERE store_name = ? AND date = ?
    """, (store_name, date))

    row = cursor.fetchone()
    conn.close()

    if row:
        return jsonify({'success': True, 'score': dict(row)})
    else:
        return jsonify({'success': True, 'score': None})


@app.route('/api/supervision/score', methods=['POST'])
def save_supervision_score():
    """儲存/更新督導評分"""
    data = request.json

    # 驗證必填欄位
    store_name = data.get('store_name', '').strip()
    date = data.get('date', '').strip()

    if not store_name or not date:
        return jsonify({'success': False, 'message': '店別和日期必填'}), 400

    # 驗證日期格式
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return jsonify({'success': False, 'message': '日期格式錯誤，應為 YYYY-MM-DD'}), 400

    # 驗證分數只能是 0/1/2
    score_fields = ['attendance', 'appearance', 'service_attitude', 'professional_knowledge',
                   'sales_process', 'storefront_cleanliness', 'store_cleanliness', 'product_display',
                   'cable_management', 'warehouse_organization', 'reply_speed', 'reply_attitude',
                   'information_complete']

    for field in score_fields:
        value = data.get(field, 0)
        if value not in [0, 1, 2]:
            return jsonify({'success': False, 'message': f'{field} 分數只能為 0/1/2'}), 400

    # problem_grasp 和 follow_up 也接受文字內容（用於存放問題描述和後續追蹤）
    for field in ['problem_grasp', 'follow_up']:
        value = data.get(field, 0)
        # 如果是數字，檢查範圍；如果是字串，允許通過
        if isinstance(value, (int, float)) and value not in [0, 1, 2]:
            return jsonify({'success': False, 'message': f'{field} 分數只能為 0/1/2'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 檢查是否已存在
        cursor.execute("""
            SELECT id FROM supervision_scores
            WHERE store_name = ? AND date = ?
        """, (store_name, date))

        existing = cursor.fetchone()
        now = datetime.now().isoformat()

        if existing:
            # 更新
            cursor.execute("""
                UPDATE supervision_scores SET
                    attendance = ?, appearance = ?, service_attitude = ?,
                    professional_knowledge = ?, sales_process = ?,
                    storefront_cleanliness = ?, store_cleanliness = ?,
                    product_display = ?, cable_management = ?,
                    warehouse_organization = ?, reply_speed = ?,
                    reply_attitude = ?, problem_grasp = ?,
                    information_complete = ?, follow_up = ?,
                    total_score = ?, evaluator = ?, evaluator_title = ?, updated_at = ?
                WHERE store_name = ? AND date = ?
            """, (
                data.get('attendance', 0), data.get('appearance', 0),
                data.get('service_attitude', 0), data.get('professional_knowledge', 0),
                data.get('sales_process', 0), data.get('storefront_cleanliness', 0),
                data.get('store_cleanliness', 0), data.get('product_display', 0),
                data.get('cable_management', 0), data.get('warehouse_organization', 0),
                data.get('reply_speed', 0), data.get('reply_attitude', 0),
                data.get('problem_grasp', 0), data.get('information_complete', 0),
                data.get('follow_up', 0), data.get('total_score', 0),
                data.get('evaluator', ''), data.get('evaluator_title', ''),
                now, store_name, date
            ))
            message = '評分已更新'
        else:
            # 新增
            cursor.execute("""
                INSERT INTO supervision_scores (
                    store_name, date, attendance, appearance, service_attitude,
                    professional_knowledge, sales_process, storefront_cleanliness,
                    store_cleanliness, product_display, cable_management,
                    warehouse_organization, reply_speed, reply_attitude,
                    problem_grasp, information_complete, follow_up,
                    total_score, evaluator, evaluator_title,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                store_name, date,
                data.get('attendance', 0), data.get('appearance', 0),
                data.get('service_attitude', 0), data.get('professional_knowledge', 0),
                data.get('sales_process', 0), data.get('storefront_cleanliness', 0),
                data.get('store_cleanliness', 0), data.get('product_display', 0),
                data.get('cable_management', 0), data.get('warehouse_organization', 0),
                data.get('reply_speed', 0), data.get('reply_attitude', 0),
                data.get('problem_grasp', 0), data.get('information_complete', 0),
                data.get('follow_up', 0), data.get('total_score', 0),
                data.get('evaluator', ''), data.get('evaluator_title', ''),
                now
            ))
            message = '評分已儲存'

        conn.commit()
        return jsonify({'success': True, 'message': message})

    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


# ==================== 班表 API ====================

@app.route('/api/roster', methods=['GET'])
def get_roster():
    """查詢班表"""
    location = request.args.get('store', '').strip()
    date = request.args.get('date', '').strip()

    if not location or not date:
        return jsonify({'success': False, 'error': '店別和日期必填'})

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM staff_roster
        WHERE location = ? AND date = ?
        ORDER BY staff_name
    """, (location, date))

    rows = cursor.fetchall()
    conn.close()

    return jsonify({'success': True, 'roster': [dict(row) for row in rows]})


@app.route('/api/roster', methods=['POST'])
def save_roster():
    """儲存/更新班表"""
    data = request.json

    # 驗證必填欄位
    location = data.get('location', '').strip()
    staff_name = data.get('staff_name', '').strip()
    date = data.get('date', '').strip()
    shift_code = data.get('shift_code', '').strip()

    if not location or not staff_name or not date or not shift_code:
        return jsonify({'success': False, 'message': '店別、人員、日期、班別必填'}), 400

    # 驗證日期格式
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return jsonify({'success': False, 'message': '日期格式錯誤，應為 YYYY-MM-DD'}), 400

    # 驗證班別
    if shift_code not in ['早', '晚', '值', '休', '全', '特']:
        return jsonify({'success': False, 'message': '班別只能是 早/晚/值/休/全/特'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 檢查是否已存在（同日同人）
        cursor.execute("""
            SELECT rowid FROM staff_roster
            WHERE date = ? AND staff_name = ?
        """, (date, staff_name))

        existing = cursor.fetchone()
        now = datetime.now().isoformat()

        if existing:
            # 更新
            cursor.execute("""
                UPDATE staff_roster SET
                    location = ?, shift_code = ?, updated_at = ?
                WHERE date = ? AND staff_name = ?
            """, (location, shift_code, now, date, staff_name))
            message = '班表已更新'
        else:
            # 新增
            cursor.execute("""
                INSERT INTO staff_roster (date, staff_name, location, shift_code, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (date, staff_name, location, shift_code, now))
            message = '班表已儲存'

        conn.commit()
        return jsonify({'success': True, 'message': message})

    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/roster/range', methods=['GET'])
def get_roster_range():
    """查詢指定日期範圍的班表"""
    store = request.args.get('store', '').strip()
    start = request.args.get('start', '').strip()
    end = request.args.get('end', '').strip()
    staff = request.args.get('staff', '').strip()

    if not store or not start or not end:
        return jsonify({'success': False, 'error': '店別、開始日期、結束日期必填'})

    conn = get_db_connection()
    cursor = conn.cursor()

    if staff:
        cursor.execute("""
            SELECT * FROM staff_roster
            WHERE location = ? AND date >= ? AND date <= ? AND staff_name = ?
            ORDER BY date
        """, (store, start, end, staff))
    else:
        cursor.execute("""
            SELECT * FROM staff_roster
            WHERE location = ? AND date >= ? AND date <= ?
            ORDER BY date, staff_name
        """, (store, start, end))

    rows = cursor.fetchall()
    conn.close()

    return jsonify({'success': True, 'roster': [dict(row) for row in rows]})


@app.route('/api/roster/batch', methods=['POST'])
def save_roster_batch():
    """批量儲存班表"""
    data = request.json
    records = data.get('records', [])

    if not records:
        return jsonify({'success': False, 'message': '沒有班表資料'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    try:
        saved_count = 0
        for record in records:
            location = record.get('location', '').strip()
            staff_name = record.get('staff_name', '').strip()
            date = record.get('date', '').strip()
            shift_code = record.get('shift_code', '').strip()

            if not all([location, staff_name, date, shift_code]):
                continue

            # 驗證日期格式
            try:
                datetime.strptime(date, '%Y-%m-%d')
            except ValueError:
                continue

            # 驗證班別
            if shift_code not in ['早', '晚', '值', '休', '全', '特']:
                continue

            # 檢查是否已存在
            cursor.execute("""
                SELECT rowid FROM staff_roster
                WHERE date = ? AND staff_name = ?
            """, (date, staff_name))

            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                    UPDATE staff_roster SET
                        location = ?, shift_code = ?, updated_at = ?
                    WHERE date = ? AND staff_name = ?
                """, (location, shift_code, now, date, staff_name))
            else:
                cursor.execute("""
                    INSERT INTO staff_roster (date, staff_name, location, shift_code, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (date, staff_name, location, shift_code, now))

            saved_count += 1

        conn.commit()
        return jsonify({'success': True, 'message': f'已儲存 {saved_count} 筆班表'})

    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


# ============================================
# Admin 資料管理中心 API（獨立路由，高安全性）
# 使用統一的 require_admin 裝飾器（已定義在檔案前面）
# ============================================
    return decorated_function

# Admin 稽核摘要 API
@app.route('/api/admin/audit/summary')
@require_admin
def admin_audit_summary():
    """回傳稽核檢查摘要（A1-A5）"""
    conn = get_db_connection()
    cursor = conn.cursor()

    checks = {}

    try:
        # A1: Staging resolved 但 needs 未回填
        cursor.execute("""
            SELECT COUNT(*) as cnt
            FROM staging_records s
            JOIN needs n ON (s.temp_customer_id = n.customer_staging_id
                          OR s.temp_product_id = n.product_staging_id)
            WHERE s.status = 'resolved'
              AND s.resolved_code IS NOT NULL
              AND (n.customer_code = '' OR n.customer_code IS NULL
                   OR n.product_code LIKE 'TEMP-P-%')
        """)
        checks['A1'] = cursor.fetchone()['cnt']

        # A2: 待建檔異常 - needs 已有正式碼但 staging 仍 pending/needs_review
        # 條件：staging pending/needs_review + needs 未取消 + 不是 TEMP 編號
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM (
                -- Customer A2
                SELECT s.id
                FROM staging_records s
                JOIN needs n ON n.customer_staging_id = s.temp_customer_id
                WHERE s.type = 'customer'
                  AND s.status IN ('pending', 'needs_review')
                  AND n.cancelled_at IS NULL
                  AND n.customer_code NOT LIKE 'TEMP-C-%'
                UNION ALL
                -- Product A2
                SELECT s.id
                FROM staging_records s
                JOIN needs n ON n.product_staging_id = s.temp_product_id
                WHERE s.type = 'product'
                  AND s.status IN ('pending', 'needs_review')
                  AND n.cancelled_at IS NULL
                  AND n.product_code NOT LIKE 'TEMP-P-%'
            )
        """)
        checks['A2'] = cursor.fetchone()['cnt']

        # A3: Needs 指到不存在的正式主檔
        # 排除臨時客戶 (TEMP-C-%) 和臨時產品 (TEMP-P-%, NEW-%)
        # 注意：needs.customer_code 可能存 customer_id 或 short_name
        cursor.execute("""
            SELECT COUNT(*) as cnt
            FROM needs n
            LEFT JOIN customers c1 ON n.customer_code = c1.customer_id
            LEFT JOIN customers c2 ON n.customer_code = c2.short_name
            LEFT JOIN products p ON n.product_code = p.product_code
            WHERE (n.customer_code != ''
                   AND n.customer_code NOT LIKE 'TEMP-C-%'
                   AND c1.customer_id IS NULL
                   AND c2.short_name IS NULL)
               OR (n.product_code NOT LIKE 'TEMP-P-%'
                   AND n.product_code NOT LIKE 'NEW-%'
                   AND p.product_code IS NULL)
        """)
        checks['A3'] = cursor.fetchone()['cnt']

        # A4: 同手機重複 customer staging
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM (
                SELECT raw_mobile
                FROM staging_records
                WHERE type = 'customer' AND status = 'pending'
                GROUP BY raw_mobile
                HAVING COUNT(*) > 1
            )
        """)
        checks['A4'] = cursor.fetchone()['cnt']

        # A5: Products 同名多 product_code
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM (
                SELECT product_name
                FROM products
                GROUP BY product_name
                HAVING COUNT(*) > 1
            )
        """)
        checks['A5'] = cursor.fetchone()['cnt']

        return jsonify({'success': True, 'checks': checks})

    except Exception as e:
        print(f"admin_audit_summary 錯誤: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


# Admin 稽核明細 API
@app.route('/api/admin/audit/detail')
@require_admin
def admin_audit_detail():
    """回傳稽核明細資料"""
    code = request.args.get('code', '')
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        items = []

        if code == 'A1':
            # Staging resolved 但 needs 未回填
            cursor.execute("""
                SELECT
                    s.id as staging_id,
                    s.type,
                    s.raw_input,
                    s.temp_customer_id,
                    s.temp_product_id,
                    s.resolved_code,
                    s.resolved_name,
                    n.id as need_id,
                    n.customer_code,
                    n.product_code,
                    n.item_name,
                    n.requester,
                    n.department
                FROM staging_records s
                JOIN needs n ON (s.temp_customer_id = n.customer_staging_id
                              OR s.temp_product_id = n.product_staging_id)
                WHERE s.status = 'resolved'
                  AND s.resolved_code IS NOT NULL
                  AND (n.customer_code = '' OR n.customer_code IS NULL
                       OR n.product_code LIKE 'TEMP-P-%')
                ORDER BY s.resolved_at DESC
                LIMIT 100
            """)
            items = [dict(row) for row in cursor.fetchall()]

        elif code == 'A2':
            # A2: 待建檔異常 - needs 已有正式碼但 staging 仍 pending/needs_review
            cursor.execute("""
                SELECT
                    s.id as staging_id,
                    s.type,
                    s.status as staging_status,
                    n.id as need_id,
                    n.customer_code,
                    n.product_code,
                    n.item_name,
                    n.requester,
                    n.department
                FROM staging_records s
                JOIN needs n ON n.customer_staging_id = s.temp_customer_id
                WHERE s.type = 'customer'
                  AND s.status IN ('pending', 'needs_review')
                  AND n.cancelled_at IS NULL
                  AND n.customer_code NOT LIKE 'TEMP-C-%'
                UNION ALL
                SELECT
                    s.id as staging_id,
                    s.type,
                    s.status as staging_status,
                    n.id as need_id,
                    n.customer_code,
                    n.product_code,
                    n.item_name,
                    n.requester,
                    n.department
                FROM staging_records s
                JOIN needs n ON n.product_staging_id = s.temp_product_id
                WHERE s.type = 'product'
                  AND s.status IN ('pending', 'needs_review')
                  AND n.cancelled_at IS NULL
                  AND n.product_code NOT LIKE 'TEMP-P-%'
                ORDER BY need_id DESC
                LIMIT 100
            """)
            items = [dict(row) for row in cursor.fetchall()]

        elif code == 'A3':
            # Needs 指到不存在的正式主檔
            # 排除臨時客戶 (TEMP-C-%) 和臨時產品 (TEMP-P-%, NEW-%)
            # 注意：needs.customer_code 可能存 customer_id 或 short_name
            cursor.execute("""
                SELECT
                    n.id,
                    n.customer_code,
                    n.product_code,
                    n.item_name,
                    n.requester,
                    n.department,
                    n.created_at
                FROM needs n
                LEFT JOIN customers c1 ON n.customer_code = c1.customer_id
                LEFT JOIN customers c2 ON n.customer_code = c2.short_name
                LEFT JOIN products p ON n.product_code = p.product_code
                WHERE (n.customer_code != ''
                       AND n.customer_code NOT LIKE 'TEMP-C-%'
                       AND c1.customer_id IS NULL
                       AND c2.short_name IS NULL)
                   OR (n.product_code NOT LIKE 'TEMP-P-%'
                       AND n.product_code NOT LIKE 'NEW-%'
                       AND p.product_code IS NULL)
                ORDER BY n.created_at DESC
                LIMIT 100
            """)
            items = [dict(row) for row in cursor.fetchall()]

        elif code == 'A4':
            # 同手機重複 customer staging
            cursor.execute("""
                SELECT
                    s1.id,
                    s1.raw_mobile,
                    s1.raw_input,
                    s1.temp_customer_id,
                    s1.created_at
                FROM staging_records s1
                JOIN (
                    SELECT raw_mobile
                    FROM staging_records
                    WHERE type = 'customer' AND status = 'pending'
                    GROUP BY raw_mobile
                    HAVING COUNT(*) > 1
                ) s2 ON s1.raw_mobile = s2.raw_mobile
                WHERE s1.type = 'customer' AND s1.status = 'pending'
                ORDER BY s1.raw_mobile, s1.created_at
                LIMIT 100
            """)
            items = [dict(row) for row in cursor.fetchall()]

        elif code == 'A5':
            # Products 同名多 product_code
            cursor.execute("""
                SELECT
                    p1.product_name,
                    p1.product_code,
                    p1.created_at
                FROM products p1
                JOIN (
                    SELECT product_name
                    FROM products
                    GROUP BY product_name
                    HAVING COUNT(*) > 1
                ) p2 ON p1.product_name = p2.product_name
                ORDER BY p1.product_name, p1.created_at
                LIMIT 100
            """)
            items = [dict(row) for row in cursor.fetchall()]

        return jsonify({'success': True, 'code': code, 'items': items})

    except Exception as e:
        print(f"admin_audit_detail 錯誤: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


# Admin 資料表查詢 API
@app.route('/api/admin/table')
@require_admin
def admin_table_query():
    """通用資料表查詢"""
    table_name = request.args.get('name', '')
    limit = min(int(request.args.get('limit', 100)), 500)
    offset = int(request.args.get('offset', 0))
    keyword = request.args.get('keyword', '')

    # 白名單驗證（只允許特定表）
    allowed_tables = ['needs', 'staging_records', 'customers', 'products',
                      'inventory', 'purchase_history', 'sales_history',
                      'admin_audit_log', 'admin_tombstone', 'ops_events']
    if table_name not in allowed_tables:
        return jsonify({'success': False, 'message': '不允許訪問該表'}), 403

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 構建查詢
        where_clause = "1=1"
        params = []

        if keyword:
            # 根據不同表構建搜尋條件
            if table_name == 'needs':
                where_clause += " AND (item_name LIKE ? OR product_code LIKE ? OR requester LIKE ?)"
                params.extend([f'%{keyword}%'] * 3)
            elif table_name == 'customers':
                where_clause += " AND (short_name LIKE ? OR mobile LIKE ? OR customer_id LIKE ?)"
                params.extend([f'%{keyword}%'] * 3)
            elif table_name == 'products':
                where_clause += " AND (product_name LIKE ? OR product_code LIKE ?)"
                params.extend([f'%{keyword}%'] * 2)
            elif table_name == 'admin_audit_log':
                where_clause += " AND (admin_user LIKE ? OR action LIKE ?)"
                params.extend([f'%{keyword}%'] * 2)
            elif table_name == 'ops_events':
                where_clause += " AND (event_type LIKE ? OR source LIKE ? OR actor LIKE ?)"
                params.extend([f'%{keyword}%'] * 3)

        # staging_records 特殊處理：以 needs 為準（未取消 + TEMP 編號）
        if table_name == 'staging_records':
            # 獲取資料：商品 + 客戶，以 needs 驅動，不看 staging.status
            cursor.execute("""
                -- 商品：以 needs 為準
                SELECT DISTINCT sr.*, n.id as needs_id, n.status as needs_status
                FROM needs n
                JOIN staging_records sr ON sr.temp_product_id = n.product_staging_id
                WHERE n.cancelled_at IS NULL
                  AND n.product_code LIKE 'TEMP-P-%'

                UNION ALL

                -- 客戶：以 needs 為準
                SELECT DISTINCT sr.*, n.id as needs_id, n.status as needs_status
                FROM needs n
                JOIN staging_records sr ON sr.temp_customer_id = n.customer_staging_id
                WHERE n.cancelled_at IS NULL
                  AND n.customer_code LIKE 'TEMP-C-%'

                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))

            items = [dict(row) for row in cursor.fetchall()]

            # 獲取總筆數
            cursor.execute("""
                SELECT COUNT(*) as total FROM (
                    SELECT DISTINCT sr.id
                    FROM needs n
                    JOIN staging_records sr ON sr.temp_product_id = n.product_staging_id
                    WHERE n.cancelled_at IS NULL
                      AND n.product_code LIKE 'TEMP-P-%'
                    UNION ALL
                    SELECT DISTINCT sr.id
                    FROM needs n
                    JOIN staging_records sr ON sr.temp_customer_id = n.customer_staging_id
                    WHERE n.cancelled_at IS NULL
                      AND n.customer_code LIKE 'TEMP-C-%'
                )
            """)
            total = cursor.fetchone()['total']

            return jsonify({
                'success': True,
                'table': table_name,
                'items': items,
                'total': total,
                'limit': limit,
                'offset': offset
            })

        # 獲取總筆數
        cursor.execute(f"SELECT COUNT(*) as total FROM {table_name} WHERE {where_clause}", params)
        total = cursor.fetchone()['total']

        # 決定排序欄位
        sort_field = request.args.get('sort', 'created_at')
        sort_order = request.args.get('order', 'desc').upper()

        # 不同表的預設排序欄位映射
        sort_field_map = {
            'inventory': 'report_date',
            'ops_events': 'ts',
            'admin_audit_log': 'created_at',
            'purchase_history': 'date',
            'sales_history': 'date',
            'customers': 'updated_at'  # customers 表使用 updated_at
        }

        # 驗證排序欄位是否存在，不存在則使用 id
        actual_sort_field = sort_field_map.get(table_name, sort_field)
        if actual_sort_field == 'created_at' and table_name in ['purchase_history', 'sales_history']:
            actual_sort_field = 'date'

        # 驗證排序方向
        if sort_order not in ['ASC', 'DESC']:
            sort_order = 'DESC'

        # 獲取資料
        query_params = params + [limit, offset]
        cursor.execute(f"""
            SELECT * FROM {table_name}
            WHERE {where_clause}
            ORDER BY {actual_sort_field} {sort_order}
            LIMIT ? OFFSET ?
        """, query_params)

        items = [dict(row) for row in cursor.fetchall()]

        return jsonify({
            'success': True,
            'table': table_name,
            'items': items,
            'total': total,
            'limit': limit,
            'offset': offset
        })

    except Exception as e:
        print(f"admin_table_query 錯誤: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


# Admin 單筆資料獲取 API
@app.route('/api/admin/row')
@require_admin
def admin_row_get():
    """獲取單筆資料詳情"""
    table_name = request.args.get('table', '')
    row_id = request.args.get('id')

    allowed_tables = ['needs', 'staging_records', 'customers', 'products',
                      'inventory', 'purchase_history', 'sales_history',
                      'admin_audit_log', 'admin_tombstone', 'ops_events']
    if table_name not in allowed_tables:
        return jsonify({'success': False, 'message': '不允許訪問該表'}), 403

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 檢查表是否有 id 欄位
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        has_id = any(col['name'] == 'id' for col in columns)

        if has_id:
            cursor.execute(f"SELECT * FROM {table_name} WHERE id = ?", (row_id,))
        else:
            # 對於沒有 id 的表，使用索引查詢
            # 獲取所有欄位，用 LIMIT 和 OFFSET 模擬單筆查詢
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 1 OFFSET ?", (int(row_id),))

        row = cursor.fetchone()

        if not row:
            return jsonify({'success': False, 'message': '資料不存在'}), 404

        return jsonify({'success': True, 'item': dict(row)})

    except Exception as e:
        print(f"admin_row_get 錯誤: {e}")
        return jsonify({'success': False, 'message': f'系統錯誤: {str(e)}'}), 500
    finally:
        conn.close()


# Admin 資料修正 API
@app.route('/api/admin/fix/apply', methods=['POST'])
@require_admin
def admin_fix_apply():
    """執行資料修正"""
    data = request.get_json()
    fix_code = data.get('fix_code')
    ids = data.get('ids', [])
    action = data.get('action')
    admin_user = request.args.get('admin') or request.headers.get('X-Admin-User')

    if not fix_code or not ids or not action:
        return jsonify({'success': False, 'message': '缺少必要參數'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        fixed_count = 0

        if fix_code == 'A1' and action == 'backfill':
            # 回填 staging.resolved_code 到 needs
            for item_id in ids:
                cursor.execute("""
                    UPDATE needs
                    SET customer_code = (
                        SELECT resolved_code FROM staging_records
                        WHERE temp_customer_id = needs.customer_staging_id
                    ),
                        product_code = COALESCE((
                            SELECT resolved_code FROM staging_records
                            WHERE temp_product_id = needs.product_staging_id
                        ), product_code)
                    WHERE id = ?
                """, (item_id,))
                fixed_count += cursor.rowcount

        # 記錄 audit log
        cursor.execute("""
            INSERT INTO admin_audit_log (admin_user, action, fix_code, affected_ids, affected_count, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        """, (admin_user, action, fix_code, json.dumps(ids), fixed_count))

        conn.commit()
        return jsonify({'success': True, 'fixed_count': fixed_count})

    except Exception as e:
        print(f"admin_fix_apply 錯誤: {e}")
        conn.rollback()
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


# Admin Audit Log 獲取 API
@app.route('/api/admin/audit-log')
@require_admin
def admin_audit_log():
    """獲取管理員操作日誌"""
    limit = min(int(request.args.get('limit', 50)), 100)
    offset = int(request.args.get('offset', 0))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 檢查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='admin_audit_log'
        """)
        if not cursor.fetchone():
            return jsonify({'success': True, 'items': [], 'message': '日誌表尚未建立'})

        cursor.execute("""
            SELECT * FROM admin_audit_log
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))

        items = [dict(row) for row in cursor.fetchall()]
        return jsonify({'success': True, 'items': items})

    except Exception as e:
        print(f"admin_audit_log 錯誤: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()



# ============================================
# 觀測系統 API v2.0 (Observability APIs)
# ============================================

@app.route('/api/v1/admin/observability/health')
def admin_observability_health():
    """綜合健康狀態（三區塊）"""
    try:
        health = get_overall_health()
        return jsonify({'success': True, **health})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/v1/admin/observability/freshness')
def admin_observability_freshness():
    """資料新鮮度詳情"""
    try:
        update_freshness_cache()
        freshness = get_freshness_status()
        return jsonify({'success': True, 'items': freshness})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/v1/admin/observability/ingest')
def admin_observability_ingest():
    """匯入狀態詳情"""
    try:
        ingest = get_ingest_status()
        return jsonify({'success': True, 'ingest': ingest})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/v1/admin/observability/consistency')
def admin_observability_consistency():
    """資料一致性稽核"""
    try:
        consistency = get_consistency_status()
        return jsonify({'success': True, 'consistency': consistency})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/v1/admin/observability/events')
def admin_observability_events():
    """查詢 ops_events"""
    event_type = request.args.get('type', '')
    status = request.args.get('status', '')
    hours = int(request.args.get('hours', 24))
    limit = int(request.args.get('limit', 50))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        sql = """
            SELECT id, ts, event_type, source, trace_id, actor, status,
                   duration_ms, summary, affected_rows
            FROM ops_events
            WHERE ts > datetime('now', '-{} hours')
        """.format(hours)
        params = []

        if event_type:
            sql += " AND event_type = ?"
            params.append(event_type)
        if status:
            sql += " AND status = ?"
            params.append(status)

        sql += " ORDER BY ts DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        items = [dict(r) for r in cursor.fetchall()]
        conn.close()

        return jsonify({'success': True, 'items': items})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/v1/admin/observability/trace/<trace_id>')
def admin_observability_trace(trace_id):
    """追蹤特定 trace_id"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM ops_events
            WHERE trace_id = ? OR parent_trace_id = ?
            ORDER BY ts
        """, (trace_id, trace_id))

        items = [dict(r) for r in cursor.fetchall()]
        conn.close()

        return jsonify({'success': True, 'trace_id': trace_id, 'items': items})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/v1/admin/observability/last-event')
def admin_observability_last_event():
    """取得最後一次成功/失敗事件"""
    event_type = request.args.get('type', 'IMPORT')
    status = request.args.get('status', 'OK')

    try:
        event = get_last_event(event_type, status, hours=48)
        return jsonify({'success': True, 'event': event})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/v1/admin/observability/api-performance')
def admin_observability_api_perf():
    """API 效能指標"""
    hours = int(request.args.get('hours', 1))
    try:
        perf = get_api_performance(hours)
        return jsonify({'success': True, 'performance': perf})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/v1/admin/observability/debug-sql')
def admin_observability_debug_sql():
    """取得建議排查 SQL"""
    issue_type = request.args.get('issue', 'missing_import')
    sql = get_debug_sql(issue_type)
    return jsonify({'success': True, 'issue': issue_type, 'sql': sql})

# ============================================
# 資料庫健康監控 API (DB Health Monitor)
# ============================================

@app.route('/api/admin/db/row-stats')
def admin_db_row_stats():
    """表筆數成長監控 - 監控 needs, staging_records, admin_audit_log"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        today = datetime.now().strftime('%Y-%m-%d')

        # needs 表統計
        cursor.execute("SELECT COUNT(*) as total FROM needs")
        needs_total = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as today FROM needs WHERE created_at >= ?", (today,))
        needs_today = cursor.fetchone()['today']

        # staging_records 表統計
        cursor.execute("SELECT COUNT(*) as total FROM staging_records")
        staging_total = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as today FROM staging_records WHERE DATE(created_at) = ?", (today,))
        staging_today = cursor.fetchone()['today']

        # admin_audit_log 表統計
        cursor.execute("SELECT COUNT(*) as total FROM admin_audit_log")
        audit_total = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as today FROM admin_audit_log WHERE DATE(created_at) = ?", (today,))
        audit_today = cursor.fetchone()['today']

        conn.close()

        return jsonify({
            'success': True,
            'needs': {'total': needs_total, 'today_added': needs_today},
            'staging_records': {'total': staging_total, 'today_added': staging_today},
            'admin_audit_log': {'total': audit_total, 'today_added': audit_today}
        })
    except Exception as e:
        print(f"[DB Monitor] 表筆數統計錯誤: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/db/size')
def admin_db_size():
    """資料庫檔案大小監控"""
    try:
        import os

        db_path = '/Users/aiserver/srv/db/company.db'
        wal_path = db_path + '-wal'
        shm_path = db_path + '-shm'

        # 取得檔案大小
        db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
        wal_size = os.path.getsize(wal_path) if os.path.exists(wal_path) else 0
        shm_size = os.path.getsize(shm_path) if os.path.exists(shm_path) else 0

        # 取得 journal mode
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        journal_mode = cursor.fetchone()[0]
        conn.close()

        return jsonify({
            'success': True,
            'db_size_mb': round(db_size / (1024 * 1024), 2),
            'wal_size_mb': round(wal_size / (1024 * 1024), 2),
            'shm_size_mb': round(shm_size / (1024 * 1024), 2),
            'journal_mode': journal_mode
        })
    except Exception as e:
        print(f"[DB Monitor] 檔案大小統計錯誤: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/db/slow-queries')
def admin_db_slow_queries():
    """取得最近慢查詢記錄（>200ms）"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 查詢最近 20 筆慢查詢（從 ops_events 表查詢，因為 admin_audit_log 沒有 ts 欄位）
        cursor.execute("""
            SELECT ts, source as action, duration_ms, details_json
            FROM ops_events
            WHERE duration_ms > 200
            ORDER BY ts DESC
            LIMIT 20
        """)

        rows = cursor.fetchall()
        items = [{
            'timestamp': row['ts'],
            'endpoint': row['action'],
            'duration_ms': row['duration_ms'] or 0,
            'details': row['details_json']
        } for row in rows]

        conn.close()

        return jsonify({'success': True, 'items': items})
    except Exception as e:
        print(f"[DB Monitor] 慢查詢查詢錯誤: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# 客戶資料同步 API
# ============================================

@app.route('/api/admin/customers/sync', methods=['POST'])
@require_admin
def admin_customers_sync():
    """
    手動觸發 customers 同步
    mode=init: customers → customer_master（初始化，一次性）
    mode=sync: customer_master → customers（未來定期同步）
    """
    try:
        admin_user = request.args.get('admin') or request.headers.get('X-Admin-User')
        mode = request.args.get('mode', 'sync')  # 預設為 sync

        if mode == 'init':
            # 初始化：從 customers 匯入到 customer_master
            result = sync_customers_to_master(actor=admin_user)
            action = '初始化'
        else:
            # 同步：從 customer_master 同步到 customers
            result = sync_customers_from_master(actor=admin_user)
            action = '同步'

        if result['success']:
            return jsonify({
                'success': True,
                'message': f'{action}完成：{result.get("synced", 0)} 筆',
                'mode': mode,
                'details': result
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('error', f'{action}失敗'),
                'mode': mode
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/admin/customers/source')
@require_admin
def admin_customers_source():
    """取得目前的客戶資料來源設定"""
    return jsonify({
        'success': True,
        'source': CUSTOMER_SOURCE,
        'table': get_customer_table_name()
    })


# ============================================

# ============================================
# API: 取得目標資料（供目標輸入頁面使用）
@app.route("/api/targets")
def get_targets():
    from datetime import datetime
    conn = get_db_connection()
    cursor = conn.cursor()

    year = request.args.get("year", datetime.now().year, type=int)
    month = request.args.get("month", datetime.now().month, type=int)

    # 查詢部門目標
    cursor.execute("""
        SELECT subject_name, target_amount
        FROM performance_metrics
        WHERE category = "部門" AND year = ? AND month = ? AND period_type = "monthly"
    """, (year, month))
    dept_rows = cursor.fetchall()

    # 查詢門市目標
    cursor.execute("""
        SELECT subject_name, target_amount
        FROM performance_metrics
        WHERE category = "門市" AND year = ? AND month = ? AND period_type = "monthly"
    """, (year, month))
    store_rows = cursor.fetchall()

    # 查詢個人目標
    cursor.execute("""
        SELECT subject_name, target_amount
        FROM performance_metrics
        WHERE category = "個人" AND year = ? AND month = ? AND period_type = "monthly"
    """, (year, month))
    personal_rows = cursor.fetchall()

    conn.close()

    return jsonify({
        "success": True,
        "year": year,
        "month": month,
        "departments": [{"name": r["subject_name"], "target_amount": r["target_amount"]} for r in dept_rows],
        "stores": [{"name": r["subject_name"], "target_amount": r["target_amount"]} for r in store_rows],
        "personal": [{"name": r["subject_name"], "target_amount": r["target_amount"]} for r in personal_rows]
    })

# API: 儲存目標資料
@app.route("/api/targets/save", methods=["POST"])
def save_targets():
    from datetime import datetime
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        data = request.get_json()
        year = data.get("year")
        month = data.get("month")
        targets = data.get("targets", [])

        saved_count = 0

        for target in targets:
            category = target.get("category")
            name = target.get("name")
            amount = target.get("target")

            # 檢查是否已存在
            cursor.execute("""
                SELECT 1 FROM performance_metrics
                WHERE category = ? AND subject_name = ? AND year = ? AND month = ? AND period_type = 'monthly'
            """, (category, name, year, month))

            existing = cursor.fetchone()

            if existing:
                # 更新現有記錄
                cursor.execute("""
                    UPDATE performance_metrics
                    SET target_amount = ?, updated_at = datetime('now', 'localtime')
                    WHERE category = ? AND subject_name = ? AND year = ? AND month = ? AND period_type = 'monthly'
                """, (amount, category, name, year, month))
            else:
                # 插入新記錄
                cursor.execute("""
                    INSERT INTO performance_metrics
                    (category, subject_name, target_amount, revenue_amount, profit_amount,
                     achievement_rate, margin_rate, year, month, period_type, updated_at)
                    VALUES (?, ?, ?, 0, 0, 0, 0, ?, ?, 'monthly', datetime('now', 'localtime'))
                """, (category, name, amount, year, month))

            saved_count += 1

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "saved_count": saved_count,
            "message": f"成功儲存 {saved_count} 筆目標"
        })

    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"success": False, "error": str(e)}), 500



# 啟動時記錄系統啟動事件（使用 app_context 取代 before_first_request）
def record_startup():
    with app.app_context():
        log_event(
            event_type='SYSTEM',
            source='app.py',
            actor='system',
            status='OK',
            summary='Flask 應用程式啟動'
        )
        # 更新資料新鮮度快取
        try:
            update_freshness_cache()
        except:
            pass


if __name__ == '__main__':
    print("🚀 營運系統 API 服務啟動中...")
    print("📊 請訪問: http://localhost:3000")
    print("🤖 每日 20:00 自動分析已啟動")
    print("-" * 50)

    # 固定使用 Port 3000，禁止自動切換
    FIXED_PORT = 3000

    # 檢查端口是否已被佔用
    import socket
    from werkzeug.serving import run_simple
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('0.0.0.0', FIXED_PORT))
        sock.close()
    except socket.error as e:
        print(f"❌ 錯誤：Port {FIXED_PORT} 已被佔用")
        print(f"   詳情: {e}")
        print(f"   請先停止佔用該端口的程序，再重新啟動服務")
        print(f"   禁止自動切換到其他端口")
        import sys
        sys.exit(1)

    # 啟動 Flask（使用 werkzeug run_simple 確保路由正確載入）
    try:
        run_simple('0.0.0.0', FIXED_PORT, app, use_reloader=False, use_debugger=False, threaded=True)
    except Exception as e:
        print(f"❌ Flask 啟動失敗: {e}")
        import sys
        sys.exit(1)


# ============================================
# API: 員工管理
# ============================================

@app.route("/api/staff")
def get_staff_list():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT staff_id as id, staff_code, name, department, store, role,
               phone, mobile, birth_date, hire_date, is_active, id_number
        FROM staff
        ORDER BY department, store, name
    """)

    rows = cursor.fetchall()
    conn.close()

    return jsonify({
        "success": True,
        "data": [{
            "id": r["id"],
            "staff_code": r["staff_code"],
            "name": r["name"],
            "department": r["department"],
            "store": r["store"],
            "role": r["role"],
            "phone": r["phone"],
            "mobile": r["mobile"],
            "birth_date": r["birth_date"],
            "hire_date": r["hire_date"],
            "is_active": bool(r["is_active"]),
            "id_number": r["id_number"]
        } for r in rows]
    })

@app.route("/api/staff", methods=["POST"])
def create_staff():
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO staff (staff_id, staff_code, name, department, store, role, mobile,
                               birth_date, hire_date, is_active, id_number, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime("now", "localtime"), datetime("now", "localtime"))
        """, (
            data.get("staff_code"),
            data.get("staff_code"),
            data.get("name"),
            data.get("department"),
            data.get("store"),
            data.get("role"),
            data.get("mobile"),
            data.get("birth_date"),
            data.get("hire_date"),
            1 if data.get("is_active") else 0,
            data.get("id_number")
        ))

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "員工新增成功"})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/staff/<staff_id>", methods=["PUT"])
def update_staff(staff_id):
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE staff
            SET staff_code = ?, name = ?, department = ?, store = ?, role = ?, mobile = ?,
                birth_date = ?, hire_date = ?, is_active = ?, id_number = ?, updated_at = datetime("now", "localtime")
            WHERE staff_id = ?
        """, (
            data.get("staff_code"),
            data.get("name"),
            data.get("department"),
            data.get("store"),
            data.get("role"),
            data.get("mobile"),
            data.get("birth_date"),
            data.get("hire_date"),
            1 if data.get("is_active") else 0,
            data.get("id_number"),
            staff_id
        ))

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "員工更新成功"})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/staff/<staff_id>", methods=["DELETE"])
def delete_staff(staff_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM staff WHERE staff_id = ?", (staff_id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "員工刪除成功"})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/staff/<staff_id>/password", methods=["PUT"])
def update_staff_password(staff_id):
    """更新員工密碼"""
    data = request.get_json()
    new_password = data.get("password")

    if not new_password or len(new_password) < 4:
        return jsonify({"success": False, "error": "密碼長度至少需要4個字符"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE staff
            SET password = ?, updated_at = datetime("now", "localtime")
            WHERE staff_id = ?
        """, (new_password, staff_id))

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "密碼更新成功"})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================
# API: 系統公告
# ============================================

@app.route("/api/system/announcements")
def get_system_announcements():
    """取得系統公告列表"""
    from datetime import datetime
    conn = get_db_connection()
    cursor = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        SELECT id, title, content, level, is_pinned, created_at
        FROM system_announcements
        WHERE is_active = 1
          AND (expires_at IS NULL OR datetime(expires_at) > datetime(?))
        ORDER BY is_pinned DESC, created_at DESC
    """, (now,))

    rows = cursor.fetchall()
    conn.close()

    return jsonify({
        "success": True,
        "items": [{
            "id": r["id"],
            "title": r["title"],
            "content": r["content"],
            "level": r["level"],
            "is_pinned": bool(r["is_pinned"]),
            "created_at": r["created_at"]
        } for r in rows]
    })

@app.route("/api/system/announcements", methods=["POST"])
def create_system_announcement():
    """新增系統公告（管理員）"""
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO system_announcements
            (title, content, level, is_pinned, expires_at, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime("now", "localtime"))
        """, (
            data.get("title"),
            data.get("content"),
            data.get("level", "info"),
            1 if data.get("is_pinned") else 0,
            data.get("expires_at"),
            data.get("created_by", "admin")
        ))

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "公告新增成功"})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/system/announcements/<int:announcement_id>", methods=["PUT"])
def update_system_announcement(announcement_id):
    """更新系統公告"""
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE system_announcements
            SET title = ?, content = ?, level = ?, is_pinned = ?,
                is_active = ?, expires_at = ?
            WHERE id = ?
        """, (
            data.get("title"),
            data.get("content"),
            data.get("level"),
            1 if data.get("is_pinned") else 0,
            1 if data.get("is_active", True) else 0,
            data.get("expires_at"),
            announcement_id
        ))

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "公告更新成功"})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/system/announcements/<int:announcement_id>", methods=["DELETE"])
def delete_system_announcement(announcement_id):
    """刪除系統公告（軟刪除：設為 is_active=0）"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE system_announcements
            SET is_active = 0
            WHERE id = ?
        """, (announcement_id,))

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "公告已關閉"})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/system/announcements/all")
def get_all_system_announcements():
    """取得所有系統公告（管理員用，包含已停用）"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, content, level, is_active, is_pinned, created_at, expires_at
        FROM system_announcements
        ORDER BY is_pinned DESC, created_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return jsonify({
        "success": True,
        "items": [{
            "id": r["id"],
            "title": r["title"],
            "content": r["content"],
            "level": r["level"],
            "is_active": bool(r["is_active"]),
            "is_pinned": bool(r["is_pinned"]),
            "created_at": r["created_at"],
            "expires_at": r["expires_at"]
        } for r in rows]
    })

# ============================================
# Telegram Bot 設定
# ============================================
TELEGRAM_BOT_TOKEN = "8623161623:AAGWlwGjp0Vf3bzpiVgLltQFbcGFY4kpFxo"
TELEGRAM_CHAT_ID = "8545239755"  # 老闆個人（請購通知）
TELEGRAM_ACCOUNTANT_CHAT_ID = "8203016237"  # 會計個人（調撥通知）

def send_telegram_notification(message, chat_id=None, notification_type='general',
                                related_record_id=None, related_record_type=None):
    """發送 Telegram 通知並記錄到資料庫"""
    chat_id = chat_id or TELEGRAM_CHAT_ID
    recipient_name = '老闆' if chat_id == TELEGRAM_CHAT_ID else ('會計' if chat_id == TELEGRAM_ACCOUNTANT_CHAT_ID else '未知')
    message_preview = message[:50] + '...' if len(message) > 50 else message

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=payload, timeout=5)
        result = response.json()

        # 記錄到資料庫
        status = 'success' if result.get('ok') else 'failed'
        error_msg = result.get('description') if not result.get('ok') else None

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO notification_logs
            (notification_type, recipient_chat_id, recipient_name, message_preview,
             status, error_message, related_record_id, related_record_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (notification_type, str(chat_id), recipient_name, message_preview,
              status, error_msg, related_record_id, related_record_type))
        conn.commit()
        conn.close()

        return result
    except Exception as e:
        error_msg = str(e)
        print(f"Telegram 通知發送失敗: {error_msg}")

        # 記錄失敗到資料庫
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO notification_logs
                (notification_type, recipient_chat_id, recipient_name, message_preview,
                 status, error_message, related_record_id, related_record_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (notification_type, str(chat_id), recipient_name, message_preview,
                  'failed', error_msg, related_record_id, related_record_type))
            conn.commit()
            conn.close()
        except:
            pass

        return None

# ============================================
# Email 通知功能
# ============================================
def send_email_alert(subject, body):
    """發送 Email 告警"""
    try:
        email_host = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
        email_port = int(os.getenv('EMAIL_PORT', 587))
        email_user = os.getenv('EMAIL_USER')
        email_password = os.getenv('EMAIL_PASSWORD')
        email_to = os.getenv('EMAIL_TO', email_user)

        if not email_user or not email_password:
            print("[EMAIL] 未設定 Email 帳號密碼，跳過發送")
            return False

        msg = MIMEMultipart()
        msg['From'] = email_user
        msg['To'] = email_to
        msg['Subject'] = f"[電腦舖系統告警] {subject}"

        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2 style="color: #d32f2f;">⚠️ 系統告警通知</h2>
            <div style="background: #f5f5f5; padding: 15px; border-radius: 5px;">
                {body}
            </div>
            <p style="color: #666; font-size: 0.9em;">
                時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
                系統：電腦舖營運系統
            </p>
        </body>
        </html>
        """

        msg.attach(MIMEText(body_html, 'html'))

        server = smtplib.SMTP(email_host, email_port)
        server.starttls()
        server.login(email_user, email_password)
        server.send_message(msg)
        server.quit()

        print(f"[EMAIL] 告警郵件已發送: {subject}")
        return True
    except Exception as e:
        print(f"[EMAIL] 發送失敗: {e}")
        return False


# ============================================
# API: 客戶建檔
# ============================================

# API: 取得下一個客戶編號
@app.route('/api/customer/next-id')
def get_next_customer_id():
    """根據門市前綴產生下一個客戶編號"""
    prefix = request.args.get('prefix', 'SA')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 查詢該前綴的最大編號
        cursor.execute("""
            SELECT customer_id FROM customers
            WHERE customer_id LIKE ?
            ORDER BY customer_id DESC LIMIT 1
        """, (prefix + '-%',))

        row = cursor.fetchone()
        if row:
            # 解析最後編號
            last_id = row['customer_id']
            try:
                last_num = int(last_id.split('-')[1])
                next_num = last_num + 1
            except:
                next_num = 1
        else:
            next_num = 1

        # 格式化編號（5碼數字）
        customer_id = f"{prefix}-{next_num:05d}"

        return jsonify({'success': True, 'customer_id': customer_id})
    except Exception as e:
        print(f"[ERROR] 產生客戶編號失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


# API: 檢查客戶是否重複
@app.route('/api/customer/check')
def check_customer_exists():
    """檢查手機或電話是否已存在"""
    mobile = request.args.get('mobile', '')
    phone = request.args.get('phone', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if mobile:
            cursor.execute("""
                SELECT customer_id, short_name FROM customers
                WHERE mobile = ? LIMIT 1
            """, (mobile,))
        elif phone:
            cursor.execute("""
                SELECT customer_id, short_name FROM customers
                WHERE phone1 = ? LIMIT 1
            """, (phone,))
        else:
            return jsonify({'exists': False})

        row = cursor.fetchone()
        if row:
            return jsonify({
                'exists': True,
                'customer_id': row['customer_id'],
                'short_name': row['short_name']
            })
        else:
            return jsonify({'exists': False})
    except Exception as e:
        print(f"[ERROR] 檢查客戶失敗: {e}")
        return jsonify({'exists': False, 'error': str(e)}), 500
    finally:
        conn.close()


# API: 建立客戶
@app.route('/api/customer/create', methods=['POST'])
def create_customer():
    """建立新客戶"""
    data = request.get_json()

    # 驗證必填欄位
    customer_id = data.get('customer_id', '').strip()
    short_name = data.get('short_name', '').strip()
    mobile = data.get('mobile', '').strip()

    if not customer_id or not short_name or not mobile:
        return jsonify({'success': False, 'message': '缺少必填欄位'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 再次驗證手機是否重複
        cursor.execute("SELECT 1 FROM customers WHERE mobile = ? LIMIT 1", (mobile,))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': '此手機號碼已存在'}), 409

        # 插入客戶資料
        cursor.execute("""
            INSERT INTO customers (
                customer_id, short_name, phone1, mobile, contact,
                tax_id, company_address, delivery_address, payment_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            customer_id,
            short_name,
            data.get('phone1', ''),
            mobile,
            data.get('contact', ''),
            data.get('tax_id', ''),
            data.get('company_address', ''),
            data.get('delivery_address', ''),
            data.get('payment_type', '')
        ))

        conn.commit()
        return jsonify({'success': True, 'customer_id': customer_id})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': '客戶編號已存在'}), 409
    except Exception as e:
        print(f"[ERROR] 建立客戶失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


# ============================================
# API: 產生對外銷貨單號
# ============================================

@app.route('/api/sales/next-invoice-no')
def get_next_sales_invoice_no():
    """
    產生下一個對外銷貨單號
    格式：門市代碼-YYYYMMDD-序號
    例如：FY-20260306-001
    """
    store_code = request.args.get('store', 'FY')  # 預設豐原
    date_str = request.args.get('date', datetime.now().strftime('%Y%m%d'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 查詢該門市該日期最後的序號
        prefix = f"{store_code}-{date_str}-"
        cursor.execute("""
            SELECT sales_invoice_no FROM sales_history
            WHERE sales_invoice_no LIKE ?
            ORDER BY sales_invoice_no DESC LIMIT 1
        """, (prefix + '%',))

        row = cursor.fetchone()
        if row and row['sales_invoice_no']:
            try:
                # 解析最後序號
                last_seq = int(row['sales_invoice_no'].split('-')[-1])
                next_seq = last_seq + 1
            except:
                next_seq = 1
        else:
            next_seq = 1

        # 格式化單號
        invoice_no = f"{store_code}-{date_str}-{next_seq:03d}"

        return jsonify({
            'success': True,
            'invoice_no': invoice_no,
            'store_code': store_code,
            'date': date_str,
            'sequence': next_seq
        })
    except Exception as e:
        print(f"[ERROR] 產生銷貨單號失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


# ============================================
# API: 廠商建檔
# ============================================

@app.route('/api/supplier/next-id')
def get_next_supplier_id():
    """產生下一個廠商編號"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 查詢最大的廠商編號
        cursor.execute("""
            SELECT supplier_id FROM suppliers
            WHERE supplier_id LIKE 'SUP-%'
            ORDER BY supplier_id DESC LIMIT 1
        """)

        row = cursor.fetchone()
        if row:
            try:
                last_num = int(row['supplier_id'].split('-')[1])
                next_num = last_num + 1
            except:
                next_num = 1
        else:
            next_num = 1

        supplier_id = f"SUP-{next_num:05d}"

        return jsonify({'success': True, 'supplier_id': supplier_id})
    except Exception as e:
        print(f"[ERROR] 產生廠商編號失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


@app.route('/api/supplier/create', methods=['POST'])
def create_supplier():
    """建立新廠商"""
    data = request.get_json()

    supplier_id = data.get('supplier_id', '').strip()
    supplier_name = data.get('supplier_name', '').strip()
    contact_person = data.get('contact_person', '').strip()

    if not supplier_id or not supplier_name or not contact_person:
        return jsonify({'success': False, 'message': '缺少必填欄位'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO suppliers (
                supplier_id, supplier_name, short_name, tax_id, contact_person,
                phone, mobile, email, address, payment_terms,
                bank_name, bank_account, remark, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            supplier_id,
            supplier_name,
            data.get('short_name', ''),
            data.get('tax_id', ''),
            contact_person,
            data.get('phone', ''),
            data.get('mobile', ''),
            data.get('email', ''),
            data.get('address', ''),
            data.get('payment_terms', ''),
            data.get('bank_name', ''),
            data.get('bank_account', ''),
            data.get('remark', ''),
            data.get('created_by', '')
        ))

        conn.commit()
        return jsonify({'success': True, 'supplier_id': supplier_id})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': '廠商編號已存在'}), 409
    except Exception as e:
        print(f"[ERROR] 建立廠商失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


# ============================================
# API: 產品建檔
# ============================================

@app.route('/api/product/categories')
def get_product_categories():
    """取得產品大分類列表"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT category_code as code, category_name as name
            FROM product_categories
            WHERE status = '啟用'
            ORDER BY category_code
        """)
        rows = cursor.fetchall()

        categories = [{'code': r['code'], 'name': r['name']} for r in rows]

        return jsonify({'success': True, 'categories': categories})
    except Exception as e:
        print(f"[ERROR] 取得產品分類失敗: {e}")
        return jsonify({'success': False, 'categories': []}), 500
    finally:
        conn.close()


@app.route('/api/product/subcategories')
def get_product_subcategories():
    """取得產品小分類（廠牌）列表"""
    main_code = request.args.get('main', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 從現有產品中統計小分類
        cursor.execute("""
            SELECT DISTINCT SUBSTR(product_code, 4, 2) as code
            FROM products
            WHERE product_code LIKE ?
            ORDER BY code
        """, (f"{main_code}-%",))

        rows = cursor.fetchall()
        subcategories = [{'code': r['code'], 'name': r['code']} for r in rows if r['code']]

        return jsonify({'success': True, 'subcategories': subcategories})
    except Exception as e:
        print(f"[ERROR] 取得小分類失敗: {e}")
        return jsonify({'success': False, 'subcategories': []}), 500
    finally:
        conn.close()


@app.route('/api/product/next-code')
def get_next_product_code():
    """產生下一個產品編號"""
    main_code = request.args.get('main', '')
    sub_code = request.args.get('sub', '')

    if not main_code or not sub_code:
        return jsonify({'success': False, 'message': '缺少分類資訊'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 查詢該分類最大序號
        prefix = f"{main_code}-{sub_code}-"
        cursor.execute("""
            SELECT product_code FROM products
            WHERE product_code LIKE ?
            ORDER BY product_code DESC LIMIT 1
        """, (prefix + '%',))

        row = cursor.fetchone()
        if row:
            try:
                last_seq = int(row['product_code'].split('-')[-1])
                next_seq = last_seq + 1
            except:
                next_seq = 1
        else:
            next_seq = 1

        product_code = f"{main_code}-{sub_code}-{next_seq:04d}"

        return jsonify({
            'success': True,
            'product_code': product_code,
            'sequence': next_seq
        })
    except Exception as e:
        print(f"[ERROR] 產生產品編號失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


# ============================================
# 進貨管理 API
# ============================================

@app.route('/api/suppliers/search')
def search_suppliers():
    """搜尋廠商"""
    keyword = request.args.get('keyword', '').strip()

    if not keyword:
        return jsonify({'success': True, 'suppliers': []})

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT DISTINCT supplier_name as supplier_name
            FROM purchase_history
            WHERE supplier_name LIKE ?
            ORDER BY supplier_name
            LIMIT 10
        """, (f'%{keyword}%',))

        rows = cursor.fetchall()
        suppliers = [{'supplier_name': r['supplier_name']} for r in rows]

        return jsonify({'success': True, 'suppliers': suppliers})
    except Exception as e:
        print(f"[ERROR] 搜尋廠商失敗: {e}")
        return jsonify({'success': False, 'suppliers': []}), 500
    finally:
        conn.close()


@app.route('/api/supplier/info')
def get_supplier_info():
    """取得廠商資訊（由名稱查詢）"""
    name = request.args.get('name', '').strip()

    if not name:
        return jsonify({'success': False, 'message': '缺少廠商名稱'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 先從 suppliers 表查詢
        cursor.execute("""
            SELECT supplier_id, supplier_name, contact_person, phone, email, address
            FROM suppliers
            WHERE supplier_name = ?
            LIMIT 1
        """, (name,))

        row = cursor.fetchone()

        if row:
            supplier = {
                'supplier_id': row['supplier_id'],
                'supplier_name': row['supplier_name'],
                'contact_person': row['contact_person'],
                'phone': row['phone'],
                'email': row['email'],
                'address': row['address']
            }
            return jsonify({'success': True, 'supplier': supplier})
        else:
            # 如果找不到，回傳名稱作為 ID（舊資料相容）
            return jsonify({
                'success': True,
                'supplier': {
                    'supplier_id': name,
                    'supplier_name': name
                }
            })
    except Exception as e:
        print(f"[ERROR] 取得廠商資訊失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


@app.route('/api/purchase/next-order-no')
def get_next_purchase_order_no():
    """產生下一個進貨單號"""
    today = datetime.now().strftime('%Y%m%d')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 查詢當日最大序號
        cursor.execute("""
            SELECT order_no FROM purchase_history
            WHERE order_no LIKE ?
            ORDER BY order_no DESC LIMIT 1
        """, (f'PO-{today}%',))

        row = cursor.fetchone()
        if row:
            try:
                last_seq = int(row['order_no'].split('-')[-1])
                next_seq = last_seq + 1
            except:
                next_seq = 1
        else:
            next_seq = 1

        order_no = f"PO-{today}-{next_seq:03d}"

        return jsonify({
            'success': True,
            'order_no': order_no
        })
    except Exception as e:
        print(f"[ERROR] 產生進貨單號失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


@app.route('/api/purchase/create', methods=['POST'])
def create_purchase_order():
    """建立進貨單"""
    data = request.get_json()

    order_no = data.get('order_no')
    date = data.get('date')
    supplier_name = data.get('supplier_name')
    warehouse = data.get('warehouse')
    invoice_number = data.get('invoice_number')
    items = data.get('items', [])
    created_by = data.get('created_by', '')

    if not all([order_no, date, supplier_name, warehouse]):
        return jsonify({'success': False, 'message': '缺少必填欄位'}), 400

    if not items:
        return jsonify({'success': False, 'message': '請至少輸入一筆產品明細'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 插入每筆明細
        for item in items:
            cursor.execute("""
                INSERT INTO purchase_history
                (order_no, invoice_number, date, supplier_name, warehouse, product_code, product_name, quantity, price, amount, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_no,
                invoice_number,
                date,
                supplier_name,
                warehouse,
                item.get('product_code', ''),
                item['product_name'],
                item['quantity'],
                item['price'],
                item['amount'],
                created_by
            ))

        conn.commit()

        return jsonify({
            'success': True,
            'message': f'進貨單 {order_no} 建立成功',
            'order_no': order_no,
            'item_count': len(items)
        })
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] 建立進貨單失敗: {e}")
        return jsonify({'success': False, 'message': f'系統錯誤: {str(e)}'}), 500
    finally:
        conn.close()


@app.route('/api/product/category', methods=['POST'])
def create_product_category():
    """新增產品大分類"""
    data = request.get_json()
    code = data.get('code', '').upper().strip()
    name = data.get('name', '').strip()

    if not code or len(code) != 2:
        return jsonify({'success': False, 'message': '分類代碼必須為2碼英文'}), 400
    if not name:
        return jsonify({'success': False, 'message': '請輸入分類名稱'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO product_categories (category_code, category_name, created_by)
            VALUES (?, ?, ?)
        """, (code, name, data.get('created_by', '')))

        conn.commit()
        return jsonify({'success': True, 'code': code, 'name': name})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': '分類代碼已存在'}), 409
    except Exception as e:
        print(f"[ERROR] 新增分類失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


@app.route('/api/product/create', methods=['POST'])
def create_product():
    """建立新產品"""
    data = request.get_json()

    product_code = data.get('product_code', '').strip()
    product_name = data.get('product_name', '').strip()

    if not product_code or not product_name:
        return jsonify({'success': False, 'message': '缺少必填欄位'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO products (
                product_code, product_name, category, unit,
                created_by, last_seen_at
            ) VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))
        """, (
            product_code,
            product_name,
            data.get('category', ''),
            data.get('unit', '個'),
            data.get('created_by', '')
        ))

        conn.commit()
        return jsonify({'success': True, 'product_code': product_code})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': '產品編號已存在'}), 409
    except Exception as e:
        print(f"[ERROR] 建立產品失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


@app.route('/api/product/search')
def search_product_single():
    """搜尋產品"""
    keyword = request.args.get('keyword', '').strip()

    if not keyword or len(keyword) < 2:
        return jsonify({'success': False, 'products': []})

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT product_code, product_name
            FROM products
            WHERE product_name LIKE ? OR product_code LIKE ?
            ORDER BY product_name
            LIMIT 10
        """, (f'%{keyword}%', f'%{keyword}%'))

        rows = cursor.fetchall()
        products = [{'product_code': r['product_code'], 'product_name': r['product_name']} for r in rows]

        return jsonify({'success': True, 'products': products})
    except Exception as e:
        print(f"[ERROR] 搜尋產品失敗: {e}")
        return jsonify({'success': False, 'products': []}), 500
    finally:
        conn.close()


@app.route('/api/staff/code')
def get_staff_code():
    """取得員工編號（依姓名查詢）"""
    name = request.args.get('name', '').strip()

    if not name:
        return jsonify({'success': False, 'message': '缺少姓名'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT staff_code
            FROM staff_passwords
            WHERE name = ?
            LIMIT 1
        """, (name,))

        row = cursor.fetchone()
        if row:
            return jsonify({'success': True, 'code': row['staff_code']})
        else:
            return jsonify({'success': False, 'code': None})
    except Exception as e:
        print(f"[ERROR] 取得員工編號失敗: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/supplier/next-code')
def get_next_supplier_code():
    """產生下一個廠商編號"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 找出最大的廠商編號序號
        cursor.execute("""
            SELECT supplier_id
            FROM suppliers
            WHERE supplier_id LIKE 'SUP-%'
            ORDER BY supplier_id DESC
            LIMIT 1
        """)

        row = cursor.fetchone()
        if row:
            # 解析現有編號，產生下一個序號
            parts = row['supplier_id'].split('-')
            if len(parts) >= 2:
                try:
                    current_num = int(parts[1])
                    next_num = current_num + 1
                except ValueError:
                    next_num = 1
            else:
                next_num = 1
        else:
            next_num = 1

        # 格式化序號為4碼
        supplier_code = f"SUP-{next_num:04d}"

        return jsonify({'success': True, 'supplier_code': supplier_code})
    except Exception as e:
        print(f"[ERROR] 產生廠商編號失敗: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


# ============================================
# 庫存查詢 API
# ============================================

@app.route('/api/inventory/search')
def search_inventory():
    """搜尋庫存商品（僅查詢最新日期資料）"""
    query = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    warehouse = request.args.get('warehouse', '').strip()

    if not query or len(query) < 2:
        return jsonify({'success': False, 'products': []})

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 先取得最新報表日期
        cursor.execute("SELECT MAX(report_date) as latest_date FROM inventory")
        latest_date = cursor.fetchone()['latest_date']

        sql = """
            SELECT DISTINCT i.product_id, i.item_spec
            FROM inventory i
            WHERE i.report_date = ?
            AND (i.item_spec LIKE ? OR i.product_id LIKE ?)
        """
        params = [latest_date, f'%{query}%', f'%{query}%']

        if category:
            sql += " AND i.product_id LIKE ?"
            params.append(f'{category}%')

        if warehouse:
            sql += " AND i.warehouse = ?"
            params.append(warehouse)

        sql += " ORDER BY i.item_spec LIMIT 20"

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        products = [{
            'product_id': r['product_id'],
            'item_spec': r['item_spec']
        } for r in rows]

        return jsonify({'success': True, 'products': products, 'report_date': latest_date})
    except Exception as e:
        print(f"[ERROR] 搜尋庫存失敗: {e}")
        return jsonify({'success': False, 'products': [], 'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/inventory/product/<product_id>')
def get_inventory_by_product(product_id):
    """取得指定商品的庫存明細（查詢全域最新日期的資料）"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 取得全域最新報表日期
        cursor.execute("SELECT MAX(report_date) as latest_date FROM inventory")
        result = cursor.fetchone()
        latest_date = result['latest_date'] if result else None
        
        if not latest_date:
            return jsonify({'success': False, 'message': '無庫存資料'}), 404

        # 取得商品基本資訊（從最新日期的資料）
        cursor.execute("""
            SELECT DISTINCT product_id, item_spec, unit
            FROM inventory
            WHERE product_id = ? AND report_date = ?
            LIMIT 1
        """, (product_id, latest_date))

        product_row = cursor.fetchone()
        if not product_row:
            # 商品在最新日期沒有庫存資料，回傳空庫存
            # 先嘗試取得商品基本資訊（從任何日期）
            cursor.execute("""
                SELECT DISTINCT product_id, item_spec, unit
                FROM inventory
                WHERE product_id = ?
                LIMIT 1
            """, (product_id,))
            product_row = cursor.fetchone()
            
            if not product_row:
                return jsonify({'success': False, 'message': '找不到商品'}), 404
            
            # 回傳空庫存（商品存在但最新日期無庫存）
            return jsonify({
                'success': True,
                'product': {
                    'product_id': product_row['product_id'],
                    'item_spec': product_row['item_spec'],
                    'unit': product_row['unit']
                },
                'inventory': [],
                'report_date': latest_date
            })

        # 取得各倉庫庫存（只顯示庫存 > 0 的倉庫）
        cursor.execute("""
            SELECT warehouse, wh_type, stock_quantity, unit_cost, total_cost
            FROM inventory
            WHERE product_id = ? AND report_date = ? AND stock_quantity > 0
            ORDER BY warehouse
        """, (product_id, latest_date))

        inventory_rows = cursor.fetchall()

        return jsonify({
            'success': True,
            'product': {
                'product_id': product_row['product_id'],
                'item_spec': product_row['item_spec'],
                'unit': product_row['unit']
            },
            'inventory': [{
                'warehouse': r['warehouse'],
                'wh_type': r['wh_type'],
                'stock_quantity': r['stock_quantity'],
                'unit_cost': r['unit_cost'],
                'total_cost': r['total_cost']
            } for r in inventory_rows],
            'report_date': latest_date
        })
    except Exception as e:
        print(f"[ERROR] 取得庫存明細失敗: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/inventory/list')
def list_inventory():
    """根據條件列出庫存（僅查詢最新日期資料）"""
    category = request.args.get('category', '').strip()
    warehouse = request.args.get('warehouse', '').strip()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 先取得最新報表日期
        cursor.execute("SELECT MAX(report_date) as latest_date FROM inventory")
        latest_date = cursor.fetchone()['latest_date']

        sql = """
            SELECT i.product_id, i.item_spec, i.warehouse, i.stock_quantity
            FROM inventory i
            WHERE i.report_date = ?
        """
        params = [latest_date]

        if category:
            sql += " AND i.product_id LIKE ?"
            params.append(f'{category}%')

        if warehouse:
            sql += " AND i.warehouse = ?"
            params.append(warehouse)

        sql += " ORDER BY i.item_spec, i.warehouse LIMIT 100"

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        items = [{
            'product_id': r['product_id'],
            'item_spec': r['item_spec'],
            'warehouse': r['warehouse'],
            'stock_quantity': r['stock_quantity']
        } for r in rows]

        return jsonify({
            'success': True,
            'items': items,
            'report_date': latest_date
        })
    except Exception as e:
        print(f"[ERROR] 列出庫存失敗: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


# ============================================
# API: 資料列表查詢（分頁）
# ============================================

@app.route('/api/suppliers/list')
def get_suppliers_list():
    """取得廠商列表（分頁）"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    search = request.args.get('search', '').strip()

    offset = (page - 1) * limit

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 計算總筆數
        count_sql = "SELECT COUNT(*) as total FROM suppliers WHERE 1=1"
        count_params = []
        if search:
            count_sql += " AND (supplier_name LIKE ? OR short_name LIKE ? OR supplier_id LIKE ?)"
            count_params = [f'%{search}%', f'%{search}%', f'%{search}%']
        cursor.execute(count_sql, count_params)
        total = cursor.fetchone()['total']

        # 查詢資料
        sql = """
            SELECT supplier_id, supplier_name, short_name, tax_id, contact_person,
                   phone, mobile, email, address, payment_terms, status,
                   created_at, created_by
            FROM suppliers
            WHERE 1=1
        """
        params = []
        if search:
            sql += " AND (supplier_name LIKE ? OR short_name LIKE ? OR supplier_id LIKE ?)"
            params = [f'%{search}%', f'%{search}%', f'%{search}%']
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        suppliers = [{
            'supplier_id': r['supplier_id'],
            'supplier_name': r['supplier_name'],
            'short_name': r['short_name'],
            'tax_id': r['tax_id'],
            'contact_person': r['contact_person'],
            'phone': r['phone'],
            'mobile': r['mobile'],
            'email': r['email'],
            'address': r['address'],
            'payment_terms': r['payment_terms'],
            'status': r['status'],
            'created_at': r['created_at'],
            'created_by': r['created_by']
        } for r in rows]

        return jsonify({
            'success': True,
            'suppliers': suppliers,
            'total': total,
            'page': page,
            'limit': limit,
            'total_pages': (total + limit - 1) // limit
        })
    except Exception as e:
        print(f"[ERROR] 取得廠商列表失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


@app.route('/api/supplier/update', methods=['POST'])
def update_supplier():
    """更新廠商資料"""
    data = request.get_json()
    supplier_id = data.get('supplier_id', '').strip()

    if not supplier_id:
        return jsonify({'success': False, 'message': '缺少廠商編號'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE suppliers SET
                supplier_name = ?,
                short_name = ?,
                tax_id = ?,
                contact_person = ?,
                phone = ?,
                mobile = ?,
                email = ?,
                address = ?,
                payment_terms = ?,
                bank_name = ?,
                bank_account = ?,
                remark = ?,
                status = ?,
                updated_at = datetime('now', 'localtime'),
                updated_by = ?
            WHERE supplier_id = ?
        """, (
            data.get('supplier_name', ''),
            data.get('short_name', ''),
            data.get('tax_id', ''),
            data.get('contact_person', ''),
            data.get('phone', ''),
            data.get('mobile', ''),
            data.get('email', ''),
            data.get('address', ''),
            data.get('payment_terms', ''),
            data.get('bank_name', ''),
            data.get('bank_account', ''),
            data.get('remark', ''),
            data.get('status', '啟用'),
            data.get('updated_by', ''),
            supplier_id
        ))

        conn.commit()
        return jsonify({'success': True, 'message': '廠商資料更新成功'})
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] 更新廠商失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


@app.route('/api/products/list')
def get_products_list():
    """取得產品列表（分頁）"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    search = request.args.get('search', '').strip()

    offset = (page - 1) * limit

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 計算總筆數
        count_sql = "SELECT COUNT(*) as total FROM products WHERE 1=1"
        count_params = []
        if search:
            count_sql += " AND (product_name LIKE ? OR product_code LIKE ?)"
            count_params = [f'%{search}%', f'%{search}%']
        cursor.execute(count_sql, count_params)
        total = cursor.fetchone()['total']

        # 查詢資料
        sql = """
            SELECT product_code, product_name, category, unit, created_at, created_by
            FROM products
            WHERE 1=1
        """
        params = []
        if search:
            sql += " AND (product_name LIKE ? OR product_code LIKE ?)"
            params = [f'%{search}%', f'%{search}%']
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        products = [{
            'product_code': r['product_code'],
            'product_name': r['product_name'],
            'category': r['category'],
            'unit': r['unit'],
            'created_at': r['created_at'],
            'created_by': r['created_by']
        } for r in rows]

        return jsonify({
            'success': True,
            'products': products,
            'total': total,
            'page': page,
            'limit': limit,
            'total_pages': (total + limit - 1) // limit
        })
    except Exception as e:
        print(f"[ERROR] 取得產品列表失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


@app.route('/api/product/update', methods=['POST'])
def update_product():
    """更新產品資料"""
    data = request.get_json()
    product_code = data.get('product_code', '').strip()

    if not product_code:
        return jsonify({'success': False, 'message': '缺少產品編號'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE products SET
                product_name = ?,
                category = ?,
                unit = ?,
                updated_at = datetime('now', 'localtime')
            WHERE product_code = ?
        """, (
            data.get('product_name', ''),
            data.get('category', ''),
            data.get('unit', '個'),
            product_code
        ))

        conn.commit()
        return jsonify({'success': True, 'message': '產品資料更新成功'})
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] 更新產品失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


@app.route('/api/customers/list')
def get_customers_list():
    """取得客戶列表（分頁）"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    search = request.args.get('search', '').strip()

    offset = (page - 1) * limit

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 計算總筆數
        count_sql = "SELECT COUNT(*) as total FROM customers WHERE 1=1"
        count_params = []
        if search:
            count_sql += " AND (short_name LIKE ? OR customer_id LIKE ? OR mobile LIKE ?)"
            count_params = [f'%{search}%', f'%{search}%', f'%{search}%']
        cursor.execute(count_sql, count_params)
        total = cursor.fetchone()['total']

        # 查詢資料
        sql = """
            SELECT customer_id, short_name, mobile, phone1, contact, tax_id,
                   company_address, delivery_address, payment_type, created_by
            FROM customers
            WHERE 1=1
        """
        params = []
        if search:
            sql += " AND (short_name LIKE ? OR customer_id LIKE ? OR mobile LIKE ?)"
            params = [f'%{search}%', f'%{search}%', f'%{search}%']
        sql += " ORDER BY customer_id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        customers = [{
            'customer_id': r['customer_id'],
            'short_name': r['short_name'],
            'mobile': r['mobile'],
            'phone1': r['phone1'],
            'contact': r['contact'],
            'tax_id': r['tax_id'],
            'company_address': r['company_address'],
            'delivery_address': r['delivery_address'],
            'payment_type': r['payment_type'],
            'created_by': r['created_by']
        } for r in rows]

        return jsonify({
            'success': True,
            'customers': customers,
            'total': total,
            'page': page,
            'limit': limit,
            'total_pages': (total + limit - 1) // limit
        })
    except Exception as e:
        print(f"[ERROR] 取得客戶列表失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


@app.route('/api/customer/update', methods=['POST'])
def update_customer():
    """更新客戶資料"""
    data = request.get_json()
    customer_id = data.get('customer_id', '').strip()

    if not customer_id:
        return jsonify({'success': False, 'message': '缺少客戶編號'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE customers SET
                short_name = ?,
                mobile = ?,
                phone1 = ?,
                contact = ?,
                tax_id = ?,
                company_address = ?,
                delivery_address = ?,
                payment_type = ?,
                updated_at = datetime('now', 'localtime')
            WHERE customer_id = ?
        """, (
            data.get('short_name', ''),
            data.get('mobile', ''),
            data.get('phone1', ''),
            data.get('contact', ''),
            data.get('tax_id', ''),
            data.get('company_address', ''),
            data.get('delivery_address', ''),
            data.get('payment_type', ''),
            customer_id
        ))

        conn.commit()
        return jsonify({'success': True, 'message': '客戶資料更新成功'})
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] 更新客戶失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


@app.route('/api/purchases/list')
def get_purchases_list():
    """取得進貨單列表（分頁）"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    search = request.args.get('search', '').strip()

    offset = (page - 1) * limit

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 計算總筆數（依訂單號分組）
        count_sql = """
            SELECT COUNT(DISTINCT order_no) as total
            FROM purchase_history
            WHERE 1=1
        """
        count_params = []
        if search:
            count_sql += " AND (order_no LIKE ? OR supplier_name LIKE ?)"
            count_params = [f'%{search}%', f'%{search}%']
        cursor.execute(count_sql, count_params)
        total = cursor.fetchone()['total']

        # 查詢訂單列表
        sql = """
            SELECT DISTINCT order_no, date, supplier_name, warehouse, invoice_number, created_by
            FROM purchase_history
            WHERE 1=1
        """
        params = []
        if search:
            sql += " AND (order_no LIKE ? OR supplier_name LIKE ?)"
            params = [f'%{search}%', f'%{search}%']
        sql += " ORDER BY date DESC, order_no DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(sql, params)
        orders = cursor.fetchall()

        # 查詢每張訂單的明細
        result = []
        for order in orders:
            cursor.execute("""
                SELECT product_code, product_name, quantity, price, amount
                FROM purchase_history
                WHERE order_no = ?
                ORDER BY id
            """, (order['order_no'],))
            items = cursor.fetchall()

            total_amount = sum(item['amount'] for item in items)

            result.append({
                'order_no': order['order_no'],
                'date': order['date'],
                'supplier_name': order['supplier_name'],
                'warehouse': order['warehouse'],
                'invoice_number': order['invoice_number'],
                'created_by': order['created_by'],
                'items': [{
                    'product_code': i['product_code'],
                    'product_name': i['product_name'],
                    'quantity': i['quantity'],
                    'price': i['price'],
                    'amount': i['amount']
                } for i in items],
                'total_amount': total_amount,
                'item_count': len(items)
            })

        return jsonify({
            'success': True,
            'purchases': result,
            'total': total,
            'page': page,
            'limit': limit,
            'total_pages': (total + limit - 1) // limit
        })
    except Exception as e:
        print(f"[ERROR] 取得進貨單列表失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


# ============================================
# API: 銷貨管理
# ============================================

@app.route('/api/sales/next-order-no')
def get_next_sales_order_no():
    """產生下一個銷貨單號"""
    store_code = request.args.get('store', 'FY')
    date_str = request.args.get('date', datetime.now().strftime('%Y%m%d'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        prefix = f"{store_code}-{date_str}-"
        cursor.execute("""
            SELECT sales_invoice_no FROM sales_history 
            WHERE sales_invoice_no LIKE ? 
            ORDER BY sales_invoice_no DESC LIMIT 1
        """, (prefix + '%',))
        
        row = cursor.fetchone()
        if row and row['sales_invoice_no']:
            try:
                last_seq = int(row['sales_invoice_no'].split('-')[-1])
                next_seq = last_seq + 1
            except:
                next_seq = 1
        else:
            next_seq = 1
        
        order_no = f"{store_code}-{date_str}-{next_seq:03d}"
        
        return jsonify({'success': True, 'order_no': order_no})
    except Exception as e:
        print(f"[ERROR] 產生銷貨單號失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


@app.route('/api/product/cost')
def get_product_cost():
    """取得產品當月平均成本"""
    product_code = request.args.get('code', '').strip()
    
    if not product_code:
        return jsonify({'success': False, 'cost': 0})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 取得當前年月
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        
        # 嘗試抓取當月進貨
        cursor.execute("""
            SELECT SUM(quantity) as total_qty, SUM(amount) as total_amount
            FROM purchase_history
            WHERE product_code = ? 
            AND strftime('%Y', date) = ? 
            AND strftime('%m', date) = ?
        """, (product_code, str(current_year), f"{current_month:02d}"))
        
        row = cursor.fetchone()
        
        # 若當月無進貨，遞推至上月
        if not row or not row['total_qty'] or row['total_qty'] == 0:
            # 遞推最多12個月
            for i in range(1, 13):
                check_month = current_month - i
                check_year = current_year
                if check_month <= 0:
                    check_month += 12
                    check_year -= 1
                
                cursor.execute("""
                    SELECT SUM(quantity) as total_qty, SUM(amount) as total_amount
                    FROM purchase_history
                    WHERE product_code = ? 
                    AND strftime('%Y', date) = ? 
                    AND strftime('%m', date) = ?
                """, (product_code, str(check_year), f"{check_month:02d}"))
                
                row = cursor.fetchone()
                if row and row['total_qty'] and row['total_qty'] > 0:
                    break
        
        if row and row['total_qty'] and row['total_qty'] > 0:
            avg_cost = row['total_amount'] / row['total_qty']
            return jsonify({'success': True, 'cost': round(avg_cost)})
        else:
            # 無進貨紀錄，回傳0
            return jsonify({'success': True, 'cost': 0})
    except Exception as e:
        print(f"[ERROR] 取得產品成本失敗: {e}")
        return jsonify({'success': False, 'cost': 0}), 500
    finally:
        conn.close()


@app.route('/api/sales/create', methods=['POST'])
def create_sales_order():
    """建立銷貨單"""
    data = request.get_json()
    
    sales_order_no = data.get('sales_order_no')
    date = data.get('date')
    customer_id = data.get('customer_id')
    customer_name = data.get('customer_name')
    invoice_no = data.get('invoice_no', '')
    salesperson = data.get('salesperson', '')
    salesperson_id = data.get('salesperson_id', '')
    items = data.get('items', [])
    payment_method = data.get('payment_method', '')
    due_date = data.get('due_date')
    total_amount = data.get('total_amount', 0)
    source_doc_no = data.get('source_doc_no', '')  # 來源訂單號
    deposit_amount = data.get('deposit_amount', 0)  # 已收訂金
    
    if not all([sales_order_no, date, customer_id, items, payment_method]):
        return jsonify({'success': False, 'message': '缺少必填欄位'}), 400
    
    # 檢查利潤
    for item in items:
        if item.get('profit', 0) <= 0:
            return jsonify({'success': False, 'message': '存在虧損品項，無法儲存'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 插入每筆明細
        for item in items:
            cursor.execute("""
                INSERT INTO sales_history 
                (sales_invoice_no, date, customer_id, customer_name, salesperson, salesperson_id,
                 product_code, product_name, quantity, price, amount, cost, profit, margin,
                 invoice_no, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
            """, (
                sales_order_no,
                date,
                customer_id,
                customer_name,
                salesperson,
                salesperson_id,
                item.get('product_code', ''),
                item['product_name'],
                item['quantity'],
                item['price'],
                item['amount'],
                item.get('cost', 0),
                item.get('profit', 0),
                item.get('margin', 0),
                invoice_no
            ))
        
        # 計算尾款（總金額 - 訂金）
        balance_amount = total_amount - deposit_amount
        
        # 寫入 finance_ledger 財務帳款表
        # 判斷是否為月結
        is_monthly = (payment_method == '月結')
        
        if is_monthly:
            # 月結：產生應收帳款（只針對尾款），未結清
            cursor.execute("""
                INSERT INTO finance_ledger 
                (record_type, target_id, target_name, reference_doc, total_amount, 
                 status, payment_method, due_date, cleared_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
            """, (
                'AR',  # 應收帳款
                customer_id,
                customer_name,
                sales_order_no,
                balance_amount,  # 只記錄尾款
                'UNPAID',  # 未結清
                None,  # 尚未付款
                due_date,
                None  # 尚未結清
            ))
        else:
            # 現金/匯款/刷卡/支票：直接結清（只針對尾款）
            cursor.execute("""
                INSERT INTO finance_ledger 
                (record_type, target_id, target_name, reference_doc, total_amount, 
                 status, payment_method, due_date, cleared_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
            """, (
                'AR',  # 應收帳款
                customer_id,
                customer_name,
                sales_order_no,
                balance_amount,  # 只記錄尾款
                'PAID',  # 已結清
                payment_method,
                None,  # 無到期日
                None
            ))
        
        # 如果有來源訂單，更新訂單狀態為已結案
        if source_doc_no:
            cursor.execute("""
                UPDATE sales_documents 
                SET status = 'CLOSED', updated_at = datetime('now', 'localtime')
                WHERE doc_no = ?
            """, (source_doc_no,))
        
        conn.commit()
        return jsonify({'success': True, 'message': f'銷貨單 {sales_order_no} 建立成功'})
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] 建立銷貨單失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


@app.route('/api/sales/list')
def get_sales_list():
    """取得銷貨單列表"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    search = request.args.get('search', '').strip()
    store = request.args.get('store', '').strip()
    
    offset = (page - 1) * limit
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 計算總筆數
        count_sql = """
            SELECT COUNT(DISTINCT sales_invoice_no) as total
            FROM sales_history
            WHERE sales_invoice_no IS NOT NULL AND sales_invoice_no != ''
        """
        count_params = []
        
        if search:
            count_sql += " AND (sales_invoice_no LIKE ? OR customer_name LIKE ?)"
            count_params = [f'%{search}%', f'%{search}%']
        
        if store:
            count_sql += " AND sales_invoice_no LIKE ?"
            count_params.append(f'{store}-%')
        
        cursor.execute(count_sql, count_params)
        total = cursor.fetchone()['total']
        
        # 查詢銷貨單列表
        sql = """
            SELECT DISTINCT sales_invoice_no, date, customer_name, salesperson
            FROM sales_history
            WHERE sales_invoice_no IS NOT NULL AND sales_invoice_no != ''
        """
        params = []
        
        if search:
            sql += " AND (sales_invoice_no LIKE ? OR customer_name LIKE ?)"
            params = [f'%{search}%', f'%{search}%']
        
        if store:
            sql += " AND sales_invoice_no LIKE ?"
            params.append(f'{store}-%')
        
        sql += " ORDER BY date DESC, sales_invoice_no DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(sql, params)
        orders = cursor.fetchall()
        
        # 查詢每張單的明細
        result = []
        for order in orders:
            cursor.execute("""
                SELECT product_code, product_name, quantity, price, amount, cost, profit, margin
                FROM sales_history
                WHERE sales_invoice_no = ?
                ORDER BY id
            """, (order['sales_invoice_no'],))
            items = cursor.fetchall()
            
            total_amount = sum(item['amount'] for item in items)
            
            result.append({
                'sales_order_no': order['sales_invoice_no'],
                'date': order['date'],
                'customer_name': order['customer_name'],
                'salesperson': order['salesperson'],
                'items': [{
                    'product_code': i['product_code'],
                    'product_name': i['product_name'],
                    'quantity': i['quantity'],
                    'price': i['price'],
                    'amount': i['amount'],
                    'cost': i['cost'],
                    'profit': i['profit'],
                    'margin': i['margin']
                } for i in items],
                'total_amount': total_amount,
                'item_count': len(items)
            })
        
        return jsonify({
            'success': True,
            'sales': result,
            'total': total,
            'page': page,
            'limit': limit,
            'total_pages': (total + limit - 1) // limit
        })
    except Exception as e:
        print(f"[ERROR] 取得銷貨單列表失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


@app.route('/api/sales/detail')
def get_sales_detail():
    """取得銷貨單詳情"""
    order_no = request.args.get('order_no', '').strip()
    
    if not order_no:
        return jsonify({'success': False, 'message': '缺少單號'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 查詢單據頭
        cursor.execute("""
            SELECT DISTINCT sales_invoice_no, date, customer_id, customer_name, 
                           salesperson, salesperson_id, invoice_no
            FROM sales_history
            WHERE sales_invoice_no = ?
            LIMIT 1
        """, (order_no,))
        
        header = cursor.fetchone()
        if not header:
            return jsonify({'success': False, 'message': '找不到銷貨單'}), 404
        
        # 查詢明細
        cursor.execute("""
            SELECT product_code, product_name, quantity, price, amount, cost, profit, margin
            FROM sales_history
            WHERE sales_invoice_no = ?
            ORDER BY id
        """, (order_no,))
        items = cursor.fetchall()
        
        total_amount = sum(item['amount'] for item in items)
        
        return jsonify({
            'success': True,
            'sale': {
                'sales_order_no': header['sales_invoice_no'],
                'date': header['date'],
                'customer_id': header['customer_id'],
                'customer_name': header['customer_name'],
                'salesperson': header['salesperson'],
                'salesperson_id': header['salesperson_id'],
                'invoice_no': header['invoice_no'],
                'items': [{
                    'product_code': i['product_code'],
                    'product_name': i['product_name'],
                    'quantity': i['quantity'],
                    'price': i['price'],
                    'amount': i['amount'],
                    'cost': i['cost'],
                    'profit': i['profit'],
                    'margin': i['margin']
                } for i in items],
                'total_amount': total_amount,
                'item_count': len(items)
            }
        })
    except Exception as e:
        print(f"[ERROR] 取得銷貨單詳情失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


# ============================================
# API: 報價/訂單/銷貨單管理 (sales_documents)
# ============================================

@app.route('/api/quote/next-no')
def get_next_quote_no():
    """產生下一個報價單號"""
    store_code = request.args.get('store', 'FY')
    date_str = request.args.get('date', datetime.now().strftime('%Y%m%d'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        prefix = f"QU-{store_code}-{date_str}-"
        cursor.execute("""
            SELECT doc_no FROM sales_documents 
            WHERE doc_no LIKE ? AND doc_type = 'QUOTE'
            ORDER BY doc_no DESC LIMIT 1
        """, (prefix + '%',))
        
        row = cursor.fetchone()
        if row and row['doc_no']:
            try:
                last_seq = int(row['doc_no'].split('-')[-1])
                next_seq = last_seq + 1
            except:
                next_seq = 1
        else:
            next_seq = 1
        
        quote_no = f"QU-{store_code}-{date_str}-{next_seq:03d}"
        
        return jsonify({'success': True, 'quote_no': quote_no})
    except Exception as e:
        print(f"[ERROR] 產生報價單號失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


@app.route('/api/sales-doc/create', methods=['POST'])
def create_sales_document():
    """建立銷售單據（報價/訂單/銷貨）"""
    data = request.get_json()
    
    doc_no = data.get('doc_no')
    doc_type = data.get('doc_type', 'QUOTE')
    target_id = data.get('target_id')
    target_name = data.get('target_name')
    total_amount = data.get('total_amount', 0)
    items = data.get('items', [])
    salesperson = data.get('salesperson', '')
    salesperson_id = data.get('salesperson_id', '')
    
    if not all([doc_no, target_id, items]):
        return jsonify({'success': False, 'message': '缺少必填欄位'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 插入單頭
        cursor.execute("""
            INSERT INTO sales_documents 
            (doc_no, doc_type, target_id, target_name, total_amount, 
             deposit_amount, balance_amount, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 0, ?, 'DRAFT', datetime('now', 'localtime'), datetime('now', 'localtime'))
        """, (doc_no, doc_type, target_id, target_name, total_amount, total_amount))
        
        # 插入明細
        for item in items:
            cursor.execute("""
                INSERT INTO sales_document_items 
                (doc_no, product_code, qty, unit_price, subtotal)
                VALUES (?, ?, ?, ?, ?)
            """, (
                doc_no,
                item.get('product_code', ''),
                item.get('qty', 0),
                item.get('unit_price', 0),
                item.get('subtotal', 0)
            ))
        
        conn.commit()
        return jsonify({'success': True, 'message': f'{doc_type}單 {doc_no} 建立成功'})
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] 建立銷售單據失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


@app.route('/api/sales-doc/list')
def get_sales_documents_list():
    """取得銷售單據列表"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    doc_type = request.args.get('type', 'QUOTE')
    search = request.args.get('search', '').strip()
    salesperson = request.args.get('salesperson', '').strip()
    
    offset = (page - 1) * limit
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 計算總筆數
        count_sql = """
            SELECT COUNT(*) as total FROM sales_documents
            WHERE doc_type = ?
        """
        count_params = [doc_type]
        
        if search:
            count_sql += " AND (doc_no LIKE ? OR target_name LIKE ?)"
            count_params.extend([f'%{search}%', f'%{search}%'])
        
        if salesperson:
            count_sql += " AND salesperson_id = ?"
            count_params.append(salesperson)
        
        cursor.execute(count_sql, count_params)
        total = cursor.fetchone()['total']
        
        # 查詢列表
        sql = """
            SELECT doc_no, doc_type, target_id, target_name, total_amount, 
                   status, created_at, salesperson, salesperson_id
            FROM sales_documents
            WHERE doc_type = ?
        """
        params = [doc_type]
        
        if search:
            sql += " AND (doc_no LIKE ? OR target_name LIKE ?)"
            params.extend([f'%{search}%', f'%{search}%'])
        
        if salesperson:
            sql += " AND salesperson_id = ?"
            params.append(salesperson)
        
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(sql, params)
        documents = cursor.fetchall()
        
        result = [{
            'doc_no': d['doc_no'],
            'doc_type': d['doc_type'],
            'target_id': d['target_id'],
            'target_name': d['target_name'],
            'total_amount': d['total_amount'],
            'status': d['status'],
            'created_at': d['created_at'],
            'salesperson': d['salesperson'],
            'salesperson_id': d['salesperson_id']
        } for d in documents]
        
        return jsonify({
            'success': True,
            'documents': result,
            'total': total,
            'page': page,
            'limit': limit,
            'total_pages': (total + limit - 1) // limit
        })
    except Exception as e:
        print(f"[ERROR] 取得銷售單據列表失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


@app.route('/api/sales-doc/detail')
def get_sales_document_detail():
    """取得銷售單據詳情"""
    doc_no = request.args.get('doc_no', '').strip()
    
    if not doc_no:
        return jsonify({'success': False, 'message': '缺少單號'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 查詢單頭
        cursor.execute("""
            SELECT doc_no, doc_type, target_id, target_name, total_amount,
                   deposit_amount, balance_amount, source_doc_no, status,
                   created_at, salesperson, salesperson_id
            FROM sales_documents
            WHERE doc_no = ?
            LIMIT 1
        """, (doc_no,))
        
        header = cursor.fetchone()
        if not header:
            return jsonify({'success': False, 'message': '找不到單據'}), 404
        
        # 查詢明細
        cursor.execute("""
            SELECT product_code, qty, unit_price, subtotal
            FROM sales_document_items
            WHERE doc_no = ?
            ORDER BY id
        """, (doc_no,))
        items = cursor.fetchall()
        
        return jsonify({
            'success': True,
            'document': {
                'doc_no': header['doc_no'],
                'doc_type': header['doc_type'],
                'target_id': header['target_id'],
                'target_name': header['target_name'],
                'total_amount': header['total_amount'],
                'deposit_amount': header['deposit_amount'],
                'balance_amount': header['balance_amount'],
                'source_doc_no': header['source_doc_no'],
                'status': header['status'],
                'created_at': header['created_at'],
                'salesperson': header['salesperson'],
                'salesperson_id': header['salesperson_id'],
                'items': [{
                    'product_code': i['product_code'],
                    'qty': i['qty'],
                    'unit_price': i['unit_price'],
                    'subtotal': i['subtotal']
                } for i in items]
            }
        })
    except Exception as e:
        print(f"[ERROR] 取得銷售單據詳情失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


@app.route('/api/sales-doc/convert', methods=['POST'])
def convert_sales_document():
    """轉換單據（報價轉訂單、訂單轉銷貨）"""
    data = request.get_json()
    
    source_doc_no = data.get('source_doc_no')
    new_doc_no = data.get('new_doc_no')
    new_doc_type = data.get('doc_type', 'ORDER')
    deposit_amount = data.get('deposit_amount', 0)
    
    if not all([source_doc_no, new_doc_no]):
        return jsonify({'success': False, 'message': '缺少必填欄位'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 查詢來源單
        cursor.execute("""
            SELECT * FROM sales_documents WHERE doc_no = ?
        """, (source_doc_no,))
        source = cursor.fetchone()
        
        if not source:
            return jsonify({'success': False, 'message': '找不到來源單據'}), 404
        
        # 計算餘額
        total_amount = source['total_amount']
        balance_amount = total_amount - deposit_amount
        
        # 建立新單
        cursor.execute("""
            INSERT INTO sales_documents 
            (doc_no, doc_type, target_id, target_name, total_amount,
             deposit_amount, balance_amount, source_doc_no, status, 
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'DRAFT', datetime('now', 'localtime'), datetime('now', 'localtime'))
        """, (
            new_doc_no,
            new_doc_type,
            source['target_id'],
            source['target_name'],
            total_amount,
            deposit_amount,
            balance_amount,
            source_doc_no
        ))
        
        # 複製明細
        cursor.execute("""
            SELECT product_code, qty, unit_price, subtotal
            FROM sales_document_items
            WHERE doc_no = ?
        """, (source_doc_no,))
        items = cursor.fetchall()
        
        for item in items:
            cursor.execute("""
                INSERT INTO sales_document_items 
                (doc_no, product_code, qty, unit_price, subtotal)
                VALUES (?, ?, ?, ?, ?)
            """, (
                new_doc_no,
                item['product_code'],
                item['qty'],
                item['unit_price'],
                item['subtotal']
            ))
        
        # 更新來源單狀態為已結案
        cursor.execute("""
            UPDATE sales_documents 
            SET status = 'CLOSED', updated_at = datetime('now', 'localtime')
            WHERE doc_no = ?
        """, (source_doc_no,))
        
        # 如果有訂金，寫入 finance_ledger
        if deposit_amount > 0:
            cursor.execute("""
                INSERT INTO finance_ledger 
                (record_type, target_id, target_name, reference_doc, total_amount,
                 status, payment_method, cleared_at, created_at)
                VALUES (?, ?, ?, ?, ?, 'PAID', '現金', datetime('now', 'localtime'), datetime('now', 'localtime'))
            """, (
                'AR',
                source['target_id'],
                source['target_name'],
                new_doc_no,
                deposit_amount
            ))
        
        conn.commit()
        return jsonify({'success': True, 'message': f'已成功轉換為 {new_doc_no}'})
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] 轉換單據失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()


# ============================================
# Boss 待請購清單 API

@app.route('/api/boss/pending-needs')
def boss_pending_needs():
    """回傳待請購清單 - 暫時移除權限驗證，改由前端控制"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 查詢待請購的 needs（未取消、未完成的請購單，包含待處理和已採購）
        cursor.execute("""
            SELECT
                n.id,
                n.date as invoice_no,
                n.product_code,
                n.item_name as product_name,
                n.quantity,
                n.purpose,
                n.remark as notes,
                n.requester,
                n.created_at,
                n.department,
                n.customer_code,
                n.status
            FROM needs n
            WHERE n.cancelled_at IS NULL
              AND n.status IN ('待處理', '已採購')
              AND n.request_type = '請購'
            ORDER BY 
                CASE n.status 
                    WHEN '待處理' THEN 1 
                    WHEN '已採購' THEN 2 
                END,
                n.created_at ASC
        """)
        
        needs = []
        for row in cursor.fetchall():
            need = dict(row)

            # 查詢客戶資料（如果 customer_code 存在）
            if need.get('customer_code'):
                cursor.execute("""
                    SELECT short_name as customer_name
                    FROM customers
                    WHERE customer_id = ? OR short_name = ?
                    LIMIT 1
                """, (need['customer_code'], need['customer_code']))
                customer = cursor.fetchone()
                if customer:
                    need['customer_name'] = customer['customer_name']

            # 查詢最後一次進貨資訊
            if need.get('product_code'):
                cursor.execute("""
                    SELECT
                        p.supplier_name as vendor_name,
                        p.price as last_price
                    FROM purchase_history p
                    WHERE p.product_code = ?
                    ORDER BY p.date DESC
                    LIMIT 1
                """, (need['product_code'],))

                last_purchase = cursor.fetchone()
                if last_purchase:
                    need['last_vendor'] = last_purchase['vendor_name']
                    need['last_price'] = last_purchase['last_price']
                else:
                    need['last_vendor'] = None
                    need['last_price'] = None

            needs.append(need)
        
        # 計算統計數據
        stats = {
            'pending_count': len(needs),
            'total_amount': sum(n.get('last_price', 0) * n.get('quantity', 0) 
                               for n in needs if n.get('last_price')),
            'product_count': len(set(n.get('product_code') for n in needs if n.get('product_code'))),
            'oldest_days': None
        }
        
        # 計算最久的天數
        if needs:
            oldest_date = min(n['created_at'] for n in needs if n.get('created_at'))
            if oldest_date:
                from datetime import datetime
                oldest = datetime.strptime(oldest_date, '%Y-%m-%d %H:%M:%S')
                stats['oldest_days'] = (datetime.now() - oldest).days
        
        return jsonify({
            'success': True,
            'needs': needs,
            'stats': stats
        })
        
    except Exception as e:
        print(f"[Boss] 載入待請購清單失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()

@app.route('/api/boss/needs/<int:need_id>/status', methods=['POST'])
def boss_update_need_status(need_id):
    """更新請購單狀態"""
    data = request.get_json()
    status = data.get('status')  # 'purchased', 'arrived' 或 'cancelled'
    
    if status not in ['purchased', 'arrived', 'cancelled']:
        return jsonify({'success': False, 'message': '無效的狀態'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if status == 'purchased':
            # 標記為已採購
            cursor.execute("""
                UPDATE needs
                SET arrived_at = datetime('now', 'localtime'),
                    status = '已採購'
                WHERE id = ?
            """, (need_id,))
        elif status == 'arrived':
            # 標記為已到貨（完成）
            cursor.execute("""
                UPDATE needs
                SET status = '已完成'
                WHERE id = ?
            """, (need_id,))
        else:
            # 標記為已取消
            cursor.execute("""
                UPDATE needs 
                SET cancelled_at = datetime('now', 'localtime'),
                    status = '已取消'
                WHERE id = ?
            """, (need_id,))
        
        conn.commit()
        
        if cursor.rowcount > 0:
            return jsonify({'success': True, 'message': '更新成功'})
        else:
            return jsonify({'success': False, 'message': '找不到該筆資料'}), 404
            
    except Exception as e:
        print(f"[Boss] 更新請購狀態失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()

# ============================================
# 靜態檔案路由（必須放在所有 API 路由之後）
@app.route('/api/boss/needs/<int:need_id>/notes', methods=['POST'])
def boss_update_need_notes(need_id):
    """更新請購單備註"""
    data = request.get_json()
    notes = data.get('notes', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE needs
            SET remark = ?
            WHERE id = ?
        """, (notes, need_id))

        conn.commit()

        if cursor.rowcount > 0:
            return jsonify({'success': True, 'message': '備註已儲存'})
        else:
            return jsonify({'success': False, 'message': '找不到該筆資料'}), 404

    except Exception as e:
        print(f"[Boss] 儲存備註失敗: {e}")
        return jsonify({'success': False, 'message': '系統錯誤'}), 500
    finally:
        conn.close()

# ============================================
@app.route('/static/<path:filename>')
def serve_static(filename):
    """提供 static 檔案服務"""
    return send_from_directory(app.static_folder, filename)

@app.route('/<path:path>')
def static_files(path):
    """提供靜態檔案服務"""
    # 檢查是否為 API 路徑（不應該發生，因為 API 路由優先）
    if path.startswith('api/'):
        return jsonify({'success': False, 'message': 'API endpoint not found'}), 404
    
    # 如果是 .html 檔案，使用模板渲染
    if path.endswith('.html') or '.' not in path:
        template_name = path if path.endswith('.html') else f'{path}.html'
        try:
            return render_template(template_name)
        except:
            # 如果模板不存在，fallback 到靜態檔案
            pass
    
    return send_from_directory(STATIC_DIR, path)


# ============================================
# API: 逾期收貨提醒 - 檢查使用者待確認收貨的需求
# ============================================
@app.route('/api/needs/overdue-arrival', methods=['GET'])
def get_overdue_arrival_needs():
    """
    取得指定使用者逾期未收貨的需求
    - 調撥：已調撥且超過 3 天未收貨
    - 請購：已採購且超過 5 天未收貨
    """
    requester = request.args.get('requester', '')
    
    if not requester:
        return jsonify({'success': False, 'message': '缺少 requester 參數'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 調撥類：已調撥且超過 3 天
        cursor.execute("""
            SELECT id, item_name, quantity, request_type, transfer_from, 
                   processed_at as action_date, status,
                   julianday('now', 'localtime') - julianday(processed_at) as overdue_days
            FROM needs
            WHERE requester = ?
              AND request_type = '調撥'
              AND status = '已調撥'
              AND processed_at IS NOT NULL
              AND julianday('now', 'localtime') - julianday(processed_at) >= 3
              AND cancelled_at IS NULL
            ORDER BY processed_at ASC
        """, (requester,))
        
        transfer_needs = [dict(row) for row in cursor.fetchall()]
        
        # 請購類：已採購且超過 5 天
        cursor.execute("""
            SELECT id, item_name, quantity, request_type, vendor_name,
                   processed_at as action_date, status,
                   julianday('now', 'localtime') - julianday(processed_at) as overdue_days
            FROM needs
            WHERE requester = ?
              AND request_type = '請購'
              AND status = '已採購'
              AND processed_at IS NOT NULL
              AND julianday('now', 'localtime') - julianday(processed_at) >= 5
              AND cancelled_at IS NULL
            ORDER BY processed_at ASC
        """, (requester,))
        
        purchase_needs = [dict(row) for row in cursor.fetchall()]
        
        # 合併結果
        all_needs = transfer_needs + purchase_needs
        
        return jsonify({
            'success': True,
            'items': all_needs,
            'count': len(all_needs),
            'transfer_count': len(transfer_needs),
            'purchase_count': len(purchase_needs)
        })
        
    except Exception as e:
        print(f"[OverdueArrival] 查詢失敗: {e}")
        return jsonify({'success': False, 'message': '查詢失敗'}), 500
    finally:
        conn.close()

# ============================================
# 推薦備貨商品 API
# ============================================

# API: 取得推薦商品分類列表
@app.route('/api/recommended-categories', methods=['GET'])
def get_recommended_categories():
    """取得所有推薦商品分類"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT id, name, sort_order
            FROM recommended_categories
            ORDER BY sort_order ASC, id ASC
        ''')
        categories = [dict(row) for row in cursor.fetchall()]
        return jsonify({'success': True, 'categories': categories})
    except Exception as e:
        print(f"[RecommendedCategories] 查詢失敗: {e}")
        return jsonify({'success': False, 'message': '查詢失敗'}), 500
    finally:
        conn.close()

# API: 新增推薦商品分類
@app.route('/api/recommended-categories', methods=['POST'])
def create_recommended_category():
    """新增推薦商品分類"""
    data = request.get_json()
    name = data.get('name', '').strip()
    
    if not name:
        return jsonify({'success': False, 'message': '分類名稱不能為空'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO recommended_categories (name, sort_order)
            VALUES (?, (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM recommended_categories))
        ''', (name,))
        conn.commit()
        return jsonify({'success': True, 'id': cursor.lastrowid, 'message': '分類新增成功'})
    except Exception as e:
        print(f"[RecommendedCategories] 新增失敗: {e}")
        return jsonify({'success': False, 'message': '新增失敗'}), 500
    finally:
        conn.close()

# API: 更新推薦商品分類
@app.route('/api/recommended-categories/<int:category_id>', methods=['PUT'])
def update_recommended_category(category_id):
    """更新推薦商品分類"""
    data = request.get_json()
    name = data.get('name', '').strip()
    
    if not name:
        return jsonify({'success': False, 'message': '分類名稱不能為空'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE recommended_categories SET name = ? WHERE id = ?
        ''', (name, category_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'message': '分類不存在'}), 404
        return jsonify({'success': True, 'message': '分類更新成功'})
    except Exception as e:
        print(f"[RecommendedCategories] 更新失敗: {e}")
        return jsonify({'success': False, 'message': '更新失敗'}), 500
    finally:
        conn.close()

# API: 刪除推薦商品分類
@app.route('/api/recommended-categories/<int:category_id>', methods=['DELETE'])
def delete_recommended_category(category_id):
    """刪除推薦商品分類"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 檢查是否有商品使用此分類
        cursor.execute('SELECT COUNT(*) as count FROM recommended_products WHERE category_id = ?', (category_id,))
        result = cursor.fetchone()
        if result and result['count'] > 0:
            return jsonify({'success': False, 'message': '此分類下還有商品，無法刪除'}), 400
        
        cursor.execute('DELETE FROM recommended_categories WHERE id = ?', (category_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'message': '分類不存在'}), 404
        return jsonify({'success': True, 'message': '分類刪除成功'})
    except Exception as e:
        print(f"[RecommendedCategories] 刪除失敗: {e}")
        return jsonify({'success': False, 'message': '刪除失敗'}), 500
    finally:
        conn.close()

# API: 取得推薦商品列表
@app.route('/api/recommended-products', methods=['GET'])
def get_recommended_products():
    """取得推薦商品列表（前台：只顯示上架的，後台：可顯示全部）"""
    show_inactive = request.args.get('show_inactive', '0') == '1'
    category_id = request.args.get('category_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = '''
            SELECT p.id, p.category_id, p.product_code as model_no, p.name, 
                   p.external_link, p.description, p.min_stock, p.is_active, 
                   p.sort_order, p.created_at, c.name as category_name
            FROM recommended_products p
            LEFT JOIN recommended_categories c ON p.category_id = c.id
            WHERE 1=1
        '''
        params = []
        
        if not show_inactive:
            query += ' AND p.is_active = 1'
        
        if category_id:
            query += ' AND p.category_id = ?'
            params.append(category_id)
        
        query += ' ORDER BY c.sort_order ASC, p.sort_order ASC, p.id ASC'
        
        cursor.execute(query, params)
        products = [dict(row) for row in cursor.fetchall()]
        return jsonify({'success': True, 'products': products})
    except Exception as e:
        print(f"[RecommendedProducts] 查詢失敗: {e}")
        return jsonify({'success': False, 'message': '查詢失敗'}), 500
    finally:
        conn.close()

# API: 新增推薦商品
@app.route('/api/recommended-products', methods=['POST'])
def create_recommended_product():
    """新增推薦商品"""
    data = request.get_json()
    
    product_code = data.get('model_no', '').strip()
    name = data.get('name', '').strip()
    category_id = data.get('category_id')
    external_link = data.get('external_link', '').strip()
    description = data.get('description', '').strip()
    min_stock = data.get('min_stock', 1)
    
    if not product_code or not name:
        return jsonify({'success': False, 'message': '編號和名稱不能為空'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO recommended_products 
            (category_id, product_code, name, external_link, description, min_stock, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM recommended_products))
        ''', (category_id, product_code, name, external_link, description, min_stock))
        conn.commit()
        return jsonify({'success': True, 'id': cursor.lastrowid, 'message': '商品新增成功'})
    except Exception as e:
        print(f"[RecommendedProducts] 新增失敗: {e}")
        return jsonify({'success': False, 'message': '新增失敗'}), 500
    finally:
        conn.close()

# API: 更新推薦商品
@app.route('/api/recommended-products/<int:product_id>', methods=['PUT'])
def update_recommended_product(product_id):
    """更新推薦商品"""
    data = request.get_json()
    
    product_code = data.get('model_no', '').strip()
    name = data.get('name', '').strip()
    category_id = data.get('category_id')
    external_link = data.get('external_link', '').strip()
    description = data.get('description', '').strip()
    min_stock = data.get('min_stock', 1)
    is_active = data.get('is_active', 1)
    
    if not product_code or not name:
        return jsonify({'success': False, 'message': '編號和名稱不能為空'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE recommended_products 
            SET category_id = ?, product_code = ?, name = ?, external_link = ?, 
                description = ?, min_stock = ?, is_active = ?
            WHERE id = ?
        ''', (category_id, product_code, name, external_link, description, min_stock, is_active, product_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'message': '商品不存在'}), 404
        return jsonify({'success': True, 'message': '商品更新成功'})
    except Exception as e:
        print(f"[RecommendedProducts] 更新失敗: {e}")
        return jsonify({'success': False, 'message': '更新失敗'}), 500
    finally:
        conn.close()

# API: 刪除推薦商品
@app.route('/api/recommended-products/<int:product_id>', methods=['DELETE'])
def delete_recommended_product(product_id):
    """刪除推薦商品"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM recommended_products WHERE id = ?', (product_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'message': '商品不存在'}), 404
        return jsonify({'success': True, 'message': '商品刪除成功'})
    except Exception as e:
        print(f"[RecommendedProducts] 刪除失敗: {e}")
        return jsonify({'success': False, 'message': '刪除失敗'}), 500
    finally:
        conn.close()

# API: 送出備貨需求（從推薦商品）
@app.route('/api/recommended-products/order', methods=['POST'])
def create_order_from_recommended():
    """從推薦商品建立備貨需求"""
    data = request.get_json()
    items = data.get('items', [])  # [{product_id, quantity}]
    requester = data.get('requester', '')
    
    if not items or not requester:
        return jsonify({'success': False, 'message': '請選擇商品並提供申請人'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        created_needs = []
        for item in items:
            product_id = item.get('product_id')
            quantity = item.get('quantity', 0)
            
            if quantity <= 0:
                continue
            
            # 取得商品資訊
            cursor.execute('''
                SELECT product_code, name, min_stock 
                FROM recommended_products 
                WHERE id = ? AND is_active = 1
            ''', (product_id,))
            product = cursor.fetchone()
            
            if not product:
                continue
            
            # 建立備貨需求
            need_no = f"REC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{product_id}"
            item_name = f"{product['product_code']} {product['name']}"
            
            cursor.execute('''
                INSERT INTO needs (need_no, requester, item_name, quantity, request_type, status, source, created_at)
                VALUES (?, ?, ?, ?, '請購', '待審核', 'recommended', datetime('now', 'localtime'))
            ''', (need_no, requester, item_name, quantity))
            
            created_needs.append({
                'need_no': need_no,
                'item_name': item_name,
                'quantity': quantity
            })
        
        conn.commit()
        
        if not created_needs:
            return jsonify({'success': False, 'message': '沒有成功建立任何需求單'}), 400
        
        return jsonify({
            'success': True,
            'message': f'成功建立 {len(created_needs)} 筆備貨需求',
            'needs': created_needs
        })
        
    except Exception as e:
        print(f"[RecommendedProducts] 建立需求單失敗: {e}")
        return jsonify({'success': False, 'message': '建立需求單失敗'}), 500
    finally:
        conn.close()
