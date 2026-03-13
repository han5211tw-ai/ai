# Staff Management Admin API
# 在 app.py 中添加以下路由

from flask import request, jsonify, g
from functools import wraps
import sqlite3
import time

# === Staff Admin API ===

@app.route('/api/admin/staff/list', methods=['GET'])
@require_admin
def admin_staff_list():
    """取得員工列表"""
    keyword = request.args.get('keyword', '').strip()
    limit = min(int(request.args.get('limit', 100)), 500)
    offset = int(request.args.get('offset', 0))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 構建查詢條件
        where_clause = "1=1"
        params = []
        
        if keyword:
            where_clause += " AND (staff_id LIKE ? OR name LIKE ?)"
            params.extend([f'%{keyword}%', f'%{keyword}%'])
        
        # 取得總筆數
        cursor.execute(f"SELECT COUNT(*) as total FROM staff WHERE {where_clause}", params)
        total = cursor.fetchone()['total']
        
        # 取得資料
        query_params = params + [limit, offset]
        cursor.execute(f'''
            SELECT staff_id, name, title, org_type, department, store, role, 
                   phone, is_active, created_at, updated_at
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

@app.route('/api/admin/staff/row', methods=['GET'])
@require_admin
def admin_staff_row():
    """取得單筆員工資料"""
    staff_id = request.args.get('staff_id')
    
    if not staff_id:
        return jsonify({'success': False, 'message': '缺少 staff_id'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT staff_id, name, title, org_type, department, store, role,
                   phone, id_card, birthday, is_active, created_at, updated_at
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

@app.route('/api/admin/staff/create', methods=['POST'])
@require_admin
def admin_staff_create():
    """新增員工"""
    data = request.get_json()
    
    required_fields = ['name', 'staff_id']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'success': False, 'message': f'缺少必要欄位: {field}'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 檢查 staff_id 是否已存在
        cursor.execute("SELECT 1 FROM staff WHERE staff_id = ?", (data['staff_id'],))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': '員工編號已存在'}), 400
        
        # 生成新員工資料
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            INSERT INTO staff (staff_id, name, title, org_type, department, store, role,
                             phone, id_card, birthday, is_active, password, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['staff_id'],
            data['name'],
            data.get('title', ''),
            data.get('org_type', 'STAFF'),
            data.get('department', ''),
            data.get('store'),
            data.get('role', 'staff'),
            data.get('phone', ''),
            data.get('id_card', ''),
            data.get('birthday', ''),
            1,  # is_active
            data.get('password', ''),  # 預設密碼
            now,
            now
        ))
        
        conn.commit()
        
        # 記錄操作日誌
        log_event(
            event_type='STAFF_CREATE',
            source='api:/api/admin/staff/create',
            actor=g.admin_user,
            status='OK',
            summary=f'新增員工 {data["staff_id"]} - {data["name"]}',
            affected_rows=1,
            details={'staff_id': data['staff_id'], 'name': data['name']}
        )
        
        return jsonify({'success': True, 'message': '員工新增成功', 'staff_id': data['staff_id']})
        
    except Exception as e:
        conn.rollback()
        print(f"admin_staff_create error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/staff/update', methods=['POST'])
@require_admin
def admin_staff_update():
    """更新員工資料"""
    data = request.get_json()
    staff_id = data.get('staff_id')
    
    if not staff_id:
        return jsonify({'success': False, 'message': '缺少 staff_id'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 取得更新前資料
        cursor.execute("SELECT * FROM staff WHERE staff_id = ?", (staff_id,))
        before = cursor.fetchone()
        
        if not before:
            return jsonify({'success': False, 'message': '員工不存在'}), 404
        
        # 構建更新欄位
        update_fields = []
        params = []
        
        updatable_fields = ['name', 'title', 'org_type', 'department', 'store', 
                           'role', 'phone', 'id_card', 'birthday', 'is_active']
        
        for field in updatable_fields:
            if field in data:
                update_fields.append(f"{field} = ?")
                params.append(data[field])
        
        if not update_fields:
            return jsonify({'success': False, 'message': '沒有要更新的欄位'}), 400
        
        # 添加 updated_at
        update_fields.append("updated_at = datetime('now', 'localtime')")
        
        params.append(staff_id)
        
        cursor.execute(f'''
            UPDATE staff 
            SET {', '.join(update_fields)}
            WHERE staff_id = ?
        ''', params)
        
        conn.commit()
        
        # 記錄操作日誌
        changes = {k: data[k] for k in updatable_fields if k in data}
        log_event(
            event_type='STAFF_UPDATE',
            source='api:/api/admin/staff/update',
            actor=g.admin_user,
            status='OK',
            summary=f'更新員工 {staff_id}',
            affected_rows=cursor.rowcount,
            details={'staff_id': staff_id, 'changes': changes}
        )
        
        return jsonify({'success': True, 'message': '員工資料更新成功'})
        
    except Exception as e:
        conn.rollback()
        print(f"admin_staff_update error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/staff/reset-password', methods=['POST'])
@require_admin
def admin_staff_reset_password():
    """重設員工密碼"""
    data = request.get_json()
    staff_id = data.get('staff_id')
    new_password = data.get('new_password')
    
    if not staff_id or not new_password:
        return jsonify({'success': False, 'message': '缺少必要欄位'}), 400
    
    # 驗證密碼格式（身分證後四碼）
    if not re.match(r'^\d{4}$', new_password):
        return jsonify({'success': False, 'message': '密碼必須為4位數字'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE staff 
            SET password = ?, updated_at = datetime('now', 'localtime')
            WHERE staff_id = ?
        ''', (new_password, staff_id))
        
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'message': '員工不存在'}), 404
        
        conn.commit()
        
        # 記錄操作日誌（不記錄密碼）
        log_event(
            event_type='STAFF_RESET_PASSWORD',
            source='api:/api/admin/staff/reset-password',
            actor=g.admin_user,
            status='OK',
            summary=f'重設員工 {staff_id} 密碼',
            affected_rows=1,
            details={'staff_id': staff_id}
        )
        
        return jsonify({'success': True, 'message': '密碼重設成功'})
        
    except Exception as e:
        conn.rollback()
        print(f"admin_staff_reset_password error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/staff/sync-from-staff-password', methods=['POST'])
@require_admin
def admin_staff_sync_from_staff_password():
    """從 staff_password 同步資料到 staff"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 取得 staff_password 的資料
        cursor.execute("SELECT name, department, password, title FROM staff_passwords")
        staff_password_data = cursor.fetchall()
        
        synced = 0
        unmatched = []
        
        for name, department, password, title in staff_password_data:
            # 嘗試用 name 對應
            cursor.execute("SELECT staff_id FROM staff WHERE name = ?", (name,))
            match = cursor.fetchone()
            
            if match:
                # 更新密碼
                cursor.execute('''
                    UPDATE staff 
                    SET password = ?, updated_at = datetime('now', 'localtime')
                    WHERE staff_id = ?
                ''', (password, match['staff_id']))
                synced += 1
            else:
                unmatched.append(name)
        
        conn.commit()
        
        # 記錄操作日誌
        log_event(
            event_type='STAFF_SYNC',
            source='api:/api/admin/staff/sync-from-staff-password',
            actor=g.admin_user,
            status='OK',
            summary=f'同步 staff_password 到 staff',
            affected_rows=synced,
            details={'synced': synced, 'unmatched': unmatched}
        )
        
        return jsonify({
            'success': True,
            'message': f'同步完成，{synced} 位員工已更新',
            'synced': synced,
            'unmatched': unmatched
        })
        
    except Exception as e:
        conn.rollback()
        print(f"admin_staff_sync error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()
