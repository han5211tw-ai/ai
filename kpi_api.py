#!/opt/homebrew/bin/python3
"""
KPI 績效考核系統 API
電腦舖 2026 年績效與獎金制度
"""

from flask import Blueprint, request, jsonify
import sqlite3
import os
from functools import wraps

kpi_bp = Blueprint('kpi', __name__, url_prefix='/api/kpi')

DB_PATH = os.environ.get('DB_PATH', '/Users/aiserver/srv/db/company.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_current_user(request):
    """從請求中取得當前使用者"""
    user = request.args.get('user') or request.headers.get('X-User')
    if not user and request.is_json:
        try:
            user = request.json.get('user')
        except:
            pass
    return user

def get_user_role(user_name):
    """判斷使用者角色"""
    if not user_name:
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 檢查是否為老闆
    cursor.execute("SELECT title FROM staff_passwords WHERE name = ?", (user_name,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return None
    
    title = result['title']
    if title == '老闆' or user_name == '黃柏翰':
        return 'boss'
    elif '主管' in title or '經理' in title or '督導' in title:
        return 'manager'
    else:
        return 'staff'

def get_staff_department(staff_name):
    """取得員工部門"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT department, title FROM staff WHERE name = ?", (staff_name,))
    result = cursor.fetchone()
    conn.close()
    return result['department'] if result else None, result['title'] if result else None

def determine_staff_role(department, title, staff_name):
    """判斷員工角色類型"""
    # 會計獨立處理
    if staff_name == '黃環馥':
        return 'accounting'
    # 主管獨立處理（用主管KPI）
    if title and ('主管' in title or '經理' in title or '督導' in title):
        return 'manager'
    # 業務員工（業務部且非主管）
    if department and '業務' in department:
        return 'business'
    # 門市員工（門市部或工程師）
    if department:
        if '工程' in department or '門市' in department:
            return 'store'
    return 'store'  # 預設

# ========== API 路由 ==========

@kpi_bp.route('/overview', methods=['GET'])
def get_kpi_overview():
    """取得 KPI 總覽"""
    year = request.args.get('year', 2026, type=int)
    quarter = request.args.get('quarter', 1, type=int)
    user = get_current_user(request)
    role = get_user_role(user)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 取得季度淨利
        cursor.execute("""
            SELECT * FROM quarterly_profit 
            WHERE year = ? AND quarter = ?
        """, (year, quarter))
        profit = cursor.fetchone()
        
        # 取得員工 KPI 分數
        cursor.execute("""
            SELECT * FROM kpi_scores 
            WHERE year = ? AND quarter = ? AND staff_role IN ('store', 'engineer')
            ORDER BY total_score DESC
        """, (year, quarter))
        staff_scores = [dict(row) for row in cursor.fetchall()]
        
        # 取得主管 KPI 分數
        cursor.execute("""
            SELECT * FROM kpi_scores 
            WHERE year = ? AND quarter = ? AND staff_role = 'manager'
        """, (year, quarter))
        manager_scores = [dict(row) for row in cursor.fetchall()]
        
        # 取得會計 KPI 分數
        cursor.execute("""
            SELECT * FROM kpi_scores 
            WHERE year = ? AND quarter = ? AND staff_role = 'accounting'
        """, (year, quarter))
        accounting_scores = [dict(row) for row in cursor.fetchall()]
        
        # 根據權限過濾資料
        if role == 'staff':
            # 個人只能看自己
            staff_scores = [s for s in staff_scores if s['staff_name'] == user]
            manager_scores = []
            accounting_scores = []
        elif role == 'manager':
            # 主管看自己 + 部屬
            dept, _ = get_staff_department(user)
            # 這裡需要根據部門關係過濾，暫時簡化
        
        return jsonify({
            'success': True,
            'current_user': user,
            'user_role': role,
            'year': year,
            'quarter': quarter,
            'profit': dict(profit) if profit else None,
            'staff_scores': staff_scores,
            'manager_scores': manager_scores,
            'accounting_scores': accounting_scores
        })
    except Exception as e:
        print(f"[KPI] 取得總覽失敗: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@kpi_bp.route('/calculate', methods=['POST'])
def calculate_kpi():
    """計算 KPI 分數"""
    data = request.get_json()
    year = data.get('year', 2026)
    quarter = data.get('quarter', 1)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 取得季度淨利
        cursor.execute("SELECT net_profit FROM quarterly_profit WHERE year = ? AND quarter = ?", 
                      (year, quarter))
        profit_row = cursor.fetchone()
        
        if not profit_row:
            return jsonify({'success': False, 'message': '尚未設定季度淨利'}), 400
        
        net_profit = profit_row['net_profit']
        employee_pool = net_profit * 0.13
        
        # 計算日期範圍
        quarter_months = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}
        start_month, end_month = quarter_months[quarter]
        start_date = f"{year}-{start_month:02d}-01"
        end_date = f"{year}-{end_month:02d}-31"
        
        # 預先計算季度月份相關變數（供後續使用）
        quarter_months_map = {1: [1, 2, 3], 2: [4, 5, 6], 3: [7, 8, 9], 4: [10, 11, 12]}
        months = quarter_months_map[quarter]
        months_placeholders = ','.join(['?' for _ in months])
        
        # 取得所有員工
        cursor.execute("SELECT name, department, title FROM staff WHERE is_active = 1")
        staff_list = cursor.fetchall()
        
        # 取得公司季度目標（1+2+3月加總）
        cursor.execute(f"""
            SELECT SUM(target_amount) as total_target
            FROM performance_metrics 
            WHERE year = ? AND category = '公司' AND month IN ({months_placeholders})
        """, (year,) + tuple(months))
        company_target_row = cursor.fetchone()
        company_target = company_target_row['total_target'] or 1
        
        # 取得公司實際銷售額（從 sales_history 計算，未稅）
        cursor.execute("""
            SELECT SUM(amount / 1.05) as total_revenue
            FROM sales_history 
            WHERE date >= ? AND date <= ?
        """, (start_date, end_date))
        company_revenue_row = cursor.fetchone()
        company_revenue = company_revenue_row['total_revenue'] or 0
        
        company_achievement_rate = company_revenue / company_target if company_target > 0 else 0
        
        # 計算五星好評數（從 store_reviews 表讀取）
        # 根據季度取得對應的 record_date（如 2026Q1）
        quarter_code = f"{year}Q{quarter}"
        cursor.execute("""
            SELECT SUM(review_count) as review_count 
            FROM store_reviews 
            WHERE record_date = ?
        """, (quarter_code,))
        result = cursor.fetchone()
        review_count = result['review_count'] or 0
        review_target = 200
        review_score = max(0, 10 - (review_target - review_count) * 0.1) if review_count < review_target else 10
        
        # 計算服務次數（工程同仁）
        cursor.execute("""
            SELECT COUNT(*) as service_count 
            FROM service_records 
            WHERE date >= ? AND date <= ?
        """, (start_date, end_date))
        service_count = cursor.fetchone()['service_count'] or 0
        service_target = 360
        service_score = max(0, 15 - (service_target - service_count) * 0.1) if service_count < service_target else 15
        
        staff_scores = []
        
        for staff in staff_list:
            staff_name = staff['name']
            department = staff['department']
            title = staff['title']
            role = determine_staff_role(department, title, staff_name)
            
            # 排除老闆（黃柏翰）
            if staff_name == '黃柏翰':
                continue
            
            # 主管 KPI（莊圍迪、萬書佑）- 部分自動計算
            if role == 'manager':
                # 取得主管的部門
                dept = department or ''
                
                # 1. 部門整體毛利達成率 (30分)
                # 計算該部門所有員工的業績和毛利（使用未稅）
                cursor.execute("""
                    SELECT 
                        SUM(sh.amount / 1.05) as dept_sales,
                        SUM((sh.amount / 1.05) - sh.cost) as dept_profit
                    FROM sales_history sh
                    JOIN staff s ON sh.salesperson = s.name
                    WHERE sh.date >= ? AND sh.date <= ?
                    AND s.department = ?
                """, (start_date, end_date, dept))
                dept_result = cursor.fetchone()
                dept_sales = dept_result['dept_sales'] or 0
                dept_profit = dept_result['dept_profit'] or 0
                
                # 取得部門季度目標（1+2+3月加總）
                cursor.execute(f"""
                    SELECT SUM(target_amount) as dept_target
                    FROM performance_metrics 
                    WHERE year = ? AND category = '部門' AND subject_name LIKE ?
                    AND month IN ({months_placeholders})
                """, (year, f'%{dept}%') + tuple(months))
                dept_target_row = cursor.fetchone()
                dept_target = dept_target_row['dept_target'] or 1
                
                dept_achievement_rate = dept_sales / dept_target if dept_target > 0 else 0
                m_kpi1 = min(30, dept_achievement_rate * 30)
                
                # 2. 所屬同仁 KPI 平均得分 (20分)
                # 先取得該主管部門的所有員工
                cursor.execute("""
                    SELECT name FROM staff WHERE department = ? AND is_active = 1 AND name != ?
                """, (dept, staff_name))
                dept_staff = [row['name'] for row in cursor.fetchall()]
                
                # 計算部屬平均 KPI 得分
                if dept_staff:
                    placeholders = ','.join(['?' for _ in dept_staff])
                    cursor.execute(f"""
                        SELECT AVG(total_score) as avg_score
                        FROM kpi_scores
                        WHERE year = ? AND quarter = ? AND staff_name IN ({placeholders})
                    """, (year, quarter) + tuple(dept_staff))
                    avg_result = cursor.fetchone()
                    staff_avg_score = avg_result['avg_score'] or 0
                else:
                    staff_avg_score = 0
                
                m_kpi2 = min(20, staff_avg_score * 0.2)  # 20分滿分
                
                # 3. 公司整體毛利達成率 (20分)
                # 使用已計算的公司達成率
                m_kpi3 = min(20, company_achievement_rate * 20)
                
                # 4-6. 其他項目人工評分，預設為0
                m_kpi4 = 0  # Good/Bad 離職率
                m_kpi5 = 0  # 客訴與重大失誤
                m_kpi6 = 0  # 跨部門貢獻
                
                total_manager_score = m_kpi1 + m_kpi2 + m_kpi3 + m_kpi4 + m_kpi5 + m_kpi6
                
                cursor.execute("""
                    INSERT OR REPLACE INTO kpi_scores 
                    (year, quarter, staff_name, staff_role, 
                     m_kpi1_dept_margin, m_kpi2_staff_avg, m_kpi3_company_margin,
                     m_kpi4_turnover, m_kpi5_complaint, m_kpi6_cross_dept,
                     total_score, updated_at)
                    VALUES (?, ?, ?, 'manager', ?, ?, ?, ?, ?, ?, ?, datetime('now','localtime'))
                """, (year, quarter, staff_name, m_kpi1, m_kpi2, m_kpi3, m_kpi4, m_kpi5, m_kpi6, total_manager_score))
                continue
            
            # 會計 KPI（黃環馥）- 人工評分，這裡只建立空記錄
            if role == 'accounting':
                cursor.execute("""
                    INSERT OR REPLACE INTO kpi_scores 
                    (year, quarter, staff_name, staff_role, total_score, updated_at)
                    VALUES (?, ?, ?, 'accounting', 0, datetime('now','localtime'))
                """, (year, quarter, staff_name))
                continue
            
            # 門市/工程同仁 KPI
            # 1. 個人業績達成率（使用未稅金額計算）
            cursor.execute("""
                SELECT 
                    SUM(amount / 1.05) as total_sales_excl_tax,
                    SUM(cost) as total_cost,
                    SUM((amount / 1.05) - cost) as total_profit
                FROM sales_history 
                WHERE salesperson = ? AND date >= ? AND date <= ?
            """, (staff_name, start_date, end_date))
            sales_result = cursor.fetchone()
            actual_sales = sales_result['total_sales_excl_tax'] or 0
            actual_profit = sales_result['total_profit'] or 0
            
            # 取得個人季度目標（1+2+3月加總）
            cursor.execute(f"""
                SELECT SUM(target_amount) as total_target 
                FROM performance_metrics 
                WHERE year = ? AND category = '個人' AND subject_name = ?
                AND month IN ({months_placeholders})
            """, (year, staff_name) + tuple(months))
            target_row = cursor.fetchone()
            personal_target = target_row['total_target'] if target_row and target_row['total_target'] else 1
            
            achievement_rate = actual_sales / personal_target if personal_target > 0 else 0
            
            if role == 'store':
                # ===== 門市員工 KPI =====
                # 1. 個人業績達成率 (40分)
                kpi1 = min(40, achievement_rate * 40)
                # 2. 個人毛利率 (20分)，標準 22%
                margin_rate = actual_profit / actual_sales if actual_sales > 0 else 0
                kpi2 = min(20, (margin_rate / 0.22) * 20)
                # 3. 全公司總業績達成率 (15分)
                kpi3 = min(15, company_achievement_rate * 15)
                # 4. 全公司五星好評 (10分)
                kpi4 = review_score
                
            else:
                # ===== 業務員工 KPI =====
                # 1. 個人業績達成率 (30分)
                kpi1 = min(30, achievement_rate * 30)
                # 2. 個人毛利率 (30分)，標準 25%
                margin_rate = actual_profit / actual_sales if actual_sales > 0 else 0
                kpi2 = min(30, (margin_rate / 0.25) * 30)
                # 3. 全公司總業績達成率 (10分)
                kpi3 = min(10, company_achievement_rate * 10)
                # 4. 全部門服務次數 (15分)
                kpi4 = service_score
            
            # 5. 關鍵貢獻（從資料表讀取）
            cursor.execute("""
                SELECT SUM(score) as total_contribution_score
                FROM kpi_contributions
                WHERE year = ? AND quarter = ? AND staff_name = ? AND status = 'approved'
            """, (year, quarter, staff_name))
            contribution_row = cursor.fetchone()
            kpi5 = min(15, (contribution_row['total_contribution_score'] or 0))
            
            total_score = kpi1 + kpi2 + kpi3 + kpi4 + kpi5
            
            # 儲存或更新 KPI 分數
            cursor.execute("""
                INSERT OR REPLACE INTO kpi_scores 
                (year, quarter, staff_name, staff_role, 
                 kpi1_achievement, kpi2_margin, kpi3_company_achievement, kpi4_reviews, kpi5_contribution,
                 total_score, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now','localtime'))
            """, (year, quarter, staff_name, role, kpi1, kpi2, kpi3, kpi4, kpi5, total_score))
            
            staff_scores.append({
                'staff_name': staff_name,
                'staff_role': role,
                'kpi1_achievement': kpi1,
                'kpi2_margin': kpi2,
                'kpi3_company_achievement': kpi3,
                'kpi4_reviews': kpi4,
                'kpi5_contribution': kpi5,
                'total_score': total_score
            })
        
        # 計算排名與加權
        staff_scores.sort(key=lambda x: x['total_score'], reverse=True)
        
        for i, score in enumerate(staff_scores):
            rank = i + 1
            multiplier = {1: 1.30, 2: 1.20, 3: 1.10, 4: 1.05}.get(rank, 1.00)
            
            # 計算獎金
            staff_count = 8.65  # 固定值
            base_amount = employee_pool / staff_count
            bonus_amount = int(base_amount * multiplier)
            
            cursor.execute("""
                UPDATE kpi_scores 
                SET rank = ?, multiplier = ?, bonus_amount = ?
                WHERE year = ? AND quarter = ? AND staff_name = ?
            """, (rank, multiplier, bonus_amount, year, quarter, score['staff_name']))
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'已計算 {len(staff_scores)} 位員工的 KPI',
            'staff_count': len(staff_scores)
        })
        
    except Exception as e:
        print(f"[KPI] 計算失敗: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@kpi_bp.route('/profit', methods=['POST'])
def set_profit():
    """設定季度淨利"""
    data = request.get_json()
    year = data.get('year')
    quarter = data.get('quarter')
    net_profit = data.get('net_profit')
    created_by = data.get('created_by') or get_current_user(request)
    
    if not all([year, quarter, net_profit]):
        return jsonify({'success': False, 'message': '缺少必要參數'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO quarterly_profit 
            (year, quarter, net_profit, created_by, updated_at)
            VALUES (?, ?, ?, ?, datetime('now','localtime'))
        """, (year, quarter, net_profit, created_by))
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': '季度淨利已設定',
            'data': {'year': year, 'quarter': quarter, 'net_profit': net_profit}
        })
    except Exception as e:
        print(f"[KPI] 設定淨利失敗: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@kpi_bp.route('/contributions', methods=['GET'])
def get_contributions():
    """取得關鍵貢獻列表"""
    year = request.args.get('year', type=int)
    quarter = request.args.get('quarter', type=int)
    staff_name = request.args.get('staff')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = "SELECT * FROM kpi_contributions WHERE year = ? AND quarter = ?"
        params = [year, quarter]
        
        if staff_name:
            query += " AND staff_name = ?"
            params.append(staff_name)
        
        query += " ORDER BY staff_name, item_number"
        
        cursor.execute(query, params)
        contributions = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'success': True,
            'contributions': contributions
        })
    except Exception as e:
        print(f"[KPI] 取得貢獻失敗: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@kpi_bp.route('/contributions', methods=['POST'])
def create_contribution():
    """新增關鍵貢獻"""
    data = request.get_json()
    year = data.get('year')
    quarter = data.get('quarter')
    staff_name = data.get('staff_name')
    item_number = data.get('item_number')
    description = data.get('description')
    category = data.get('category')  # 'teamwork' or 'individual'
    evidence_type = data.get('evidence_type')
    evidence_url = data.get('evidence_url')
    
    if not all([year, quarter, staff_name, item_number, description]):
        return jsonify({'success': False, 'message': '缺少必要參數'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO kpi_contributions 
            (year, quarter, staff_name, item_number, description, category, 
             evidence_type, evidence_url, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', datetime('now','localtime'))
        """, (year, quarter, staff_name, item_number, description, category,
              evidence_type, evidence_url))
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': '貢獻項目已提交，等待主管審核'
        })
    except Exception as e:
        print(f"[KPI] 新增貢獻失敗: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@kpi_bp.route('/contributions/<int:contribution_id>/review', methods=['POST'])
def review_contribution(contribution_id):
    """審核關鍵貢獻"""
    data = request.get_json()
    status = data.get('status')  # 'approved' or 'rejected'
    reviewed_by = data.get('reviewed_by') or get_current_user(request)
    
    if status not in ['approved', 'rejected']:
        return jsonify({'success': False, 'message': '無效的審核狀態'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 取得該貢獻的員工資訊
        cursor.execute("SELECT staff_name FROM kpi_contributions WHERE id = ?", (contribution_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({'success': False, 'message': '找不到該貢獻項目'}), 404
        
        staff_name = row['staff_name']
        
        # 檢查員工角色
        cursor.execute("SELECT title FROM staff WHERE name = ?", (staff_name,))
        staff_row = cursor.fetchone()
        staff_title = staff_row['title'] if staff_row else ''
        
        # 檢查審核者角色
        cursor.execute("SELECT title FROM staff_passwords WHERE name = ?", (reviewed_by,))
        reviewer_row = cursor.fetchone()
        reviewer_title = reviewer_row['title'] if reviewer_row else ''
        
        # 判斷審核權限
        is_manager = '主管' in staff_title or '經理' in staff_title
        is_boss = (reviewer_title == '老闆') or (reviewed_by == '黃柏翰')
        
        # 主管的貢獻需要老闆審核
        if is_manager and not is_boss:
            return jsonify({'success': False, 'message': '主管的貢獻需要老闆審核'}), 403
        
        score = 5 if status == 'approved' else 0
        
        cursor.execute("""
            UPDATE kpi_contributions 
            SET status = ?, reviewed_by = ?, reviewed_at = datetime('now','localtime'), score = ?
            WHERE id = ?
        """, (status, reviewed_by, score, contribution_id))
        
        conn.commit()
        
        action_text = '通過' if status == 'approved' else '拒絕'
        return jsonify({
            'success': True,
            'message': '已' + action_text + '此貢獻項目'
        })
    except Exception as e:
        print(f"[KPI] 審核失敗: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@kpi_bp.route('/manager-scores', methods=['POST'])
def set_manager_scores():
    """設定主管 KPI 分數（人工評分）"""
    data = request.get_json()
    year = data.get('year')
    quarter = data.get('quarter')
    staff_name = data.get('staff_name')
    scores = data.get('scores', {})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        total = sum([
            scores.get('m_kpi1_dept_margin', 0),
            scores.get('m_kpi2_staff_avg', 0),
            scores.get('m_kpi3_company_margin', 0),
            scores.get('m_kpi4_turnover', 0),
            scores.get('m_kpi5_complaint', 0),
            scores.get('m_kpi6_cross_dept', 0)
        ])
        
        cursor.execute("""
            INSERT OR REPLACE INTO kpi_scores 
            (year, quarter, staff_name, staff_role, 
             m_kpi1_dept_margin, m_kpi2_staff_avg, m_kpi3_company_margin,
             m_kpi4_turnover, m_kpi5_complaint, m_kpi6_cross_dept,
             total_score, updated_at)
            VALUES (?, ?, ?, 'manager', ?, ?, ?, ?, ?, ?, ?, datetime('now','localtime'))
        """, (year, quarter, staff_name,
              scores.get('m_kpi1_dept_margin', 0),
              scores.get('m_kpi2_staff_avg', 0),
              scores.get('m_kpi3_company_margin', 0),
              scores.get('m_kpi4_turnover', 0),
              scores.get('m_kpi5_complaint', 0),
              scores.get('m_kpi6_cross_dept', 0),
              total))
        
        conn.commit()
        
        return jsonify({'success': True, 'message': '主管 KPI 已更新'})
    except Exception as e:
        print(f"[KPI] 設定主管分數失敗: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@kpi_bp.route('/accounting-scores', methods=['POST'])
def set_accounting_scores():
    """設定會計 KPI 分數（人工評分）"""
    data = request.get_json()
    year = data.get('year')
    quarter = data.get('quarter')
    scores = data.get('scores', {})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        total = sum([
            scores.get('a_kpi1_accuracy', 0),
            scores.get('a_kpi2_on_time', 0),
            scores.get('a_kpi3_ar_control', 0),
            scores.get('a_kpi4_support', 0),
            scores.get('a_kpi5_cost_opt', 0)
        ])
        
        # 計算會計獎金
        cursor.execute("SELECT net_profit FROM quarterly_profit WHERE year = ? AND quarter = ?",
                      (year, quarter))
        profit_row = cursor.fetchone()
        accounting_pool = profit_row['net_profit'] * 0.01 if profit_row else 0
        bonus_amount = int(accounting_pool * (total / 100))
        
        cursor.execute("""
            INSERT OR REPLACE INTO kpi_scores 
            (year, quarter, staff_name, staff_role, 
             a_kpi1_accuracy, a_kpi2_on_time, a_kpi3_ar_control,
             a_kpi4_support, a_kpi5_cost_opt,
             total_score, bonus_amount, updated_at)
            VALUES (?, ?, '黃環馥', 'accounting', ?, ?, ?, ?, ?, ?, ?, datetime('now','localtime'))
        """, (year, quarter,
              scores.get('a_kpi1_accuracy', 0),
              scores.get('a_kpi2_on_time', 0),
              scores.get('a_kpi3_ar_control', 0),
              scores.get('a_kpi4_support', 0),
              scores.get('a_kpi5_cost_opt', 0),
              total, bonus_amount))
        
        conn.commit()
        
        return jsonify({'success': True, 'message': '會計 KPI 已更新'})
    except Exception as e:
        print(f"[KPI] 設定會計分數失敗: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()
