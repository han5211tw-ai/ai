#!/usr/bin/env python3
# ERP v2 — OpenClaw
# Port 8800 (測試用)

import os
import sqlite3
import json
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, jsonify, request, abort, send_from_directory


# ─────────────────────────────────────────────
# 環境設定
# ─────────────────────────────────────────────
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key, value)

load_env()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.environ.get('DB_PATH', os.path.join(BASE_DIR, 'db', 'company.db'))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static'),
)
app.config['TEMPLATES_AUTO_RELOAD'] = True


# ─────────────────────────────────────────────
# 資料庫
# ─────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # WAL 模式（與 parser 共用不衝突）
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=3000')
    return conn


# ─────────────────────────────────────────────
# 輔助：JSON 回傳
# ─────────────────────────────────────────────
def ok(data=None, **kwargs):
    payload = {'success': True}
    if data is not None:
        payload['data'] = data
    payload.update(kwargs)
    return jsonify(payload)

def err(message, code=400):
    return jsonify({'success': False, 'message': message}), code


# ─────────────────────────────────────────────
# 頁面路由
# ─────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin/health')
def admin_health_page():
    return render_template('admin/health.html')

@app.route('/admin/recommended_products')
def admin_recommended_products_page():
    return render_template('admin/recommended_products.html')

@app.route('/admin/bonus_rules')
def admin_bonus_rules_page():
    return render_template('admin/bonus_rules.html')

@app.route('/admin/bonus_report')
def admin_bonus_report_page():
    return render_template('admin/bonus_report.html')

@app.route('/admin/announcement_management')
@app.route('/admin/announcement_management.html')
def admin_announcement_management_page():
    return render_template('admin/announcement_management.html')

@app.route('/student-chat')
def student_chat():
    """學生 AI 聊天室頁面（公開，無需登入）"""
    return render_template('student_chat.html')

@app.route('/<path:page>')
def render_page(page):
    # 去除 .html 後綴
    if page.endswith('.html'):
        page = page[:-5]
    try:
        return render_template(f'{page}.html')
    except Exception:
        abort(404)


# ─────────────────────────────────────────────
# API: 系統健康
# ─────────────────────────────────────────────
@app.route('/api/health')
def health_check():
    db_ok = False
    try:
        conn = get_db()
        conn.execute('SELECT 1')
        conn.close()
        db_ok = True
    except Exception:
        pass
    return jsonify({
        'status': 'ok' if db_ok else 'degraded',
        'db': db_ok,
        'version': 'v2',
        'time': datetime.now().isoformat()
    })


# ─────────────────────────────────────────────
# API: 認證
# ─────────────────────────────────────────────
@app.route('/api/auth/verify', methods=['POST'])
def auth_verify():
    data     = request.get_json() or {}
    name     = (data.get('name') or '').strip()
    password = (data.get('password') or '').strip()

    if not name or not password:
        return err('請輸入姓名與密碼')

    conn = get_db()
    user = conn.execute(
        '''SELECT sp.name, sp.password, sp.title, sp.department,
                  s.staff_id as employee_id
           FROM staff_passwords sp
           LEFT JOIN staff s ON s.staff_id = sp.staff_id
           WHERE sp.name = ? AND sp.password = ?''',
        (name, password)
    ).fetchone()
    conn.close()

    if not user:
        return err('姓名或密碼錯誤', 401)

    return ok(user={
        'name':        user['name'],
        'title':       user['title'],
        'department':  user['department'] or '',
        'employee_id': user['employee_id'] or '',
    })


@app.route('/api/boss/verify', methods=['POST'])
def boss_verify():
    data     = request.get_json() or {}
    password = (data.get('password') or '').strip()

    if not password:
        return err('請輸入密碼')

    conn = get_db()
    row = conn.execute(
        "SELECT password FROM boss_password LIMIT 1"
    ).fetchone()
    conn.close()

    if not row or row['password'] != password:
        return err('密碼錯誤', 401)

    return ok()


@app.route('/api/accountant/verify', methods=['POST'])
def accountant_verify():
    data     = request.get_json() or {}
    name     = (data.get('name') or '').strip()
    password = (data.get('password') or '').strip()

    if not name or not password:
        return err('請輸入姓名與密碼')

    conn = get_db()
    user = conn.execute(
        "SELECT name, title FROM staff_passwords WHERE name = ? AND password = ? AND title = '會計'",
        (name, password)
    ).fetchone()
    conn.close()

    if not user:
        return err('驗證失敗', 401)

    return ok(user={'name': user['name'], 'title': user['title']})


# ─────────────────────────────────────────────
# API: 系統公告
# ─────────────────────────────────────────────
@app.route('/api/system/announcements', methods=['GET'])
def get_announcements():
    conn = get_db()
    rows = conn.execute(
        '''SELECT id, title, content, level, is_pinned, created_at
           FROM system_announcements
           WHERE is_active = 1
           ORDER BY is_pinned DESC, created_at DESC
           LIMIT 20'''
    ).fetchall()
    conn.close()
    return ok([dict(r) for r in rows])


@app.route('/api/system/announcements', methods=['POST'])
def create_announcement():
    data    = request.get_json() or {}
    title   = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()
    if not title:
        return err('請輸入標題')
    conn = get_db()
    conn.execute(
        '''INSERT INTO system_announcements (title, content, priority, is_active, created_at)
           VALUES (?, ?, ?, 1, datetime('now','localtime'))''',
        (title, content, data.get('priority', 0))
    )
    conn.commit()
    conn.close()
    return ok(message='公告已新增')


# ─────────────────────────────────────────────
# API: 公告管理（完整 CRUD）
# ─────────────────────────────────────────────
@app.route('/api/system/announcements/all', methods=['GET'])
def get_announcements_all():
    """後台：取全部公告（含停用）"""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT id, title, content, level, is_active, is_pinned, created_by, created_at, expires_at
            FROM system_announcements ORDER BY is_pinned DESC, created_at DESC
        """).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


@app.route('/api/system/announcements/<int:ann_id>', methods=['PUT'])
def update_announcement(ann_id):
    data = request.get_json() or {}
    conn = get_db()
    try:
        conn.execute("""
            UPDATE system_announcements
            SET title=?, content=?, level=?, is_active=?, is_pinned=?, expires_at=?
            WHERE id=?
        """, (data.get('title'), data.get('content'), data.get('level','info'),
              int(data.get('is_active',1)), int(data.get('is_pinned',0)),
              data.get('expires_at'), ann_id))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/system/announcements/<int:ann_id>', methods=['DELETE'])
def delete_announcement(ann_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM system_announcements WHERE id=?", (ann_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 員工管理
# ─────────────────────────────────────────────
@app.route('/api/staff/list')
def staff_list_api():
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT staff_id, name, title, department, store, role,
                   mobile, hire_date, birth_date, is_active, staff_code
            FROM staff ORDER BY department, store, name
        """).fetchall()
        # 同步 staff_passwords 密碼
        pws = {r['name']: r['password'] for r in conn.execute(
            "SELECT name, password FROM staff_passwords"
        ).fetchall()}
        result = []
        for r in rows:
            d = dict(r)
            d['password'] = pws.get(d['name'], '')
            result.append(d)
        return jsonify({'success': True, 'staff': result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/staff/<staff_id>', methods=['PUT'])
def staff_update(staff_id):
    data = request.get_json() or {}
    conn = get_db()
    try:
        conn.execute("""
            UPDATE staff SET title=?, department=?, store=?, role=?,
                   mobile=?, hire_date=?, birth_date=?, is_active=?,
                   updated_at=datetime('now','localtime')
            WHERE staff_id=?
        """, (data.get('title'), data.get('department'), data.get('store'),
              data.get('role'), data.get('mobile'), data.get('hire_date'),
              data.get('birth_date'), int(data.get('is_active',1)), staff_id))

        # 同步更新 staff_passwords
        pw = (data.get('password') or '').strip()
        if pw:
            conn.execute("UPDATE staff_passwords SET password=? WHERE name=?",
                         (pw, data.get('name','')))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 獎金規則
# ─────────────────────────────────────────────
@app.route('/api/bonus-rules', methods=['GET'])
def bonus_rules_get():
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT id, rule_name, product_code, product_name, start_date, end_date,
                   bonus_type, bonus_value, min_quantity, target_scope, is_active,
                   created_by, created_at
            FROM bonus_rules ORDER BY start_date DESC, id DESC
        """).fetchall()
        return jsonify({'success': True, 'rules': [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/bonus-rules', methods=['POST'])
def bonus_rules_create():
    data = request.get_json() or {}
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO bonus_rules
              (rule_name, product_code, product_name, start_date, end_date,
               bonus_type, bonus_value, min_quantity, target_scope, target_codes,
               is_active, created_by)
            VALUES (?,?,?,?,?,?,?,?,?,?,1,?)
        """, (data.get('rule_name'), data.get('product_code'), data.get('product_name'),
              data.get('start_date'), data.get('end_date'), data.get('bonus_type','fixed'),
              float(data.get('bonus_value',0)), int(data.get('min_quantity',1)),
              data.get('target_scope','all'), data.get('target_codes',''),
              data.get('created_by','admin')))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/bonus-rules/<int:rule_id>', methods=['PUT'])
def bonus_rules_update(rule_id):
    data = request.get_json() or {}
    conn = get_db()
    try:
        conn.execute("""
            UPDATE bonus_rules SET rule_name=?, product_code=?, product_name=?,
                   start_date=?, end_date=?, bonus_type=?, bonus_value=?,
                   min_quantity=?, target_scope=?, is_active=?,
                   updated_at=datetime('now','localtime')
            WHERE id=?
        """, (data.get('rule_name'), data.get('product_code'), data.get('product_name'),
              data.get('start_date'), data.get('end_date'), data.get('bonus_type','fixed'),
              float(data.get('bonus_value',0)), int(data.get('min_quantity',1)),
              data.get('target_scope','all'), int(data.get('is_active',1)), rule_id))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/bonus-rules/<int:rule_id>', methods=['DELETE'])
def bonus_rules_delete(rule_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM bonus_rules WHERE id=?", (rule_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 獎金計算 & 報表
# ─────────────────────────────────────────────
@app.route('/api/bonus-calculate', methods=['POST'])
def bonus_calculate():
    """依銷貨記錄與有效獎金規則計算各業務員獎金"""
    data       = request.get_json() or {}
    date_start = data.get('date_start', '')
    date_end   = data.get('date_end', '')
    if not date_start or not date_end:
        return jsonify({'success': False, 'message': '請提供日期範圍'}), 400

    conn = get_db()
    try:
        rules = conn.execute("""
            SELECT * FROM bonus_rules
            WHERE is_active=1
              AND start_date <= ? AND end_date >= ?
        """, (date_end, date_start)).fetchall()

        results = []
        for rule in rules:
            r = dict(rule)
            # 查詢符合條件的銷貨明細
            rows = conn.execute("""
                SELECT salesperson, salesperson_id, product_name,
                       SUM(quantity) as total_qty, SUM(amount) as total_amount,
                       GROUP_CONCAT(DISTINCT invoice_no) as invoice_nos
                FROM sales_history
                WHERE date >= ? AND date <= ? AND product_code = ?
                GROUP BY salesperson, salesperson_id
            """, (date_start, date_end, r['product_code'])).fetchall()

            for row in rows:
                row = dict(row)
                qty = row['total_qty'] or 0
                if qty < (r['min_quantity'] or 1):
                    continue
                if r['bonus_type'] == 'fixed':
                    bonus = qty * float(r['bonus_value'])
                else:  # percent
                    bonus = row['total_amount'] * float(r['bonus_value']) / 100

                results.append({
                    'rule_id':        r['id'],
                    'rule_name':      r['rule_name'],
                    'salesperson':    row['salesperson'],
                    'salesperson_id': row['salesperson_id'],
                    'product_code':   r['product_code'],
                    'product_name':   r['product_name'],
                    'sales_quantity': qty,
                    'sales_amount':   row['total_amount'],
                    'bonus_amount':   round(bonus, 0),
                    'invoice_nos':    row['invoice_nos'] or '',
                })

        return jsonify({'success': True, 'results': results,
                        'date_start': date_start, 'date_end': date_end})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/bonus-results', methods=['GET'])
def bonus_results_get():
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT id, rule_id, period_start, period_end, salesperson_name,
                   product_name, sales_quantity, sales_amount, bonus_amount,
                   status, confirmed_at, created_at
            FROM bonus_results ORDER BY created_at DESC LIMIT 200
        """).fetchall()
        return jsonify({'success': True, 'results': [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 推薦備貨
# ─────────────────────────────────────────────
@app.route('/api/recommended-categories', methods=['GET'])
def rec_categories_get():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, name, sort_order FROM recommended_categories ORDER BY sort_order, id"
        ).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


@app.route('/api/recommended-categories', methods=['POST'])
def rec_categories_create():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'message': '請輸入分類名稱'}), 400
    conn = get_db()
    try:
        max_sort = conn.execute("SELECT COALESCE(MAX(sort_order),0) FROM recommended_categories").fetchone()[0]
        conn.execute("INSERT INTO recommended_categories (name, sort_order) VALUES (?,?)",
                     (name, max_sort + 1))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/recommended-categories/<int:cat_id>', methods=['DELETE'])
def rec_categories_delete(cat_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM recommended_categories WHERE id=?", (cat_id,))
        conn.execute("DELETE FROM recommended_products WHERE category_id=?", (cat_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/recommended-products', methods=['GET'])
def rec_products_get():
    cat_id = request.args.get('category_id', type=int)
    conn   = get_db()
    try:
        if cat_id:
            rows = conn.execute("""
                SELECT rp.id, rp.category_id, rc.name as category_name,
                       rp.item_name, rp.product_code, rp.quantity,
                       rp.external_link, rp.description, rp.is_active, rp.sort_order
                FROM recommended_products rp
                JOIN recommended_categories rc ON rc.id = rp.category_id
                WHERE rp.category_id=? ORDER BY rp.sort_order, rp.id
            """, (cat_id,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT rp.id, rp.category_id, rc.name as category_name,
                       rp.item_name, rp.product_code, rp.quantity,
                       rp.external_link, rp.description, rp.is_active, rp.sort_order
                FROM recommended_products rp
                JOIN recommended_categories rc ON rc.id = rp.category_id
                ORDER BY rc.sort_order, rp.sort_order, rp.id
            """).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


@app.route('/api/recommended-products', methods=['POST'])
def rec_products_create():
    data = request.get_json() or {}
    conn = get_db()
    try:
        max_s = conn.execute(
            "SELECT COALESCE(MAX(sort_order),0) FROM recommended_products WHERE category_id=?",
            (data.get('category_id'),)
        ).fetchone()[0]
        conn.execute("""
            INSERT INTO recommended_products
              (category_id, item_name, product_code, quantity, external_link, description, is_active, sort_order)
            VALUES (?,?,?,?,?,?,1,?)
        """, (data.get('category_id'), data.get('item_name'), data.get('product_code',''),
              int(data.get('quantity',1)), data.get('external_link',''),
              data.get('description',''), max_s + 1))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/recommended-products/<int:prod_id>', methods=['PUT'])
def rec_products_update(prod_id):
    data = request.get_json() or {}
    conn = get_db()
    try:
        conn.execute("""
            UPDATE recommended_products
            SET item_name=?, product_code=?, quantity=?, external_link=?,
                description=?, is_active=?, category_id=?
            WHERE id=?
        """, (data.get('item_name'), data.get('product_code',''),
              int(data.get('quantity',1)), data.get('external_link',''),
              data.get('description',''), int(data.get('is_active',1)),
              data.get('category_id'), prod_id))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/recommended-products/<int:prod_id>', methods=['DELETE'])
def rec_products_delete(prod_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM recommended_products WHERE id=?", (prod_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 首頁 — 業績統計（本季）
# ─────────────────────────────────────────────
def current_quarter_range():
    """回傳本季開始日與結束日（YYYY-MM-DD）"""
    today = datetime.today()
    q = (today.month - 1) // 3
    starts = [(1,1),(4,1),(7,1),(10,1)]
    ends   = [(3,31),(6,30),(9,30),(12,31)]
    qs, qe = starts[q], ends[q]
    start = f"{today.year}-{qs[0]:02d}-{qs[1]:02d}"
    end   = f"{today.year}-{qe[0]:02d}-{qe[1]:02d}"
    return start, end

@app.route('/api/summary')
def get_summary():
    start, end = current_quarter_range()
    conn = get_db()
    total = conn.execute(
        "SELECT SUM(amount) FROM sales_history WHERE date >= ? AND date <= ?",
        (start, end)
    ).fetchone()[0] or 0

    day_count = conn.execute(
        "SELECT COUNT(DISTINCT date) FROM sales_history WHERE date >= ? AND date <= ?",
        (start, end)
    ).fetchone()[0] or 1

    max_val = conn.execute(
        """SELECT MAX(daily_total) FROM
           (SELECT SUM(amount) as daily_total FROM sales_history
            WHERE date >= ? AND date <= ? GROUP BY date)""",
        (start, end)
    ).fetchone()[0] or 0

    conn.close()
    return jsonify({
        'total': total,
        'avg':   total // day_count,
        'max':   max_val,
        'start': start,
        'end':   end,
    })


# ─────────────────────────────────────────────
# API: 每日銷售（本季，門市部+業務部分開）
# ─────────────────────────────────────────────
STORE_STAFF = ['林榮祺', '林峙文', '劉育仕', '林煜捷', '張永承', '張家碩']

@app.route('/api/sales/daily')
def get_daily_sales():
    start, end = current_quarter_range()
    conn = get_db()

    total_rows = {
        r['date']: r['amount']
        for r in conn.execute(
            "SELECT date, SUM(amount) as amount FROM sales_history "
            "WHERE date >= ? AND date <= ? GROUP BY date ORDER BY date",
            (start, end)
        ).fetchall()
    }

    ph = ','.join(['?'] * len(STORE_STAFF))
    store_rows = {
        r['date']: r['amount']
        for r in conn.execute(
            f"SELECT date, SUM(amount) as amount FROM sales_history "
            f"WHERE date >= ? AND date <= ? AND salesperson IN ({ph}) GROUP BY date",
            [start, end] + STORE_STAFF
        ).fetchall()
    }
    conn.close()

    result = []
    for date, total in total_rows.items():
        store = store_rows.get(date, 0)
        result.append({
            'date':     date,
            'store':    store,
            'business': total - store,
            'total':    total,
        })
    return jsonify(result)


# ─────────────────────────────────────────────
# API: 需求表（待處理清單）
# ─────────────────────────────────────────────
@app.route('/api/needs/latest')
def get_latest_needs():
    filter_type = request.args.get('type', 'all')
    conn = get_db()
    try:
        if filter_type == '調撥':
            rows = conn.execute("""
                SELECT id, date, item_name, quantity, customer_code, department,
                       requester, vendor_name, status, product_code, remark,
                       purpose, request_type, transfer_from
                FROM needs
                WHERE request_type = '調撥'
                  AND (status IS NULL OR status IN ('', '待處理', '已調撥'))
                  AND cancelled_at IS NULL AND completed_at IS NULL
                ORDER BY date DESC, id DESC LIMIT 50
            """).fetchall()
        elif filter_type == '請購':
            rows = conn.execute("""
                SELECT id, date, item_name, quantity, customer_code, department,
                       requester, vendor_name, status, product_code, remark,
                       purpose, request_type, transfer_from
                FROM needs
                WHERE (request_type = '請購' OR request_type IS NULL OR request_type = '')
                  AND (status IS NULL OR status IN ('', '待處理', '已採購'))
                  AND cancelled_at IS NULL AND completed_at IS NULL
                ORDER BY date DESC, id DESC LIMIT 50
            """).fetchall()
        else:
            rows = conn.execute("""
                SELECT id, date, item_name, quantity, customer_code, department,
                       requester, vendor_name, status, product_code, remark,
                       purpose, request_type, transfer_from
                FROM needs
                WHERE (status IS NULL OR status IN ('', '待處理', '已採購', '已調撥'))
                  AND cancelled_at IS NULL AND completed_at IS NULL
                ORDER BY date DESC, id DESC LIMIT 50
            """).fetchall()

        if not rows:
            return jsonify({'date': None, 'items': []})

        items = []
        for row in rows:
            r = dict(row)
            product_code = r.get('product_code') or ''
            display_name = r.get('item_name') or ''

            # 嘗試從庫存表補齊產品名稱
            if product_code and not any('\u4e00' <= c <= '\u9fff' for c in display_name):
                inv = conn.execute(
                    "SELECT item_spec FROM inventory WHERE product_id = ? "
                    "ORDER BY report_date DESC LIMIT 1", (product_code,)
                ).fetchone()
                if inv and inv['item_spec']:
                    display_name = inv['item_spec']

            # 客戶名稱
            customer_name = ''
            cust_code = r.get('customer_code') or ''
            if cust_code and cust_code not in ('nan', 'None', 'NaN'):
                cust = conn.execute(
                    "SELECT short_name FROM customers WHERE customer_id = ? LIMIT 1",
                    (cust_code,)
                ).fetchone()
                if cust:
                    customer_name = cust['short_name']
            else:
                cust_code = ''

            items.append({
                'id':            r['id'],
                'date':          r['date'],
                'item_name':     r['item_name'],
                'display_name':  display_name,
                'quantity':      r['quantity'],
                'customer_code': cust_code,
                'customer_name': customer_name,
                'department':    r['department'],
                'requester':     r['requester'],
                'status':        r['status'] or '待處理',
                'product_code':  product_code,
                'remark':        r['remark'] or '',
                'purpose':       r['purpose'] or '備貨',
                'request_type':  r['request_type'] or '請購',
                'transfer_from': r['transfer_from'] or '',
            })

        return jsonify({'date': rows[0]['date'], 'items': items})
    except Exception as e:
        return jsonify({'date': None, 'items': [], 'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/needs/arrive', methods=['POST'])
def arrive_need():
    data    = request.get_json() or {}
    need_id = data.get('id')
    if not need_id:
        return err('缺少 ID')

    conn = get_db()
    try:
        row = conn.execute("SELECT status FROM needs WHERE id = ?", (need_id,)).fetchone()
        if not row:
            return err('找不到此需求')
        if row['status'] not in ('已採購', '已調撥'):
            return err('狀態不符，無法標記到貨')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            "UPDATE needs SET status='已完成', arrived_at=?, completed_at=? WHERE id=?",
            (now, now, need_id)
        )
        conn.commit()
        return ok()
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()


@app.route('/api/needs/overdue-arrival')
def get_overdue_arrival():
    requester = request.args.get('requester', '').strip()
    if not requester:
        return err('缺少 requester')

    conn = get_db()
    try:
        transfer = conn.execute("""
            SELECT id, item_name, quantity, request_type, transfer_from,
                   processed_at as action_date, status,
                   julianday('now','localtime') - julianday(processed_at) as overdue_days
            FROM needs
            WHERE requester = ? AND request_type = '調撥' AND status = '已調撥'
              AND processed_at IS NOT NULL
              AND julianday('now','localtime') - julianday(processed_at) >= 3
              AND cancelled_at IS NULL
            ORDER BY processed_at ASC
        """, (requester,)).fetchall()

        purchase = conn.execute("""
            SELECT id, item_name, quantity, request_type, vendor_name,
                   processed_at as action_date, status,
                   julianday('now','localtime') - julianday(processed_at) as overdue_days
            FROM needs
            WHERE requester = ? AND request_type = '請購' AND status = '已採購'
              AND processed_at IS NOT NULL
              AND julianday('now','localtime') - julianday(processed_at) >= 5
              AND cancelled_at IS NULL
            ORDER BY processed_at ASC
        """, (requester,)).fetchall()

        items = [dict(r) for r in transfer] + [dict(r) for r in purchase]
        return jsonify({'success': True, 'items': items, 'count': len(items)})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 客戶搜尋
# ─────────────────────────────────────────────
@app.route('/api/customers/search')
def customers_search():
    q = (request.args.get('q') or '').strip()
    if not q:
        return ok([])
    like = f'%{q}%'
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT customer_id, short_name, full_name, mobile, tax_id
            FROM customers
            WHERE (short_name LIKE ? OR full_name LIKE ?
                   OR mobile LIKE ? OR tax_id LIKE ?
                   OR customer_id LIKE ?)
              AND status != 'inactive'
            ORDER BY short_name
            LIMIT 20
        """, (like, like, like, like, like)).fetchall()
        return ok([dict(r) for r in rows])
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 庫存（依產品代碼，回傳各倉庫）
# ─────────────────────────────────────────────
@app.route('/api/inventory/product/<code>')
def inventory_by_product(code):
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT warehouse, SUM(quantity) as quantity
            FROM inventory
            WHERE product_id = ?
            GROUP BY warehouse
            ORDER BY warehouse
        """, (code,)).fetchall()
        return ok([dict(r) for r in rows])
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 需求表批次送出
# ─────────────────────────────────────────────
import time as _time

@app.route('/api/needs/batch', methods=['POST'])
def needs_batch():
    data = request.get_json() or {}
    items = data.get('items', [])
    if not items:
        return err('請至少填寫一筆需求')

    header = data.get('header', {})
    date_val     = header.get('date') or datetime.today().strftime('%Y-%m-%d')
    request_type = header.get('request_type', '請購')
    purpose      = header.get('purpose', '備貨')
    requester    = (header.get('requester') or '').strip()
    department   = (header.get('department') or '').strip()
    customer_code = (header.get('customer_code') or '').strip()

    if not requester:
        return err('缺少提交者姓名')

    conn = get_db()
    try:
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 防重複送出：3秒內同人同品項
        inserted = []
        for item in items:
            product_code = (item.get('product_code') or '').strip()
            item_name    = (item.get('item_name') or '').strip()
            quantity     = item.get('quantity', 1)
            remark       = (item.get('remark') or '').strip()
            is_new_product = item.get('is_new_product', False)

            if not item_name and not product_code:
                continue

            # 驗證 product_code 格式（若有填）
            if product_code and not is_new_product:
                import re
                if not re.match(r'^[A-Z0-9\-]+$', product_code, re.IGNORECASE):
                    return err(f'產品代碼格式錯誤：{product_code}')

            # 3秒防重複
            dup = conn.execute("""
                SELECT id FROM needs
                WHERE requester = ? AND product_code = ? AND item_name = ?
                  AND datetime(created_at) >= datetime('now', '-3 seconds', 'localtime')
            """, (requester, product_code, item_name)).fetchone()
            if dup:
                continue

            conn.execute("""
                INSERT INTO needs
                  (date, request_type, purpose, requester, department,
                   customer_code, product_code, item_name, quantity, remark,
                   status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '待處理', ?)
            """, (date_val, request_type, purpose, requester, department,
                  customer_code, product_code, item_name, quantity, remark, now_str))
            inserted.append(item_name or product_code)

        conn.commit()
        if not inserted:
            return err('無有效資料可送出（可能重複提交）')
        return ok(count=len(inserted), items=inserted)
    except Exception as e:
        conn.rollback()
        return err(str(e), 500)
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 近期需求（30分鐘內，同部門）
# ─────────────────────────────────────────────
@app.route('/api/needs/recent')
def needs_recent():
    requester  = (request.args.get('requester') or '').strip()
    department = (request.args.get('department') or '').strip()
    title      = (request.args.get('title') or '').strip()

    if not requester:
        return err('缺少 requester')

    conn = get_db()
    try:
        # 老闆/會計可看全部，其他只看自己部門
        if title in ('老闆', '會計'):
            rows = conn.execute("""
                SELECT id, date, request_type, purpose, requester, department,
                       customer_code, product_code, item_name, quantity, remark,
                       status, created_at
                FROM needs
                WHERE datetime(created_at) >= datetime('now', '-30 minutes', 'localtime')
                  AND cancelled_at IS NULL
                ORDER BY created_at DESC
                LIMIT 50
            """).fetchall()
        elif department:
            rows = conn.execute("""
                SELECT id, date, request_type, purpose, requester, department,
                       customer_code, product_code, item_name, quantity, remark,
                       status, created_at
                FROM needs
                WHERE department = ?
                  AND datetime(created_at) >= datetime('now', '-30 minutes', 'localtime')
                  AND cancelled_at IS NULL
                ORDER BY created_at DESC
                LIMIT 50
            """, (department,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT id, date, request_type, purpose, requester, department,
                       customer_code, product_code, item_name, quantity, remark,
                       status, created_at
                FROM needs
                WHERE requester = ?
                  AND datetime(created_at) >= datetime('now', '-30 minutes', 'localtime')
                  AND cancelled_at IS NULL
                ORDER BY created_at DESC
                LIMIT 50
            """, (requester,)).fetchall()

        result = []
        for r in rows:
            d = dict(r)
            # 是否可取消：本人送出 且 30分鐘內 且 老闆/會計可強制
            can_cancel = (
                d['requester'] == requester
                or title in ('老闆', '會計')
            )
            d['can_cancel'] = can_cancel
            result.append(d)

        return ok(result)
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 取消需求
# ─────────────────────────────────────────────
@app.route('/api/needs/cancel', methods=['POST'])
def needs_cancel():
    data      = request.get_json() or {}
    need_id   = data.get('id')
    requester = (data.get('requester') or '').strip()
    title     = (data.get('title') or '').strip()

    if not need_id or not requester:
        return err('缺少必要欄位')

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT requester, status, created_at, cancelled_at FROM needs WHERE id = ?",
            (need_id,)
        ).fetchone()

        if not row:
            return err('找不到此需求')
        if row['cancelled_at']:
            return err('已取消')
        if row['status'] not in ('待處理', '', None):
            return err('此需求已在處理中，無法取消')

        # 權限：本人 或 老闆/會計
        if title not in ('老闆', '會計') and row['requester'] != requester:
            return err('無權限取消他人的需求')

        # 一般員工：30分鐘內才能取消
        if title not in ('老闆', '會計'):
            created = datetime.strptime(row['created_at'], '%Y-%m-%d %H:%M:%S')
            if (datetime.now() - created).total_seconds() > 1800:
                return err('超過30分鐘，無法取消')

        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            "UPDATE needs SET cancelled_at = ?, status = '已取消' WHERE id = ?",
            (now_str, need_id)
        )
        conn.commit()
        return ok()
    except Exception as e:
        conn.rollback()
        return err(str(e), 500)
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 需求歷史（分頁）
# ─────────────────────────────────────────────
@app.route('/api/needs/history')
def needs_history():
    requester  = (request.args.get('requester') or '').strip()
    department = (request.args.get('department') or '').strip()
    title      = (request.args.get('title') or '').strip()
    status_filter = request.args.get('status', 'all')  # all/active/done/cancelled
    search     = (request.args.get('search') or '').strip()
    page       = max(1, int(request.args.get('page', 1)))
    per_page   = 20

    conn = get_db()
    try:
        conditions = []
        params = []

        # 部門 / 角色 篩選
        if title not in ('老闆', '會計'):
            if department:
                conditions.append('department = ?')
                params.append(department)
            else:
                conditions.append('requester = ?')
                params.append(requester)

        # 狀態篩選
        if status_filter == 'active':
            conditions.append("(status IS NULL OR status IN ('', '待處理', '已採購', '已調撥'))")
            conditions.append('cancelled_at IS NULL')
        elif status_filter == 'done':
            conditions.append("status = '已完成'")
        elif status_filter == 'cancelled':
            conditions.append('cancelled_at IS NOT NULL')

        # 關鍵字
        if search:
            conditions.append("(item_name LIKE ? OR product_code LIKE ? OR requester LIKE ?)")
            like = f'%{search}%'
            params += [like, like, like]

        where = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''

        total = conn.execute(
            f'SELECT COUNT(*) FROM needs {where}', params
        ).fetchone()[0]

        rows = conn.execute(
            f"""SELECT id, date, request_type, purpose, requester, department,
                       customer_code, product_code, item_name, quantity, remark,
                       status, created_at, cancelled_at, completed_at
                FROM needs {where}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?""",
            params + [per_page, (page - 1) * per_page]
        ).fetchall()

        return ok(
            items=[dict(r) for r in rows],
            total=total,
            page=page,
            per_page=per_page,
            pages=(total + per_page - 1) // per_page
        )
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 老闆 — 待請購清單
# ─────────────────────────────────────────────
@app.route('/api/boss/pending-needs')
def boss_pending_needs():
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT n.id, n.date, n.product_code, n.item_name as product_name,
                   n.quantity, n.purpose, n.remark as notes,
                   n.requester, n.created_at, n.department,
                   n.customer_code, n.status, n.request_type
            FROM needs n
            WHERE n.cancelled_at IS NULL
              AND n.status IN ('待處理', '已採購')
              AND (n.request_type = '請購' OR n.request_type IS NULL OR n.request_type = '')
            ORDER BY
                CASE n.status WHEN '待處理' THEN 1 WHEN '已採購' THEN 2 END,
                n.created_at ASC
        """).fetchall()

        needs = []
        for row in rows:
            need = dict(row)

            # 客戶名稱
            cust = need.get('customer_code')
            if cust and cust not in ('nan', 'None', ''):
                c = conn.execute(
                    "SELECT short_name FROM customers WHERE customer_id = ? LIMIT 1",
                    (cust,)
                ).fetchone()
                if c:
                    need['customer_name'] = c['short_name']

            # 最近進貨
            pc = need.get('product_code')
            if pc:
                lp = conn.execute(
                    """SELECT supplier_name as vendor_name, price as last_price
                       FROM purchase_history WHERE product_code = ?
                       ORDER BY date DESC LIMIT 1""",
                    (pc,)
                ).fetchone()
                if lp:
                    need['last_vendor'] = lp['vendor_name']
                    need['last_price']  = lp['last_price']

            needs.append(need)

        # 統計
        oldest_days = None
        if needs:
            dates = [n['created_at'] for n in needs if n.get('created_at')]
            if dates:
                oldest = datetime.strptime(min(dates), '%Y-%m-%d %H:%M:%S')
                oldest_days = (datetime.now() - oldest).days

        stats = {
            'pending_count': len(needs),
            'total_amount': sum(
                (n.get('last_price') or 0) * (n.get('quantity') or 0)
                for n in needs if n.get('last_price')
            ),
            'product_count': len(set(n['product_code'] for n in needs if n.get('product_code'))),
            'oldest_days': oldest_days,
        }

        return jsonify({'success': True, 'needs': needs, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/needs/purchase', methods=['POST'])
def purchase_need():
    data      = request.get_json() or {}
    need_id   = data.get('id')
    requester = (data.get('requester') or '').strip()
    if not need_id or not requester:
        return err('缺少必要欄位')

    conn = get_db()
    try:
        user = conn.execute(
            "SELECT title FROM staff_passwords WHERE name = ?", (requester,)
        ).fetchone()
        if not user or user['title'] != '老闆':
            return err('無老闆權限', 403)

        row = conn.execute(
            "SELECT status FROM needs WHERE id = ?", (need_id,)
        ).fetchone()
        if not row:
            return err('找不到資料', 404)

        if row['status'] == '待處理':
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn.execute(
                "UPDATE needs SET status='已採購', processed_at=? WHERE id=?",
                (now, need_id)
            )
            conn.commit()
        return ok()
    except Exception as e:
        conn.rollback()
        return err(str(e), 500)
    finally:
        conn.close()


@app.route('/api/boss/needs/<int:need_id>/status', methods=['POST'])
def boss_update_need_status(need_id):
    data   = request.get_json() or {}
    status = data.get('status')
    conn   = get_db()
    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if status == 'cancelled':
            conn.execute(
                "UPDATE needs SET cancelled_at=?, status='已取消' WHERE id=?",
                (now, need_id)
            )
        else:
            return err('不支援的狀態')
        conn.commit()
        return ok()
    except Exception as e:
        conn.rollback()
        return err(str(e), 500)
    finally:
        conn.close()


@app.route('/api/boss/needs/<int:need_id>/notes', methods=['POST'])
def boss_update_need_notes(need_id):
    data  = request.get_json() or {}
    notes = data.get('notes', '')
    conn  = get_db()
    try:
        conn.execute("UPDATE needs SET remark=? WHERE id=?", (notes, need_id))
        conn.commit()
        return ok()
    except Exception as e:
        conn.rollback()
        return err(str(e), 500)
    finally:
        conn.close()


# ─────────────────────────────────────────────
# 輔助：業績期間日期範圍
# ─────────────────────────────────────────────
STORE_STAFF_LIST   = ['林榮祺', '林峙文', '劉育仕', '林煜捷', '張永承', '張家碩']
BUSINESS_STAFF_LIST = ['鄭宇晉', '梁仁佑']
ALL_PERF_STAFF = STORE_STAFF_LIST + BUSINESS_STAFF_LIST

def period_date_range(period_type, year, month):
    """回傳 (start_date, end_date) YYYY-MM-DD 字串"""
    import calendar
    if period_type == 'monthly':
        last_day = calendar.monthrange(year, month)[1]
        return f'{year}-{month:02d}-01', f'{year}-{month:02d}-{last_day:02d}'
    elif period_type == 'quarterly':
        q         = (month - 1) // 3
        sm        = q * 3 + 1
        em        = sm + 2
        last_day  = calendar.monthrange(year, em)[1]
        return f'{year}-{sm:02d}-01', f'{year}-{em:02d}-{last_day:02d}'
    else:  # yearly
        return f'{year}-01-01', f'{year}-12-31'

def quarter_months(month):
    """回傳本季的 start_month, end_month"""
    q  = (month - 1) // 3
    sm = q * 3 + 1
    return sm, sm + 2


# ─────────────────────────────────────────────
# API: 部門業績
# ─────────────────────────────────────────────
@app.route('/api/performance/department')
def get_dept_performance():
    today       = datetime.today()
    year        = request.args.get('year',        default=today.year,  type=int)
    month       = request.args.get('month',       default=today.month, type=int)
    period_type = request.args.get('period_type', default='quarterly')

    start_date, end_date = period_date_range(period_type, year, month)

    conn = get_db()
    try:
        # 實際業績（即時從 sales_history 算）
        ph = ','.join(['?'] * len(ALL_PERF_STAFF))
        rows = conn.execute(f"""
            SELECT
                CASE WHEN salesperson IN ({','.join(['?']*len(STORE_STAFF_LIST))})
                     THEN '門市部' ELSE '業務部' END as dept_name,
                SUM(amount) as revenue,
                SUM(profit) as profit,
                COUNT(*) as order_count
            FROM sales_history
            WHERE date >= ? AND date <= ?
              AND salesperson IN ({ph})
            GROUP BY dept_name
        """, STORE_STAFF_LIST + [start_date, end_date] + ALL_PERF_STAFF).fetchall()

        sales_map = {r['dept_name']: dict(r) for r in rows}

        # 目標（從 performance_metrics 讀）
        if period_type == 'monthly':
            tgt_rows = conn.execute("""
                SELECT subject_name, target_amount
                FROM performance_metrics
                WHERE category = '部門' AND year = ? AND month = ?
                  AND period_type = 'monthly'
            """, (year, month)).fetchall()
        elif period_type == 'quarterly':
            sm, em = quarter_months(month)
            tgt_rows = conn.execute("""
                SELECT subject_name, SUM(target_amount) as target_amount
                FROM performance_metrics
                WHERE category = '部門' AND year = ?
                  AND month >= ? AND month <= ? AND period_type = 'monthly'
                GROUP BY subject_name
            """, (year, sm, em)).fetchall()
        else:
            tgt_rows = conn.execute("""
                SELECT subject_name, SUM(target_amount) as target_amount
                FROM performance_metrics
                WHERE category = '部門' AND year = ? AND period_type = 'monthly'
                GROUP BY subject_name
            """, (year,)).fetchall()

        target_map = {r['subject_name']: r['target_amount'] for r in tgt_rows}

        result = []
        for dept in ['門市部', '業務部']:
            s       = sales_map.get(dept, {})
            revenue = s.get('revenue') or 0
            profit  = s.get('profit')  or 0
            target  = target_map.get(dept, 0) or 0
            result.append({
                'name':             dept,
                'target':           target,
                'revenue':          revenue,
                'profit':           profit,
                'order_count':      s.get('order_count', 0),
                'achievement_rate': revenue / target if target > 0 else 0,
                'margin_rate':      profit / revenue if revenue > 0 else 0,
                'year':             year,
                'month':            month,
                'period_type':      period_type,
                'start_date':       start_date,
                'end_date':         end_date,
            })

        return jsonify(result)
    except Exception as e:
        return jsonify([]), 500
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 部門每日趨勢（本期）
# ─────────────────────────────────────────────
@app.route('/api/performance/department/daily')
def dept_daily_trend():
    today       = datetime.today()
    year        = request.args.get('year',        default=today.year,  type=int)
    month       = request.args.get('month',       default=today.month, type=int)
    period_type = request.args.get('period_type', default='quarterly')

    start_date, end_date = period_date_range(period_type, year, month)
    conn = get_db()
    try:
        total_rows = {
            r['date']: r['total']
            for r in conn.execute(
                "SELECT date, SUM(amount) as total FROM sales_history "
                "WHERE date >= ? AND date <= ? AND salesperson IN ({}) "
                "GROUP BY date ORDER BY date".format(
                    ','.join(['?'] * len(ALL_PERF_STAFF))),
                [start_date, end_date] + ALL_PERF_STAFF
            ).fetchall()
        }
        store_rows = {
            r['date']: r['total']
            for r in conn.execute(
                "SELECT date, SUM(amount) as total FROM sales_history "
                "WHERE date >= ? AND date <= ? AND salesperson IN ({}) "
                "GROUP BY date ORDER BY date".format(
                    ','.join(['?'] * len(STORE_STAFF_LIST))),
                [start_date, end_date] + STORE_STAFF_LIST
            ).fetchall()
        }
        result = []
        for date, total in total_rows.items():
            store = store_rows.get(date, 0)
            result.append({'date': date, 'store': store, 'business': total - store})
        return jsonify(result)
    except Exception as e:
        return jsonify([])
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 門市業績
# ─────────────────────────────────────────────
STORE_MAP = {
    '豐原': ['林榮祺', '林峙文'],
    '潭子': ['劉育仕', '林煜捷'],
    '大雅': ['張永承', '張家碩'],
}
STORE_ORDER = ['豐原', '潭子', '大雅']

@app.route('/api/performance/store')
def get_store_performance():
    today       = datetime.today()
    year        = request.args.get('year',        default=today.year,  type=int)
    month       = request.args.get('month',       default=today.month, type=int)
    period_type = request.args.get('period_type', default='quarterly')

    start_date, end_date = period_date_range(period_type, year, month)

    conn = get_db()
    try:
        all_store_staff = [p for staff in STORE_MAP.values() for p in staff]
        ph = ','.join(['?'] * len(all_store_staff))
        rows = conn.execute(f"""
            SELECT salesperson, SUM(amount) as revenue, SUM(profit) as profit, COUNT(*) as order_count
            FROM sales_history
            WHERE date >= ? AND date <= ? AND salesperson IN ({ph})
            GROUP BY salesperson
        """, [start_date, end_date] + all_store_staff).fetchall()

        # 門市彙總
        store_stats = {s: {'revenue': 0, 'profit': 0, 'orders': 0} for s in STORE_ORDER}
        for r in rows:
            for store_name, staff_list in STORE_MAP.items():
                if r['salesperson'] in staff_list:
                    store_stats[store_name]['revenue'] += r['revenue'] or 0
                    store_stats[store_name]['profit']  += r['profit']  or 0
                    store_stats[store_name]['orders']  += r['order_count']

        # 目標
        if period_type == 'monthly':
            tgt_rows = conn.execute("""
                SELECT subject_name, target_amount FROM performance_metrics
                WHERE category = '門市' AND year=? AND month=? AND period_type='monthly'
            """, (year, month)).fetchall()
        elif period_type == 'quarterly':
            sm, em = quarter_months(month)
            tgt_rows = conn.execute("""
                SELECT subject_name, SUM(target_amount) as target_amount FROM performance_metrics
                WHERE category = '門市' AND year=? AND month>=? AND month<=? AND period_type='monthly'
                GROUP BY subject_name
            """, (year, sm, em)).fetchall()
        else:
            tgt_rows = conn.execute("""
                SELECT subject_name, SUM(target_amount) as target_amount FROM performance_metrics
                WHERE category = '門市' AND year=? AND period_type='monthly'
                GROUP BY subject_name
            """, (year,)).fetchall()

        # subject_name 可能是 '豐原門市' 也可能是 '豐原'
        target_map = {}
        for r in tgt_rows:
            key = r['subject_name'].replace('門市', '')
            target_map[key] = r['target_amount']

        result = []
        for store_name in STORE_ORDER:
            s       = store_stats[store_name]
            revenue = s['revenue']
            profit  = s['profit']
            target  = target_map.get(store_name, 0) or 0
            result.append({
                'store_name':       store_name,
                'target':           target,
                'revenue':          revenue,
                'profit':           profit,
                'order_count':      s['orders'],
                'achievement_rate': revenue / target if target > 0 else 0,
                'margin_rate':      profit / revenue if revenue > 0 else 0,
            })
        return jsonify(result)
    except Exception as e:
        return jsonify([])
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 門市五星好評數
# ─────────────────────────────────────────────
@app.route('/api/store/reviews')
def get_store_reviews():
    conn = get_db()
    try:
        # 優先用 google_reviews_stats（自動統計），否則用 store_reviews
        has_new = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='google_reviews_stats'"
        ).fetchone()

        if has_new:
            rows = conn.execute(
                "SELECT store_name, five_star as review_count FROM google_reviews_stats ORDER BY store_name"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT store_name, review_count FROM store_reviews ORDER BY store_name"
            ).fetchall()

        return jsonify([{'store': r['store_name'], 'reviews': r['review_count']} for r in rows])
    except Exception as e:
        return jsonify([])
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: Google 評論
# ─────────────────────────────────────────────
@app.route('/api/google-reviews')
def get_google_reviews():
    conn = get_db()
    try:
        has_tbl = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='google_reviews'"
        ).fetchone()
        if not has_tbl:
            return jsonify([])

        store     = request.args.get('store')
        min_stars = request.args.get('min_stars', type=int)
        limit     = request.args.get('limit', 50, type=int)

        conditions = []
        params = []
        if store:
            conditions.append('store_name = ?')
            params.append(store)
        if min_stars:
            conditions.append('star_rating >= ?')
            params.append(min_stars)

        where = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''
        rows = conn.execute(
            f"SELECT store_name, reviewer_name, review_date, star_rating, review_snippet, email_received_at "
            f"FROM google_reviews {where} ORDER BY email_received_at DESC LIMIT ?",
            params + [limit]
        ).fetchall()

        return jsonify([{
            'store':    r['store_name'],
            'reviewer': r['reviewer_name'],
            'date':     r['review_date'],
            'stars':    r['star_rating'],
            'snippet':  r['review_snippet'],
        } for r in rows])
    except Exception as e:
        return jsonify([])
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 門市督導評分（環境整潔，1-5項）
# ─────────────────────────────────────────────
@app.route('/api/store/supervision')
def get_store_supervision():
    score_type  = request.args.get('type', 'all')
    today       = datetime.today()
    date_start  = f'{today.year}-{today.month:02d}-01'
    conn        = get_db()
    try:
        if score_type == 'environment':
            rows = conn.execute("""
                SELECT store_name,
                    AVG(CAST(COALESCE(storefront_cleanliness,'0') AS FLOAT)) as avg_storefront,
                    AVG(CAST(COALESCE(store_cleanliness,'0')     AS FLOAT)) as avg_cleanliness,
                    AVG(CAST(COALESCE(product_display,'0')       AS FLOAT)) as avg_display,
                    AVG(CAST(COALESCE(cable_management,'0')      AS FLOAT)) as avg_cable,
                    AVG(CAST(COALESCE(warehouse_organization,'0') AS FLOAT)) as avg_warehouse
                FROM supervision_scores
                WHERE date >= ?
                GROUP BY store_name
            """, (date_start,)).fetchall()

            counts = {
                r['store_name']: r['inspection_count']
                for r in conn.execute(
                    "SELECT store_name, COUNT(DISTINCT date) as inspection_count "
                    "FROM supervision_scores WHERE date >= ? GROUP BY store_name",
                    (date_start,)
                ).fetchall()
            }

            result = []
            for r in rows:
                total = sum([
                    r['avg_storefront'] or 0,
                    r['avg_cleanliness'] or 0,
                    r['avg_display'] or 0,
                    r['avg_cable'] or 0,
                    r['avg_warehouse'] or 0,
                ])
                pct = round((total / 10) * 100) if total > 0 else 0
                result.append({
                    'store':            r['store_name'],
                    'percentage':       pct,
                    'raw_score':        round(total, 1),
                    'inspection_count': counts.get(r['store_name'], 0),
                })
            return jsonify(result)

        else:
            # 全項目平均
            rows = conn.execute("""
                SELECT store_name,
                    AVG(CAST(COALESCE(total_score,'0') AS FLOAT)) as avg_total,
                    AVG(CAST(COALESCE(percentage,'0')  AS FLOAT)) as avg_pct,
                    COUNT(DISTINCT date) as inspection_count
                FROM supervision_scores WHERE date >= ?
                GROUP BY store_name
            """, (date_start,)).fetchall()
            return jsonify([{
                'store':            r['store_name'],
                'avg_total':        round(r['avg_total'] or 0, 1),
                'percentage':       round(r['avg_pct'] or 0),
                'inspection_count': r['inspection_count'],
            } for r in rows])
    except Exception as e:
        return jsonify([])
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 個人業績排名
# ─────────────────────────────────────────────
EXCLUDED_NAMES = {'莊圍迪', '萬書佑', 'Unknown', '黃柏翰', ''}

@app.route('/api/performance/personal')
def get_personal_performance():
    today       = datetime.today()
    year        = request.args.get('year',        default=today.year,  type=int)
    month       = request.args.get('month',       default=today.month, type=int)
    period_type = request.args.get('period_type', default='quarterly')

    start_date, end_date = period_date_range(period_type, year, month)

    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT salesperson,
                   SUM(amount)  as revenue,
                   SUM(profit)  as profit,
                   COUNT(*)     as order_count
            FROM sales_history
            WHERE date >= ? AND date <= ?
              AND salesperson NOT IN ('莊圍迪','萬書佑','Unknown','黃柏翰','')
              AND product_code IS NOT NULL AND product_code != ''
              AND product_code LIKE '%-%'
            GROUP BY salesperson
            ORDER BY revenue DESC
        """, (start_date, end_date)).fetchall()

        # 目標
        if period_type == 'monthly':
            tgt_rows = conn.execute("""
                SELECT subject_name, target_amount FROM performance_metrics
                WHERE category='個人' AND year=? AND month=? AND period_type='monthly'
            """, (year, month)).fetchall()
        elif period_type == 'quarterly':
            sm, em = quarter_months(month)
            tgt_rows = conn.execute("""
                SELECT subject_name, SUM(target_amount) as target_amount FROM performance_metrics
                WHERE category='個人' AND year=? AND month>=? AND month<=? AND period_type='monthly'
                GROUP BY subject_name
            """, (year, sm, em)).fetchall()
        else:
            tgt_rows = conn.execute("""
                SELECT subject_name, SUM(target_amount) as target_amount FROM performance_metrics
                WHERE category='個人' AND year=? AND period_type='monthly'
                GROUP BY subject_name
            """, (year,)).fetchall()

        target_map = {r['subject_name']: r['target_amount'] for r in tgt_rows}

        result = []
        for rank, r in enumerate(rows, 1):
            name    = r['salesperson']
            if name in EXCLUDED_NAMES:
                continue
            revenue = r['revenue']  or 0
            profit  = r['profit']   or 0
            orders  = r['order_count'] or 0
            target  = target_map.get(name, 0) or 0
            result.append({
                'rank':             rank,
                'name':             name,
                'total':            revenue,
                'orders':           orders,
                'avg':              revenue // orders if orders > 0 else 0,
                'target':           target,
                'achievement_rate': revenue / target if target > 0 else 0,
                'margin_rate':      profit / revenue if revenue > 0 else 0,
            })
        return jsonify(result)
    except Exception as e:
        return jsonify([])
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 個人督導評分（本月，6-16項）
# ─────────────────────────────────────────────
SUPERVISION_FIELDS = [
    ('attendance',            '6. 出勤狀況'),
    ('appearance',            '7. 服裝儀容'),
    ('service_attitude',      '8. 服務態度'),
    ('professional_knowledge','9. 專業知識'),
    ('sales_process',         '10. 銷售流程'),
    ('work_attitude',         '11. 工作態度'),
    ('reply_speed',           '12. 回覆速度'),
    ('reply_attitude',        '13. 回覆態度'),
    ('problem_grasp',         '14. 問題掌握'),
    ('information_complete',  '15. 資料完整'),
    ('follow_up',             '16. 後續追蹤'),
]

@app.route('/api/personal/supervision')
def get_personal_supervision():
    user_name = (request.args.get('user') or '').strip()
    if not user_name:
        return jsonify({'success': False, 'message': '缺少使用者名稱'}), 400

    today      = datetime.today()
    date_start = f'{today.year}-{today.month:02d}-01'
    conn       = get_db()
    try:
        avgs = ', '.join(
            f"AVG(CAST(COALESCE({f},'0') AS FLOAT)) as avg_{f}"
            for f, _ in SUPERVISION_FIELDS
        )
        row = conn.execute(
            f"SELECT {avgs} FROM supervision_scores WHERE employee_name=? AND date>=?",
            (user_name, date_start)
        ).fetchone()

        if not row or row[f'avg_{SUPERVISION_FIELDS[0][0]}'] is None:
            return jsonify({'success': True, 'scores': None, 'message': '本月暫無評分資料'})

        scores = {f: round(row[f'avg_{f}'] or 0, 1) for f, _ in SUPERVISION_FIELDS}
        total  = sum(scores.values())
        max_t  = 22  # 11項 × 2分
        pct    = round((total / max_t) * 100)

        # 督導次數
        cnt = conn.execute(
            "SELECT COUNT(DISTINCT date) as cnt FROM supervision_scores WHERE employee_name=? AND date>=?",
            (user_name, date_start)
        ).fetchone()['cnt']

        return jsonify({
            'success':    True,
            'scores':     scores,
            'labels':     {f: lbl for f, lbl in SUPERVISION_FIELDS},
            'total':      round(total, 1),
            'max':        max_t,
            'percentage': pct,
            'count':      cnt,
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 業務部績效
# ─────────────────────────────────────────────
@app.route('/api/performance/business')
def get_business_performance():
    today       = datetime.today()
    year        = request.args.get('year',        default=today.year,  type=int)
    month       = request.args.get('month',       default=today.month, type=int)
    period_type = request.args.get('period_type', default='monthly')

    start_date, end_date = period_date_range(period_type, year, month)

    conn = get_db()
    try:
        placeholders = ','.join('?' * len(BUSINESS_STAFF_LIST))
        rows = conn.execute(f"""
            SELECT salesperson,
                   SUM(amount)  as revenue,
                   SUM(profit)  as profit,
                   COUNT(*)     as order_count
            FROM sales_history
            WHERE date >= ? AND date <= ?
              AND salesperson IN ({placeholders})
              AND product_code IS NOT NULL AND product_code != ''
              AND product_code LIKE '%-%'
            GROUP BY salesperson
            ORDER BY revenue DESC
        """, (start_date, end_date, *BUSINESS_STAFF_LIST)).fetchall()

        # 目標
        if period_type == 'monthly':
            tgt_rows = conn.execute("""
                SELECT subject_name, target_amount FROM performance_metrics
                WHERE category='個人' AND year=? AND month=? AND period_type='monthly'
                  AND subject_name IN ({})
            """.format(','.join('?' * len(BUSINESS_STAFF_LIST))),
                (year, month, *BUSINESS_STAFF_LIST)).fetchall()
        elif period_type == 'quarterly':
            sm, em = quarter_months(month)
            tgt_rows = conn.execute("""
                SELECT subject_name, SUM(target_amount) as target_amount FROM performance_metrics
                WHERE category='個人' AND year=? AND month>=? AND month<=? AND period_type='monthly'
                  AND subject_name IN ({})
                GROUP BY subject_name
            """.format(','.join('?' * len(BUSINESS_STAFF_LIST))),
                (year, sm, em, *BUSINESS_STAFF_LIST)).fetchall()
        else:
            tgt_rows = conn.execute("""
                SELECT subject_name, SUM(target_amount) as target_amount FROM performance_metrics
                WHERE category='個人' AND year=? AND period_type='monthly'
                  AND subject_name IN ({})
                GROUP BY subject_name
            """.format(','.join('?' * len(BUSINESS_STAFF_LIST))),
                (year, *BUSINESS_STAFF_LIST)).fetchall()

        target_map = {r['subject_name']: r['target_amount'] for r in tgt_rows}

        result = []
        for r in rows:
            name    = r['salesperson']
            revenue = r['revenue']  or 0
            profit  = r['profit']   or 0
            orders  = r['order_count'] or 0
            target  = target_map.get(name, 0) or 0
            result.append({
                'name':             name,
                'total':            revenue,
                'orders':           orders,
                'avg':              revenue // orders if orders > 0 else 0,
                'target':           target,
                'achievement_rate': revenue / target if target > 0 else 0,
                'margin_rate':      profit / revenue if revenue > 0 else 0,
            })

        # 確保 BUSINESS_STAFF_LIST 中未出現的人也有空資料
        existing = {r['name'] for r in result}
        for name in BUSINESS_STAFF_LIST:
            if name not in existing:
                result.append({
                    'name': name, 'total': 0, 'orders': 0, 'avg': 0,
                    'target': target_map.get(name, 0) or 0,
                    'achievement_rate': 0, 'margin_rate': 0,
                })

        return jsonify(result)
    except Exception as e:
        return jsonify([])
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 服務記錄統計（業務部頁面用）
# ─────────────────────────────────────────────
@app.route('/api/service-records/detail')
def get_service_records_detail():
    today       = datetime.today()
    year        = request.args.get('year',        default=today.year,  type=int)
    month       = request.args.get('month',       default=today.month, type=int)
    period_type = request.args.get('period_type', default='monthly')

    start_date, end_date = period_date_range(period_type, year, month)

    conn = get_db()
    try:
        # 業務員總覽
        placeholders = ','.join('?' * len(BUSINESS_STAFF_LIST))
        summary_rows = conn.execute(f"""
            SELECT salesperson,
                   COUNT(*)                    as total_count,
                   COUNT(DISTINCT customer_code) as unique_customers,
                   SUM(CASE WHEN is_contract=1 THEN 1 ELSE 0 END) as contract_count
            FROM service_records
            WHERE date >= ? AND date <= ?
              AND salesperson IN ({placeholders})
            GROUP BY salesperson
            ORDER BY total_count DESC
        """, (start_date, end_date, *BUSINESS_STAFF_LIST)).fetchall()

        # 服務類型分布
        type_rows = conn.execute(f"""
            SELECT service_type as type, COUNT(*) as count
            FROM service_records
            WHERE date >= ? AND date <= ?
              AND salesperson IN ({placeholders})
              AND service_type IS NOT NULL AND service_type != ''
            GROUP BY service_type
            ORDER BY count DESC
        """, (start_date, end_date, *BUSINESS_STAFF_LIST)).fetchall()

        # 客戶來源分布
        source_rows = conn.execute(f"""
            SELECT customer_source as source, COUNT(*) as count
            FROM service_records
            WHERE date >= ? AND date <= ?
              AND salesperson IN ({placeholders})
              AND customer_source IS NOT NULL AND customer_source != ''
            GROUP BY customer_source
            ORDER BY count DESC
        """, (start_date, end_date, *BUSINESS_STAFF_LIST)).fetchall()

        # 每日趨勢（最近 30 天）
        daily_start = (datetime.today() - timedelta(days=29)).strftime('%Y-%m-%d')
        daily_rows = conn.execute(f"""
            SELECT date, salesperson, COUNT(*) as count
            FROM service_records
            WHERE date >= ?
              AND salesperson IN ({placeholders})
            GROUP BY date, salesperson
            ORDER BY date DESC
        """, (daily_start, *BUSINESS_STAFF_LIST)).fetchall()

        return jsonify({
            'success': True,
            'salesperson_summary': [dict(r) for r in summary_rows],
            'service_types':       [dict(r) for r in type_rows],
            'customer_sources':    [dict(r) for r in source_rows],
            'daily_stats':         [dict(r) for r in daily_rows],
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e), 'salesperson_summary': [],
                        'service_types': [], 'customer_sources': [], 'daily_stats': []}), 500
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 客戶搜尋（完整版，含購買紀錄）
# ─────────────────────────────────────────────
@app.route('/api/customer/search')
def customer_search():
    q    = (request.args.get('q') or '').strip()
    page = request.args.get('page', default=1, type=int)
    per  = 20
    if not q:
        return jsonify({'success': True, 'customers': [], 'total': 0})
    like = f'%{q}%'
    conn = get_db()
    try:
        # 合併 customers + customer_master 搜尋
        rows = conn.execute("""
            SELECT customer_id, short_name,
                   phone1, mobile, tax_id, company_address, payment_type, updated_at
            FROM customers
            WHERE short_name LIKE ? OR mobile LIKE ? OR phone1 LIKE ?
                  OR tax_id LIKE ? OR customer_id LIKE ?
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
        """, (like, like, like, like, like, per, (page-1)*per)).fetchall()
        total = conn.execute("""
            SELECT COUNT(*) FROM customers
            WHERE short_name LIKE ? OR mobile LIKE ? OR phone1 LIKE ?
                  OR tax_id LIKE ? OR customer_id LIKE ?
        """, (like, like, like, like, like)).fetchone()[0]
        return jsonify({'success': True, 'customers': [dict(r) for r in rows], 'total': total})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/customer/detail/<customer_id>')
def customer_detail(customer_id):
    conn = get_db()
    try:
        cust = conn.execute(
            "SELECT * FROM customers WHERE customer_id=?", (customer_id,)
        ).fetchone()
        if not cust:
            return jsonify({'success': False, 'message': '找不到客戶'}), 404

        # 最近 50 筆購買紀錄
        sales = conn.execute("""
            SELECT date, invoice_no, product_code, product_name,
                   quantity, price, amount, salesperson
            FROM sales_history
            WHERE customer_id=?
            ORDER BY date DESC, id DESC
            LIMIT 50
        """, (customer_id,)).fetchall()

        # 消費統計
        stats = conn.execute("""
            SELECT COUNT(DISTINCT invoice_no) as order_count,
                   SUM(amount) as total_amount,
                   MAX(date)   as last_purchase
            FROM sales_history
            WHERE customer_id=?
        """, (customer_id,)).fetchone()

        return jsonify({
            'success':  True,
            'customer': dict(cust),
            'sales':    [dict(r) for r in sales],
            'stats':    dict(stats) if stats else {},
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 庫存查詢（列表）
# ─────────────────────────────────────────────
@app.route('/api/inventory/list')
def inventory_list():
    q         = (request.args.get('q') or '').strip()
    warehouse = (request.args.get('warehouse') or '').strip()
    page      = request.args.get('page', default=1, type=int)
    per       = 50
    conn = get_db()
    try:
        # 最新報告日期
        latest = conn.execute(
            "SELECT MAX(report_date) as d FROM inventory"
        ).fetchone()['d']

        conditions = ["i.report_date=?"]
        params     = [latest]
        if warehouse:
            conditions.append("i.warehouse=?")
            params.append(warehouse)
        if q:
            conditions.append("(i.product_id LIKE ? OR i.item_spec LIKE ?)")
            params.extend([f'%{q}%', f'%{q}%'])

        where = ' AND '.join(conditions)

        # 當月進貨加權平均成本（CTE）
        month_start = datetime.now().strftime('%Y-%m-01')
        month_end   = datetime.now().strftime('%Y-%m-%d')

        rows = conn.execute(f"""
            WITH monthly_cost AS (
                SELECT product_code,
                       CAST(SUM(amount) AS REAL) / SUM(quantity) AS avg_cost
                FROM purchase_history
                WHERE date >= ? AND date <= ?
                  AND quantity > 0 AND amount > 0
                GROUP BY product_code
            )
            SELECT i.product_id, i.item_spec, i.unit, i.warehouse, i.wh_type,
                   i.stock_quantity,
                   COALESCE(mc.avg_cost, i.unit_cost) AS unit_cost,
                   i.stock_quantity * COALESCE(mc.avg_cost, i.unit_cost) AS total_cost
            FROM inventory i
            LEFT JOIN monthly_cost mc ON mc.product_code = i.product_id
            WHERE {where} AND i.stock_quantity > 0
            ORDER BY CASE i.warehouse
                WHEN '豐原門市' THEN 1
                WHEN '潭子門市' THEN 2
                WHEN '大雅門市' THEN 3
                WHEN '業務部'   THEN 4
                WHEN '總公司倉庫' THEN 5
                ELSE 9 END, i.product_id
            LIMIT ? OFFSET ?
        """, (month_start, month_end, *params, per, (page-1)*per)).fetchall()

        total = conn.execute(f"""
            SELECT COUNT(*) FROM inventory i
            WHERE {where} AND i.stock_quantity > 0
        """, params).fetchone()[0]

        WH_ORDER = ['豐原門市', '潭子門市', '大雅門市', '業務部', '總公司倉庫']
        wh_raw = conn.execute("""
            SELECT DISTINCT warehouse FROM inventory
            WHERE report_date=?
        """, (latest,)).fetchall()
        wh_set = {r['warehouse'] for r in wh_raw}
        warehouses = [w for w in WH_ORDER if w in wh_set] + \
                     [w for w in sorted(wh_set) if w not in WH_ORDER]

        return jsonify({
            'success':    True,
            'data':       [dict(r) for r in rows],
            'total':      total,
            'report_date': latest,
            'warehouses': warehouses,
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 班表查詢
# ─────────────────────────────────────────────
@app.route('/api/roster/monthly')
def roster_monthly():
    today    = datetime.today()
    year     = request.args.get('year',  default=today.year,  type=int)
    month    = request.args.get('month', default=today.month, type=int)
    location = (request.args.get('location') or '').strip()
    conn = get_db()
    try:
        import calendar
        last_day = calendar.monthrange(year, month)[1]
        start = f'{year}-{month:02d}-01'
        end   = f'{year}-{month:02d}-{last_day:02d}'

        cond   = "WHERE date >= ? AND date <= ?"
        params = [start, end]
        if location:
            cond  += " AND location=?"
            params.append(location)

        rows = conn.execute(f"""
            SELECT date, staff_name, location, shift_code
            FROM staff_roster {cond}
            ORDER BY date, location, staff_name
        """, params).fetchall()

        # 整理成 {date: [{staff_name, location, shift_code}]}
        roster = {}
        for r in rows:
            roster.setdefault(r['date'], []).append({
                'staff_name': r['staff_name'],
                'location':   r['location'],
                'shift_code': r['shift_code'],
            })

        locations = conn.execute("""
            SELECT DISTINCT location FROM staff_roster
            WHERE date >= ? AND date <= ?
            ORDER BY location
        """, (start, end)).fetchall()

        return jsonify({
            'success':   True,
            'roster':    roster,
            'year':      year,
            'month':     month,
            'locations': [r['location'] for r in locations],
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 調撥需求（會計用）
# ─────────────────────────────────────────────
@app.route('/api/needs/transfers')
def needs_transfers():
    status   = request.args.get('status', default='待處理')
    dept     = (request.args.get('department') or '').strip()
    conn = get_db()
    try:
        cond   = "WHERE request_type='調撥' AND cancelled_at IS NULL"
        params = []
        if status == 'all':
            cond += " AND status IN ('待處理','已調撥','已完成')"
        else:
            cond  += " AND status=?"
            params.append(status)
        if dept:
            cond  += " AND department=?"
            params.append(dept)
        rows = conn.execute(f"""
            SELECT id, date, product_code, item_name, quantity,
                   department, requester, transfer_from, status, request_type,
                   remark, created_at, arrived_at, completed_at, processed_at
            FROM needs {cond}
            ORDER BY created_at DESC
            LIMIT 200
        """, params).fetchall()
        return jsonify({'success': True, 'needs': [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/needs/<int:need_id>/transfer', methods=['POST'])
def transfer_need(need_id):
    """會計將調撥需求「待處理」→「已調撥」"""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT status, request_type FROM needs WHERE id=?", (need_id,)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'message': '找不到此需求'}), 404
        if row['request_type'] != '調撥':
            return jsonify({'success': False, 'message': '此需求非調撥類型'}), 400
        if row['status'] != '待處理':
            return jsonify({'success': False, 'message': f'狀態不符（目前：{row["status"]}），無法標記已調撥'}), 400
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            "UPDATE needs SET status='已調撥', processed_at=? WHERE id=?",
            (now, need_id)
        )
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/needs/<int:need_id>/arrive', methods=['POST'])
def need_arrive(need_id):
    conn = get_db()
    try:
        conn.execute("""
            UPDATE needs SET arrived_at=datetime('now','localtime'), status='已到貨'
            WHERE id=?
        """, (need_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/needs/<int:need_id>/complete', methods=['POST'])
def need_complete(need_id):
    conn = get_db()
    try:
        conn.execute("""
            UPDATE needs SET completed_at=datetime('now','localtime'), status='已完成'
            WHERE id=?
        """, (need_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 門市主管 — 今日班表 + 本月小計
# ─────────────────────────────────────────────
@app.route('/api/store-manager/today')
def store_manager_today():
    dept     = (request.args.get('department') or '').strip()
    today    = datetime.today()
    date_str = today.strftime('%Y-%m-%d')
    # department 格式如「豐原門市」，location 是「豐原」
    location = dept.replace('門市', '').strip()

    conn = get_db()
    try:
        # 今日班表
        roster = conn.execute("""
            SELECT staff_name, shift_code, location
            FROM staff_roster WHERE date=? AND location=?
            ORDER BY staff_name
        """, (date_str, location)).fetchall()

        # 今日銷售（本門市員工）
        staff_names = [r['staff_name'] for r in roster] or ['__none__']
        ph = ','.join('?' * len(staff_names))
        today_sales = conn.execute(f"""
            SELECT salesperson, COUNT(*) as orders, SUM(amount) as revenue
            FROM sales_history
            WHERE date=? AND salesperson IN ({ph})
            GROUP BY salesperson
        """, (date_str, *staff_names)).fetchall()

        # 本月累計（本門市）
        month_start = f'{today.year}-{today.month:02d}-01'
        month_sales = conn.execute(f"""
            SELECT SUM(amount) as revenue, COUNT(*) as orders
            FROM sales_history
            WHERE date >= ? AND date <= ? AND salesperson IN ({ph})
        """, (month_start, date_str, *staff_names)).fetchone()

        # 本門市待處理需求
        pending = conn.execute("""
            SELECT id, product_code, item_name, quantity, requester,
                   request_type, status, created_at, remark
            FROM needs
            WHERE department=? AND status IN ('待處理','已到貨')
            ORDER BY created_at DESC
            LIMIT 30
        """, (dept,)).fetchall()

        return jsonify({
            'success':     True,
            'date':        date_str,
            'location':    location,
            'roster':      [dict(r) for r in roster],
            'today_sales': [dict(r) for r in today_sales],
            'month_revenue': month_sales['revenue'] or 0 if month_sales else 0,
            'month_orders':  month_sales['orders']  or 0 if month_sales else 0,
            'pending_needs': [dict(r) for r in pending],
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 服務記錄（外勤）
# ─────────────────────────────────────────────
@app.route('/api/service-records', methods=['GET'])
def service_records_list():
    salesperson = (request.args.get('salesperson') or '').strip()
    days        = request.args.get('days', default=30, type=int)
    since       = (datetime.today() - timedelta(days=days)).strftime('%Y-%m-%d')
    conn = get_db()
    try:
        cond   = "WHERE date >= ?"
        params = [since]
        if salesperson:
            cond  += " AND salesperson=?"
            params.append(salesperson)
        rows = conn.execute(f"""
            SELECT id, date, customer_code, customer_name, service_item,
                   service_type, customer_source, is_contract, salesperson, store, updated_at
            FROM service_records {cond}
            ORDER BY date DESC, id DESC LIMIT 100
        """, params).fetchall()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify([])
    finally:
        conn.close()


@app.route('/api/service-records', methods=['POST'])
def service_records_create():
    data = request.get_json() or {}
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO service_records
              (date, customer_code, customer_name, service_item, service_type,
               customer_source, is_contract, salesperson, store, is_new_customer, customer_status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data.get('date') or datetime.today().strftime('%Y-%m-%d'),
            data.get('customer_code', ''),
            data.get('customer_name', ''),
            data.get('service_item', ''),
            data.get('service_type', ''),
            data.get('customer_source', ''),
            1 if data.get('is_contract') else 0,
            data.get('salesperson', ''),
            data.get('store', ''),
            1 if data.get('is_new_customer') else 0,
            'approved',
        ))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/service-records/<int:record_id>', methods=['DELETE'])
def service_records_delete(record_id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM service_records WHERE id=?", (record_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 督導評分
# ─────────────────────────────────────────────
@app.route('/api/supervision/submit', methods=['POST'])
def supervision_submit():
    data = request.get_json() or {}
    env_fields    = ['storefront_cleanliness','store_cleanliness','product_display',
                     'cable_management','warehouse_organization']
    person_fields = ['attendance','appearance','service_attitude','professional_knowledge',
                     'sales_process','work_attitude','reply_speed','reply_attitude',
                     'problem_grasp','information_complete','follow_up']
    all_fields = env_fields + person_fields
    scores = {f: data.get(f) for f in all_fields}
    filled = [float(v) for v in scores.values() if v is not None and v != '']
    total  = sum(filled)
    pct    = round((total / 32) * 100, 1) if filled else 0

    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO supervision_scores
              (date, store_name, employee_name,
               storefront_cleanliness, store_cleanliness, product_display,
               cable_management, warehouse_organization,
               attendance, appearance, service_attitude, professional_knowledge,
               sales_process, work_attitude, reply_speed, reply_attitude,
               problem_grasp, information_complete, follow_up,
               total_score, percentage, issues, suggestions, evaluator, evaluator_title)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data.get('date') or datetime.today().strftime('%Y-%m-%d'),
            data.get('store_name', ''), data.get('employee_name', ''),
            scores.get('storefront_cleanliness'), scores.get('store_cleanliness'),
            scores.get('product_display'),        scores.get('cable_management'),
            scores.get('warehouse_organization'),
            scores.get('attendance'),             scores.get('appearance'),
            scores.get('service_attitude'),       scores.get('professional_knowledge'),
            scores.get('sales_process'),          scores.get('work_attitude'),
            scores.get('reply_speed'),            scores.get('reply_attitude'),
            scores.get('problem_grasp'),          scores.get('information_complete'),
            scores.get('follow_up'),
            total, pct,
            data.get('issues', ''), data.get('suggestions', ''),
            data.get('evaluator', ''), data.get('evaluator_title', ''),
        ))
        conn.commit()
        return jsonify({'success': True, 'total': total, 'percentage': pct})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/supervision/recent')
def supervision_recent():
    limit = request.args.get('limit', default=20, type=int)
    conn  = get_db()
    try:
        rows = conn.execute("""
            SELECT id, date, store_name, employee_name, total_score, percentage, evaluator, updated_at
            FROM supervision_scores
            ORDER BY date DESC, id DESC LIMIT ?
        """, (limit,)).fetchall()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify([])
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 班表批量輸入
# ─────────────────────────────────────────────
@app.route('/api/roster/batch', methods=['POST'])
def roster_batch():
    data    = request.get_json() or {}
    entries = data.get('entries', [])
    if not entries:
        return jsonify({'success': False, 'message': '無資料'}), 400
    conn = get_db()
    try:
        for e in entries:
            conn.execute("""
                INSERT INTO staff_roster (date, staff_name, location, shift_code, updated_at)
                VALUES (?,?,?,?,datetime('now','localtime'))
                ON CONFLICT(date, staff_name) DO UPDATE SET
                  shift_code=excluded.shift_code,
                  location=excluded.location,
                  updated_at=excluded.updated_at
            """, (e.get('date'), e.get('staff_name'), e.get('location'), e.get('shift_code')))
        conn.commit()
        return jsonify({'success': True, 'updated': len(entries)})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 業績目標
# ─────────────────────────────────────────────
@app.route('/api/targets')
def targets_get():
    today = datetime.today()
    year  = request.args.get('year',  default=today.year,  type=int)
    month = request.args.get('month', default=today.month, type=int)
    conn  = get_db()
    try:
        rows = conn.execute("""
            SELECT category, subject_name, target_amount, year, month
            FROM performance_metrics
            WHERE year=? AND month=? AND period_type='monthly'
            ORDER BY category, subject_name
        """, (year, month)).fetchall()
        return jsonify({'success': True, 'targets': [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/targets/save', methods=['POST'])
def targets_save():
    data    = request.get_json() or {}
    targets = data.get('targets', [])
    if not targets:
        return jsonify({'success': False, 'message': '無資料'}), 400
    conn = get_db()
    try:
        for t in targets:
            conn.execute("""
                INSERT INTO performance_metrics
                  (category, subject_name, target_amount, year, month, period_type,
                   revenue_amount, profit_amount, achievement_rate, margin_rate)
                VALUES (?,?,?,?,?,'monthly',0,0,0,0)
                ON CONFLICT(category, subject_name, year, month, period_type)
                  DO UPDATE SET target_amount=excluded.target_amount,
                                updated_at=datetime('now','localtime')
            """, (t.get('category'), t.get('subject_name'),
                  int(t.get('target_amount', 0)), t.get('year'), t.get('month')))
        conn.commit()
        return jsonify({'success': True, 'saved': len(targets)})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: 銷貨輸入
# ─────────────────────────────────────────────
@app.route('/api/products/search')
def products_search():
    """搜尋產品（從 inventory 及 products 表）"""
    q    = request.args.get('q', '').strip()
    wh   = request.args.get('warehouse', '')
    conn = get_db()
    try:
        if not q:
            return jsonify([])
        like = f'%{q}%'
        # 先從庫存查詢（有庫存量）
        rows = conn.execute("""
            SELECT DISTINCT i.product_id as product_code,
                   i.item_spec as product_name,
                   i.unit,
                   SUM(i.stock_quantity) as total_qty,
                   MAX(i.unit_cost) as unit_cost
            FROM inventory i
            WHERE (i.product_id LIKE ? OR i.item_spec LIKE ?)
              AND i.stock_quantity > 0
            GROUP BY i.product_id, i.item_spec
            ORDER BY i.item_spec
            LIMIT 30
        """, (like, like)).fetchall()
        if not rows:
            # fallback：從 products 表
            rows2 = conn.execute("""
                SELECT product_code, product_name, unit, 0 as total_qty, 0 as unit_cost
                FROM products
                WHERE product_code LIKE ? OR product_name LIKE ?
                ORDER BY product_name LIMIT 20
            """, (like, like)).fetchall()
            return jsonify([dict(r) for r in rows2])
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/query/sales')
def query_sales():
    """單據查詢頁 — 銷貨單（支援日期範圍）"""
    q         = request.args.get('q', '').strip()
    date_from = request.args.get('from', '').strip()
    date_to   = request.args.get('to', '').strip()
    page      = request.args.get('page', 1, type=int)
    per_page  = 30
    conn      = get_db()
    try:
        conds, params = [], []
        if q:
            conds.append("(customer_name LIKE ? OR salesperson LIKE ? OR product_name LIKE ? OR invoice_no LIKE ?)")
            params += [f'%{q}%'] * 4
        if date_from:
            conds.append("date >= ?"); params.append(date_from)
        if date_to:
            conds.append("date <= ?"); params.append(date_to)
        where = ('WHERE ' + ' AND '.join(conds)) if conds else ''
        offset = (page - 1) * per_page

        total = conn.execute(f"SELECT COUNT(*) FROM sales_history {where}", params).fetchone()[0]

        month_start = datetime.now().strftime('%Y-%m-01')
        month_end   = datetime.now().strftime('%Y-%m-%d')

        rows = conn.execute(f"""
            WITH monthly_cost AS (
                SELECT product_code,
                       CAST(SUM(amount) AS REAL) / SUM(quantity) AS avg_cost
                FROM purchase_history
                WHERE date >= ? AND date <= ?
                  AND quantity > 0 AND amount > 0
                GROUP BY product_code
            )
            SELECT s.id, s.invoice_no, s.date, s.customer_name, s.salesperson,
                   s.product_code, s.product_name, s.quantity, s.price, s.amount,
                   COALESCE(mc.avg_cost, s.cost) AS cost,
                   s.amount - s.quantity * COALESCE(mc.avg_cost, s.cost) AS profit,
                   CASE WHEN s.amount > 0
                        THEN ROUND((s.amount - s.quantity * COALESCE(mc.avg_cost, s.cost)) * 100.0 / s.amount, 1)
                        ELSE NULL END AS margin
            FROM sales_history s
            LEFT JOIN monthly_cost mc ON mc.product_code = s.product_code
            {where}
            ORDER BY s.date DESC, s.invoice_no DESC, s.id ASC
            LIMIT ? OFFSET ?
        """, [month_start, month_end] + params + [per_page, offset]).fetchall()

        return jsonify({
            'success': True,
            'total': total,
            'pages': max(1, -(-total // per_page)),
            'rows': [dict(r) for r in rows],
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/sales/list')
def sales_list():
    """銷貨紀錄列表（逐筆）"""
    q         = request.args.get('q', '').strip()
    sp        = request.args.get('salesperson', '')
    page      = request.args.get('page', 1, type=int)
    per_page  = 30
    offset    = (page - 1) * per_page
    conn      = get_db()
    try:
        conds, params = [], []
        if q:
            conds.append("(invoice_no LIKE ? OR customer_name LIKE ? OR product_name LIKE ? OR salesperson LIKE ?)")
            params += [f'%{q}%', f'%{q}%', f'%{q}%', f'%{q}%']
        if sp:
            conds.append("salesperson = ?")
            params.append(sp)
        where = ('WHERE ' + ' AND '.join(conds)) if conds else ''

        total = conn.execute(
            f"SELECT COUNT(*) FROM sales_history {where}", params
        ).fetchone()[0]

        month_start = datetime.now().strftime('%Y-%m-01')
        month_end   = datetime.now().strftime('%Y-%m-%d')

        rows = conn.execute(f"""
            WITH monthly_cost AS (
                SELECT product_code,
                       CAST(SUM(amount) AS REAL) / SUM(quantity) AS avg_cost
                FROM purchase_history
                WHERE date >= ? AND date <= ?
                  AND quantity > 0 AND amount > 0
                GROUP BY product_code
            )
            SELECT s.id, s.invoice_no, s.date, s.customer_name, s.salesperson,
                   s.product_code, s.product_name, s.quantity, s.price, s.amount,
                   COALESCE(mc.avg_cost, s.cost) AS cost,
                   s.amount - s.quantity * COALESCE(mc.avg_cost, s.cost) AS profit,
                   CASE WHEN s.amount > 0
                        THEN ROUND((s.amount - s.quantity * COALESCE(mc.avg_cost, s.cost)) * 100.0 / s.amount, 1)
                        ELSE NULL END AS margin
            FROM sales_history s
            LEFT JOIN monthly_cost mc ON mc.product_code = s.product_code
            {where}
            ORDER BY s.date DESC, s.invoice_no DESC, s.id ASC
            LIMIT ? OFFSET ?
        """, [month_start, month_end] + params + [per_page, offset]).fetchall()

        return jsonify({
            'success': True,
            'total': total,
            'pages': (total + per_page - 1) // per_page,
            'page': page,
            'rows': [dict(r) for r in rows]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/sales/submit', methods=['POST'])
def sales_submit():
    """新增銷貨單 → 寫入 sales_history"""
    data     = request.get_json() or {}
    items    = data.get('items', [])
    if not items:
        return jsonify({'success': False, 'message': '請至少輸入一項產品'}), 400

    invoice_no    = data.get('invoice_no', '').strip()
    date          = data.get('date', '')
    customer_id   = data.get('customer_id', '')
    customer_name = data.get('customer_name', '')
    salesperson   = data.get('salesperson', '')
    salesperson_id= data.get('salesperson_id', '')

    if not date or not invoice_no:
        return jsonify({'success': False, 'message': '日期與發票號碼為必填'}), 400

    conn = get_db()
    try:
        # 確認發票號碼不重複
        exists = conn.execute(
            "SELECT 1 FROM sales_history WHERE invoice_no=? LIMIT 1", (invoice_no,)
        ).fetchone()
        if exists:
            return jsonify({'success': False, 'message': f'發票號碼 {invoice_no} 已存在'}), 409

        for idx, it in enumerate(items):
            product_code = it.get('product_code', '')
            product_name = it.get('product_name', '')
            qty          = int(it.get('quantity', 1))
            price        = float(it.get('price', 0))
            cost         = float(it.get('cost', 0))
            amount       = qty * price
            profit       = amount - qty * cost
            margin       = round(profit / amount * 100, 2) if amount else 0

            conn.execute("""
                INSERT INTO sales_history
                  (invoice_no, date, customer_id, salesperson, product_code,
                   product_name, quantity, price, amount, customer_name,
                   cost, profit, margin, salesperson_id, source_file, source_row)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (invoice_no, date, customer_id, salesperson, product_code,
                  product_name, qty, price, amount, customer_name,
                  cost, profit, margin, salesperson_id, 'manual', idx + 1))

        conn.commit()
        return jsonify({'success': True, 'invoice_no': invoice_no, 'item_count': len(items)})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/sales/<invoice_no>', methods=['DELETE'])
def sales_delete(invoice_no):
    """刪除整張銷貨單（需老闆/督導權限，前端控制）"""
    conn = get_db()
    try:
        affected = conn.execute(
            "DELETE FROM sales_history WHERE invoice_no=?", (invoice_no,)
        ).rowcount
        conn.commit()
        return jsonify({'success': True, 'deleted': affected})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/sales/row/<int:row_id>', methods=['DELETE'])
def sales_delete_row(row_id):
    """逐筆刪除單一銷貨紀錄（需老闆權限，前端控制）"""
    conn = get_db()
    try:
        affected = conn.execute(
            "DELETE FROM sales_history WHERE id=?", (row_id,)
        ).rowcount
        conn.commit()
        if affected == 0:
            return jsonify({'success': False, 'message': '找不到此筆紀錄'}), 404
        return jsonify({'success': True, 'deleted': affected})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


# ─────────────────────────────────────────────
# Phase 6：LINE 回覆表
# ─────────────────────────────────────────────
@app.route('/api/line-replies', methods=['GET'])
def line_replies_list():
    conn = get_db()
    try:
        page     = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 30))
        keyword  = request.args.get('keyword', '').strip()
        resolved = request.args.get('resolved', '')   # '0' | '1' | ''
        store    = request.args.get('store', '').strip()

        conds, params = [], []
        if keyword:
            conds.append('(customer_line_name LIKE ? OR inquiry_content LIKE ? OR reply_content LIKE ?)')
            params.extend([f'%{keyword}%'] * 3)
        if resolved in ('0', '1'):
            conds.append('is_resolved=?')
            params.append(int(resolved))
        if store:
            conds.append('reply_store=?')
            params.append(store)

        where = ('WHERE ' + ' AND '.join(conds)) if conds else ''
        total = conn.execute(f'SELECT COUNT(*) FROM line_replies {where}', params).fetchone()[0]
        offset = (page - 1) * per_page
        rows = conn.execute(
            f'SELECT * FROM line_replies {where} ORDER BY reply_datetime DESC LIMIT ? OFFSET ?',
            params + [per_page, offset]
        ).fetchall()
        return jsonify({
            'success': True, 'total': total,
            'pages': (total + per_page - 1) // per_page,
            'page': page,
            'rows': [dict(r) for r in rows]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/line-replies', methods=['POST'])
def line_replies_create():
    data = request.get_json() or {}
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO line_replies
              (reply_datetime, customer_line_name, inquiry_content, reply_content,
               reply_store, reply_staff, is_resolved)
            VALUES (?,?,?,?,?,?,?)
        """, (
            data.get('reply_datetime', ''),
            data.get('customer_line_name', ''),
            data.get('inquiry_content', ''),
            data.get('reply_content', ''),
            data.get('reply_store', ''),
            data.get('reply_staff', ''),
            int(data.get('is_resolved', 0))
        ))
        conn.commit()
        return jsonify({'success': True, 'id': conn.execute('SELECT last_insert_rowid()').fetchone()[0]})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/line-replies/<int:rid>', methods=['PUT'])
def line_replies_update(rid):
    data = request.get_json() or {}
    conn = get_db()
    try:
        fields, vals = [], []
        for col in ('reply_datetime', 'customer_line_name', 'inquiry_content',
                    'reply_content', 'reply_store', 'reply_staff', 'is_resolved'):
            if col in data:
                fields.append(f'{col}=?')
                vals.append(data[col])
        if not fields:
            return jsonify({'success': False, 'message': '無更新欄位'}), 400
        vals.append(rid)
        conn.execute(f'UPDATE line_replies SET {", ".join(fields)} WHERE id=?', vals)
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/line-replies/<int:rid>', methods=['DELETE'])
def line_replies_delete(rid):
    conn = get_db()
    try:
        conn.execute('DELETE FROM line_replies WHERE id=?', (rid,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


# ─────────────────────────────────────────────
# Phase 6：個人獎金查詢
# ─────────────────────────────────────────────
@app.route('/api/bonus-personal', methods=['GET'])
def bonus_personal():
    """查詢指定人員在日期範圍內的獎金明細（bonus_results 表）"""
    salesperson = request.args.get('salesperson', '').strip()
    date_start  = request.args.get('date_start', '')
    date_end    = request.args.get('date_end', '')
    conn = get_db()
    try:
        conds, params = [], []
        if salesperson:
            conds.append('salesperson=?')
            params.append(salesperson)
        if date_start:
            conds.append('sale_date>=?')
            params.append(date_start)
        if date_end:
            conds.append('sale_date<=?')
            params.append(date_end)

        where = ('WHERE ' + ' AND '.join(conds)) if conds else ''
        rows = conn.execute(
            f'SELECT * FROM bonus_results {where} ORDER BY sale_date DESC',
            params
        ).fetchall()

        total_bonus = sum(r['bonus_amount'] for r in rows)
        return jsonify({
            'success': True,
            'total_bonus': total_bonus,
            'count': len(rows),
            'rows': [dict(r) for r in rows]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


# ─────────────────────────────────────────────
# Phase 6：待建檔中心
# ─────────────────────────────────────────────
@app.route('/api/staging/list', methods=['GET'])
def staging_list():
    """列出所有待處理暫存記錄（customer/product）"""
    conn = get_db()
    try:
        status = request.args.get('status', 'pending')
        type_  = request.args.get('type', '')

        conds, params = ['1=1'], []
        if status:
            conds.append('sr.status=?')
            params.append(status)
        if type_:
            conds.append('sr.type=?')
            params.append(type_)

        where = 'WHERE ' + ' AND '.join(conds)
        rows = conn.execute(
            f'SELECT * FROM staging_records {where} ORDER BY created_at DESC',
            params
        ).fetchall()
        return jsonify({'success': True, 'rows': [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/staging/<int:sid>/resolve', methods=['PUT'])
def staging_resolve(sid):
    conn = get_db()
    try:
        conn.execute(
            "UPDATE staging_records SET status='resolved' WHERE id=?", (sid,)
        )
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/product-staging/list', methods=['GET'])
def product_staging_list():
    conn = get_db()
    try:
        status = request.args.get('status', 'pending')
        conds, params = ['1=1'], []
        if status:
            conds.append('status=?')
            params.append(status)
        rows = conn.execute(
            f'SELECT * FROM product_staging WHERE {" AND ".join(conds)} ORDER BY created_at DESC',
            params
        ).fetchall()
        return jsonify({'success': True, 'rows': [dict(r) for r in rows]})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/product-staging/<int:sid>/resolve', methods=['PUT'])
def product_staging_resolve(sid):
    conn = get_db()
    try:
        conn.execute(
            "UPDATE product_staging SET status='resolved' WHERE id=?", (sid,)
        )
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/staging/stats', methods=['GET'])
def staging_stats():
    """取得各類型待處理數量（供首頁等使用）"""
    conn = get_db()
    try:
        sr_pending = conn.execute(
            "SELECT COUNT(*) FROM staging_records WHERE status='pending'"
        ).fetchone()[0]
        ps_pending = conn.execute(
            "SELECT COUNT(*) FROM product_staging WHERE status='pending'"
        ).fetchone()[0]
        return jsonify({
            'success': True,
            'staging_records': sr_pending,
            'product_staging': ps_pending,
            'total': sr_pending + ps_pending
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


# ─────────────────────────────────────────────
# 學生 AI 聊天室 (Port 0329)
# ─────────────────────────────────────────────
# 學生 AI 聊天室 API（公開，無需登入）
# ─────────────────────────────────────────────
@app.route('/api/student-chat', methods=['POST'])
def student_chat_api():
    """學生 AI 聊天 API - 連接到本地 oMLX 模型"""
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({'success': False, 'message': '請輸入訊息'}), 400
    
    try:
        # 呼叫本地 oMLX 模型
        import requests
        
        # oMLX 本地 API 端點 (預設在 port 8000 或其他端口)
        # 這裡使用簡單的 HTTP 請求到本地模型
        omlx_url = os.environ.get('OMLX_URL', 'http://localhost:8000/v1/chat/completions')
        
        # 如果沒有 oMLX，使用簡單回應做示範
        if os.environ.get('USE_SIMPLE_RESPONSE', 'true').lower() == 'true':
            # 示範模式：根據關鍵字給回應
            response_text = generate_demo_response(message)
            return jsonify({'success': True, 'response': response_text})
        
        # 實際呼叫 oMLX
        response = requests.post(omlx_url, json={
            'model': 'qwen3.5-9b',
            'messages': [
                {'role': 'system', 'content': '你是一個友善、有創意的 AI 助理，專門陪伴高中生聊天、抒發情緒、發想創意。請用輕鬆、溫暖的語氣回應。'},
                {'role': 'user', 'content': message}
            ],
            'stream': False,
            'max_tokens': 500
        }, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            ai_message = result['choices'][0]['message']['content']
            return jsonify({'success': True, 'response': ai_message})
        else:
            # 如果 oMLX 沒有回應，使用示範回應
            response_text = generate_demo_response(message)
            return jsonify({'success': True, 'response': response_text})
            
    except Exception as e:
        # 發生錯誤時使用示範回應
        response_text = generate_demo_response(message)
        return jsonify({'success': True, 'response': response_text})

def generate_demo_response(message):
    """示範模式：根據關鍵字產生回應"""
    msg_lower = message.lower()
    
    if any(k in msg_lower for k in ['煩', '累', '壓力', '不開心', '難過']):
        return "聽起來你最近有點辛苦呢... 要不要說說發生了什麼事？有時候把心事說出來會舒服一點 🤗"
    
    elif any(k in msg_lower for k in ['點子', '創意', '想法', '建議']):
        return "好呀！讓我們一起動動腦筋 💡\n\n1. 試試看「腦力激盪」：先不管可不可行，把所有想到的都寫下來\n2. 換個角度想：如果是你喜歡的作家/導演，他們會怎麼處理？\n3. 結合興趣：把你喜歡的事物混搭在一起，常常會有驚喜！\n\n你想針對哪個方向深入聊聊？"
    
    elif any(k in msg_lower for k in ['故事', '小說', '劇本', '科幻']):
        return "來編個故事吧！🚀\n\n「當人類發現，夢境其實是另一個平行宇宙的入口...」\n\n你覺得接下來會發生什麼事？主角是誰？他/她為什麼要進入夢境世界？"
    
    elif any(k in msg_lower for k in ['音樂', '歌', '聽歌']):
        return "音樂是最好的療癒！🎵\n\n看你想要什麼氛圍：\n• 放鬆：Lo-fi hip hop、輕爵士\n• 專注：古典樂、環境音樂\n• 充電：獨立搖滾、電子音樂\n\n你現在是什麼心情？我可以推薦更具體的！"
    
    elif any(k in msg_lower for k in ['放鬆', '休息', '無聊']):
        return "放鬆也很重要！這裡有幾個點子 ✨\n\n• 試試「5-4-3-2-1」技巧：找出5個看到的、4個摸到的、3個聽到的、2個聞到的、1個嚐到的\n• 畫個塗鴉，不用想太多\n• 聽一首沒聽過的歌，閉上眼睛感受\n• 寫下三件今天值得感謝的事\n\n哪個聽起來不錯？"
    
    elif any(k in msg_lower for k in ['你好', '嗨', 'hi', 'hello']):
        return "嗨！很高興認識你 👋\n\n我是 COSH AI，可以陪你聊天、發想點子、或者只是靜靜地聽你說話。\n\n今天想聊什麼呢？"
    
    else:
        return "有趣的想法！可以多說一點嗎？我很好奇你的想法 💭\n\n或者，如果你想轉換心情，我可以：\n• 幫你想一些創意點子\n• 陪你聊聊心情\n• 一起發想故事\n• 推薦放鬆的方式"

# ─────────────────────────────────────────────
# 報價作業（quote_input）
# ─────────────────────────────────────────────
def _ensure_sales_doc_schema(conn):
    """補齊 sales_documents / sales_document_items 所需欄位"""
    doc_cols  = {c[1] for c in conn.execute('PRAGMA table_info(sales_documents)')}
    item_cols = {c[1] for c in conn.execute('PRAGMA table_info(sales_document_items)')}
    for col, dtype in [('target_name','TEXT'),('created_by','TEXT'),('note','TEXT'),('valid_until','TEXT')]:
        if col not in doc_cols:
            conn.execute(f'ALTER TABLE sales_documents ADD COLUMN {col} {dtype}')
    for col, dtype in [('product_name','TEXT'),('note','TEXT')]:
        if col not in item_cols:
            conn.execute(f'ALTER TABLE sales_document_items ADD COLUMN {col} {dtype}')
    conn.commit()


@app.route('/quote_input')
def quote_input():
    return render_template('quote_input.html')


# ─────────────────────────────────────────────
# 進貨輸入
# ─────────────────────────────────────────────
@app.route('/purchase_input')
def purchase_input():
    return render_template('purchase_input.html')


@app.route('/query')
def doc_query():
    return render_template('query.html')


@app.route('/api/purchase/next-no')
def purchase_next_no():
    date_str = (request.args.get('date') or datetime.now().strftime('%Y%m%d'))[:8]
    conn = get_db()
    try:
        prefix = f'PO-{date_str}-'
        rows = conn.execute(
            "SELECT order_no FROM purchase_history WHERE order_no LIKE ? ORDER BY order_no DESC LIMIT 1",
            (prefix + '%',)
        ).fetchone()
        if rows:
            last_seq = int(rows['order_no'].split('-')[-1])
            seq = last_seq + 1
        else:
            seq = 1
        return jsonify({'success': True, 'order_no': f'{prefix}{seq:03d}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/purchase/suppliers')
def purchase_suppliers():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT DISTINCT supplier_name FROM purchase_history WHERE supplier_name IS NOT NULL ORDER BY supplier_name"
        ).fetchall()
        return jsonify({'success': True, 'suppliers': [r['supplier_name'] for r in rows]})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/purchase/submit', methods=['POST'])
def purchase_submit():
    data = request.get_json() or {}
    order_no  = (data.get('order_no') or '').strip()
    date      = (data.get('date') or '').strip()
    supplier  = (data.get('supplier_name') or '').strip()
    invoice   = (data.get('invoice_number') or '').strip()
    warehouse = (data.get('warehouse') or '').strip()
    created_by= (data.get('created_by') or '').strip()
    items     = data.get('items', [])

    if not order_no or not date or not supplier or not items:
        return jsonify({'success': False, 'message': '單號、日期、供應商、品項為必填'}), 400

    conn = get_db()
    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for item in items:
            qty    = int(item.get('quantity', 0))
            price  = float(item.get('price', 0))
            amount = round(qty * price)
            conn.execute("""
                INSERT INTO purchase_history
                  (order_no, invoice_number, date, supplier_name,
                   product_code, product_name, quantity, price, amount,
                   warehouse, created_by, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (order_no, invoice or None, date, supplier,
                  item.get('product_code',''), item.get('product_name',''),
                  qty, price, amount,
                  warehouse or None, created_by or None, now))
        conn.commit()
        return jsonify({'success': True, 'order_no': order_no, 'item_count': len(items)})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/purchase/list')
def purchase_list():
    q         = request.args.get('q', '').strip()
    date_from = request.args.get('from', '').strip()
    date_to   = request.args.get('to', '').strip()
    page      = request.args.get('page', 1, type=int)
    per_page  = 30
    offset    = (page - 1) * per_page
    conn = get_db()
    try:
        where  = "WHERE 1=1"
        params = []
        if q:
            where += " AND (order_no LIKE ? OR supplier_name LIKE ? OR product_name LIKE ? OR invoice_number LIKE ?)"
            params += [f'%{q}%'] * 4
        if date_from:
            where += " AND date >= ?"; params.append(date_from)
        if date_to:
            where += " AND date <= ?"; params.append(date_to)
        total = conn.execute(f"SELECT COUNT(*) FROM purchase_history {where}", params).fetchone()[0]
        rows  = conn.execute(f"""
            SELECT id, order_no, invoice_number, date, supplier_name,
                   product_code, product_name, quantity, price, amount,
                   warehouse, created_by
            FROM purchase_history {where}
            ORDER BY date DESC, order_no DESC, id ASC
            LIMIT ? OFFSET ?
        """, params + [per_page, offset]).fetchall()
        return jsonify({
            'success': True,
            'rows':  [dict(r) for r in rows],
            'total': total,
            'pages': max(1, -(-total // per_page)),
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/purchase/row/<int:row_id>', methods=['DELETE'])
def purchase_delete_row(row_id):
    conn = get_db()
    try:
        affected = conn.execute("DELETE FROM purchase_history WHERE id=?", (row_id,)).rowcount
        conn.commit()
        if affected == 0:
            return jsonify({'success': False, 'message': '找不到此筆紀錄'}), 404
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/quote/next-no')
def quote_next_no():
    date_str = (request.args.get('date') or datetime.now().strftime('%Y%m%d'))[:8]
    conn = get_db()
    try:
        _ensure_sales_doc_schema(conn)
        prefix = f'QT{date_str}-'
        row = conn.execute(
            "SELECT doc_no FROM sales_documents WHERE doc_type='QUOTE' AND doc_no LIKE ? "
            "ORDER BY doc_no DESC LIMIT 1", (prefix + '%',)
        ).fetchone()
        seq = 1
        if row:
            try: seq = int(row['doc_no'].split('-')[-1]) + 1
            except: pass
        return jsonify({'success': True, 'quote_no': f'{prefix}{seq:03d}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/sales-doc/create', methods=['POST'])
def sales_doc_create():
    data = request.get_json() or {}
    doc_no   = (data.get('doc_no') or '').strip()
    doc_type = (data.get('doc_type') or 'QUOTE').strip()
    target_id   = (data.get('target_id') or '').strip()
    target_name = (data.get('target_name') or '').strip()
    total   = int(data.get('total_amount') or 0)
    items   = data.get('items') or []
    created_by  = (data.get('created_by') or '').strip()
    note    = (data.get('note') or '').strip()
    valid_until = (data.get('valid_until') or '').strip()

    if not doc_no or not target_name or not items:
        return jsonify({'success': False, 'message': '缺少必要欄位'}), 400

    conn = get_db()
    try:
        _ensure_sales_doc_schema(conn)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("""
            INSERT INTO sales_documents
              (doc_no, doc_type, target_id, target_name, total_amount,
               deposit_amount, balance_amount, status, created_by, note, valid_until,
               created_at, updated_at)
            VALUES (?,?,?,?,?, 0,?,?,?, ?,?, ?,?)
        """, (doc_no, doc_type, target_id, target_name, total,
              total, 'DRAFT', created_by, note, valid_until, now, now))
        for it in items:
            pname = (it.get('product_name') or '').strip()
            pcode = (it.get('product_code') or pname).strip()
            qty   = int(it.get('qty') or 1)
            price = int(it.get('unit_price') or 0)
            sub   = int(it.get('subtotal') or qty * price)
            item_note = (it.get('note') or '').strip()
            conn.execute("""
                INSERT INTO sales_document_items
                  (doc_no, product_code, product_name, qty, unit_price, subtotal, note, created_at)
                VALUES (?,?,?,?,?,?,?,?)
            """, (doc_no, pcode, pname, qty, price, sub, item_note, now))
        conn.commit()
        return jsonify({'success': True, 'doc_no': doc_no})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/sales-doc/list')
def sales_doc_list():
    doc_type = (request.args.get('type') or 'QUOTE').strip()
    limit    = min(int(request.args.get('limit') or 30), 100)
    keyword  = (request.args.get('q') or '').strip()
    conn = get_db()
    try:
        _ensure_sales_doc_schema(conn)
        cond, params = "WHERE doc_type=?", [doc_type]
        if keyword:
            cond += " AND (doc_no LIKE ? OR target_name LIKE ?)"
            params += [f'%{keyword}%', f'%{keyword}%']
        rows = conn.execute(
            f"SELECT * FROM sales_documents {cond} ORDER BY created_at DESC LIMIT ?",
            params + [limit]
        ).fetchall()
        docs = []
        for r in rows:
            d = dict(r)
            items = conn.execute(
                "SELECT * FROM sales_document_items WHERE doc_no=? ORDER BY id",
                (d['doc_no'],)
            ).fetchall()
            d['items'] = [dict(i) for i in items]
            docs.append(d)
        return jsonify({'success': True, 'documents': docs})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/sales-doc/query')
def sales_doc_query():
    doc_type   = (request.args.get('type') or '').strip()   # QUOTE / ORDER / '' = 全部
    status     = (request.args.get('status') or '').strip()
    q          = (request.args.get('q') or '').strip()
    date_from  = (request.args.get('from') or '').strip()
    date_to    = (request.args.get('to') or '').strip()
    page       = request.args.get('page', 1, type=int)
    per_page   = 20
    conn = get_db()
    try:
        _ensure_sales_doc_schema(conn)
        conds, params = [], []
        if doc_type:
            conds.append("doc_type=?"); params.append(doc_type)
        if status:
            conds.append("status=?"); params.append(status)
        if q:
            conds.append("(doc_no LIKE ? OR target_name LIKE ? OR note LIKE ?)")
            params += [f'%{q}%', f'%{q}%', f'%{q}%']
        if date_from:
            conds.append("DATE(created_at) >= ?"); params.append(date_from)
        if date_to:
            conds.append("DATE(created_at) <= ?"); params.append(date_to)
        where = ('WHERE ' + ' AND '.join(conds)) if conds else ''

        total = conn.execute(
            f"SELECT COUNT(*) FROM sales_documents {where}", params
        ).fetchone()[0]

        rows = conn.execute(
            f"SELECT * FROM sales_documents {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [per_page, (page-1)*per_page]
        ).fetchall()

        docs = []
        for r in rows:
            d = dict(r)
            items = conn.execute(
                "SELECT * FROM sales_document_items WHERE doc_no=? ORDER BY id",
                (d['doc_no'],)
            ).fetchall()
            d['items'] = [dict(i) for i in items]
            docs.append(d)

        return jsonify({
            'success': True,
            'documents': docs,
            'total': total,
            'pages': max(1, -(-total // per_page)),
            'page': page,
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/sales-doc/status', methods=['POST'])
def sales_doc_status():
    """更新單據狀態"""
    data   = request.get_json() or {}
    doc_no = (data.get('doc_no') or '').strip()
    status = (data.get('status') or '').strip()
    if not doc_no or not status:
        return jsonify({'success': False, 'message': '缺少參數'}), 400
    conn = get_db()
    try:
        _ensure_sales_doc_schema(conn)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            "UPDATE sales_documents SET status=?, updated_at=? WHERE doc_no=?",
            (status, now, doc_no)
        )
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/sales-doc/delete', methods=['POST'])
def sales_doc_delete():
    data   = request.get_json() or {}
    doc_no = (data.get('doc_no') or '').strip()
    if not doc_no:
        return jsonify({'success': False, 'message': '缺少單號'}), 400
    conn = get_db()
    try:
        _ensure_sales_doc_schema(conn)
        conn.execute("DELETE FROM sales_document_items WHERE doc_no=?", (doc_no,))
        conn.execute("DELETE FROM sales_documents WHERE doc_no=?", (doc_no,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/sales-doc/convert', methods=['POST'])
def sales_doc_convert():
    data       = request.get_json() or {}
    src_no     = (data.get('source_doc_no') or '').strip()
    tgt_type   = (data.get('target_type') or 'ORDER').strip()
    deposit    = int(data.get('deposit_amount') or 0)
    created_by = (data.get('created_by') or '').strip()
    if not src_no:
        return jsonify({'success': False, 'message': '缺少來源單號'}), 400
    conn = get_db()
    try:
        _ensure_sales_doc_schema(conn)
        src = conn.execute(
            "SELECT * FROM sales_documents WHERE doc_no=?", (src_no,)
        ).fetchone()
        if not src:
            return jsonify({'success': False, 'message': '找不到來源單據'}), 404
        src = dict(src)
        # 產生新單號
        prefix_map = {'ORDER': 'SO', 'INVOICE': 'IV'}
        prefix = prefix_map.get(tgt_type, tgt_type[:2])
        today  = datetime.now().strftime('%Y%m%d')
        row = conn.execute(
            "SELECT doc_no FROM sales_documents WHERE doc_type=? AND doc_no LIKE ? "
            "ORDER BY doc_no DESC LIMIT 1",
            (tgt_type, f'{prefix}{today}-%')
        ).fetchone()
        seq = 1
        if row:
            try: seq = int(row['doc_no'].split('-')[-1]) + 1
            except: pass
        new_no  = f'{prefix}{today}-{seq:03d}'
        total   = src['total_amount']
        balance = total - deposit
        now     = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("""
            INSERT INTO sales_documents
              (doc_no, doc_type, target_id, target_name, total_amount,
               deposit_amount, balance_amount, source_doc_no, status,
               created_by, note, created_at, updated_at)
            VALUES (?,?,?,?,?, ?,?,?,?,?,?,?,?)
        """, (new_no, tgt_type, src.get('target_id',''), src.get('target_name',''),
              total, deposit, balance, src_no, 'DRAFT',
              created_by, src.get('note',''), now, now))
        # 複製明細
        items = conn.execute(
            "SELECT * FROM sales_document_items WHERE doc_no=?", (src_no,)
        ).fetchall()
        for it in items:
            conn.execute("""
                INSERT INTO sales_document_items
                  (doc_no, product_code, product_name, qty, unit_price, subtotal, note, created_at)
                VALUES (?,?,?,?,?,?,?,?)
            """, (new_no, it['product_code'], it.get('product_name',''),
                  it['qty'], it['unit_price'], it['subtotal'],
                  it.get('note',''), now))
        # 更新來源單狀態
        conn.execute(
            "UPDATE sales_documents SET status='CONVERTED', updated_at=? WHERE doc_no=?",
            (now, src_no)
        )
        conn.commit()
        return jsonify({'success': True, 'new_doc_no': new_no})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


# ─────────────────────────────────────────────
# 錯誤處理
# ─────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'success': False, 'message': '伺服器錯誤', 'detail': str(e)}), 500


# ─────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8800))
    app.run(host='0.0.0.0', port=port, debug=True)
