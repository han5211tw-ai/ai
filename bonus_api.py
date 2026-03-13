

# ============================================
# 銷售獎金計算 API
# ============================================

# API: 取得獎金規則列表
@app.route('/api/bonus-rules', methods=['GET'])
def get_bonus_rules():
    """取得所有獎金規則"""
    show_inactive = request.args.get('show_inactive', '0') == '1'
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = 'SELECT * FROM bonus_rules WHERE 1=1'
        if not show_inactive:
            query += ' AND is_active = 1'
        query += ' ORDER BY created_at DESC'
        
        cursor.execute(query)
        rules = [dict(row) for row in cursor.fetchall()]
        return jsonify({'success': True, 'rules': rules})
    except Exception as e:
        print(f"[BonusRules] 查詢失敗: {e}")
        return jsonify({'success': False, 'message': '查詢失敗'}), 500
    finally:
        conn.close()

# API: 新增獎金規則
@app.route('/api/bonus-rules', methods=['POST'])
def create_bonus_rule():
    """新增獎金規則"""
    data = request.get_json()
    
    rule_name = data.get('rule_name', '').strip()
    product_code = data.get('product_code', '').strip()
    product_name = data.get('product_name', '').strip()
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    bonus_type = data.get('bonus_type', 'fixed')
    bonus_value = data.get('bonus_value', 0)
    min_quantity = data.get('min_quantity', 1)
    target_scope = data.get('target_scope', 'all')
    target_codes = data.get('target_codes', '').strip()
    
    if not rule_name or not start_date or not end_date:
        return jsonify({'success': False, 'message': '規則名稱、開始日期、結束日期不能為空'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO bonus_rules 
            (rule_name, product_code, product_name, start_date, end_date, 
             bonus_type, bonus_value, min_quantity, target_scope, target_codes, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (rule_name, product_code, product_name, start_date, end_date,
              bonus_type, bonus_value, min_quantity, target_scope, target_codes, 'system'))
        conn.commit()
        return jsonify({'success': True, 'id': cursor.lastrowid, 'message': '規則新增成功'})
    except Exception as e:
        print(f"[BonusRules] 新增失敗: {e}")
        return jsonify({'success': False, 'message': '新增失敗'}), 500
    finally:
        conn.close()

# API: 更新獎金規則
@app.route('/api/bonus-rules/<int:rule_id>', methods=['PUT'])
def update_bonus_rule(rule_id):
    """更新獎金規則"""
    data = request.get_json()
    
    rule_name = data.get('rule_name', '').strip()
    product_code = data.get('product_code', '').strip()
    product_name = data.get('product_name', '').strip()
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    bonus_type = data.get('bonus_type', 'fixed')
    bonus_value = data.get('bonus_value', 0)
    min_quantity = data.get('min_quantity', 1)
    target_scope = data.get('target_scope', 'all')
    target_codes = data.get('target_codes', '').strip()
    is_active = data.get('is_active', 1)
    
    if not rule_name or not start_date or not end_date:
        return jsonify({'success': False, 'message': '規則名稱、開始日期、結束日期不能為空'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE bonus_rules 
            SET rule_name = ?, product_code = ?, product_name = ?, start_date = ?, end_date = ?,
                bonus_type = ?, bonus_value = ?, min_quantity = ?, target_scope = ?, target_codes = ?,
                is_active = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (rule_name, product_code, product_name, start_date, end_date,
              bonus_type, bonus_value, min_quantity, target_scope, target_codes, is_active, rule_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'message': '規則不存在'}), 404
        return jsonify({'success': True, 'message': '規則更新成功'})
    except Exception as e:
        print(f"[BonusRules] 更新失敗: {e}")
        return jsonify({'success': False, 'message': '更新失敗'}), 500
    finally:
        conn.close()

# API: 刪除獎金規則
@app.route('/api/bonus-rules/<int:rule_id>', methods=['DELETE'])
def delete_bonus_rule(rule_id):
    """刪除獎金規則"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM bonus_rules WHERE id = ?', (rule_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'message': '規則不存在'}), 404
        return jsonify({'success': True, 'message': '規則刪除成功'})
    except Exception as e:
        print(f"[BonusRules] 刪除失敗: {e}")
        return jsonify({'success': False, 'message': '刪除失敗'}), 500
    finally:
        conn.close()

# API: 計算獎金
@app.route('/api/bonus-calculate', methods=['POST'])
def calculate_bonus():
    """計算指定週期的獎金"""
    data = request.get_json()
    period_start = data.get('period_start')
    period_end = data.get('period_end')
    
    if not period_start or not period_end:
        return jsonify({'success': False, 'message': '請提供計算週期'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. 取得所有啟用的規則
        cursor.execute('''
            SELECT * FROM bonus_rules 
            WHERE is_active = 1 
            AND start_date <= ? AND end_date >= ?
        ''', (period_end, period_start))
        rules = [dict(row) for row in cursor.fetchall()]
        
        if not rules:
            return jsonify({'success': False, 'message': '該週期無有效獎金規則'}), 400
        
        # 2. 查詢銷售資料
        cursor.execute('''
            SELECT s.salesperson_id, s.salesperson_name, s.product_code, s.product_name,
                   s.quantity, s.amount, s.sales_invoice_no, s.date
            FROM sales_history s
            WHERE s.date BETWEEN ? AND ?
        ''', (period_start, period_end))
        sales = [dict(row) for row in cursor.fetchall()]
        
        # 3. 清除該週期的舊計算結果
        cursor.execute('DELETE FROM bonus_results WHERE period_start = ? AND period_end = ?',
                      (period_start, period_end))
        
        # 4. 逐筆匹配規則並計算
        results = []
        for sale in sales:
            for rule in rules:
                if match_bonus_rule(sale, rule):
                    bonus_amount = calculate_bonus_amount(sale, rule)
                    
                    # 檢查是否已有相同規則+人員+商品的記錄
                    existing = next((r for r in results 
                                   if r['rule_id'] == rule['id'] 
                                   and r['salesperson_id'] == sale['salesperson_id']
                                   and r['product_code'] == sale['product_code']), None)
                    
                    if existing:
                        existing['sales_quantity'] += sale['quantity']
                        existing['sales_amount'] += sale['amount']
                        existing['bonus_amount'] += bonus_amount
                        existing['invoice_nos'] += ',' + sale['sales_invoice_no']
                    else:
                        results.append({
                            'rule_id': rule['id'],
                            'period_start': period_start,
                            'period_end': period_end,
                            'salesperson_id': sale['salesperson_id'],
                            'salesperson_name': sale['salesperson_name'],
                            'product_code': sale['product_code'],
                            'product_name': sale['product_name'],
                            'sales_quantity': sale['quantity'],
                            'sales_amount': sale['amount'],
                            'bonus_amount': bonus_amount,
                            'invoice_nos': sale['sales_invoice_no'],
                            'status': 'pending'
                        })
        
        # 5. 儲存結果
        for result in results:
            cursor.execute('''
                INSERT INTO bonus_results 
                (rule_id, period_start, period_end, salesperson_id, salesperson_name,
                 product_code, product_name, sales_quantity, sales_amount, bonus_amount, invoice_nos, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (result['rule_id'], result['period_start'], result['period_end'],
                  result['salesperson_id'], result['salesperson_name'],
                  result['product_code'], result['product_name'],
                  result['sales_quantity'], result['sales_amount'],
                  result['bonus_amount'], result['invoice_nos'], result['status']))
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功計算 {len(results)} 筆獎金記錄',
            'count': len(results)
        })
        
    except Exception as e:
        print(f"[BonusCalculate] 計算失敗: {e}")
        return jsonify({'success': False, 'message': '計算失敗'}), 500
    finally:
        conn.close()

def match_bonus_rule(sale, rule):
    """判斷銷售記錄是否符合獎金規則"""
    # 檢查商品編號
    if rule['product_code'] and sale['product_code'] != rule['product_code']:
        return False
    
    # 檢查商品名稱模糊匹配
    if rule['product_name'] and rule['product_name'] not in sale['product_name']:
        return False
    
    # 檢查適用範圍
    if rule['target_scope'] == 'staff' and rule['target_codes']:
        if sale['salesperson_id'] not in rule['target_codes'].split(','):
            return False
    
    return True

def calculate_bonus_amount(sale, rule):
    """計算獎金金額"""
    if rule['bonus_type'] == 'fixed':
        # 固定金額：每單位獎金 × 數量
        return rule['bonus_value'] * sale['quantity']
    elif rule['bonus_type'] == 'percent':
        # 百分比：銷售額 × 百分比
        return sale['amount'] * (rule['bonus_value'] / 100)
    return 0

# API: 取得獎金計算結果
@app.route('/api/bonus-results', methods=['GET'])
def get_bonus_results():
    """取得獎金計算結果"""
    period_start = request.args.get('period_start')
    period_end = request.args.get('period_end')
    salesperson_id = request.args.get('salesperson_id')
    status = request.args.get('status')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = '''
            SELECT r.*, b.rule_name, b.bonus_type, b.bonus_value
            FROM bonus_results r
            JOIN bonus_rules b ON r.rule_id = b.id
            WHERE 1=1
        '''
        params = []
        
        if period_start:
            query += ' AND r.period_start >= ?'
            params.append(period_start)
        if period_end:
            query += ' AND r.period_end <= ?'
            params.append(period_end)
        if salesperson_id:
            query += ' AND r.salesperson_id = ?'
            params.append(salesperson_id)
        if status:
            query += ' AND r.status = ?'
            params.append(status)
        
        query += ' ORDER BY r.created_at DESC'
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        print(f"[BonusResults] 查詢失敗: {e}")
        return jsonify({'success': False, 'message': '查詢失敗'}), 500
    finally:
        conn.close()

# API: 確認獎金
@app.route('/api/bonus-results/<int:result_id>/confirm', methods=['POST'])
def confirm_bonus_result(result_id):
    """確認獎金記錄"""
    data = request.get_json()
    confirmed_by = data.get('confirmed_by', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE bonus_results 
            SET status = 'confirmed', confirmed_by = ?, confirmed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (confirmed_by, result_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'message': '記錄不存在'}), 404
        return jsonify({'success': True, 'message': '獎金已確認'})
    except Exception as e:
        print(f"[BonusResults] 確認失敗: {e}")
        return jsonify({'success': False, 'message': '確認失敗'}), 500
    finally:
        conn.close()

# API: 批次確認獎金
@app.route('/api/bonus-results/batch-confirm', methods=['POST'])
def batch_confirm_bonus_results():
    """批次確認獎金記錄"""
    data = request.get_json()
    result_ids = data.get('result_ids', [])
    confirmed_by = data.get('confirmed_by', '')
    
    if not result_ids:
        return jsonify({'success': False, 'message': '請選擇要確認的記錄'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        placeholders = ','.join(['?' for _ in result_ids])
        cursor.execute(f'''
            UPDATE bonus_results 
            SET status = 'confirmed', confirmed_by = ?, confirmed_at = CURRENT_TIMESTAMP
            WHERE id IN ({placeholders})
        ''', [confirmed_by] + result_ids)
        conn.commit()
        return jsonify({'success': True, 'message': f'已確認 {cursor.rowcount} 筆獎金'})
    except Exception as e:
        print(f"[BonusResults] 批次確認失敗: {e}")
        return jsonify({'success': False, 'message': '批次確認失敗'}), 500
    finally:
        conn.close()
