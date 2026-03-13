#!/opt/homebrew/bin/python3
"""
TEMP 新品/新客戶回歸測試
確保：按已完成不會讓 TEMP 消失；只有取消或轉正式碼才會消失
"""

import sqlite3
import subprocess
import json
import sys
from datetime import datetime

DB_PATH = '/Users/aiserver/srv/db/company.db'
API_BASE = 'http://localhost:3000'
TEST_MARKER = '[TEST_TEMP_FLOW]'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def api_call(endpoint):
    """呼叫 API"""
    try:
        result = subprocess.run(
            ['curl', '-s', f'{API_BASE}{endpoint}'],
            capture_output=True, text=True, timeout=10
        )
        return json.loads(result.stdout)
    except Exception as e:
        return {'error': str(e)}

def api_call_with_retry(endpoint, retries=3, delay=1):
    """呼叫 API 帶重試"""
    import time
    for i in range(retries):
        result = api_call(endpoint)
        if 'error' not in result:
            return result
        time.sleep(delay)
    return result

def log_step(step, msg):
    print(f"\n{'='*60}")
    print(f"步驟 {step}: {msg}")
    print('='*60)

def check_db_temp_p():
    """查詢 TEMP-P 未取消的 needs"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, product_code, product_staging_id, status, cancelled_at, item_name
        FROM needs
        WHERE product_staging_id LIKE 'TEMP-P-%'
          AND cancelled_at IS NULL
        ORDER BY id DESC
        LIMIT 5
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def check_db_temp_c():
    """查詢 TEMP-C 未取消的 needs"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, customer_code, customer_staging_id, status, cancelled_at, item_name
        FROM needs
        WHERE customer_staging_id LIKE 'TEMP-C-%'
          AND cancelled_at IS NULL
        ORDER BY id DESC
        LIMIT 5
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def check_db_staging(temp_id, type_='product'):
    """查詢對應的 staging"""
    conn = get_db()
    cursor = conn.cursor()
    if type_ == 'product':
        cursor.execute("""
            SELECT id, type, temp_product_id, status, created_at
            FROM staging_records
            WHERE type='product' AND temp_product_id = ?
        """, (temp_id,))
    else:
        cursor.execute("""
            SELECT id, type, temp_customer_id, status, created_at
            FROM staging_records
            WHERE type='customer' AND temp_customer_id = ?
        """, (temp_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def create_test_data():
    """建立測試資料：TEMP-P needs + staging"""
    log_step(1, "建立測試資料：TEMP-P needs（未取消）")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 建立 needs
    temp_id = f'TEMP-P-TEST-{datetime.now().strftime("%Y%m%d%H%M%S")}'
    cursor.execute("""
        INSERT INTO needs (date, item_name, quantity, department, requester, status, created_at,
                          is_new_product, product_staging_id, product_status, product_code)
        VALUES (date('now'), ?, 1, '門市部', '測試員', '待處理', datetime('now'),
                1, ?, 'pending', ?)
    """, (f'{TEST_MARKER} 測試新品', temp_id, temp_id))
    need_id = cursor.lastrowid
    
    # 建立 staging
    cursor.execute("""
        INSERT INTO staging_records (type, raw_input, temp_product_id, source_type, requester, 
                                     department, status, created_at)
        VALUES ('product', ?, ?, 'needs', '測試員', '門市部', 'pending', datetime('now'))
    """, (f'{TEST_MARKER} 測試新品', temp_id))
    staging_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    print(f"  ✓ 建立 Needs ID: {need_id}")
    print(f"  ✓ 建立 Staging ID: {staging_id}")
    print(f"  ✓ TEMP 編號: {temp_id}")
    
    return need_id, staging_id, temp_id

def mark_need_completed(need_id):
    """將 needs 標記為已完成"""
    log_step(2, f"將 needs {need_id} 標記為「已完成」")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE needs SET status = '已完成' WHERE id = ?
    """, (need_id,))
    conn.commit()
    conn.close()
    
    print(f"  ✓ Needs {need_id} 狀態更新為「已完成」")

def verify_visible(temp_id, step_num):
    """驗證三處都可見"""
    log_step(step_num, f"驗證 TEMP {temp_id} 在三處都可見")
    
    all_pass = True
    
    # 1. 前台 API - 商品
    result = api_call('/api/staging/records?type=product')
    records = result.get('records', [])
    found = any(r.get('temp_product_id') == temp_id for r in records)
    print(f"  前台 API (/api/staging/records?type=product):")
    print(f"    - 返回 {len(records)} 筆")
    print(f"    - {'✓ PASS' if found else '✗ FAIL'}: 找到 {temp_id}")
    if not found:
        all_pass = False
    
    # 2. 後台 API
    result = api_call('/api/admin/table?name=staging_records&limit=100&admin=黃柏翰')
    items = result.get('items', [])
    found = any(r.get('temp_product_id') == temp_id for r in items)
    print(f"  後台 API (/api/admin/table?name=staging_records):")
    print(f"    - 返回 {len(items)} 筆")
    print(f"    - {'✓ PASS' if found else '✗ FAIL'}: 找到 {temp_id}")
    if not found:
        all_pass = False
    
    # 3. DB 直接查詢
    rows = check_db_temp_p()
    found = any(r['product_staging_id'] == temp_id for r in rows)
    print(f"  DB 查詢 (TEMP-P 未取消):")
    print(f"    - 找到 {len(rows)} 筆")
    print(f"    - {'✓ PASS' if found else '✗ FAIL'}: 包含 {temp_id}")
    if not found:
        all_pass = False
    
    return all_pass

def cancel_need(need_id):
    """取消 needs"""
    log_step(4, f"將 needs {need_id} 取消（設定 cancelled_at）")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE needs SET cancelled_at = datetime('now') WHERE id = ?
    """, (need_id,))
    conn.commit()
    conn.close()
    
    print(f"  ✓ Needs {need_id} 已取消")

def verify_hidden(temp_id, step_num):
    """驗證三處都不可見"""
    log_step(step_num, f"驗證 TEMP {temp_id} 在三處都不可見")
    
    all_pass = True
    
    # 1. 前台 API - 商品
    result = api_call('/api/staging/records?type=product')
    records = result.get('records', [])
    found = any(r.get('temp_product_id') == temp_id for r in records)
    print(f"  前台 API (/api/staging/records?type=product):")
    print(f"    - 返回 {len(records)} 筆")
    print(f"    - {'✓ PASS' if not found else '✗ FAIL'}: 未找到 {temp_id}")
    if found:
        all_pass = False
    
    # 2. 後台 API
    result = api_call('/api/admin/table?name=staging_records&limit=100&admin=黃柏翰')
    items = result.get('items', [])
    found = any(r.get('temp_product_id') == temp_id for r in items)
    print(f"  後台 API (/api/admin/table?name=staging_records):")
    print(f"    - 返回 {len(items)} 筆")
    print(f"    - {'✓ PASS' if not found else '✗ FAIL'}: 未找到 {temp_id}")
    if found:
        all_pass = False
    
    # 3. DB 直接查詢
    rows = check_db_temp_p()
    found = any(r['product_staging_id'] == temp_id for r in rows)
    print(f"  DB 查詢 (TEMP-P 未取消):")
    print(f"    - 找到 {len(rows)} 筆")
    print(f"    - {'✓ PASS' if not found else '✗ FAIL'}: 不包含 {temp_id}")
    if found:
        all_pass = False
    
    return all_pass

def cleanup(need_id, staging_id):
    """清理測試資料"""
    log_step(6, "清理測試資料")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM needs WHERE id = ?", (need_id,))
    cursor.execute("DELETE FROM staging_records WHERE id = ?", (staging_id,))
    conn.commit()
    conn.close()
    
    print(f"  ✓ 刪除 Needs {need_id}")
    print(f"  ✓ 刪除 Staging {staging_id}")

def run_test():
    """執行完整測試流程"""
    print("="*60)
    print("TEMP 新品/新客戶回歸測試")
    print("="*60)
    print("\n核心規則：")
    print("  1. 未取消 + TEMP-P/TEMP-C：必須出現在待建檔中心")
    print("  2. 已完成（needs.status='已完成'）不影響顯示")
    print("  3. 取消（cancelled_at not null）：必須消失")
    print("  4. 轉正式碼：必須消失")
    
    try:
        # Step 1: 建立測試資料
        need_id, staging_id, temp_id = create_test_data()
        
        # Step 2: 標記為已完成
        mark_need_completed(need_id)
        
        # Step 3: 驗證「已完成」仍可見
        pass1 = verify_visible(temp_id, 3)
        
        # Step 4: 取消
        cancel_need(need_id)
        
        # Step 5: 驗證「取消」後不可見
        pass2 = verify_hidden(temp_id, 5)
        
        # Step 6: 清理
        cleanup(need_id, staging_id)
        
        # 總結
        print("\n" + "="*60)
        if pass1 and pass2:
            print("✓✓✓ 全部測試通過 (PASS) ✓✓✓")
        else:
            print("✗✗✗ 部分測試失敗 (FAIL) ✗✗✗")
            if not pass1:
                print("  - 「已完成」驗證失敗")
            if not pass2:
                print("  - 「取消」驗證失敗")
        print("="*60)
        
        return pass1 and pass2
        
    except Exception as e:
        print(f"\n✗ 測試過程發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = run_test()
    sys.exit(0 if success else 1)
