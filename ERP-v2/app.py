#!/usr/bin/env python3
# ERP v2 — OpenClaw
# Port 8800 (測試用)

import os
import uuid
import sqlite3
import json
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, jsonify, request, abort, send_from_directory, send_file


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
# 待建檔 staging 共用邏輯
# ─────────────────────────────────────────────
import re as _re

def _gen_temp_id(conn, prefix):
    """產生臨時編號：TEMP-YYYYMMDD-NNN（流水號）"""
    today = datetime.now().strftime('%Y%m%d')
    tag = f'TEMP-{today}-'
    # 查找今天最大流水號
    if prefix == 'C':
        col = 'temp_customer_id'
    else:
        col = 'temp_product_id'
    row = conn.execute(
        f"SELECT {col} FROM staging_records WHERE {col} LIKE ? ORDER BY {col} DESC LIMIT 1",
        (f'{tag}%',)
    ).fetchone()
    if row and row[0]:
        try:
            seq = int(row[0].replace(tag, '')) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f'{tag}{seq:03d}'


def _clean_mobile(mobile):
    """清理手機號碼，回傳 09 開頭 10 碼或 None"""
    if not mobile:
        return None
    cleaned = _re.sub(r'[^0-9]', '', str(mobile))
    if _re.match(r'^09\d{8}$', cleaned):
        return cleaned
    return None


def staging_ensure_customer(conn, raw_name, raw_mobile, requester, department,
                            source_type='needs', source_id=None):
    """確保新客戶進入 staging。同手機去重，回傳 temp_customer_id。"""
    clean_mob = _clean_mobile(raw_mobile)
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if clean_mob:
        # 同手機去重：檢查是否已有 pending 的同手機記錄
        existing = conn.execute(
            """SELECT id, raw_input, temp_customer_id FROM staging_records
               WHERE type='customer' AND raw_mobile=? AND status='pending'""",
            (clean_mob,)
        ).fetchone()
        if existing:
            # 更新 last_seen_at
            conn.execute(
                "UPDATE staging_records SET last_seen_at=? WHERE id=?",
                (now_str, existing['id'])
            )
            # 同手機不同姓名：加註記
            if raw_name and existing['raw_input'] != raw_name:
                conn.execute(
                    """UPDATE staging_records SET audit_log=COALESCE(audit_log,'')||?
                       WHERE id=?""",
                    (f'\n[{now_str}] 同手機({clean_mob})不同姓名待確認: {existing["raw_input"]} vs {raw_name}',
                     existing['id'])
                )
            return existing['temp_customer_id']

    # 建立新的 staging 記錄
    temp_id = _gen_temp_id(conn, 'C')
    conn.execute(
        """INSERT INTO staging_records
           (type, raw_input, raw_mobile, temp_customer_id,
            source_type, source_id, requester, department,
            status, created_at, last_seen_at)
           VALUES ('customer',?,?,?,?,?,?,?,'pending',?,?)""",
        (raw_name, clean_mob, temp_id,
         source_type, source_id, requester, department,
         now_str, now_str)
    )
    return temp_id


def staging_ensure_product(conn, raw_name, requester, department,
                           source_type='needs', source_id=None):
    """新品產品進入 staging（每筆獨立，不去重）。回傳 temp_product_id。"""
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    temp_id = _gen_temp_id(conn, 'P')
    conn.execute(
        """INSERT INTO staging_records
           (type, raw_input, temp_product_id,
            source_type, source_id, requester, department,
            status, created_at, last_seen_at)
           VALUES ('product',?,?,?,?,?,?,'pending',?,?)""",
        (raw_name, temp_id,
         source_type, source_id, requester, department,
         now_str, now_str)
    )
    return temp_id


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
    password = (data.get('password') or '').strip()

    if not password:
        return err('請輸入密碼')

    conn = get_db()
    users = conn.execute(
        '''SELECT sp.name, sp.password, sp.title, sp.department,
                  s.staff_id as employee_id
           FROM staff_passwords sp
           LEFT JOIN staff s ON s.staff_id = sp.staff_id
           WHERE sp.password = ?''',
        (password,)
    ).fetchall()
    conn.close()

    if not users:
        return err('密碼錯誤', 401)
    if len(users) > 1:
        return err('密碼重複，請聯繫管理員設定唯一密碼', 401)

    user = users[0]
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
        '''INSERT INTO system_announcements (title, content, level, is_active, created_at)
           VALUES (?, ?, ?, 1, datetime('now','localtime'))''',
        (title, content, data.get('level', 'info'))
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
            SELECT customer_id, short_name, mobile, phone1, tax_id, payment_type
            FROM customers
            WHERE (short_name LIKE ?
                   OR mobile LIKE ? OR phone1 LIKE ?
                   OR tax_id LIKE ?
                   OR customer_id LIKE ?)
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
        latest = conn.execute("SELECT MAX(report_date) FROM inventory").fetchone()[0]
        WH_ORDER = ['豐原門市','潭子門市','大雅門市','業務部','總公司倉庫']
        rows = conn.execute("""
            SELECT warehouse, SUM(stock_quantity) as quantity
            FROM inventory
            WHERE product_id = ? AND report_date = ? AND stock_quantity > 0
            GROUP BY warehouse
        """, (code, latest)).fetchall()
        data = sorted([dict(r) for r in rows],
                      key=lambda x: WH_ORDER.index(x['warehouse'])
                                    if x['warehouse'] in WH_ORDER else 99)
        return ok(data)
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
    # 支援兩種格式：header 內的 request_type，或根層級的 request_type（推薦備貨選購使用）
    request_type = header.get('request_type') or data.get('request_type', '請購')
    purpose      = header.get('purpose', '備貨')
    requester    = (header.get('requester') or data.get('staff_name') or '').strip()
    department   = (header.get('department') or data.get('staff_dept') or '').strip()
    customer_code = (header.get('customer_code') or '').strip()
    transfer_from = (header.get('transfer_from') or data.get('transfer_from') or '').strip()

    if not requester:
        return err('缺少提交者姓名')

    # 新客戶資訊
    is_new_customer = header.get('is_new_customer', False)
    customer_name   = (header.get('customer_name') or '').strip()
    customer_mobile = (header.get('customer_mobile') or '').strip()

    conn = get_db()
    try:
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # ── 新客戶 staging 自動建檔 ──
        temp_customer_id = None
        if is_new_customer and customer_name:
            temp_customer_id = staging_ensure_customer(
                conn, customer_name, customer_mobile,
                requester, department, source_type='needs')
            # 用臨時編號作為 customer_code
            customer_code = temp_customer_id

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
                if not _re.match(r'^[A-Z0-9\-]+$', product_code, _re.IGNORECASE):
                    return err(f'產品代碼格式錯誤：{product_code}')

            # ── 新品產品 staging 自動建檔 ──
            if is_new_product and item_name:
                temp_prod_id = staging_ensure_product(
                    conn, item_name, requester, department, source_type='needs')
                # 用臨時編號取代空的 product_code
                if not product_code:
                    product_code = temp_prod_id

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
                   status, created_at, transfer_from,
                   is_new_customer, is_new_product)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '待處理', ?, ?, ?, ?)
            """, (date_val, request_type, purpose, requester, department,
                  customer_code, product_code, item_name, quantity, remark,
                  now_str, transfer_from,
                  1 if is_new_customer else 0,
                  1 if is_new_product else 0))
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
        # 實際業績（即時從 sales_history 算，毛利以當期進貨均價重算）
        ph = ','.join(['?'] * len(ALL_PERF_STAFF))
        rows = conn.execute(f"""
            WITH monthly_cost AS (
                SELECT product_code,
                       CAST(SUM(amount) AS REAL) / SUM(quantity) AS avg_cost
                FROM purchase_history
                WHERE date >= ? AND date <= ?
                  AND quantity > 0 AND amount > 0
                GROUP BY product_code
            )
            SELECT
                CASE WHEN s.salesperson IN ({','.join(['?']*len(STORE_STAFF_LIST))})
                     THEN '門市部' ELSE '業務部' END as dept_name,
                SUM(s.amount) as revenue,
                SUM(s.amount - s.quantity * COALESCE(mc.avg_cost, s.cost * 1.0 / MAX(s.quantity, 1))) as profit,
                COUNT(*) as order_count
            FROM sales_history s
            LEFT JOIN monthly_cost mc ON mc.product_code = s.product_code
            WHERE s.date >= ? AND s.date <= ?
              AND s.salesperson IN ({ph})
            GROUP BY dept_name
        """, [start_date, end_date] + STORE_STAFF_LIST + [start_date, end_date] + ALL_PERF_STAFF).fetchall()

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
            WITH monthly_cost AS (
                SELECT product_code,
                       CAST(SUM(amount) AS REAL) / SUM(quantity) AS avg_cost
                FROM purchase_history
                WHERE date >= ? AND date <= ?
                  AND quantity > 0 AND amount > 0
                GROUP BY product_code
            )
            SELECT s.salesperson,
                   SUM(s.amount) as revenue,
                   SUM(s.amount - s.quantity * COALESCE(mc.avg_cost, s.cost * 1.0 / MAX(s.quantity, 1))) as profit,
                   COUNT(*) as order_count
            FROM sales_history s
            LEFT JOIN monthly_cost mc ON mc.product_code = s.product_code
            WHERE s.date >= ? AND s.date <= ? AND s.salesperson IN ({ph})
            GROUP BY s.salesperson
        """, [start_date, end_date] + [start_date, end_date] + all_store_staff).fetchall()

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
# API: 門市五星好評（依當季 google_reviews 即時統計）
@app.route('/api/store/reviews')
def get_store_reviews():
    conn = get_db()
    try:
        # 計算本季起始日
        today = datetime.now()
        q_month = ((today.month - 1) // 3) * 3 + 1  # 1,4,7,10
        q_start = f'{today.year}-{q_month:02d}-01'

        # 優先從 google_reviews 即時統計本季五星數
        has_gr = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='google_reviews'"
        ).fetchone()

        if has_gr:
            rows = conn.execute(
                """SELECT store_name, COUNT(*) as review_count
                   FROM google_reviews
                   WHERE star_rating = 5 AND review_date >= ?
                   GROUP BY store_name ORDER BY store_name""",
                (q_start,)
            ).fetchall()
        else:
            # fallback: 舊版 store_reviews
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
                pct = round((total / 25) * 100) if total > 0 else 0
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
            WITH monthly_cost AS (
                SELECT product_code,
                       CAST(SUM(amount) AS REAL) / SUM(quantity) AS avg_cost
                FROM purchase_history
                WHERE date >= ? AND date <= ?
                  AND quantity > 0 AND amount > 0
                GROUP BY product_code
            )
            SELECT s.salesperson,
                   SUM(s.amount) as revenue,
                   SUM(s.amount - s.quantity * COALESCE(mc.avg_cost, s.cost * 1.0 / MAX(s.quantity, 1))) as profit,
                   COUNT(*) as order_count
            FROM sales_history s
            LEFT JOIN monthly_cost mc ON mc.product_code = s.product_code
            WHERE s.date >= ? AND s.date <= ?
              AND s.salesperson NOT IN ('莊圍迪','萬書佑','Unknown','黃柏翰','')
              AND s.product_code IS NOT NULL AND s.product_code != ''
              AND s.product_code LIKE '%-%'
            GROUP BY s.salesperson
            ORDER BY revenue DESC
        """, (start_date, end_date, start_date, end_date)).fetchall()

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
        max_t  = 55  # 11項 × 5分
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


# API: 所有人員督導評分（老闆用）
@app.route('/api/personal/supervision/all')
def get_all_personal_supervision():
    today      = datetime.today()
    date_start = f'{today.year}-{today.month:02d}-01'
    conn       = get_db()
    try:
        # 取得本月有評分的所有人員
        names = conn.execute(
            "SELECT DISTINCT employee_name FROM supervision_scores WHERE date >= ? ORDER BY employee_name",
            (date_start,)
        ).fetchall()
        if not names:
            return ok(staff=[])

        avgs = ', '.join(
            f"AVG(CAST(COALESCE({f},'0') AS FLOAT)) as avg_{f}"
            for f, _ in SUPERVISION_FIELDS
        )

        result = []
        for nr in names:
            emp = nr['employee_name']
            row = conn.execute(
                f"SELECT {avgs} FROM supervision_scores WHERE employee_name=? AND date>=?",
                (emp, date_start)
            ).fetchone()
            if not row or row[f'avg_{SUPERVISION_FIELDS[0][0]}'] is None:
                continue

            scores = {f: round(row[f'avg_{f}'] or 0, 1) for f, _ in SUPERVISION_FIELDS}
            total  = sum(scores.values())
            max_t  = len(SUPERVISION_FIELDS) * 5
            pct    = round((total / max_t) * 100)
            cnt    = conn.execute(
                "SELECT COUNT(DISTINCT date) as cnt FROM supervision_scores WHERE employee_name=? AND date>=?",
                (emp, date_start)
            ).fetchone()['cnt']

            result.append({
                'name':       emp,
                'scores':     scores,
                'total':      round(total, 1),
                'max':        max_t,
                'percentage': pct,
                'count':      cnt,
            })

        # 依百分比降序
        result.sort(key=lambda x: x['percentage'], reverse=True)
        return ok(
            staff=result,
            labels={f: lbl for f, lbl in SUPERVISION_FIELDS}
        )
    except Exception as e:
        return err(str(e))
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
            WITH monthly_cost AS (
                SELECT product_code,
                       CAST(SUM(amount) AS REAL) / SUM(quantity) AS avg_cost
                FROM purchase_history
                WHERE date >= ? AND date <= ?
                  AND quantity > 0 AND amount > 0
                GROUP BY product_code
            )
            SELECT s.salesperson,
                   SUM(s.amount) as revenue,
                   SUM(s.amount - s.quantity * COALESCE(mc.avg_cost, s.cost * 1.0 / MAX(s.quantity, 1))) as profit,
                   COUNT(*) as order_count
            FROM sales_history s
            LEFT JOIN monthly_cost mc ON mc.product_code = s.product_code
            WHERE s.date >= ? AND s.date <= ?
              AND s.salesperson IN ({placeholders})
              AND s.product_code IS NOT NULL AND s.product_code != ''
              AND s.product_code LIKE '%-%'
            GROUP BY s.salesperson
            ORDER BY revenue DESC
        """, (start_date, end_date, start_date, end_date, *BUSINESS_STAFF_LIST)).fetchall()

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
    per  = 50
    conn = get_db()
    try:
        if q:
            like   = f'%{q}%'
            where  = "WHERE short_name LIKE ? OR mobile LIKE ? OR phone1 LIKE ? OR tax_id LIKE ? OR customer_id LIKE ?"
            params = (like, like, like, like, like)
            order  = "ORDER BY updated_at DESC"
        else:
            where  = ""
            params = ()
            order  = "ORDER BY updated_at DESC"
        rows = conn.execute(f"""
            SELECT customer_id, short_name,
                   phone1, mobile, tax_id, company_address, payment_type, updated_at
            FROM customers {where} {order}
            LIMIT ? OFFSET ?
        """, (*params, per, (page-1)*per)).fetchall()
        total = conn.execute(
            f"SELECT COUNT(*) FROM customers {where}", params
        ).fetchone()[0]
        return jsonify({'success': True, 'customers': [dict(r) for r in rows], 'total': total, 'page': page, 'per': per})
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
            ),
            inv_latest AS (
                SELECT product_id, item_spec, unit, warehouse, wh_type,
                       SUM(stock_quantity)  AS stock_quantity,
                       MAX(unit_cost)       AS unit_cost
                FROM inventory i
                WHERE {where} AND i.stock_quantity > 0
                GROUP BY product_id, item_spec, unit, warehouse, wh_type
            )
            SELECT i.product_id, i.item_spec, i.unit, i.warehouse, i.wh_type,
                   i.stock_quantity,
                   COALESCE(mc.avg_cost, i.unit_cost) AS unit_cost,
                   i.stock_quantity * COALESCE(mc.avg_cost, i.unit_cost) AS total_cost
            FROM inv_latest i
            LEFT JOIN monthly_cost mc ON mc.product_code = i.product_id
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
            SELECT COUNT(*) FROM (
                SELECT product_id, warehouse
                FROM inventory i
                WHERE {where} AND i.stock_quantity > 0
                GROUP BY product_id, warehouse
            )
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
        row = conn.execute("SELECT status FROM needs WHERE id=?", (need_id,)).fetchone()
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
        return err(str(e))
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
        is_new = data.get('is_new_customer', False)
        customer_name = (data.get('customer_name') or '').strip()
        customer_code = (data.get('customer_code') or '').strip()
        customer_mobile = (data.get('customer_mobile') or '').strip()
        salesperson = (data.get('salesperson') or '').strip()
        store = (data.get('store') or '').strip()

        # ── 新客戶 staging 自動建檔 ──
        if is_new and customer_name:
            temp_id = staging_ensure_customer(
                conn, customer_name, customer_mobile,
                salesperson, store, source_type='service_records')
            customer_code = temp_id

        conn.execute("""
            INSERT INTO service_records
              (date, customer_code, customer_name, service_item, service_type,
               customer_source, is_contract, salesperson, store, is_new_customer, customer_status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data.get('date') or datetime.today().strftime('%Y-%m-%d'),
            customer_code,
            customer_name,
            data.get('service_item', ''),
            data.get('service_type', ''),
            data.get('customer_source', ''),
            1 if data.get('is_contract') else 0,
            salesperson,
            store,
            1 if is_new else 0,
            'approved',
        ))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/service-records/<int:record_id>', methods=['PUT'])
def service_records_update(record_id):
    data = request.get_json() or {}
    conn = get_db()
    try:
        fields, vals = [], []
        for col in ('date', 'customer_code', 'customer_name', 'service_item',
                     'service_type', 'customer_source', 'salesperson', 'store'):
            if col in data:
                fields.append(f'{col}=?')
                vals.append(data[col])
        if 'is_contract' in data:
            fields.append('is_contract=?')
            vals.append(1 if data['is_contract'] else 0)
        if 'is_new_customer' in data:
            fields.append('is_new_customer=?')
            vals.append(1 if data['is_new_customer'] else 0)
        if not fields:
            return jsonify({'success': False, 'message': '無更新欄位'}), 400
        vals.append(record_id)
        conn.execute(f"UPDATE service_records SET {', '.join(fields)} WHERE id=?", vals)
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
    pct    = round((total / 80) * 100, 1) if filled else 0

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
    """搜尋產品（以 products 主檔為準，附帶當前庫存量＋進貨月均成本）"""
    q    = request.args.get('q', '').strip()
    conn = get_db()
    try:
        if not q:
            return jsonify([])
        like = f'%{q}%'
        today = datetime.now().strftime('%Y-%m-%d')
        fallback_start = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        # 成本優先順序：最近一次進貨單價 > 近90天加權平均 > 0
        rows = conn.execute("""
            WITH last_purchase AS (
                SELECT product_code,
                       CAST(amount AS REAL) / quantity AS unit_cost,
                       ROW_NUMBER() OVER (PARTITION BY product_code ORDER BY date DESC, id DESC) AS rn
                FROM purchase_history
                WHERE quantity > 0 AND amount > 0
            ),
            recent_avg AS (
                SELECT product_code,
                       CAST(SUM(amount) AS REAL) / SUM(quantity) AS avg_cost
                FROM purchase_history
                WHERE date >= ? AND date <= ?
                  AND quantity > 0 AND amount > 0
                GROUP BY product_code
            )
            SELECT p.product_code,
                   p.product_name,
                   p.unit,
                   COALESCE(SUM(i.stock_quantity), 0) AS total_qty,
                   COALESCE(lp.unit_cost, ra.avg_cost, 0) AS unit_cost
            FROM products p
            LEFT JOIN inventory i
                   ON i.product_id = p.product_code
                  AND i.report_date = (SELECT MAX(report_date) FROM inventory)
                  AND i.stock_quantity > 0
            LEFT JOIN last_purchase lp ON lp.product_code = p.product_code AND lp.rn = 1
            LEFT JOIN recent_avg ra ON ra.product_code = p.product_code
            WHERE p.product_code LIKE ? OR p.product_name LIKE ?
            GROUP BY p.product_code, p.product_name
            ORDER BY p.product_name
            LIMIT 30
        """, (fallback_start, today, like, like)).fetchall()
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
                   COALESCE(mc.avg_cost, s.cost * 1.0 / MAX(s.quantity, 1)) AS cost,
                   s.amount - s.quantity * COALESCE(mc.avg_cost, s.cost * 1.0 / MAX(s.quantity, 1)) AS profit,
                   CASE WHEN s.amount > 0
                        THEN ROUND((s.amount - s.quantity * COALESCE(mc.avg_cost, s.cost * 1.0 / MAX(s.quantity, 1))) * 100.0 / s.amount, 1)
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
            conds.append("(sales_invoice_no LIKE ? OR invoice_no LIKE ? OR customer_name LIKE ? OR product_name LIKE ? OR salesperson LIKE ?)")
            params += [f'%{q}%', f'%{q}%', f'%{q}%', f'%{q}%', f'%{q}%']
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
            SELECT s.id, s.invoice_no, s.sales_invoice_no, s.date,
                   s.customer_name, s.salesperson,
                   s.product_code, s.product_name, s.quantity, s.price, s.amount,
                   COALESCE(mc.avg_cost, s.cost * 1.0 / MAX(s.quantity, 1)) AS cost,
                   s.amount - s.quantity * COALESCE(mc.avg_cost, s.cost * 1.0 / MAX(s.quantity, 1)) AS profit,
                   CASE WHEN s.amount > 0
                        THEN ROUND((s.amount - s.quantity * COALESCE(mc.avg_cost, s.cost * 1.0 / MAX(s.quantity, 1))) * 100.0 / s.amount, 1)
                        ELSE NULL END AS margin
            FROM sales_history s
            LEFT JOIN monthly_cost mc ON mc.product_code = s.product_code
            {where}
            ORDER BY s.date DESC, s.sales_invoice_no DESC, s.id ASC
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


# ── 門市代碼對照 ──
STORE_CODE_MAP = {
    '豐原門市': 'FY', '豐原': 'FY',
    '潭子門市': 'TZ', '潭子': 'TZ',
    '大雅門市': 'DY', '大雅': 'DY',
    '業務部':   'OW', '-': 'OW', '': 'OW',
}


def _ensure_sales_no_column(conn):
    """確保 sales_history 有新增欄位"""
    cols = {c[1] for c in conn.execute('PRAGMA table_info(sales_history)')}
    new_cols = [
        ('source_doc_no', "TEXT DEFAULT ''"),
        ('warehouse', "TEXT DEFAULT ''"),
        ('payment_method', "TEXT DEFAULT ''"),
        ('deposit_amount', "INTEGER DEFAULT 0"),
    ]
    changed = False
    for col, dtype in new_cols:
        if col not in cols:
            conn.execute(f"ALTER TABLE sales_history ADD COLUMN {col} {dtype}")
            changed = True
    if changed:
        conn.commit()


@app.route('/api/sales/next-invoice-no')
def next_sales_invoice_no():
    """自動產生銷貨單號：{門市代碼}-{YYYYMMDD}-{NNN}"""
    warehouse = request.args.get('warehouse', '').strip()
    date_str  = request.args.get('date', '').strip().replace('-', '')
    if not date_str:
        date_str = datetime.now().strftime('%Y%m%d')
    # 取門市代碼，無對應預設 FY
    store_code = STORE_CODE_MAP.get(warehouse, 'FY')
    prefix = f'{store_code}-{date_str}-'
    conn = get_db()
    try:
        _ensure_sales_no_column(conn)
        row = conn.execute(
            "SELECT sales_invoice_no FROM sales_history "
            "WHERE sales_invoice_no LIKE ? "
            "ORDER BY sales_invoice_no DESC LIMIT 1",
            (prefix + '%',)
        ).fetchone()
        if row and row['sales_invoice_no']:
            last_no = row['sales_invoice_no']
            try:
                last_seq = int(last_no.rsplit('-', 1)[-1])
            except ValueError:
                last_seq = 0
            next_seq = last_seq + 1
        else:
            next_seq = 1
        invoice_no = f'{prefix}{next_seq:03d}'
        return jsonify({'success': True, 'invoice_no': invoice_no, 'store_code': store_code})
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

    invoice_no     = data.get('invoice_no', '').strip()       # 發票號碼（選填）
    sales_no       = data.get('sales_invoice_no', '').strip() # 銷貨單號 FY-YYYYMMDD-NNN
    date           = data.get('date', '')
    customer_id    = data.get('customer_id', '')
    customer_name  = data.get('customer_name', '')
    salesperson    = data.get('salesperson', '')
    salesperson_id = data.get('salesperson_id', '')
    warehouse      = data.get('warehouse', '')
    source_doc_no  = data.get('source_doc_no', '')   # 來源訂單單號
    payment_method = data.get('payment_method', '')  # 付款方式：現金/匯款/刷卡/月結/申辦分期
    deposit_amount = int(data.get('deposit_amount', 0) or 0)  # 訂金（從訂單帶入）

    if not date or not sales_no:
        return jsonify({'success': False, 'message': '日期與銷貨單號為必填'}), 400

    conn = get_db()
    try:
        _ensure_sales_no_column(conn)

        # 確認銷貨單號不重複
        exists = conn.execute(
            "SELECT 1 FROM sales_history WHERE sales_invoice_no=? LIMIT 1", (sales_no,)
        ).fetchone()
        if exists:
            return jsonify({'success': False, 'message': f'銷貨單號 {sales_no} 已存在'}), 409

        # 預先查詢成本：最近一次進貨單價 > 近 90 天加權平均 > 0
        cost_map = {}
        # 1) 最近一次進貨單價（每個品項取最新一筆）
        last_rows = conn.execute("""
            SELECT product_code, CAST(amount AS REAL) / quantity AS unit_cost
            FROM purchase_history
            WHERE quantity > 0 AND amount > 0
              AND id IN (
                SELECT MAX(id) FROM purchase_history
                WHERE quantity > 0 AND amount > 0
                GROUP BY product_code
              )
        """).fetchall()
        for cr in last_rows:
            cost_map[cr['product_code']] = cr['unit_cost']
        # 2) 近 90 天加權平均（補充沒有最近進貨的品項）
        fallback_start = (datetime.strptime(date[:10], '%Y-%m-%d') - timedelta(days=90)).strftime('%Y-%m-%d')
        avg_rows = conn.execute("""
            SELECT product_code,
                   CAST(SUM(amount) AS REAL) / SUM(quantity) AS avg_cost
            FROM purchase_history
            WHERE date >= ? AND date <= ?
              AND quantity > 0 AND amount > 0
            GROUP BY product_code
        """, (fallback_start, date)).fetchall()
        for cr in avg_rows:
            if cr['product_code'] not in cost_map:
                cost_map[cr['product_code']] = cr['avg_cost']

        for idx, it in enumerate(items):
            product_code = it.get('product_code', '')
            product_name = it.get('product_name', '')
            qty          = int(it.get('quantity', 1))
            price        = float(it.get('price', 0))
            # 成本優先順序：進貨月均成本 > 前端帶入值 > 0
            frontend_cost = float(it.get('cost', 0))
            avg_cost      = cost_map.get(product_code)
            unit_cost     = avg_cost if avg_cost else frontend_cost
            cost          = round(unit_cost * qty, 0)  # cost 存總成本
            amount        = qty * price
            profit        = amount - cost
            margin        = round(profit / amount * 100, 2) if amount else 0

            conn.execute("""
                INSERT INTO sales_history
                  (invoice_no, date, customer_id, salesperson, product_code,
                   product_name, quantity, price, amount, customer_name,
                   cost, profit, margin, salesperson_id, source_file, source_row,
                   sales_invoice_no, source_doc_no, warehouse, payment_method,
                   deposit_amount)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (invoice_no, date, customer_id, salesperson, product_code,
                  product_name, qty, price, amount, customer_name,
                  cost, profit, margin, salesperson_id, 'manual', idx + 1,
                  sales_no, source_doc_no, warehouse, payment_method,
                  deposit_amount))

        # ── 自動產生應收帳款（月結 / 申辦分期） ──
        total_amount = sum(int(it.get('quantity', 1)) * float(it.get('price', 0)) for it in items)
        receivable_amount = total_amount - deposit_amount  # 扣除訂金
        if receivable_amount > 0:
            # 判定是否月結：前端選擇「月結」或客戶 payment_type='M'
            is_monthly = payment_method == '月結'
            if not is_monthly and customer_id:
                cust_row = conn.execute(
                    "SELECT payment_type FROM customers WHERE customer_id=?",
                    (customer_id,)).fetchone()
                if cust_row and cust_row['payment_type'] == 'M':
                    is_monthly = True

            now_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            dep_note = f'（已扣訂金 ${deposit_amount:,}）' if deposit_amount > 0 else ''

            if is_monthly:
                # 月結：結帳日統一 25 號，下個月月底匯款
                from calendar import monthrange
                pdate = datetime.strptime(date[:10], '%Y-%m-%d')
                closing_day = 25
                last_day_of_month = monthrange(pdate.year, pdate.month)[1]
                close_day = min(closing_day, last_day_of_month)
                if pdate.day <= close_day:
                    close_m, close_y = pdate.month, pdate.year
                else:
                    close_m = pdate.month + 1
                    close_y = pdate.year
                    if close_m > 12:
                        close_m, close_y = 1, close_y + 1
                pay_m = close_m + 1
                pay_y = close_y
                if pay_m > 12:
                    pay_m, pay_y = 1, pay_y + 1
                pay_last = monthrange(pay_y, pay_m)[1]
                due_date_str = f'{pay_y}-{pay_m:02d}-{pay_last:02d}'
                billing_period = f'{close_y}-{close_m:02d}'
                conn.execute("""INSERT INTO finance_receivables
                    (customer_id, customer_name, invoice_no, amount, due_date, status, note, created_at)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    (customer_id, customer_name, invoice_no, receivable_amount,
                     due_date_str, 'unpaid', f'帳期 {billing_period}{dep_note}', now_ts))

            elif payment_method == '申辦分期':
                # 申辦分期：取貨後一週分期公司匯款
                pdate = datetime.strptime(date[:10], '%Y-%m-%d')
                due_date_str = (pdate + timedelta(days=7)).strftime('%Y-%m-%d')
                conn.execute("""INSERT INTO finance_receivables
                    (customer_id, customer_name, invoice_no, amount, due_date, status, note, created_at)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    (customer_id, customer_name, invoice_no, receivable_amount,
                     due_date_str, 'unpaid', f'申辦分期{dep_note}', now_ts))

        conn.commit()
        return jsonify({'success': True, 'invoice_no': invoice_no,
                        'sales_invoice_no': sales_no, 'item_count': len(items)})
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


@app.route('/api/sales/row/<int:row_id>', methods=['PUT'])
def sales_update_row(row_id):
    """修改單一銷貨紀錄（老闆/會計可用）"""
    data = request.get_json() or {}
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM sales_history WHERE id=?", (row_id,)).fetchone()
        if not row:
            return jsonify({'success': False, 'message': '找不到此筆紀錄'}), 404
        product_code  = data.get('product_code',  row['product_code'])
        product_name  = data.get('product_name',  row['product_name'])
        quantity      = int(data.get('quantity',  row['quantity']))
        price         = int(data.get('price',     row['price']))
        amount        = int(data.get('amount',    row['amount']))
        cost          = int(data.get('cost',      row['cost'] or 0))
        salesperson   = data.get('salesperson',   row['salesperson'])
        customer_name = data.get('customer_name', row['customer_name'])
        profit = amount - cost
        margin = round(profit / amount * 100, 2) if amount else 0
        conn.execute(
            """UPDATE sales_history SET
               product_code=?, product_name=?, quantity=?, price=?, amount=?,
               cost=?, profit=?, margin=?, salesperson=?, customer_name=?,
               updated_at=datetime('now','localtime')
               WHERE id=?""",
            (product_code, product_name, quantity, price, amount,
             cost, profit, margin, salesperson, customer_name, row_id)
        )
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/sales/anomalies', methods=['GET'])
def sales_anomalies():
    """取得近期 SE-* 品號金額超過 5000 的異常銷貨紀錄"""
    days = int(request.args.get('days', 30))
    threshold = int(request.args.get('threshold', 5000))
    conn = get_db()
    try:
        from datetime import date, timedelta
        since = (date.today() - timedelta(days=days)).isoformat()
        rows = conn.execute(
            """SELECT id, date, invoice_no, customer_name, salesperson,
                      product_code, product_name, quantity, amount, cost, margin
               FROM sales_history
               WHERE product_code LIKE 'SE-%'
                 AND amount > ?
                 AND date >= ?
                 AND (anomaly_ack IS NULL OR anomaly_ack = 0)
               ORDER BY date DESC""",
            (threshold, since)
        ).fetchall()
        return jsonify({'success': True, 'rows': [dict(r) for r in rows], 'threshold': threshold})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/sales/anomaly-ack/<int:row_id>', methods=['PUT'])
def sales_anomaly_ack(row_id):
    """確認（放行）一筆銷貨異常記錄，之後不再顯示"""
    conn = get_db()
    try:
        conn.execute('UPDATE sales_history SET anomaly_ack = 1 WHERE id = ?', (row_id,))
        conn.commit()
        return jsonify({'success': True})
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
            conds.append('status=?')
            params.append(status)
        if type_:
            conds.append('type=?')
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
    data = request.get_json() or {}
    resolved_code = (data.get('resolved_code') or '').strip()
    resolved_name = (data.get('resolved_name') or '').strip()
    resolve_method = (data.get('resolve_method') or '手動標記').strip()
    conn = get_db()
    try:
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            """UPDATE staging_records
               SET status='resolved', resolved_code=?, resolved_name=?,
                   resolve_method=?, resolved_at=?, updated_at=?
               WHERE id=?""",
            (resolved_code or None, resolved_name or None,
             resolve_method, now_str, now_str, sid)
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


# ─────────────────────────────────────────────
# 客戶建檔
# ─────────────────────────────────────────────
@app.route('/customer_create')
def customer_create_page():
    return render_template('customer_create.html')


@app.route('/api/customer/next-id')
def customer_next_id():
    """依前綴回傳下一個可用的客戶編號"""
    prefix = (request.args.get('prefix') or 'FY').upper().strip()
    conn = get_db()
    try:
        row = conn.execute("""
            SELECT customer_id FROM customers
            WHERE customer_id LIKE ?
            ORDER BY customer_id DESC LIMIT 1
        """, (f'{prefix}-%',)).fetchone()
        if row:
            parts = row['customer_id'].split('-')
            try:
                next_num = int(parts[-1]) + 1
            except ValueError:
                next_num = 1
        else:
            next_num = 1
        next_id = f'{prefix}-{next_num:05d}'
        return ok({'next_id': next_id})
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()


@app.route('/api/customer/create', methods=['POST'])
def customer_create():
    data    = request.get_json() or {}
    conn    = get_db()
    try:
        cid = (data.get('customer_id') or '').strip()
        name = (data.get('short_name') or '').strip()
        if not cid or not name:
            return err('客戶編號與名稱為必填')
        # 檢查是否已存在
        exists = conn.execute(
            "SELECT 1 FROM customers WHERE customer_id=?", (cid,)
        ).fetchone()
        if exists:
            return err(f'客戶編號 {cid} 已存在')
        conn.execute("""
            INSERT INTO customers
              (customer_id, short_name, phone1, mobile, contact,
               tax_id, company_address, delivery_address, payment_type,
               updated_at, created_by)
            VALUES (?,?,?,?,?,?,?,?,?, datetime('now','localtime'), ?)
        """, (
            cid,
            name,
            (data.get('phone1') or '').strip(),
            (data.get('mobile') or '').strip(),
            (data.get('contact') or '').strip(),
            (data.get('tax_id') or '').strip(),
            (data.get('company_address') or '').strip(),
            (data.get('delivery_address') or '').strip(),
            (data.get('payment_type') or '').strip(),
            data.get('created_by') or '',
        ))
        conn.commit()
        return ok({'customer_id': cid, 'message': f'客戶 {name}（{cid}）建檔成功'})
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()


@app.route('/api/customer/update', methods=['POST'])
def customer_update():
    data = request.get_json() or {}
    conn = get_db()
    try:
        cid = (data.get('customer_id') or '').strip()
        if not cid:
            return err('缺少客戶編號')
        conn.execute("""
            UPDATE customers SET
              short_name=?, phone1=?, mobile=?, contact=?,
              tax_id=?, company_address=?, delivery_address=?,
              payment_type=?, updated_at=datetime('now','localtime')
            WHERE customer_id=?
        """, (
            (data.get('short_name') or '').strip(),
            (data.get('phone1') or '').strip(),
            (data.get('mobile') or '').strip(),
            (data.get('contact') or '').strip(),
            (data.get('tax_id') or '').strip(),
            (data.get('company_address') or '').strip(),
            (data.get('delivery_address') or '').strip(),
            (data.get('payment_type') or '').strip(),
            cid,
        ))
        conn.commit()
        if conn.execute("SELECT changes()").fetchone()[0] == 0:
            return err('找不到此客戶')
        return ok({'message': '資料更新成功'})
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()


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
        rows = conn.execute("""
            SELECT s.supplier_name, COUNT(DISTINCT p.order_no) AS cnt
            FROM suppliers s
            LEFT JOIN purchase_history p ON p.supplier_name = s.supplier_name
            WHERE s.status = '正常'
            GROUP BY s.supplier_name
            ORDER BY cnt DESC
        """).fetchall()
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
    company   = (data.get('company') or '').strip()
    created_by= (data.get('created_by') or '').strip()
    tax_amount= int(data.get('tax_amount', 0) or 0)
    items     = data.get('items', [])

    if not order_no or not date or not supplier or not items:
        return jsonify({'success': False, 'message': '單號、日期、供應商、品項為必填'}), 400

    conn = get_db()
    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # 若供應商不在 suppliers 表中，自動建檔
        exists = conn.execute("SELECT 1 FROM suppliers WHERE supplier_name=?", (supplier,)).fetchone()
        if not exists:
            next_row = conn.execute("SELECT supplier_id FROM suppliers ORDER BY supplier_id DESC LIMIT 1").fetchone()
            if next_row and next_row['supplier_id']:
                try:
                    next_num = int(next_row['supplier_id'].split('-')[-1]) + 1
                except ValueError:
                    next_num = 1
            else:
                next_num = 1
            conn.execute("""INSERT INTO suppliers (supplier_id, supplier_name, status, created_at, created_by)
                VALUES (?, ?, '正常', ?, ?)""", (f'SP-{next_num:04d}', supplier, now, created_by or '系統自動建檔'))
        total_amount = 0
        for item in items:
            qty    = int(item.get('quantity', 0))
            price  = float(item.get('price', 0))
            amount = round(qty * price)
            total_amount += amount
            conn.execute("""
                INSERT INTO purchase_history
                  (order_no, invoice_number, date, supplier_name,
                   product_code, product_name, quantity, price, amount,
                   warehouse, company, created_by, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (order_no, invoice or None, date, supplier,
                  item.get('product_code',''), item.get('product_name',''),
                  qty, price, amount,
                  warehouse or None, company or None, created_by or None, now))

        # 自動建立應付帳款，到期日依廠商帳期計算
        if total_amount > 0:
            sup = conn.execute(
                "SELECT closing_day, pay_day, payment_method FROM suppliers WHERE supplier_name=?",
                (supplier,)).fetchone()
            due_date = ''
            if sup and sup['closing_day'] and sup['payment_method'] in ('匯款', '支票'):
                from calendar import monthrange
                pdate = datetime.strptime(date, '%Y-%m-%d')
                cd = sup['closing_day']
                # 判斷進貨日落在哪個結帳週期
                last_day = monthrange(pdate.year, pdate.month)[1]
                close_day = min(cd, last_day)
                if pdate.day <= close_day:
                    # 本月結帳 → 下月付款
                    close_m, close_y = pdate.month, pdate.year
                else:
                    # 下月結帳 → 再下月付款
                    close_m = pdate.month + 1
                    close_y = pdate.year
                    if close_m > 12:
                        close_m = 1
                        close_y += 1
                # 付款月 = 結帳月的下一個月
                pay_m = close_m + 1
                pay_y = close_y
                if pay_m > 12:
                    pay_m = 1
                    pay_y += 1
                if sup['payment_method'] == '匯款':
                    # 匯款：固定付款日（預設28）
                    pd = sup['pay_day'] or 28
                    pay_last = monthrange(pay_y, pay_m)[1]
                    due_date = f'{pay_y}-{pay_m:02d}-{min(pd, pay_last):02d}'
                else:
                    # 支票：月底寄出
                    pay_last = monthrange(pay_y, pay_m)[1]
                    due_date = f'{pay_y}-{pay_m:02d}-{pay_last:02d}'
            elif sup and sup['payment_method'] == '現金自取':
                due_date = ''  # 現金自取無固定到期日

            payable_amount = total_amount + tax_amount  # 含稅金額
            note = f'進貨單 {order_no} 自動建立'
            if tax_amount > 0:
                note += f'（未稅 {total_amount:,}＋稅 {tax_amount:,}）'
            conn.execute("""INSERT INTO finance_payables
                (vendor_name, order_no, amount, pretax_amount, tax_amount,
                 due_date, status, company, note, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (supplier, order_no, payable_amount, total_amount, tax_amount,
                 due_date, 'unpaid', company or None, note, now))

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
    company   = request.args.get('company', '').strip()
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
        if company:
            where += " AND company = ?"; params.append(company)
        total = conn.execute(f"SELECT COUNT(*) FROM purchase_history {where}", params).fetchone()[0]
        rows  = conn.execute(f"""
            SELECT id, order_no, invoice_number, date, supplier_name,
                   product_code, product_name, quantity, price, amount,
                   warehouse, company, created_by
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


@app.route('/api/purchase/row/<int:row_id>', methods=['PUT'])
def purchase_update_row(row_id):
    """修改單一進貨紀錄（老闆/會計可用）"""
    data = request.get_json() or {}
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM purchase_history WHERE id=?", (row_id,)).fetchone()
        if not row:
            return jsonify({'success': False, 'message': '找不到此筆紀錄'}), 404
        product_code  = data.get('product_code',  row['product_code'])
        product_name  = data.get('product_name',  row['product_name'])
        quantity      = int(data.get('quantity',  row['quantity']))
        price         = int(data.get('price',     row['price']))
        amount        = int(data.get('amount',    row['amount']))
        supplier_name  = data.get('supplier_name', row['supplier_name'])
        company        = data.get('company',       row['company'])
        invoice_number = data.get('invoice_number', row['invoice_number'])
        warehouse      = data.get('warehouse',     row['warehouse'])
        conn.execute(
            """UPDATE purchase_history SET
               product_code=?, product_name=?, quantity=?, price=?, amount=?,
               supplier_name=?, company=?, invoice_number=?, warehouse=?,
               updated_at=datetime('now','localtime')
               WHERE id=?""",
            (product_code, product_name, quantity, price, amount,
             supplier_name, company, invoice_number, warehouse, row_id)
        )
        conn.commit()
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


@app.route('/api/sales-doc/confirmed-orders')
def sales_doc_confirmed_orders():
    """取得已確認的訂單（含品項）供銷貨帶入使用"""
    keyword = (request.args.get('q') or '').strip()
    conn = get_db()
    try:
        _ensure_sales_doc_schema(conn)
        params = ['ORDER', 'CONFIRMED']
        cond   = "WHERE doc_type=? AND status=?"
        if keyword:
            cond  += " AND (doc_no LIKE ? OR target_name LIKE ?)"
            params += [f'%{keyword}%', f'%{keyword}%']
        rows = conn.execute(
            f"SELECT * FROM sales_documents {cond} ORDER BY created_at DESC LIMIT 50",
            params
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
        return jsonify({'success': True, 'orders': docs})
    except Exception as e:
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


@app.route('/api/sales-doc/update', methods=['PUT'])
def sales_doc_update():
    """修改報價/訂單標頭欄位（老闆/會計可用）"""
    data   = request.get_json() or {}
    doc_no = (data.get('doc_no') or '').strip()
    if not doc_no:
        return jsonify({'success': False, 'message': '缺少單號'}), 400
    conn = get_db()
    try:
        _ensure_sales_doc_schema(conn)
        row = conn.execute("SELECT * FROM sales_documents WHERE doc_no=?", (doc_no,)).fetchone()
        if not row:
            return jsonify({'success': False, 'message': '找不到單據'}), 404
        target_name    = data.get('target_name',    row['target_name']    if 'target_name'    in row.keys() else '')
        deposit_amount = data.get('deposit_amount', row['deposit_amount'] or 0)
        note           = data.get('note',           row['note']           if 'note'           in row.keys() else '')
        valid_until    = data.get('valid_until',    row['valid_until']    if 'valid_until'    in row.keys() else '')
        total_amount   = data.get('total_amount',   row['total_amount']   or 0)
        balance_amount = int(total_amount) - int(deposit_amount)
        conn.execute(
            """UPDATE sales_documents SET
               target_name=?, deposit_amount=?, balance_amount=?, note=?, valid_until=?,
               total_amount=?, updated_at=datetime('now','localtime')
               WHERE doc_no=?""",
            (target_name, deposit_amount, balance_amount, note, valid_until,
             total_amount, doc_no)
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
# 廠商建檔
# ─────────────────────────────────────────────
@app.route('/supplier_create')
def supplier_create_page():
    return render_template('supplier_create.html')


@app.route('/api/supplier/next-id')
def supplier_next_id():
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT supplier_id FROM suppliers ORDER BY supplier_id DESC LIMIT 1"
        ).fetchone()
        if row and row['supplier_id']:
            try:
                next_num = int(row['supplier_id'].split('-')[-1]) + 1
            except ValueError:
                next_num = 1
        else:
            next_num = 1
        return ok({'next_id': f'SP-{next_num:04d}'})
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()


@app.route('/supplier_search')
def supplier_search_page():
    return render_template('supplier_search.html')


@app.route('/inventory_count')
def inventory_count_page():
    return render_template('inventory_count.html')


@app.route('/api/supplier/list')
def supplier_list():
    q    = (request.args.get('q') or '').strip()
    page = request.args.get('page', 1, type=int)
    per  = 50
    conn = get_db()
    try:
        if q:
            like = f'%{q}%'
            where = "WHERE supplier_name LIKE ? OR short_name LIKE ? OR contact_person LIKE ? OR supplier_id LIKE ?"
            params = (like, like, like, like)
        else:
            where  = ""
            params = ()
        rows = conn.execute(f"""
            SELECT supplier_id, supplier_name, short_name,
                   phone, mobile, contact_person,
                   payment_method, closing_day, pay_day, status
            FROM suppliers {where}
            ORDER BY supplier_id
            LIMIT ? OFFSET ?
        """, (*params, per, (page-1)*per)).fetchall()
        total = conn.execute(f"SELECT COUNT(*) FROM suppliers {where}", params).fetchone()[0]
        return ok({'list': [dict(r) for r in rows], 'total': total, 'page': page, 'per': per})
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()


@app.route('/api/supplier/detail/<supplier_id>')
def supplier_detail(supplier_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM suppliers WHERE supplier_id=?", (supplier_id,)
        ).fetchone()
        if not row:
            return err('找不到此廠商', 404)
        purchases = conn.execute("""
            SELECT date, product_code, product_name, quantity, amount
            FROM purchase_history
            WHERE supplier_name = ?
            ORDER BY date DESC LIMIT 20
        """, (row['supplier_name'],)).fetchall()
        return ok({
            'data':      dict(row),
            'purchases': [dict(p) for p in purchases],
        })
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()


@app.route('/api/supplier/create', methods=['POST'])
def supplier_create():
    data = request.get_json() or {}
    conn = get_db()
    try:
        sid  = (data.get('supplier_id') or '').strip()
        name = (data.get('supplier_name') or '').strip()
        if not sid or not name:
            return err('廠商編號與廠商名稱為必填')
        exists = conn.execute(
            "SELECT 1 FROM suppliers WHERE supplier_id=?", (sid,)
        ).fetchone()
        if exists:
            return err(f'廠商編號 {sid} 已存在')
        conn.execute("""
            INSERT INTO suppliers
              (supplier_id, supplier_name, short_name, tax_id,
               contact_person, phone, mobile, email, address,
               payment_method, closing_day, pay_day,
               bank_name, bank_branch, bank_account, remark, status,
               created_at, updated_at, created_by)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'正常',
                    datetime('now','localtime'), datetime('now','localtime'), ?)
        """, (
            sid,
            name,
            (data.get('short_name')      or '').strip(),
            (data.get('tax_id')          or '').strip(),
            (data.get('contact_person')  or '').strip(),
            (data.get('phone')           or '').strip(),
            (data.get('mobile')          or '').strip(),
            (data.get('email')           or '').strip(),
            (data.get('address')         or '').strip(),
            (data.get('payment_method')  or '').strip(),
            data.get('closing_day') or None,
            data.get('pay_day') or None,
            (data.get('bank_name')       or '').strip(),
            (data.get('bank_branch')     or '').strip(),
            (data.get('bank_account')    or '').strip(),
            (data.get('remark')          or '').strip(),
            data.get('created_by') or '',
        ))
        conn.commit()
        return ok({'supplier_id': sid, 'message': f'廠商 {name}（{sid}）建檔成功'})
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()


@app.route('/api/supplier/<supplier_id>', methods=['PUT'])
def supplier_update(supplier_id):
    data = request.get_json() or {}
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM suppliers WHERE supplier_id=?", (supplier_id,)).fetchone()
        if not row:
            return err('找不到此廠商', 404)
        fields = ['supplier_name', 'short_name', 'tax_id', 'contact_person',
                  'phone', 'mobile', 'email', 'address',
                  'payment_method', 'closing_day', 'pay_day',
                  'bank_name', 'bank_branch', 'bank_account', 'remark', 'status']
        int_fields = {'closing_day', 'pay_day'}
        sets, vals = [], []
        for f in fields:
            if f in data:
                sets.append(f"{f} = ?")
                if f in int_fields:
                    v = data[f]
                    vals.append(int(v) if v not in (None, '', 0) else None)
                else:
                    vals.append((data[f] or '').strip())
        if not sets:
            return err('未提供任何更新欄位')
        sets.append("updated_at = datetime('now','localtime')")
        if data.get('updated_by'):
            sets.append("updated_by = ?")
            vals.append(data['updated_by'])
        vals.append(supplier_id)
        conn.execute(f"UPDATE suppliers SET {', '.join(sets)} WHERE supplier_id = ?", vals)
        conn.commit()
        return ok({'message': '廠商資料更新成功'})
    except Exception as e:
        conn.rollback()
        return err(str(e), 500)
    finally:
        conn.close()


# ─────────────────────────────────────────────
# 產品建檔
# ─────────────────────────────────────────────
@app.route('/product_create')
def product_create_page():
    return render_template('product_create.html')


@app.route('/api/product/categories')
def product_categories():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT category_code, category_name FROM product_categories ORDER BY category_code"
        ).fetchall()
        return ok([dict(r) for r in rows])
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()


@app.route('/api/product/next-code')
def product_next_code():
    """依 類別碼-品牌碼 前綴，回傳下一個可用產品編號"""
    cat   = (request.args.get('cat')   or '').strip().upper()
    brand = (request.args.get('brand') or '').strip().upper()
    if not cat or not brand:
        return err('缺少 cat 或 brand 參數')
    prefix = f'{cat}-{brand}-'
    conn = get_db()
    try:
        row = conn.execute("""
            SELECT product_code FROM products
            WHERE product_code LIKE ?
            ORDER BY product_code DESC LIMIT 1
        """, (f'{prefix}%',)).fetchone()
        if row:
            try:
                next_num = int(row['product_code'].split('-')[-1]) + 1
            except ValueError:
                next_num = 1
        else:
            next_num = 1
        return ok({'next_code': f'{prefix}{next_num:04d}'})
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()


@app.route('/api/product/create', methods=['POST'])
def product_create():
    data = request.get_json() or {}
    conn = get_db()
    try:
        code = (data.get('product_code') or '').strip()
        name = (data.get('product_name') or '').strip()
        if not code or not name:
            return err('產品編號與品名為必填')
        exists = conn.execute(
            "SELECT 1 FROM products WHERE product_code=?", (code,)
        ).fetchone()
        if exists:
            return err(f'產品編號 {code} 已存在')
        conn.execute("""
            INSERT INTO products
              (product_code, product_name, category, unit,
               created_at, updated_at, created_by)
            VALUES (?, ?, ?, ?, datetime('now','localtime'), datetime('now','localtime'), ?)
        """, (
            code,
            name,
            (data.get('category') or '').strip(),
            (data.get('unit') or '個').strip(),
            data.get('created_by') or '',
        ))
        conn.commit()
        return ok({'product_code': code, 'message': f'產品 {name}（{code}）建檔成功'})
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: KPI 考核
# ─────────────────────────────────────────────
@app.route('/kpi_review')
def kpi_review_page():
    return render_template('kpi_review.html')

import math
def _cur_year():  return datetime.today().year
def _cur_quarter(): return math.ceil(datetime.today().month / 3)

@app.route('/api/kpi/scores')
def kpi_scores():
    year    = int(request.args.get('year', _cur_year()))
    quarter = int(request.args.get('quarter', _cur_quarter()))
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT id, staff_name, staff_role,
                   kpi1_achievement, kpi2_margin, kpi3_company_achievement,
                   kpi4_reviews, kpi5_contribution,
                   m_kpi1_dept_margin, m_kpi2_staff_avg, m_kpi3_company_margin,
                   m_kpi4_turnover, m_kpi5_complaint, m_kpi6_cross_dept,
                   a_kpi1_accuracy, a_kpi2_on_time, a_kpi3_ar_control,
                   a_kpi4_support, a_kpi5_cost_opt,
                   total_score, rank, multiplier, bonus_amount,
                   updated_at
            FROM kpi_scores
            WHERE year = ? AND quarter = ?
            ORDER BY staff_role, rank, total_score DESC
        """, (year, quarter)).fetchall()
        return ok(scores=[dict(r) for r in rows])
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()


@app.route('/api/kpi/update', methods=['POST'])
def kpi_update():
    data = request.get_json() or {}
    row_id = data.get('id')
    if not row_id:
        return err('缺少 id')

    # 允許更新的欄位（老闆手動評分）
    ALLOWED = {
        'kpi4_reviews', 'kpi5_contribution',
        'm_kpi1_dept_margin', 'm_kpi2_staff_avg', 'm_kpi3_company_margin',
        'm_kpi4_turnover', 'm_kpi5_complaint', 'm_kpi6_cross_dept',
        'a_kpi1_accuracy', 'a_kpi2_on_time', 'a_kpi3_ar_control',
        'a_kpi4_support', 'a_kpi5_cost_opt',
        'total_score', 'rank', 'multiplier', 'bonus_amount',
    }
    updates = {k: v for k, v in data.items() if k in ALLOWED}
    if not updates:
        return err('沒有可更新的欄位')

    set_clause = ', '.join(f'{k} = ?' for k in updates)
    values = list(updates.values()) + [datetime.now().strftime('%Y-%m-%d %H:%M:%S'), row_id]

    conn = get_db()
    try:
        conn.execute(
            f"UPDATE kpi_scores SET {set_clause}, updated_at = ? WHERE id = ?",
            values
        )
        conn.commit()
        return ok({'message': '更新成功'})
    except Exception as e:
        conn.rollback()
        return err(str(e), 500)
    finally:
        conn.close()


@app.route('/api/kpi/profit')
def kpi_profit_get():
    year    = int(request.args.get('year', _cur_year()))
    quarter = int(request.args.get('quarter', _cur_quarter()))
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM quarterly_profit WHERE year=? AND quarter=?",
            (year, quarter)
        ).fetchone()
        return ok(profit=dict(row) if row else None)
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()


@app.route('/api/kpi/profit', methods=['POST'])
def kpi_profit_save():
    data       = request.get_json() or {}
    year       = int(data.get('year', _cur_year()))
    quarter    = int(data.get('quarter', _cur_quarter()))
    net_profit = int(data.get('net_profit', 0))
    created_by = (data.get('created_by') or '').strip()
    status     = (data.get('status') or 'draft').strip()

    conn = get_db()
    try:
        exists = conn.execute(
            "SELECT id FROM quarterly_profit WHERE year=? AND quarter=?",
            (year, quarter)
        ).fetchone()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if exists:
            conn.execute("""
                UPDATE quarterly_profit
                SET net_profit=?, status=?, updated_at=?
                WHERE year=? AND quarter=?
            """, (net_profit, status, now, year, quarter))
        else:
            conn.execute("""
                INSERT INTO quarterly_profit (year, quarter, net_profit, status, created_by, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?)
            """, (year, quarter, net_profit, status, created_by, now, now))
        conn.commit()
        return ok({'message': '季度淨利已儲存'})
    except Exception as e:
        conn.rollback()
        return err(str(e), 500)
    finally:
        conn.close()


@app.route('/api/kpi/auto-review-score')
def kpi_auto_review_score():
    """計算 Google 五星好評 KPI④ 自動分數（全員相同）"""
    year    = int(request.args.get('year', _cur_year()))
    quarter = int(request.args.get('quarter', _cur_quarter()))

    # 季度日期範圍
    q_start = {1: f'{year}-01-01', 2: f'{year}-04-01',
               3: f'{year}-07-01', 4: f'{year}-10-01'}[quarter]
    q_end   = {1: f'{year}-03-31', 2: f'{year}-06-30',
               3: f'{year}-09-30', 4: f'{year}-12-31'}[quarter]

    conn = get_db()
    try:
        # 有效五星：須附文字評論，同一客戶同季同店僅計一次
        row = conn.execute("""
            SELECT COUNT(DISTINCT reviewer_name || '|' || store_name) AS cnt
            FROM google_reviews
            WHERE star_rating = 5
              AND review_snippet IS NOT NULL AND review_snippet != ''
              AND review_date BETWEEN ? AND ?
        """, (q_start, q_end)).fetchone()
        five_star_count = row['cnt'] if row else 0

        target = 200
        if five_star_count >= target:
            score = 10.0
        else:
            score = max(0.0, round(10.0 - (target - five_star_count) * 0.1, 1))

        return ok({
            'five_star_count': five_star_count,
            'target': target,
            'score': score,
            'period': f'{year} Q{quarter}',
            'q_start': q_start,
            'q_end': q_end,
        })
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()


@app.route('/api/kpi/auto-service-score')
def kpi_auto_service_score():
    """計算業務 KPI④ 全部門服務次數 自動分數（全業務員相同）"""
    year    = int(request.args.get('year', _cur_year()))
    quarter = int(request.args.get('quarter', _cur_quarter()))

    q_start = {1: f'{year}-01-01', 2: f'{year}-04-01',
               3: f'{year}-07-01', 4: f'{year}-10-01'}[quarter]
    q_end   = {1: f'{year}-03-31', 2: f'{year}-06-30',
               3: f'{year}-09-30', 4: f'{year}-12-31'}[quarter]

    conn = get_db()
    try:
        # 計算 service_records 中該季的已核可服務筆數
        row = conn.execute("""
            SELECT COUNT(*) AS cnt
            FROM service_records
            WHERE date BETWEEN ? AND ?
              AND (customer_status = 'approved' OR customer_status IS NULL)
        """, (q_start, q_end)).fetchone()
        service_count = row['cnt'] if row else 0

        target = 360
        if service_count >= target:
            score = 15.0
        else:
            score = max(0.0, round(15.0 - (target - service_count) * 0.1, 1))

        return ok({
            'service_count': service_count,
            'target': target,
            'score': score,
            'period': f'{year} Q{quarter}',
        })
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()


@app.route('/api/kpi/apply-service-score', methods=['POST'])
def kpi_apply_service_score():
    """將服務次數分數寫入該期別所有業務人員的 kpi4_reviews"""
    data    = request.get_json() or {}
    year    = int(data.get('year', _cur_year()))
    quarter = int(data.get('quarter', _cur_quarter()))
    score   = float(data.get('score', 0))

    conn = get_db()
    try:
        conn.execute("""
            UPDATE kpi_scores
            SET kpi4_reviews = ?,
                updated_at   = datetime('now','localtime')
            WHERE year = ? AND quarter = ?
              AND staff_role IN ('business')
        """, (score, year, quarter))
        conn.commit()
        affected = conn.execute("SELECT changes()").fetchone()[0]
        return ok({'updated': affected, 'score': score})
    except Exception as e:
        conn.rollback()
        return err(str(e), 500)
    finally:
        conn.close()


@app.route('/api/kpi/apply-review-score', methods=['POST'])
def kpi_apply_review_score():
    """將 Google 評論分數寫入該期別所有人的 kpi4_reviews"""
    data    = request.get_json() or {}
    year    = int(data.get('year', _cur_year()))
    quarter = int(data.get('quarter', _cur_quarter()))
    score   = float(data.get('score', 0))

    conn = get_db()
    try:
        conn.execute("""
            UPDATE kpi_scores
            SET kpi4_reviews = ?,
                updated_at   = datetime('now','localtime')
            WHERE year = ? AND quarter = ?
        """, (score, year, quarter))
        conn.commit()
        affected = conn.execute(
            "SELECT changes()"
        ).fetchone()[0]
        return ok({'updated': affected, 'score': score})
    except Exception as e:
        conn.rollback()
        return err(str(e), 500)
    finally:
        conn.close()


# ─────────────────────────────────────────────
# API: KPI 關鍵貢獻
# ─────────────────────────────────────────────

# 照片存放位置：app 根目錄下的 kpi_evidence/
# 正式部署路徑：/Users/aiserver/srv/web-site/computershop-erp/kpi_evidence/
KPI_EVIDENCE_DIR = os.path.join(BASE_DIR, 'kpi_evidence')
os.makedirs(KPI_EVIDENCE_DIR, exist_ok=True)

# 團隊合作類別（符合才能達到滿分 15 分）
TEAM_CATEGORIES = {'指導新人或分享專業技巧', '跨分店/部門支援', 'SOP改善提案', '客戶轉介給同事'}


def _recalc_kpi5(conn, staff_name, year, quarter):
    """依審核通過的貢獻項目，重新計算 kpi5_contribution 並更新 kpi_scores"""
    rows = conn.execute("""
        SELECT category, score FROM kpi_contributions
        WHERE staff_name=? AND year=? AND quarter=? AND status='approved'
        ORDER BY item_number
    """, (staff_name, year, quarter)).fetchall()

    total = sum(r['score'] or 5 for r in rows)
    # 團隊合作條款：至少 1 項屬於指定類別，否則上限 10
    has_team = any(r['category'] in TEAM_CATEGORIES for r in rows)
    if not has_team and total > 10:
        total = 10.0
    total = min(15.0, total)

    conn.execute("""
        UPDATE kpi_scores
        SET kpi5_contribution = ?, updated_at = datetime('now','localtime')
        WHERE staff_name=? AND year=? AND quarter=?
    """, (total, staff_name, year, quarter))


@app.route('/kpi/evidence/<path:filename>')
def kpi_evidence_file(filename):
    """Serve KPI 佐證照片（存放在 DB 同層的 kpi_evidence/ 資料夾）"""
    return send_from_directory(KPI_EVIDENCE_DIR, filename)


@app.route('/kpi_contribution')
def kpi_contribution_page():
    return render_template('kpi_contribution.html')


@app.route('/api/kpi/contributions')
def kpi_contributions_list():
    year       = request.args.get('year', type=int)
    quarter    = request.args.get('quarter', type=int)
    staff_name = (request.args.get('staff_name') or '').strip()
    status     = (request.args.get('status') or '').strip()
    dept       = (request.args.get('dept') or '').strip()   # 'store','business','manager','accounting'

    conn = get_db()
    try:
        conds, params = [], []
        if year:    conds.append('c.year=?');    params.append(year)
        if quarter: conds.append('c.quarter=?'); params.append(quarter)
        if staff_name:
            conds.append('c.staff_name=?'); params.append(staff_name)
        if status:
            conds.append('c.status=?'); params.append(status)
        if dept:
            # join staff to filter by role
            conds.append("""c.staff_name IN (
                SELECT name FROM staff WHERE role IN (
                    CASE ? WHEN 'store' THEN 'engineer' ELSE ? END
                ) OR (? IN ('store') AND role='engineer')
            )""")
            # simpler approach: pass role list
            role_map = {
                'store':      ('engineer',),
                'business':   ('sales',),
                'manager':    ('manager',),
                'accounting': ('accountant',),
            }
            roles = role_map.get(dept, ())
            if roles:
                placeholders = ','.join('?' for _ in roles)
                conds[-1] = f"c.staff_name IN (SELECT name FROM staff WHERE role IN ({placeholders}))"
                params.extend(roles)
            else:
                conds.pop()

        where = ('WHERE ' + ' AND '.join(conds)) if conds else ''
        rows = conn.execute(f"""
            SELECT c.*, s.title as staff_title, s.department, s.store
            FROM kpi_contributions c
            LEFT JOIN staff s ON s.name = c.staff_name
            {where}
            ORDER BY c.created_at DESC
        """, params).fetchall()
        return ok(items=[dict(r) for r in rows])
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()


@app.route('/api/kpi/contribution/submit', methods=['POST'])
def kpi_contribution_submit():
    data       = request.get_json() or {}
    staff_name = (data.get('staff_name') or '').strip()
    year       = int(data.get('year', datetime.now().year))
    quarter    = int(data.get('quarter', _cur_quarter()))
    description= (data.get('description') or '').strip()
    category   = (data.get('category') or '').strip()
    evidence_url = (data.get('evidence_url') or '').strip()

    if not staff_name or not description or not category:
        return err('姓名、說明與類別為必填')

    conn = get_db()
    try:
        # 計算已有幾項（不含拒絕的）
        cnt = conn.execute("""
            SELECT COUNT(*) FROM kpi_contributions
            WHERE staff_name=? AND year=? AND quarter=?
              AND status != 'rejected'
        """, (staff_name, year, quarter)).fetchone()[0]
        if cnt >= 3:
            return err('每季最多提出 3 項關鍵貢獻')

        item_number = cnt + 1
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("""
            INSERT INTO kpi_contributions
              (year, quarter, staff_name, item_number, description, category,
               evidence_type, evidence_url, status, score, created_at)
            VALUES (?,?,?,?,?,?,?,?,'pending', 5, ?)
        """, (year, quarter, staff_name, item_number, description, category,
              'photo' if evidence_url else 'text', evidence_url, now_str))
        conn.commit()
        return ok({'message': '提交成功，等待主管審核'})
    except Exception as e:
        conn.rollback()
        return err(str(e), 500)
    finally:
        conn.close()


@app.route('/api/kpi/contribution/upload', methods=['POST'])
def kpi_contribution_upload():
    """上傳佐證照片，回傳可存取的 URL"""
    file = request.files.get('file')
    if not file or file.filename == '':
        return err('未選擇檔案')
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.pdf'):
        return err('不支援的檔案格式，請上傳圖片或 PDF')

    filename = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(KPI_EVIDENCE_DIR, filename)
    file.save(save_path)
    return ok({'url': f'/kpi/evidence/{filename}', 'filename': filename})


@app.route('/api/kpi/contribution/review', methods=['POST'])
def kpi_contribution_review():
    data    = request.get_json() or {}
    item_id = data.get('id')
    action  = (data.get('action') or '').strip()    # 'approve' | 'reject'
    reviewer= (data.get('reviewer') or '').strip()

    if not item_id or action not in ('approve', 'reject') or not reviewer:
        return err('缺少必要欄位')

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM kpi_contributions WHERE id=?", (item_id,)
        ).fetchone()
        if not row:
            return err('找不到此項目')
        if row['status'] not in ('pending',):
            return err('此項目已被審核')

        new_status = 'approved' if action == 'approve' else 'rejected'
        now_str    = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn.execute("""
            UPDATE kpi_contributions
            SET status=?, reviewed_by=?, reviewed_at=?
            WHERE id=?
        """, (new_status, reviewer, now_str, item_id))

        # 核准後重新計算 kpi5
        if new_status == 'approved':
            _recalc_kpi5(conn, row['staff_name'], row['year'], row['quarter'])

        conn.commit()
        return ok({'message': '審核完成', 'status': new_status})
    except Exception as e:
        conn.rollback()
        return err(str(e), 500)
    finally:
        conn.close()


@app.route('/api/kpi/contribution/delete', methods=['POST'])
def kpi_contribution_delete():
    """員工刪除自己的待審 pending 項目"""
    data       = request.get_json() or {}
    item_id    = data.get('id')
    staff_name = (data.get('staff_name') or '').strip()

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT staff_name, status FROM kpi_contributions WHERE id=?", (item_id,)
        ).fetchone()
        if not row:
            return err('找不到此項目')
        if row['staff_name'] != staff_name:
            return err('無權刪除他人的項目')
        if row['status'] != 'pending':
            return err('已審核的項目無法刪除')
        conn.execute("DELETE FROM kpi_contributions WHERE id=?", (item_id,))
        conn.commit()
        return ok()
    except Exception as e:
        conn.rollback()
        return err(str(e), 500)
    finally:
        conn.close()


@app.route('/api/kpi/available-periods')
def kpi_available_periods():
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT DISTINCT year, quarter
            FROM kpi_scores
            ORDER BY year DESC, quarter DESC
        """).fetchall()
        return ok(periods=[{'year': r['year'], 'quarter': r['quarter']} for r in rows])
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()


# ─────────────────────────────────────────────
# 財務模組 API
# ─────────────────────────────────────────────

# ── 零用金：查詢各門市餘額 ──
@app.route('/api/finance/petty-cash')
def finance_petty_cash_list():
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM finance_petty_cash ORDER BY id").fetchall()
        return ok(data=[dict(r) for r in rows])
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()

# ── 零用金：查詢流水記錄 ──
@app.route('/api/finance/petty-cash/log')
def finance_petty_cash_log_list():
    conn = get_db()
    try:
        store = request.args.get('store', '')
        month = request.args.get('month', '')  # YYYY-MM
        where, params = [], []
        if store:
            where.append("store_name = ?")
            params.append(store)
        if month:
            where.append("created_at LIKE ?")
            params.append(month + '%')
        w = ('WHERE ' + ' AND '.join(where)) if where else ''
        rows = conn.execute(f"SELECT * FROM finance_petty_cash_log {w} ORDER BY created_at DESC", params).fetchall()
        return ok(data=[dict(r) for r in rows])
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()

# ── 零用金：登記支出 ──
@app.route('/api/finance/petty-cash/log', methods=['POST'])
def finance_petty_cash_log_create():
    conn = get_db()
    try:
        d = request.get_json() or {}
        amount = float(d.get('amount', 0))
        category = d.get('category', '').strip()
        description = d.get('description', '').strip()
        handler = d.get('handler', '').strip()
        department = d.get('department', '').strip()
        invoice_no = d.get('invoice_no', '').strip()
        if amount <= 0 or not handler:
            return err('金額、經手人為必填')
        # 檢查共用帳戶餘額
        pc = conn.execute("SELECT balance FROM finance_petty_cash WHERE store_name='共用'").fetchone()
        if not pc:
            return err('找不到零用金帳戶')
        if pc['balance'] < amount:
            return err(f'零用金餘額不足（目前 {pc["balance"]:.0f}，欲支出 {amount:.0f}）')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("""INSERT INTO finance_petty_cash_log
            (store_name, log_type, amount, category, description, handler, created_at, invoice_no, department)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            ('共用', 'expense', amount, category, description, handler, now, invoice_no, department))
        conn.execute("UPDATE finance_petty_cash SET balance = balance - ?, updated_at = ? WHERE store_name = '共用'",
            (amount, now))
        conn.commit()
        return ok()
    except Exception as e:
        conn.rollback()
        return err(str(e), 500)
    finally:
        conn.close()

# ── 零用金：補充 ──
@app.route('/api/finance/petty-cash/refill', methods=['POST'])
def finance_petty_cash_refill():
    conn = get_db()
    try:
        d = request.get_json() or {}
        amount = float(d.get('amount', 0))
        handler = d.get('handler', '').strip()
        if amount <= 0 or not handler:
            return err('金額、經手人為必填')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("""INSERT INTO finance_petty_cash_log
            (store_name, log_type, amount, category, description, handler, created_at, invoice_no, department)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            ('共用', 'refill', amount, '補充', f'零用金補充 ${amount:.0f}', handler, now, '', ''))
        conn.execute("UPDATE finance_petty_cash SET balance = balance + ?, last_refill_at = ?, updated_at = ? WHERE store_name = '共用'",
            (amount, now, now))
        conn.commit()
        return ok()
    except Exception as e:
        conn.rollback()
        return err(str(e), 500)
    finally:
        conn.close()

# ── 零用金：設定初始金額 ──
@app.route('/api/finance/petty-cash/init', methods=['POST'])
def finance_petty_cash_init():
    conn = get_db()
    try:
        d = request.get_json() or {}
        amount = float(d.get('amount', 0))
        if amount < 0:
            return err('金額不可為負')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("UPDATE finance_petty_cash SET initial_amount=?, balance=?, updated_at=? WHERE store_name='共用'",
            (amount, amount, now))
        conn.commit()
        return ok()
    except Exception as e:
        conn.rollback()
        return err(str(e), 500)
    finally:
        conn.close()

# ── 應收帳款：列表 ──
@app.route('/api/finance/receivables')
def finance_receivables_list():
    conn = get_db()
    try:
        status = request.args.get('status', '')
        month = request.args.get('month', '')
        where, params = [], []
        if status:
            where.append("status = ?")
            params.append(status)
        if month:
            where.append("created_at LIKE ?")
            params.append(month + '%')
        w = ('WHERE ' + ' AND '.join(where)) if where else ''
        rows = conn.execute(f"SELECT * FROM finance_receivables {w} ORDER BY due_date ASC, created_at DESC", params).fetchall()
        return ok(data=[dict(r) for r in rows])
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()

# ── 應收帳款：新增 ──
@app.route('/api/finance/receivables', methods=['POST'])
def finance_receivables_create():
    conn = get_db()
    try:
        d = request.get_json() or {}
        customer_name = d.get('customer_name', '').strip()
        amount = float(d.get('amount', 0))
        if not customer_name or amount <= 0:
            return err('客戶名稱和金額為必填')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("""INSERT INTO finance_receivables
            (customer_id, customer_name, invoice_no, amount, due_date, status, note, created_at)
            VALUES (?,?,?,?,?,?,?,?)""",
            (d.get('customer_id',''), customer_name, d.get('invoice_no',''),
             amount, d.get('due_date',''), 'unpaid', d.get('note',''), now))
        conn.commit()
        return ok()
    except Exception as e:
        conn.rollback()
        return err(str(e), 500)
    finally:
        conn.close()

# ── 應收帳款：標記已收款 ──
@app.route('/api/finance/receivables/confirm', methods=['POST'])
def finance_receivables_confirm():
    conn = get_db()
    try:
        d = request.get_json() or {}
        rid = d.get('id')
        if not rid:
            return err('缺少 id')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("UPDATE finance_receivables SET status='paid', paid_at=? WHERE id=?", (now, rid))
        conn.commit()
        return ok()
    except Exception as e:
        conn.rollback()
        return err(str(e), 500)
    finally:
        conn.close()

# ── 應收帳款：整批沖帳（同一客戶同一帳期） ──
@app.route('/api/finance/receivables/batch-confirm', methods=['POST'])
def finance_receivables_batch_confirm():
    conn = get_db()
    try:
        d = request.get_json() or {}
        customer_id = d.get('customer_id', '').strip()
        billing_period = d.get('billing_period', '').strip()  # e.g. "2026-04"
        if not customer_id or not billing_period:
            return err('缺少 customer_id 或 billing_period')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        affected = conn.execute("""
            UPDATE finance_receivables SET status='paid', paid_at=?
            WHERE customer_id=? AND status='unpaid' AND note LIKE ?
        """, (now, customer_id, f'帳期 {billing_period}%')).rowcount
        conn.commit()
        return ok(data={'updated': affected})
    except Exception as e:
        conn.rollback()
        return err(str(e), 500)
    finally:
        conn.close()

# ── 應收帳款：月結摘要（按客戶 × 帳期彙總） ──
@app.route('/api/finance/receivables/summary')
def finance_receivables_summary():
    conn = get_db()
    try:
        status = request.args.get('status', 'unpaid')
        where, params = [], []
        if status:
            where.append("status = ?")
            params.append(status)
        w = ('WHERE ' + ' AND '.join(where)) if where else ''
        rows = conn.execute(f"""
            SELECT customer_id, customer_name, note,
                   COUNT(*) as invoice_count,
                   SUM(amount) as total_amount,
                   MIN(due_date) as due_date,
                   MAX(created_at) as last_created
            FROM finance_receivables {w}
            GROUP BY customer_id, note
            ORDER BY due_date ASC, customer_name ASC
        """, params).fetchall()
        return ok(data=[dict(r) for r in rows])
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()

# ── 應付帳款：列表 ──
@app.route('/api/finance/payables')
def finance_payables_list():
    conn = get_db()
    try:
        status = request.args.get('status', '')
        month = request.args.get('month', '')
        company = request.args.get('company', '').strip()
        where, params = [], []
        if status:
            where.append("status = ?")
            params.append(status)
        if month:
            where.append("created_at LIKE ?")
            params.append(month + '%')
        if company:
            where.append("company = ?")
            params.append(company)
        w = ('WHERE ' + ' AND '.join(where)) if where else ''
        rows = conn.execute(f"SELECT * FROM finance_payables {w} ORDER BY due_date ASC, created_at DESC", params).fetchall()
        return ok(data=[dict(r) for r in rows])
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()

# ── 應付帳款：新增 ──
@app.route('/api/finance/payables', methods=['POST'])
def finance_payables_create():
    conn = get_db()
    try:
        d = request.get_json() or {}
        vendor_name = d.get('vendor_name', '').strip()
        amount = float(d.get('amount', 0))
        if not vendor_name or amount <= 0:
            return err('廠商名稱和金額為必填')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        company = d.get('company', '').strip()
        pretax = float(d.get('pretax_amount', 0) or 0)
        tax    = float(d.get('tax_amount', 0) or 0)
        # 若前端有帶未稅＋稅額，amount 用含稅；否則 amount 即為全額
        if pretax > 0 and tax > 0:
            amount = pretax + tax
        elif pretax > 0:
            pretax = amount
        else:
            pretax = amount
        conn.execute("""INSERT INTO finance_payables
            (vendor_name, order_no, amount, pretax_amount, tax_amount,
             due_date, status, note, company, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (vendor_name, d.get('order_no',''), amount, pretax, tax,
             d.get('due_date',''), 'unpaid', d.get('note',''), company or None, now))
        conn.commit()
        return ok()
    except Exception as e:
        conn.rollback()
        return err(str(e), 500)
    finally:
        conn.close()

# ── 應付帳款：標記已付款 ──
@app.route('/api/finance/payables/confirm', methods=['POST'])
def finance_payables_confirm():
    conn = get_db()
    try:
        d = request.get_json() or {}
        pid = d.get('id')
        if not pid:
            return err('缺少 id')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("UPDATE finance_payables SET status='paid', paid_at=? WHERE id=?", (now, pid))
        conn.commit()
        return ok()
    except Exception as e:
        conn.rollback()
        return err(str(e), 500)
    finally:
        conn.close()

# ── 收支日記帳：列表 ──
@app.route('/api/finance/transactions')
def finance_transactions_list():
    conn = get_db()
    try:
        store = request.args.get('store', '')
        month = request.args.get('month', '')
        ttype = request.args.get('type', '')
        where, params = [], []
        if store:
            where.append("store_name = ?")
            params.append(store)
        if month:
            where.append("date LIKE ?")
            params.append(month + '%')
        if ttype:
            where.append("type = ?")
            params.append(ttype)
        w = ('WHERE ' + ' AND '.join(where)) if where else ''
        rows = conn.execute(f"SELECT * FROM finance_transactions {w} ORDER BY date DESC, id DESC", params).fetchall()
        return ok(data=[dict(r) for r in rows])
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()

# ── 收支日記帳：新增 ──
@app.route('/api/finance/transactions', methods=['POST'])
def finance_transactions_create():
    conn = get_db()
    try:
        d = request.get_json() or {}
        date = d.get('date', '').strip()
        ttype = d.get('type', '').strip()
        amount = float(d.get('amount', 0))
        if not date or ttype not in ('income','expense') or amount <= 0:
            return err('日期、類型（income/expense）、金額為必填')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("""INSERT INTO finance_transactions
            (date, store_name, type, category, amount, description, handler, created_at)
            VALUES (?,?,?,?,?,?,?,?)""",
            (date, d.get('store_name',''), ttype, d.get('category',''),
             amount, d.get('description',''), d.get('handler',''), now))
        conn.commit()
        return ok()
    except Exception as e:
        conn.rollback()
        return err(str(e), 500)
    finally:
        conn.close()

# ── 財務總覽（損益、現金流） ──
@app.route('/api/finance/dashboard')
def finance_dashboard():
    conn = get_db()
    try:
        month = request.args.get('month', datetime.now().strftime('%Y-%m'))
        y, m = month.split('-')
        start = f"{y}-{m}-01"
        end_m = int(m) + 1
        end_y = int(y)
        if end_m > 12:
            end_m = 1
            end_y += 1
        end = f"{end_y}-{end_m:02d}-01"

        # 營業收入 & 銷貨成本（直接從 sales_history 的 profit 欄位反算）
        r = conn.execute("""
            SELECT COALESCE(SUM(amount),0) as revenue,
                   COALESCE(SUM(profit),0) as total_profit
            FROM sales_history WHERE date >= ? AND date < ?
        """, (start, end)).fetchone()
        revenue = r['revenue']
        sales_profit = r['total_profit']
        cogs = revenue - sales_profit  # 銷貨成本 = 營收 - 毛利

        # 薪資/獎金
        r = conn.execute("SELECT COALESCE(SUM(bonus_amount),0) as total FROM bonus_results WHERE status='confirmed' AND period_start >= ? AND period_start < ?", (start, end)).fetchone()
        bonus = r['total']

        # 其他支出（收支日記帳）
        r = conn.execute("SELECT COALESCE(SUM(amount),0) as total FROM finance_transactions WHERE type='expense' AND date >= ? AND date < ?", (start, end)).fetchone()
        other_expense = r['total']

        # 其他收入（收支日記帳）
        r = conn.execute("SELECT COALESCE(SUM(amount),0) as total FROM finance_transactions WHERE type='income' AND date >= ? AND date < ?", (start, end)).fetchone()
        other_income = r['total']

        # 零用金支出
        r = conn.execute("SELECT COALESCE(SUM(amount),0) as total FROM finance_petty_cash_log WHERE log_type='expense' AND created_at >= ? AND created_at < ?", (start, end)).fetchone()
        petty_expense = r['total']

        gross_profit = revenue - cogs  # = sales_profit
        gross_margin = round(gross_profit / revenue * 100, 1) if revenue else 0

        # 本月進貨金額（僅供參考，非銷貨成本）
        r = conn.execute("SELECT COALESCE(SUM(amount),0) as total FROM purchase_history WHERE date >= ? AND date < ?", (start, end)).fetchone()
        purchase_total = r['total']

        net_profit = gross_profit - bonus - other_expense - petty_expense + other_income

        # 各門市/部門收入（門市部用 store 分，業務部/總公司用 department 分）
        store_revenue = conn.execute("""
            SELECT CASE
                     WHEN s.store IS NOT NULL AND s.store != '' AND s.store != '-'
                       THEN s.store || '門市'
                     WHEN s.department IS NOT NULL AND s.department != ''
                       THEN s.department
                     ELSE '未分類'
                   END as store_name,
                   COALESCE(SUM(sh.amount),0) as total
            FROM sales_history sh
            LEFT JOIN staff s ON sh.salesperson = s.name
            WHERE sh.date >= ? AND sh.date < ?
            GROUP BY store_name ORDER BY total DESC
        """, (start, end)).fetchall()

        # 應收/應付摘要
        recv_unpaid = conn.execute("SELECT COALESCE(SUM(amount),0) as total FROM finance_receivables WHERE status='unpaid'").fetchone()['total']
        pay_unpaid = conn.execute("SELECT COALESCE(SUM(amount),0) as total FROM finance_payables WHERE status='unpaid'").fetchone()['total']

        return ok(data={
            'month': month,
            'revenue': revenue,
            'cogs': cogs,
            'gross_profit': gross_profit,
            'gross_margin': gross_margin,
            'purchase_total': purchase_total,
            'bonus': bonus,
            'other_expense': other_expense,
            'other_income': other_income,
            'petty_expense': petty_expense,
            'net_profit': net_profit,
            'store_revenue': [dict(r) for r in store_revenue],
            'receivables_unpaid': recv_unpaid,
            'payables_unpaid': pay_unpaid,
        })
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()

# ── 稅務統計 ──
@app.route('/api/finance/tax')
def finance_tax():
    conn = get_db()
    try:
        year = request.args.get('year', datetime.now().strftime('%Y'))
        rows = conn.execute("""
            SELECT substr(date,1,7) as month,
                   COALESCE(SUM(amount),0) as sales_amount,
                   ROUND(COALESCE(SUM(amount),0) * 5.0 / 105, 0) as tax_amount
            FROM sales_history
            WHERE date LIKE ?
            GROUP BY substr(date,1,7)
            ORDER BY month
        """, (year + '%',)).fetchall()
        return ok(data=[dict(r) for r in rows])
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()

# ── 現金流預測 ──
@app.route('/api/finance/cashflow')
def finance_cashflow():
    conn = get_db()
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        future = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

        # 預計收入：未收應收帳款（到期日在未來30天內）
        recv = conn.execute("""
            SELECT due_date, COALESCE(SUM(amount),0) as total
            FROM finance_receivables
            WHERE status='unpaid' AND due_date >= ? AND due_date <= ?
            GROUP BY due_date ORDER BY due_date
        """, (today, future)).fetchall()

        # 預計支出：未付應付帳款
        pay = conn.execute("""
            SELECT due_date, COALESCE(SUM(amount),0) as total
            FROM finance_payables
            WHERE status='unpaid' AND due_date >= ? AND due_date <= ?
            GROUP BY due_date ORDER BY due_date
        """, (today, future)).fetchall()

        # 歷史日均收支（過去30天）
        past = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        r = conn.execute("SELECT COALESCE(SUM(amount),0)/30.0 as avg FROM sales_history WHERE date >= ? AND date <= ?", (past, today)).fetchone()
        avg_daily_income = r['avg']
        r = conn.execute("SELECT COALESCE(SUM(amount),0)/30.0 as avg FROM finance_transactions WHERE type='expense' AND date >= ? AND date <= ?", (past, today)).fetchone()
        avg_daily_expense = r['avg']

        return ok(data={
            'period': {'from': today, 'to': future},
            'expected_income': [dict(r) for r in recv],
            'expected_expense': [dict(r) for r in pay],
            'avg_daily_income': round(avg_daily_income, 0),
            'avg_daily_expense': round(avg_daily_expense, 0),
        })
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()

# ── 廠商對帳 ──
@app.route('/api/finance/vendor-reconcile')
def finance_vendor_reconcile():
    conn = get_db()
    try:
        month = request.args.get('month', datetime.now().strftime('%Y-%m'))
        company = request.args.get('company', '').strip()
        y, m = month.split('-')
        start = f"{y}-{m}-01"
        end_m = int(m) + 1
        end_y = int(y)
        if end_m > 12:
            end_m = 1
            end_y += 1
        end = f"{end_y}-{end_m:02d}-01"

        # 本月進貨彙總（按廠商）
        purch_where = "WHERE date >= ? AND date < ?"
        purch_params = [start, end]
        if company:
            purch_where += " AND company = ?"
            purch_params.append(company)
        purchases = conn.execute(f"""
            SELECT supplier_name, company, COUNT(*) as order_count,
                   COALESCE(SUM(quantity),0) as total_qty,
                   COALESCE(SUM(amount),0) as total_amount
            FROM purchase_history
            {purch_where}
            GROUP BY supplier_name, company
            ORDER BY total_amount DESC
        """, purch_params).fetchall()

        # 應付帳款（按廠商）
        pay_where = "WHERE created_at >= ? AND created_at < ?"
        pay_params = [start, end]
        if company:
            pay_where += " AND company = ?"
            pay_params.append(company)
        payables = conn.execute(f"""
            SELECT vendor_name, company, status, COALESCE(SUM(amount),0) as total
            FROM finance_payables
            {pay_where}
            GROUP BY vendor_name, company, status
            ORDER BY vendor_name
        """, pay_params).fetchall()

        # 廠商帳期資訊
        sup_terms = conn.execute("""
            SELECT supplier_name, payment_method, closing_day, pay_day
            FROM suppliers WHERE status='正常'
        """).fetchall()
        terms_map = {r['supplier_name']: dict(r) for r in sup_terms}

        return ok(data={
            'month': month,
            'purchases': [dict(r) for r in purchases],
            'payables': [dict(r) for r in payables],
            'terms': terms_map,
        })
    except Exception as e:
        return err(str(e), 500)
    finally:
        conn.close()


# ─────────────────────────────────────────────
# 確保 company 欄位存在（雙公司支援）
# ─────────────────────────────────────────────
def _ensure_company_columns():
    conn = get_db()
    try:
        for table in ('purchase_history', 'finance_payables'):
            cols = [r['name'] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
            if 'company' not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN company TEXT")
                conn.commit()
    except Exception:
        pass
    finally:
        conn.close()

_ensure_company_columns()


# ─────────────────────────────────────────────
# 盤點作業
# ─────────────────────────────────────────────

@app.route('/api/inventory-count/create', methods=['POST'])
def inventory_count_create():
    """建立盤點單：快照指定倉庫當下庫存"""
    data = request.get_json() or {}
    warehouse = (data.get('warehouse') or '').strip()
    created_by = (data.get('created_by') or '').strip()
    note = (data.get('note') or '').strip()
    if not warehouse:
        return err('請選擇盤點倉庫')

    conn = get_db()
    try:
        # 產生盤點單號 IC-YYYYMMDD-NNN
        today = datetime.now().strftime('%Y%m%d')
        tag = f'IC-{today}-'
        last = conn.execute(
            "SELECT count_no FROM inventory_count WHERE count_no LIKE ? ORDER BY count_no DESC LIMIT 1",
            (f'{tag}%',)
        ).fetchone()
        seq = 1
        if last:
            try: seq = int(last['count_no'].replace(tag, '')) + 1
            except: seq = 1
        count_no = f'{tag}{seq:03d}'

        # 建主表
        conn.execute(
            """INSERT INTO inventory_count (count_no, warehouse, status, note, created_by)
               VALUES (?, ?, 'drafting', ?, ?)""",
            (count_no, warehouse, note, created_by)
        )
        count_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # 快照該倉庫當下庫存（最新 report_date）
        items = conn.execute(
            """SELECT product_id, item_spec, stock_quantity
               FROM inventory
               WHERE warehouse = ?
                 AND report_date = (SELECT MAX(report_date) FROM inventory WHERE warehouse = ?)
                 AND stock_quantity > 0
               ORDER BY product_id""",
            (warehouse, warehouse)
        ).fetchall()

        for item in items:
            conn.execute(
                """INSERT INTO inventory_count_items (count_id, product_code, product_name, book_qty)
                   VALUES (?, ?, ?, ?)""",
                (count_id, item['product_id'], item['item_spec'], item['stock_quantity'])
            )

        conn.commit()
        return ok(count_id=count_id, count_no=count_no, item_count=len(items))
    except Exception as e:
        return err(str(e))
    finally:
        conn.close()


@app.route('/api/inventory-count/list')
def inventory_count_list():
    """盤點單列表"""
    status = request.args.get('status', '')
    conn = get_db()
    try:
        sql = "SELECT * FROM inventory_count ORDER BY created_at DESC"
        params = []
        if status:
            sql = "SELECT * FROM inventory_count WHERE status=? ORDER BY created_at DESC"
            params = [status]
        rows = conn.execute(sql, params).fetchall()
        return ok(counts=[dict(r) for r in rows])
    finally:
        conn.close()


@app.route('/api/inventory-count/<int:count_id>')
def inventory_count_detail(count_id):
    """盤點單明細（含所有品項）"""
    conn = get_db()
    try:
        header = conn.execute("SELECT * FROM inventory_count WHERE id=?", (count_id,)).fetchone()
        if not header:
            return err('找不到此盤點單')
        items = conn.execute(
            """SELECT * FROM inventory_count_items WHERE count_id=?
               ORDER BY product_code""",
            (count_id,)
        ).fetchall()
        return ok(header=dict(header), items=[dict(i) for i in items])
    finally:
        conn.close()


@app.route('/api/inventory-count/<int:count_id>/save', methods=['POST'])
def inventory_count_save(count_id):
    """儲存盤點實盤數量（可多次儲存）"""
    data = request.get_json() or {}
    items = data.get('items', [])  # [{id, actual_qty, remark}]
    conn = get_db()
    try:
        header = conn.execute("SELECT status FROM inventory_count WHERE id=?", (count_id,)).fetchone()
        if not header:
            return err('找不到此盤點單')
        if header['status'] != 'drafting':
            return err('此盤點單已送出，無法修改')
        for item in items:
            aq = item.get('actual_qty')
            conn.execute(
                "UPDATE inventory_count_items SET actual_qty=?, remark=? WHERE id=? AND count_id=?",
                (int(aq) if aq is not None and str(aq).strip() != '' else None,
                 item.get('remark', ''),
                 item['id'], count_id)
            )
        conn.commit()
        return ok(message='已儲存')
    except Exception as e:
        return err(str(e))
    finally:
        conn.close()


@app.route('/api/inventory-count/<int:count_id>/submit', methods=['POST'])
def inventory_count_submit(count_id):
    """送出盤點單（鎖定不可再改）"""
    conn = get_db()
    try:
        header = conn.execute("SELECT status FROM inventory_count WHERE id=?", (count_id,)).fetchone()
        if not header:
            return err('找不到此盤點單')
        if header['status'] != 'drafting':
            return err('此盤點單已送出')
        # 檢查是否所有品項都已填入實盤數量
        unfilled = conn.execute(
            "SELECT COUNT(*) as cnt FROM inventory_count_items WHERE count_id=? AND actual_qty IS NULL",
            (count_id,)
        ).fetchone()['cnt']
        if unfilled > 0:
            return err(f'尚有 {unfilled} 項未填寫實盤數量')
        conn.execute(
            "UPDATE inventory_count SET status='submitted', submitted_at=datetime('now','localtime') WHERE id=?",
            (count_id,)
        )
        conn.commit()
        return ok(message='盤點單已送出')
    except Exception as e:
        return err(str(e))
    finally:
        conn.close()


@app.route('/api/inventory-count/<int:count_id>/approve', methods=['POST'])
def inventory_count_approve(count_id):
    """老闆審核通過：將有差異的品項寫入調整紀錄"""
    data = request.get_json() or {}
    approved_by = (data.get('approved_by') or '').strip()
    conn = get_db()
    try:
        header = conn.execute("SELECT * FROM inventory_count WHERE id=?", (count_id,)).fetchone()
        if not header:
            return err('找不到此盤點單')
        if header['status'] != 'submitted':
            return err('此盤點單尚未送出或已審核')

        # 取得有差異的品項
        diffs = conn.execute(
            """SELECT * FROM inventory_count_items
               WHERE count_id=? AND diff != 0""",
            (count_id,)
        ).fetchall()

        # 寫入調整紀錄
        for d in diffs:
            conn.execute(
                """INSERT INTO inventory_adjustments
                   (count_id, product_code, product_name, warehouse, book_qty, actual_qty, adjust_qty, approved_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (count_id, d['product_code'], d['product_name'], header['warehouse'],
                 d['book_qty'], d['actual_qty'], d['diff'], approved_by)
            )

        conn.execute(
            "UPDATE inventory_count SET status='approved', reviewed_by=?, reviewed_at=datetime('now','localtime') WHERE id=?",
            (approved_by, count_id)
        )
        conn.commit()
        return ok(message='審核通過', adjusted_count=len(diffs))
    except Exception as e:
        return err(str(e))
    finally:
        conn.close()


@app.route('/api/inventory-count/<int:count_id>', methods=['DELETE'])
def inventory_count_delete(count_id):
    """刪除盤點單（僅 drafting 狀態可刪）"""
    conn = get_db()
    try:
        header = conn.execute("SELECT status FROM inventory_count WHERE id=?", (count_id,)).fetchone()
        if not header:
            return err('找不到此盤點單')
        if header['status'] != 'drafting':
            return err('僅「盤點中」的盤點單可以刪除')
        conn.execute("DELETE FROM inventory_count_items WHERE count_id=?", (count_id,))
        conn.execute("DELETE FROM inventory_count WHERE id=?", (count_id,))
        conn.commit()
        return ok(message='已刪除')
    except Exception as e:
        return err(str(e))
    finally:
        conn.close()


@app.route('/api/inventory-count/<int:count_id>/reject', methods=['POST'])
def inventory_count_reject(count_id):
    """老闆退回盤點單（回到 drafting 可重新填寫）"""
    data = request.get_json() or {}
    reviewed_by = (data.get('reviewed_by') or '').strip()
    conn = get_db()
    try:
        header = conn.execute("SELECT status FROM inventory_count WHERE id=?", (count_id,)).fetchone()
        if not header:
            return err('找不到此盤點單')
        if header['status'] != 'submitted':
            return err('此盤點單尚未送出')
        conn.execute(
            "UPDATE inventory_count SET status='drafting', reviewed_by=?, reviewed_at=datetime('now','localtime') WHERE id=?",
            (reviewed_by, count_id)
        )
        conn.commit()
        return ok(message='已退回重新盤點')
    except Exception as e:
        return err(str(e))
    finally:
        conn.close()


# ─────────────────────────────────────────────
# PDF 列印
# ─────────────────────────────────────────────
from pdf_utils import (
    generate_pdf, build_header, build_items_table, build_totals_block,
    build_note_block, build_signature_block, build_footer_elements,
    fmt_num, fmt_date, Spacer, mm
)

@app.route('/api/pdf/quote/<path:doc_no>')
def pdf_quote(doc_no):
    """報價單 PDF"""
    conn = get_db()
    try:
        doc = conn.execute("SELECT * FROM sales_documents WHERE doc_no=?", (doc_no,)).fetchone()
        if not doc:
            return err('找不到此報價單'), 404
        items = conn.execute(
            "SELECT * FROM sales_document_items WHERE doc_no=? ORDER BY id", (doc_no,)
        ).fetchall()
        d = dict(doc)
        item_list = [dict(i) for i in items]

        def make():
            fields = [
                ('客戶', d.get('target_name') or ''),
                ('日期', fmt_date(d.get('created_at'))),
                ('有效期限', fmt_date(d.get('valid_until') or '')),
                ('客戶編號', d.get('target_id') or ''),
                ('業務', d.get('created_by') or ''),
            ]
            cust = d.get('target_name') or ''
            sp = d.get('created_by') or ''
            elems = build_header('報價單', doc_no, extra_fields=fields,
                                 customer_name=cust, salesperson=sp)

            rows = []
            for idx, it in enumerate(item_list, 1):
                rows.append([
                    str(idx),
                    it.get('product_name') or it.get('product_code') or '',
                    fmt_num(it.get('qty')),
                    fmt_num(it.get('unit_price')),
                    fmt_num(it.get('subtotal')),
                ])
            elems.append(build_items_table(
                ['#', '品名', '數量', '單價', '小計'],
                rows,
                col_widths=[8, 68, 14, 22, 22],
                align_right_cols={2, 3, 4}
            ))
            elems.append(Spacer(1, 4 * mm))
            elems.append(build_totals_block([('合計', fmt_num(d.get('total_amount')))]))
            note = d.get('note') or ''
            if note:
                elems.append(Spacer(1, 4 * mm))
                elems.append(build_note_block(note))
            elems.extend(build_signature_block(salesperson=sp))
            elems += build_footer_elements()
            return elems

        buf = generate_pdf(make)
        resp = send_file(buf, mimetype='application/pdf',
                         as_attachment=False, download_name=f'報價單_{doc_no}.pdf')
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return resp
    except Exception as e:
        return err(str(e)), 500
    finally:
        conn.close()


# ── 書信式列印（HTML）──────────────────────────────
def _fmt_date_zh(d):
    """將 '2026-04-03' 轉為 '2026 年 4 月 3 日'"""
    s = fmt_date(d)
    if not s:
        return ''
    try:
        parts = s.split('-')
        return f'{parts[0]} 年 {int(parts[1])} 月 {int(parts[2])} 日'
    except Exception:
        return s


def _fmt_date_dot(d):
    """將 '2026-04-03' 轉為 '2026 . 4 . 3'"""
    s = fmt_date(d)
    if not s:
        return ''
    try:
        parts = s.split('-')
        return f'{parts[0]} . {int(parts[1])} . {int(parts[2])}'
    except Exception:
        return s


@app.route('/print/quote/<path:doc_no>')
def print_quote(doc_no):
    """報價單 — 書信式 HTML 列印"""
    conn = get_db()
    try:
        doc = conn.execute("SELECT * FROM sales_documents WHERE doc_no=?", (doc_no,)).fetchone()
        if not doc:
            return err('找不到此報價單'), 404
        rows = conn.execute(
            "SELECT * FROM sales_document_items WHERE doc_no=? ORDER BY id", (doc_no,)
        ).fetchall()
        d = dict(doc)
        items = []
        for it in rows:
            it = dict(it)
            items.append({
                'name': it.get('product_name') or it.get('product_code') or '',
                'qty': fmt_num(it.get('qty')),
                'price': fmt_num(it.get('subtotal')),
            })
        total = fmt_num(d.get('total_amount'))
        return render_template('print_letter.html',
            doc_type='報價單',
            doc_no=doc_no,
            company=d.get('company') or '電瑙舖資訊有限公司',
            tax_id='27488187',
            date_display=_fmt_date_zh(d.get('created_at')),
            date_short=_fmt_date_dot(d.get('created_at')),
            date_stamp=fmt_date(d.get('created_at')),
            customer_name=d.get('target_name') or '',
            salesperson=d.get('created_by') or '',
            valid_until=fmt_date(d.get('valid_until') or ''),
            valid_until_display=_fmt_date_zh(d.get('valid_until') or ''),
            items=items,
            totals=[{'label': '商品合計', 'value': total}, {'label': '本次報價', 'value': total}],
            note=d.get('note') or '',
            extra_info=[],
        )
    except Exception as e:
        return err(str(e)), 500
    finally:
        conn.close()


@app.route('/print/order/<path:doc_no>')
def print_order(doc_no):
    """訂單 — 書信式 HTML 列印"""
    conn = get_db()
    try:
        doc = conn.execute("SELECT * FROM sales_documents WHERE doc_no=?", (doc_no,)).fetchone()
        if not doc:
            return err('找不到此訂單'), 404
        rows = conn.execute(
            "SELECT * FROM sales_document_items WHERE doc_no=? ORDER BY id", (doc_no,)
        ).fetchall()
        d = dict(doc)
        items = []
        for it in rows:
            it = dict(it)
            items.append({
                'name': it.get('product_name') or it.get('product_code') or '',
                'qty': fmt_num(it.get('qty')),
                'price': fmt_num(it.get('subtotal')),
            })
        total = int(d.get('total_amount') or 0)
        deposit = int(d.get('deposit_amount') or 0)
        balance = int(d.get('balance_amount') or 0) or (total - deposit)
        totals = [{'label': '商品合計', 'value': fmt_num(total)}]
        if deposit:
            totals.append({'label': '訂金', 'value': fmt_num(deposit)})
            totals.append({'label': '尾款', 'value': fmt_num(balance)})
        else:
            totals.append({'label': '本次應付', 'value': fmt_num(total)})
        return render_template('print_letter.html',
            doc_type='訂購單',
            doc_no=doc_no,
            company=d.get('company') or '電瑙舖資訊有限公司',
            tax_id='27488187',
            date_display=_fmt_date_zh(d.get('created_at')),
            date_short=_fmt_date_dot(d.get('created_at')),
            date_stamp=fmt_date(d.get('created_at')),
            customer_name=d.get('target_name') or '',
            salesperson=d.get('created_by') or '',
            valid_until='',
            valid_until_display='',
            items=items,
            totals=totals,
            note=d.get('note') or '',
            extra_info=[],
        )
    except Exception as e:
        return err(str(e)), 500
    finally:
        conn.close()


@app.route('/print/sales/<path:sales_no>')
def print_sales(sales_no):
    """銷貨單 — 書信式 HTML 列印"""
    sales_no = sales_no.strip()
    if not sales_no:
        return err('缺少銷貨單號'), 400
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM sales_history WHERE sales_invoice_no=? ORDER BY id", (sales_no,)
        ).fetchall()
        if not rows:
            rows = conn.execute(
                "SELECT * FROM sales_history WHERE invoice_no=? ORDER BY id", (sales_no,)
            ).fetchall()
        if not rows:
            return err(f'找不到銷貨單號: {sales_no}'), 404
        row_list = [dict(r) for r in rows]
        first = row_list[0]
        items = []
        total_amount = 0
        for it in row_list:
            amt = int(it.get('amount') or 0)
            total_amount += amt
            items.append({
                'name': it.get('product_name') or it.get('product_code') or '',
                'qty': fmt_num(it.get('quantity')),
                'price': fmt_num(amt),
            })
        deposit = int(first.get('deposit_amount') or 0)
        totals = [{'label': '商品合計', 'value': fmt_num(total_amount)}]
        if deposit:
            totals.append({'label': '訂金', 'value': fmt_num(deposit)})
            totals.append({'label': '尾款', 'value': fmt_num(total_amount - deposit)})
        else:
            totals.append({'label': '本次應付', 'value': fmt_num(total_amount)})
        extra = []
        wh = first.get('warehouse') or ''
        if wh:
            extra.append(('門市', wh))
        pm = first.get('payment_method') or ''
        if pm:
            extra.append(('付款方式', pm))
        return render_template('print_letter.html',
            doc_type='銷貨單',
            doc_no=sales_no,
            company='電瑙舖資訊有限公司',
            tax_id='27488187',
            date_display=_fmt_date_zh(first.get('date')),
            date_short=_fmt_date_dot(first.get('date')),
            date_stamp=fmt_date(first.get('date')),
            customer_name=first.get('customer_name') or '',
            salesperson=first.get('salesperson') or '',
            valid_until='',
            valid_until_display='',
            items=items,
            totals=totals,
            note='',
            extra_info=extra,
        )
    except Exception as e:
        return err(str(e)), 500
    finally:
        conn.close()


@app.route('/api/pdf/order/<path:doc_no>')
def pdf_order(doc_no):
    """訂單 PDF"""
    conn = get_db()
    try:
        doc = conn.execute("SELECT * FROM sales_documents WHERE doc_no=?", (doc_no,)).fetchone()
        if not doc:
            return err('找不到此訂單'), 404
        items = conn.execute(
            "SELECT * FROM sales_document_items WHERE doc_no=? ORDER BY id", (doc_no,)
        ).fetchall()
        d = dict(doc)
        item_list = [dict(i) for i in items]

        def make():
            fields = [
                ('客戶', d.get('target_name') or ''),
                ('日期', fmt_date(d.get('created_at'))),
                ('客戶編號', d.get('target_id') or ''),
                ('業務', d.get('created_by') or ''),
            ]
            cust = d.get('target_name') or ''
            sp = d.get('created_by') or ''
            elems = build_header('訂購單', doc_no, extra_fields=fields,
                                 customer_name=cust, salesperson=sp)

            rows = []
            for idx, it in enumerate(item_list, 1):
                rows.append([
                    str(idx),
                    it.get('product_name') or it.get('product_code') or '',
                    fmt_num(it.get('qty')),
                    fmt_num(it.get('unit_price')),
                    fmt_num(it.get('subtotal')),
                ])
            elems.append(build_items_table(
                ['#', '品名', '數量', '單價', '小計'],
                rows,
                col_widths=[8, 68, 14, 22, 22],
                align_right_cols={2, 3, 4}
            ))
            elems.append(Spacer(1, 4 * mm))
            total = int(d.get('total_amount') or 0)
            deposit = int(d.get('deposit_amount') or 0)
            balance = int(d.get('balance_amount') or 0) or (total - deposit)
            totals = [('合計', fmt_num(total))]
            if deposit:
                totals.append(('訂金', fmt_num(deposit)))
                totals.append(('尾款', fmt_num(balance)))
            elems.append(build_totals_block(totals))
            note = d.get('note') or ''
            if note:
                elems.append(Spacer(1, 4 * mm))
                elems.append(build_note_block(note))
            elems.extend(build_signature_block(salesperson=sp))
            elems += build_footer_elements()
            return elems

        buf = generate_pdf(make)
        resp = send_file(buf, mimetype='application/pdf',
                         as_attachment=False, download_name=f'訂單_{doc_no}.pdf')
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return resp
    except Exception as e:
        return err(str(e)), 500
    finally:
        conn.close()


@app.route('/api/pdf/sales/<path:sales_no>')
def pdf_sales(sales_no):
    """銷貨單（出貨單）PDF — 依銷貨單號列印整張"""
    sales_no = sales_no.strip()
    if not sales_no:
        return err('缺少銷貨單號'), 400
    print(f'[PDF] 銷貨單列印 sales_invoice_no={repr(sales_no)}')
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM sales_history WHERE sales_invoice_no=? ORDER BY id", (sales_no,)
        ).fetchall()
        # 向下相容：若新欄位查不到，嘗試用舊 invoice_no 欄位
        if not rows:
            rows = conn.execute(
                "SELECT * FROM sales_history WHERE invoice_no=? ORDER BY id", (sales_no,)
            ).fetchall()
        print(f'[PDF] 查詢結果: {len(rows)} 筆')
        if not rows:
            return err(f'找不到銷貨單號: {sales_no}'), 404
        items = [dict(r) for r in rows]
        first = items[0]

        def make():
            fields = [
                ('客戶', first.get('customer_name') or ''),
                ('日期', fmt_date(first.get('date'))),
                ('客戶編號', first.get('customer_id') or ''),
                ('業務', first.get('salesperson') or ''),
                ('倉庫', first.get('warehouse') or ''),
                ('付款方式', first.get('payment_method') or ''),
            ]
            cust = first.get('customer_name') or ''
            sp = first.get('salesperson') or ''
            elems = build_header('銷貨單', sales_no, extra_fields=fields,
                                 customer_name=cust, salesperson=sp)

            tbl_rows = []
            total_amount = 0
            for idx, it in enumerate(items, 1):
                amt = int(it.get('amount') or 0)
                total_amount += amt
                tbl_rows.append([
                    str(idx),
                    it.get('product_code') or '',
                    it.get('product_name') or '',
                    fmt_num(it.get('quantity')),
                    fmt_num(it.get('price')),
                    fmt_num(amt),
                ])
            elems.append(build_items_table(
                ['#', '品號', '品名', '數量', '單價', '金額'],
                tbl_rows,
                col_widths=[7, 22, 50, 12, 22, 22],
                align_right_cols={3, 4, 5}
            ))
            elems.append(Spacer(1, 4 * mm))
            totals = [('合計', fmt_num(total_amount))]
            deposit = int(first.get('deposit_amount') or 0)
            if deposit:
                totals.append(('訂金', fmt_num(deposit)))
                totals.append(('尾款', fmt_num(total_amount - deposit)))
            elems.append(build_totals_block(totals))
            elems.extend(build_signature_block(salesperson=sp))
            elems += build_footer_elements()
            return elems

        buf = generate_pdf(make)
        resp = send_file(buf, mimetype='application/pdf',
                         as_attachment=False, download_name=f'銷貨單_{sales_no}.pdf')
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return resp
    except Exception as e:
        return err(str(e)), 500
    finally:
        conn.close()




@app.route('/api/pdf/inventory-count/<int:count_id>')
def pdf_inventory_count(count_id):
    """盤點表 PDF"""
    conn = get_db()
    try:
        header = conn.execute("SELECT * FROM inventory_count WHERE id=?", (count_id,)).fetchone()
        if not header:
            return err('找不到此盤點單'), 404
        h = dict(header)
        items = conn.execute(
            "SELECT * FROM inventory_count_items WHERE count_id=? ORDER BY id", (count_id,)
        ).fetchall()
        item_list = [dict(i) for i in items]

        def make():
            status_map = {
                'drafting': '盤點中', 'submitted': '待審核',
                'approved': '已核准', 'rejected': '已退回'
            }
            fields = [
                ('倉庫', h.get('warehouse') or ''),
                ('盤點日期', fmt_date(h.get('created_at'))),
                ('狀態', status_map.get(h.get('status'), h.get('status') or '')),
                ('盤點人', h.get('created_by') or ''),
            ]
            reviewed_by = h.get('reviewed_by')
            if reviewed_by:
                fields.append(('審核人', reviewed_by))
                fields.append(('審核日期', fmt_date(h.get('reviewed_at'))))
            elems = build_header('盤點表', h.get('count_no') or '', extra_fields=fields)

            tbl_rows = []
            diff_count = 0
            for idx, it in enumerate(item_list, 1):
                book = it.get('book_qty')
                actual = it.get('actual_qty')
                diff_val = ''
                if actual is not None and book is not None:
                    d = actual - book
                    diff_val = fmt_num(d) if d != 0 else '0'
                    if d != 0:
                        diff_count += 1
                tbl_rows.append([
                    str(idx),
                    it.get('product_code') or '',
                    it.get('product_name') or '',
                    fmt_num(book),
                    fmt_num(actual) if actual is not None else '—',
                    diff_val or '—',
                    it.get('remark') or '',
                ])
            elems.append(build_items_table(
                ['#', '品號', '品名', '帳面數量', '實際數量', '差異', '備註'],
                tbl_rows,
                col_widths=[7, 20, 42, 16, 16, 14, 20],
                align_right_cols={3, 4, 5}
            ))
            elems.append(Spacer(1, 4 * mm))
            elems.append(build_totals_block([
                ('品項數', str(len(item_list))),
                ('差異項', str(diff_count)),
            ]))
            note = h.get('note') or ''
            if note:
                elems.append(Spacer(1, 4 * mm))
                elems.append(build_note_block(note))
            elems.append(Spacer(1, 8 * mm))
            elems.extend(build_signature_block(['主管', '盤點人']))
            elems += build_footer_elements()
            return elems

        buf = generate_pdf(make)
        count_no = h.get('count_no') or f'IC-{count_id}'
        resp = send_file(buf, mimetype='application/pdf',
                         as_attachment=False, download_name=f'盤點表_{count_no}.pdf')
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return resp
    except Exception as e:
        return err(str(e)), 500
    finally:
        conn.close()


# ─────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8800))
    app.run(host='0.0.0.0', port=port, debug=True)
