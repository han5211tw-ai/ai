

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
            SELECT p.*, c.name as category_name
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
    
    model_no = data.get('model_no', '').strip()
    name = data.get('name', '').strip()
    category_id = data.get('category_id')
    external_link = data.get('external_link', '').strip()
    description = data.get('description', '').strip()
    min_stock = data.get('min_stock', 1)
    
    if not model_no or not name:
        return jsonify({'success': False, 'message': '型號和名稱不能為空'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO recommended_products 
            (category_id, model_no, name, external_link, description, min_stock, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM recommended_products))
        ''', (category_id, model_no, name, external_link, description, min_stock))
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
    
    model_no = data.get('model_no', '').strip()
    name = data.get('name', '').strip()
    category_id = data.get('category_id')
    external_link = data.get('external_link', '').strip()
    description = data.get('description', '').strip()
    min_stock = data.get('min_stock', 1)
    is_active = data.get('is_active', 1)
    
    if not model_no or not name:
        return jsonify({'success': False, 'message': '型號和名稱不能為空'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE recommended_products 
            SET category_id = ?, model_no = ?, name = ?, external_link = ?, 
                description = ?, min_stock = ?, is_active = ?
            WHERE id = ?
        ''', (category_id, model_no, name, external_link, description, min_stock, is_active, product_id))
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
                SELECT model_no, name, min_stock 
                FROM recommended_products 
                WHERE id = ? AND is_active = 1
            ''', (product_id,))
            product = cursor.fetchone()
            
            if not product:
                continue
            
            # 建立備貨需求
            need_no = f"REC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{product_id}"
            item_name = f"{product['model_no']} {product['name']}"
            
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
