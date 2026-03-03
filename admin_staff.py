#!/opt/homebrew/bin/python3
"""
Staff Admin API - 員工主檔管理 (Blueprint)
第二階段：支援編輯、重設密碼、停用/啟用
"""
from flask import Blueprint, request, jsonify, g
import sqlite3
import re
import json
import os
from datetime import datetime

# 建立 Blueprint
admin_staff_bp = Blueprint('admin_staff', __name__)

# 資料庫路徑
DB_PATH = '/Users/aiserver/srv/db/company.db'

# Feature Flag：控制是否允許寫入操作
# 可透過環境變數 ENABLE_STAFF_WRITE 控制，預設為 False（安全模式）
# 設定方式：export ENABLE_STAFF_WRITE=true
ENABLE_STAFF_WRITE = os.environ.get('ENABLE_STAFF_WRITE', 'false').lower() in ('true', '1', 'yes', 'on')

def get_db_connection():
    """取得資料庫連線"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def log_staff_audit(conn, admin_user, action, target_staff_id, before_data=None, after_data=None, details=None):
    """寫入 admin_audit_log"""
    try:
        cursor = conn.cursor()
        affected_ids = json.dumps([target_staff_id]) if target_staff_id else None
        details_json = json.dumps(details, ensure_ascii=False) if details else None
        
        cursor.execute('''
            INSERT INTO admin_audit_log (admin_user, action, affected_ids, affected_count, details, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))
        ''', (
            admin_user,
            action,
            affected_ids,
            1,
            details_json
        ))
        conn.commit()
    except Exception as e:
        print(f"[WARN] admin_audit_log 寫入失敗: {e}")
        # audit log 失敗不應影響主業務

# ============================================
# Staff Admin API Routes (GET - 唯讀)
# ============================================

@admin_staff_bp.route('/api/admin/staff/list', methods=['GET'])
def admin_staff_list():
    """取得員工列表"""
    keyword = request.args.get('keyword', '').strip()
    limit = min(int(request.args.get('limit', 100)), 500)
    offset = int(request.args.get('offset', 0))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        where_clause = "1=1"
        params = []
        
        if keyword:
            where_clause += " AND (staff_id LIKE ? OR name LIKE ? OR department LIKE ? OR store LIKE ?)"
            params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])
        
        cursor.execute(f"SELECT COUNT(*) as total FROM staff WHERE {where_clause}", params)
        total = cursor.fetchone()['total']
        
        query_params = params + [limit, offset]
        cursor.execute(f'''
            SELECT staff_id, staff_code, name, title, org_type, department, store, role,
                   phone, mobile, is_active, created_at, updated_at
            FROM staff
            WHERE {where_clause}
            ORDER BY staff_id
            LIMIT ? OFFSET ?
        ''', query_params)
        
        items = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'success': True,
            'items': items,
            'total': total,
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        print(f"admin_staff_list error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@admin_staff_bp.route('/api/admin/staff/row', methods=['GET'])
def admin_staff_row():
    """取得單筆員工資料"""
    staff_id = request.args.get('staff_id')
    
    if not staff_id:
        return jsonify({'success': False, 'message': '缺少 staff_id'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT staff_id, staff_code, name, title, org_type, department, store, role,
                   phone, mobile, id_number, birth_date, hire_date, is_active, created_at, updated_at
            FROM staff
            WHERE staff_id = ?
        ''', (staff_id,))
        
        row = cursor.fetchone()
        
        if not row:
            return jsonify({'success': False, 'message': '員工不存在'}), 404
        
        return jsonify({'success': True, 'item': dict(row)})
        
    except Exception as e:
        print(f"admin_staff_row error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

# ============================================
# Staff Admin API Routes (POST - 寫入操作)
# ============================================

@admin_staff_bp.route('/api/admin/staff/update', methods=['POST'])
def admin_staff_update():
    """更新員工資料"""
    # Feature Flag 檢查
    if not ENABLE_STAFF_WRITE:
        return jsonify({'success': False, 'message': '寫入功能已停用'}), 403
    
    data = request.get_json()
    staff_id = data.get('staff_id')
    admin_user = request.args.get('admin') or request.headers.get('X-Admin-User')
    
    if not staff_id:
        return jsonify({'success': False, 'message': '缺少 staff_id'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 查詢更新前資料
        cursor.execute("SELECT * FROM staff WHERE staff_id = ?", (staff_id,))
        before_row = cursor.fetchone()
        
        if not before_row:
            conn.close()
            return jsonify({'success': False, 'message': '員工不存在'}), 404
        
        before_data = dict(before_row)
        
        # 欄位白名單：只允許修改這些欄位
        # 禁止修改：name（與 staff_passwords 關聯，修改會導致登入問題）
        # 風險說明：若開放修改 name，必須同步更新 staff_passwords.name，否則該員工將無法登入
        WHITELIST_FIELDS = ['title', 'department', 'store', 'role', 'is_active', 'mobile', 'id_number', 'birth_date', 'hire_date']
        
        # 檢查是否有禁止修改的欄位（staff_id 用於 WHERE 條件，不是修改欄位）
        if 'name' in data:
            return jsonify({'success': False, 'message': '禁止修改欄位: name（姓名與登入系統關聯）'}), 400
        if 'staff_id' in data and data.get('staff_id') != staff_id:
            return jsonify({'success': False, 'message': '禁止修改欄位: staff_id（系統主鍵不可變更）'}), 400
        
        # 構建更新欄位（僅限白名單）
        update_fields = []
        params = []
        
        for field in WHITELIST_FIELDS:
            if field in data:
                update_fields.append(f"{field} = ?")
                params.append(data[field])
        
        if not update_fields:
            conn.close()
            return jsonify({'success': False, 'message': '沒有要更新的欄位'}), 400
        
        update_fields.append("updated_at = datetime('now', 'localtime')")
        params.append(staff_id)
        
        # Transaction 開始
        cursor.execute('BEGIN TRANSACTION')
        
        cursor.execute(f'''
            UPDATE staff 
            SET {', '.join(update_fields)}
            WHERE staff_id = ?
        ''', params)
        
        # 查詢更新後資料
        cursor.execute("SELECT * FROM staff WHERE staff_id = ?", (staff_id,))
        after_row = cursor.fetchone()
        after_data = dict(after_row)
        
        conn.commit()
        
        # 寫入 audit log
        log_staff_audit(
            conn=conn,
            admin_user=admin_user,
            action='STAFF_UPDATE',
            target_staff_id=staff_id,
            before_data=before_data,
            after_data=after_data,
            details={'updated_fields': [f for f in WHITELIST_FIELDS if f in data]}
        )
        
        return jsonify({'success': True, 'message': '員工資料更新成功'})
        
    except Exception as e:
        conn.rollback()
        print(f"admin_staff_update error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@admin_staff_bp.route('/api/admin/staff/reset-password', methods=['POST'])
def admin_staff_reset_password():
    """重設員工密碼 - 使用 staff_id 定位更新 staff_passwords"""
    # Feature Flag 檢查
    if not ENABLE_STAFF_WRITE:
        return jsonify({'success': False, 'message': '寫入功能已停用'}), 403
    
    data = request.get_json()
    staff_id = data.get('staff_id')
    new_password = data.get('new_password')
    admin_user = request.args.get('admin') or request.headers.get('X-Admin-User')
    
    if not staff_id or not new_password:
        return jsonify({'success': False, 'message': '缺少必要欄位'}), 400
    
    if not re.match(r'^\d{4}$', new_password):
        return jsonify({'success': False, 'message': '密碼必須為4位數字'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 查詢員工姓名（用於 audit log）
        cursor.execute("SELECT name FROM staff WHERE staff_id = ?", (staff_id,))
        staff_row = cursor.fetchone()
        
        if not staff_row:
            conn.close()
            return jsonify({'success': False, 'message': '員工不存在'}), 404
        
        staff_name = staff_row['name']
        
        # Transaction 開始
        cursor.execute('BEGIN TRANSACTION')
        
        # 關鍵 SQL：使用 staff_id 定位更新 staff_passwords
        # 不再使用 name 作為 WHERE 條件，確保即使 name 變更也能正確更新
        cursor.execute('''
            UPDATE staff_passwords 
            SET password = ?
            WHERE staff_id = ?
        ''', (new_password, staff_id))
        
        if cursor.rowcount == 0:
            conn.rollback()
            conn.close()
            return jsonify({'success': False, 'message': 'staff_passwords 中找不到該員工'}), 404
        
        conn.commit()
        
        # 寫入 audit log（不記錄密碼本身）
        log_staff_audit(
            conn=conn,
            admin_user=admin_user,
            action='STAFF_RESET_PASSWORD',
            target_staff_id=staff_id,
            details={'staff_name': staff_name, 'note': '密碼已重設'}
        )
        
        return jsonify({'success': True, 'message': '密碼重設成功'})
        
    except Exception as e:
        conn.rollback()
        print(f"admin_staff_reset_password error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@admin_staff_bp.route('/api/admin/staff/toggle-status', methods=['POST'])
def admin_staff_toggle_status():
    """停用/啟用員工 - Soft Delete（只更新 is_active）"""
    # Feature Flag 檢查
    if not ENABLE_STAFF_WRITE:
        return jsonify({'success': False, 'message': '寫入功能已停用'}), 403
    
    data = request.get_json()
    staff_id = data.get('staff_id')
    is_active = data.get('is_active')
    admin_user = request.args.get('admin') or request.headers.get('X-Admin-User')
    
    if not staff_id or is_active is None:
        return jsonify({'success': False, 'message': '缺少必要欄位'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 查詢更新前資料
        cursor.execute("SELECT staff_id, name, is_active FROM staff WHERE staff_id = ?", (staff_id,))
        before_row = cursor.fetchone()
        
        if not before_row:
            conn.close()
            return jsonify({'success': False, 'message': '員工不存在'}), 404
        
        before_data = dict(before_row)
        
        # Transaction 開始
        cursor.execute('BEGIN TRANSACTION')
        
        # 只更新 is_active，不刪除資料
        cursor.execute('''
            UPDATE staff 
            SET is_active = ?, updated_at = datetime('now', 'localtime')
            WHERE staff_id = ?
        ''', (1 if is_active else 0, staff_id))
        
        conn.commit()
        
        # 寫入 audit log
        action = 'STAFF_ENABLE' if is_active else 'STAFF_DISABLE'
        log_staff_audit(
            conn=conn,
            admin_user=admin_user,
            action=action,
            target_staff_id=staff_id,
            before_data={'is_active': before_data['is_active']},
            after_data={'is_active': is_active},
            details={'staff_name': before_data['name']}
        )
        
        status_text = '啟用' if is_active else '停用'
        return jsonify({'success': True, 'message': f'員工已{status_text}'})
        
    except Exception as e:
        conn.rollback()
        print(f"admin_staff_toggle_status error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@admin_staff_bp.route('/api/admin/staff/create', methods=['POST'])
def admin_staff_create():
    """新增員工 - 兩段式寫入：staff 主檔 + staff_passwords 登入表"""
    # Feature Flag 檢查
    if not ENABLE_STAFF_WRITE:
        return jsonify({'success': False, 'message': '寫入功能已停用'}), 403
    
    data = request.get_json()
    admin_user = request.args.get('admin') or request.headers.get('X-Admin-User')
    
    # 防呆驗證
    staff_code = data.get('staff_code', '').strip()
    name = data.get('name', '').strip()
    department = data.get('department', '').strip()
    role = data.get('role', '').strip()
    password = data.get('password', '').strip()
    store = data.get('store', '').strip() or None
    title = data.get('title', '').strip() or None
    mobile = data.get('mobile', '').strip() or None
    id_number = data.get('id_number', '').strip() or None
    birth_date = data.get('birth_date', '').strip() or None
    hire_date = data.get('hire_date', '').strip() or None
    
    # 必填欄位檢查
    if not name:
        return jsonify({'success': False, 'message': '姓名為必填欄位'}), 400
    if not department:
        return jsonify({'success': False, 'message': '部門為必填欄位'}), 400
    if not role:
        return jsonify({'success': False, 'message': '角色為必填欄位'}), 400
    if not password or len(password) != 4 or not password.isdigit():
        return jsonify({'success': False, 'message': '初始密碼必須為4位數字'}), 400
    
    # role 白名單檢查
    VALID_ROLES = ['boss', 'accountant', 'manager', 'engineer', 'sales']
    if role not in VALID_ROLES:
        return jsonify({'success': False, 'message': f'角色必須為下列之一: {", ".join(VALID_ROLES)}'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 檢查 staff_code 是否重複
        if staff_code:
            cursor.execute("SELECT 1 FROM staff WHERE staff_code = ?", (staff_code,))
            if cursor.fetchone():
                conn.close()
                return jsonify({'success': False, 'message': f'員工編號 {staff_code} 已存在，請使用其他編號'}), 400
        
        # 檢查 name 是否已存在（避免重複建立）
        cursor.execute("SELECT 1 FROM staff WHERE name = ?", (name,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': f'姓名 {name} 已存在，請確認是否為同一人'}), 400
        
        # 產生新的 staff_id（S0001 格式）
        cursor.execute("SELECT MAX(CAST(SUBSTR(staff_id, 2) AS INTEGER)) as max_num FROM staff")
        result = cursor.fetchone()
        next_num = (result['max_num'] or 0) + 1
        staff_id = f'S{next_num:04d}'
        
        # 根據部門決定 org_type
        if department == '總公司' or role == 'boss':
            org_type = 'HQ'
        elif department == '門市部' or store:
            org_type = 'STORE'
        elif department == '業務部' or role == 'sales':
            org_type = 'SALES'
        else:
            org_type = 'HQ'
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Transaction 開始
        cursor.execute('BEGIN TRANSACTION')
        
        # 1. 寫入 staff 主檔
        cursor.execute('''
            INSERT INTO staff (staff_id, staff_code, name, title, org_type, department, store, role,
                             phone, mobile, id_number, birth_date, hire_date, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            staff_id,
            staff_code,
            name,
            title,
            org_type,
            department,
            store,
            role,
            '',  # phone (舊欄位，保留相容)
            mobile,
            id_number,
            birth_date,
            hire_date,
            1,  # is_active
            now,
            now
        ))
        
        # 2. 寫入 staff_passwords 登入表
        cursor.execute('''
            INSERT INTO staff_passwords (staff_id, name, department, title, password)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            staff_id,
            name,
            department,
            title or '',
            password
        ))
        
        conn.commit()
        
        # 寫入 audit log
        log_staff_audit(
            conn=conn,
            admin_user=admin_user,
            action='STAFF_CREATE',
            target_staff_id=staff_id,
            details={
                'staff_id': staff_id,
                'staff_code': staff_code,
                'name': name,
                'role': role,
                'department': department,
                'store': store,
                'mobile': mobile,
                'hire_date': hire_date
            }
        )
        
        return jsonify({
            'success': True,
            'message': '員工新增成功',
            'staff_id': staff_id,
            'staff_code': staff_code
        })
        
    except Exception as e:
        conn.rollback()
        print(f"admin_staff_create error: {e}")
        return jsonify({'success': False, 'message': f'新增失敗: {str(e)}'}), 500
    finally:
        conn.close()
