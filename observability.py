#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Observability Module v2.0
統一追蹤與可觀測性系統

提供：
1. 事件追蹤 (ops_events)
2. 資料新鮮度檢查 (freshness)
3. 匯入狀態監控 (ingest)
4. 資料一致性稽核 (consistency)
5. API 效能指標 (api_metrics)
"""

import sqlite3
import json
import uuid
import time
import os
from datetime import datetime, timedelta
from functools import wraps

HOME = os.path.expanduser("~")
DB_PATH = os.path.join(HOME, "srv/db/company.db")

# ==================== 工作日規則 ====================
WORKDAY_RULES = {
    'purchase': [0, 1, 2, 3, 4],      # 週一~五
    'sales': [0, 1, 2, 3, 4, 5],      # 週一~六
    'customer': [0, 1, 2, 3, 4],      # 週一~五
    'inventory': [0, 1, 2, 3, 4, 5, 6],  # 每日
    'products': [0, 1, 2, 3, 4, 5, 6],   # 每日
    'needs': [0, 1, 2, 3, 4, 5, 6],      # 每日
    'staging': [0, 1, 2, 3, 4, 5, 6]     # 每日
}

def is_workday(data_source, weekday):
    """檢查指定資料源在指定星期是否為工作日"""
    return weekday in WORKDAY_RULES.get(data_source, [0, 1, 2, 3, 4])

def get_weekday_name(weekday):
    """取得星期中文名稱"""
    names = ['週一', '週二', '週三', '週四', '週五', '週六', '週日']
    return names[weekday]

def get_db_connection():
    """建立資料庫連線"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ==================== 1. 事件追蹤系統 ====================

def log_event(event_type, source, actor=None, status='OK', duration_ms=None, 
              summary=None, details=None, trace_id=None, parent_trace_id=None,
              affected_rows=None, error_code=None, error_stack=None,
              client_ip=None, user_agent=None):
    """
    記錄系統事件到 ops_events
    
    Args:
        event_type: IMPORT/NEEDS_SUBMIT/NEEDS_CANCEL/STAGING_RESOLVE/DEPLOY/ROLLBACK/API_CALL
        source: inventory_parser / api:/api/needs/batch
        actor: 執行者
        status: OK/FAIL/PENDING
        duration_ms: 執行耗時
        summary: 短訊息
        details: dict，會轉成 JSON
        trace_id: UUID，若未提供會自動產生
    
    Returns:
        trace_id: 可用於追蹤此事件
    """
    if trace_id is None:
        trace_id = str(uuid.uuid4())[:16]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO ops_events 
            (event_type, source, trace_id, parent_trace_id, actor, status, 
             duration_ms, summary, details_json, affected_rows,
             error_code, error_stack, client_ip, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_type, source, trace_id, parent_trace_id, actor, status,
            duration_ms, summary, 
            json.dumps(details, ensure_ascii=False) if details else None,
            affected_rows, error_code, error_stack, client_ip, user_agent
        ))
        conn.commit()
        return trace_id
    except Exception as e:
        print(f"[Observability] 記錄事件失敗: {e}")
        return None
    finally:
        conn.close()

def get_last_event(event_type, status=None, hours=24):
    """取得最近一筆指定類型的事件"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    sql = """
        SELECT * FROM ops_events 
        WHERE event_type = ? 
          AND ts > datetime('now', '-{} hours')
    """.format(hours)
    
    params = [event_type]
    
    if status:
        sql += " AND status = ?"
        params.append(status)
    
    sql += " ORDER BY ts DESC LIMIT 1"
    
    cursor.execute(sql, params)
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None

def get_events_summary(hours=24):
    """取得事件摘要統計"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            event_type,
            status,
            COUNT(*) as count,
            AVG(duration_ms) as avg_duration,
            MAX(ts) as last_ts
        FROM ops_events
        WHERE ts > datetime('now', '-? hours')
        GROUP BY event_type, status
        ORDER BY event_type, status
    """, (hours,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(r) for r in rows]

# ==================== 2. 資料新鮮度 (FRESHNESS) ====================

def update_freshness_cache():
    """更新資料新鮮度快取"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now = datetime.now()
    today = now.strftime('%Y-%m-%d')
    yesterday = (now - timedelta(days=1)).strftime('%Y-%m-%d')
    weekday = now.weekday()
    
    # 各資料源的檢查邏輯
    sources_config = {
        'sales': {
            'table': 'sales_history',
            'date_col': 'date',
            'check_workday': True,
            'workday_type': 'sales'
        },
        'purchase': {
            'table': 'purchase_history',
            'date_col': 'date',
            'check_workday': True,
            'workday_type': 'purchase'
        },
        'inventory': {
            'table': 'inventory',
            'date_col': 'report_date',
            'check_workday': False
        },
        'customers': {
            'table': 'customers',
            'date_col': 'updated_at',
            'check_workday': True,
            'workday_type': 'customer'
        }
    }
    
    results = {}
    
    for source, config in sources_config.items():
        try:
            # 最新業務日期
            cursor.execute(f"""
                SELECT MAX({config['date_col']}) as latest_date,
                       COUNT(*) as total_count,
                       COUNT(CASE WHEN {config['date_col']} >= ? THEN 1 END) as yesterday_count
                FROM {config['table']}
            """, (yesterday,))
            
            row = cursor.fetchone()
            latest_date = row['latest_date']
            total_count = row['total_count']
            yesterday_count = row['yesterday_count']
            
            # 最新匯入時間（從 ops_events）
            cursor.execute("""
                SELECT MAX(ts) as latest_ts FROM ops_events
                WHERE event_type = 'IMPORT' AND source LIKE ?
            """, (f'%{source}%',))
            
            import_ts = cursor.fetchone()['latest_ts']
            
            # 計算狀態
            if config.get('check_workday'):
                is_work = is_workday(config['workday_type'], weekday)
            else:
                is_work = True
            
            if not latest_date:
                status = 'FAIL'
                lag_days = 999
            elif not is_work:
                status = 'WARN'  # 非工作日
                lag_days = 0
            elif latest_date >= yesterday:
                status = 'OK'
                lag_days = 0
            else:
                # 計算延遲
                latest = datetime.strptime(latest_date, '%Y-%m-%d')
                expected = datetime.strptime(yesterday, '%Y-%m-%d')
                lag_days = (expected - latest).days
                status = 'FAIL' if lag_days > 1 else 'WARN'
            
            details = {
                'is_workday': is_work,
                'weekday': weekday,
                'weekday_name': get_weekday_name(weekday)
            }
            
            # 更新快取
            cursor.execute("""
                INSERT OR REPLACE INTO freshness_cache
                (data_source, latest_business_date, latest_import_ts, expected_date,
                 lag_days, row_count, yesterday_count, status, details_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (source, latest_date, import_ts, yesterday, lag_days,
                  total_count, yesterday_count, status, json.dumps(details)))
            
            results[source] = {
                'status': status,
                'latest_date': latest_date,
                'lag_days': lag_days
            }
            
        except Exception as e:
            results[source] = {'status': 'ERROR', 'error': str(e)}
    
    conn.commit()
    conn.close()
    
    return results

def get_freshness_status():
    """取得資料新鮮度狀態（從快取）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM freshness_cache
        ORDER BY 
            CASE status 
                WHEN 'FAIL' THEN 1 
                WHEN 'WARN' THEN 2 
                WHEN 'OK' THEN 3 
                ELSE 4 
            END
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(r) for r in rows]

# ==================== 3. 匯入狀態 (INGEST) ====================

def get_ingest_status():
    """取得匯入任務狀態"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now = datetime.now()
    yesterday = (now - timedelta(days=1)).strftime('%Y-%m-%d')
    weekday = now.weekday()
    
    sources = ['sales', 'purchase', 'inventory', 'customers']
    results = {}
    
    for source in sources:
        # 取得快取狀態
        cursor.execute("""
            SELECT * FROM freshness_cache WHERE data_source = ?
        """, (source,))
        
        row = cursor.fetchone()
        if not row:
            results[source] = {'status': 'UNKNOWN'}
            continue
        
        # 取得最後成功/失敗事件
        last_ok = get_last_event('IMPORT', 'OK', hours=48)
        last_fail = get_last_event('IMPORT', 'FAIL', hours=48)
        
        results[source] = {
            'status': row['status'],
            'latest_date': row['latest_business_date'],
            'yesterday_count': row['yesterday_count'],
            'last_ok_trace_id': last_ok['trace_id'] if last_ok else None,
            'last_ok_ts': last_ok['ts'] if last_ok else None,
            'last_fail_trace_id': last_fail['trace_id'] if last_fail else None,
            'last_fail_ts': last_fail['ts'] if last_fail else None,
            'last_fail_error': last_fail['summary'] if last_fail else None
        }
    
    conn.close()
    return results

# ==================== 4. 資料一致性 (CONSISTENCY) ====================

def get_consistency_status():
    """取得資料一致性稽核狀態"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    results = {}
    
    # A3: Needs 指到不存在的正式主檔
    cursor.execute("""
        SELECT COUNT(*) as cnt FROM needs n
        LEFT JOIN products p ON n.product_code = p.product_code
        WHERE n.product_code != '' 
          AND n.product_code NOT LIKE 'TEMP-P-%'
          AND p.product_code IS NULL
    """)
    a3_product = cursor.fetchone()['cnt']
    
    cursor.execute("""
        SELECT COUNT(*) as cnt FROM needs n
        LEFT JOIN customers c ON n.customer_code = c.customer_id
        WHERE n.customer_code != ''
          AND n.customer_code NOT LIKE 'TEMP-C-%'
          AND c.customer_id IS NULL
    """)
    a3_customer = cursor.fetchone()['cnt']
    
    results['A3_orphan_needs'] = {
        'count': a3_product + a3_customer,
        'product_count': a3_product,
        'customer_count': a3_customer
    }
    
    # A5: Products 同名多碼
    cursor.execute("""
        SELECT product_name, COUNT(DISTINCT product_code) as code_count
        FROM products
        WHERE product_name != ''
        GROUP BY product_name
        HAVING code_count > 1
    """)
    a5_rows = cursor.fetchall()
    results['A5_duplicate_products'] = {
        'count': len(a5_rows),
        'details': [{'name': r['product_name'], 'codes': r['code_count']} for r in a5_rows[:10]]
    }
    
    # Staging resolved but needs not backfilled
    cursor.execute("""
        SELECT COUNT(*) as cnt
        FROM staging_records s
        JOIN needs n ON s.temp_customer_id = n.customer_staging_id
        WHERE s.status = 'resolved' AND n.customer_code = ''
    """)
    results['staging_not_backfilled'] = cursor.fetchone()['cnt']
    
    conn.close()
    return results

# ==================== 5. API 效能指標 ====================

def record_api_metrics(endpoint, method, duration_ms, status_code, actor=None, trace_id=None):
    """記錄 API 效能指標"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    error_count = 1 if status_code >= 400 else 0
    
    cursor.execute("""
        INSERT INTO api_metrics (endpoint, method, trace_id, duration_ms, status_code, error_count, actor)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (endpoint, method, trace_id, duration_ms, status_code, error_count, actor))
    
    conn.commit()
    conn.close()

def get_api_performance(hours=24):
    """取得 API 效能統計"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 基本統計（不包含 P50/P95，避免複雜子查詢問題）
    cursor.execute("""
        SELECT 
            endpoint,
            COUNT(*) as total_calls,
            AVG(duration_ms) as avg_duration,
            MAX(duration_ms) as max_duration,
            MIN(duration_ms) as min_duration,
            SUM(error_count) as error_count
        FROM api_metrics
        WHERE ts > datetime('now', '-{} hours')
        GROUP BY endpoint
        ORDER BY total_calls DESC
    """.format(hours))
    
    rows = cursor.fetchall()
    results = []
    for row in rows:
        row_dict = dict(row)
        # 簡化 P95 計算：使用平均值 + 2*標準差近似
        row_dict['p50'] = row_dict['avg_duration']
        row_dict['p95'] = row_dict['max_duration']
        results.append(row_dict)
    
    conn.close()
    return results

def get_slow_queries(limit=10):
    """取得慢查詢記錄（>200ms）"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查詢 ops_events 中超過 200ms 的記錄
        cursor.execute("""
            SELECT ts, source, duration_ms, details_json
            FROM ops_events
            WHERE duration_ms > 200
            ORDER BY ts DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        results = []
        for row in rows:
            results.append({
                'timestamp': row['ts'],
                'endpoint': row['source'],
                'duration_ms': row['duration_ms'] or 0,
                'details': row['details_json']
            })
        
        conn.close()
        return results
    except Exception as e:
        print(f"[SlowQuery] 查詢失敗: {e}")
        return []

# ==================== 系統狀態 ====================

def get_system_status():
    """獲取系統狀態"""
    try:
        import psutil
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        uptime_seconds = int(time.time() - psutil.boot_time())
        
        if memory.percent > 90 or disk.percent > 90:
            status = "red"
        elif memory.percent > 80 or disk.percent > 80:
            status = "yellow"
        else:
            status = "green"
        
        return {
            "status": status,
            "uptime_seconds": uptime_seconds,
            "memory_usage_percent": round(memory.percent, 1),
            "disk_usage_percent": round(disk.percent, 1)
        }
    except Exception as e:
        return {
            "status": "red",
            "uptime_seconds": 0,
            "memory_usage_percent": 0,
            "disk_usage_percent": 0,
            "error": str(e)
        }

def get_database_status():
    """獲取資料庫狀態"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        connection_ok = True
        cursor.execute("PRAGMA journal_mode")
        journal_mode = cursor.fetchone()[0]
        db_size_mb = round(os.path.getsize(DB_PATH) / (1024 * 1024), 2)
        wal_path = DB_PATH + "-wal"
        wal_size_mb = round(os.path.getsize(wal_path) / (1024 * 1024), 2) if os.path.exists(wal_path) else 0
        conn.close()
        
        if not connection_ok:
            status = "red"
        elif journal_mode != "wal":
            status = "yellow"
        elif wal_size_mb > 200:
            status = "yellow"
        else:
            status = "green"
        
        return {
            "status": status,
            "journal_mode": journal_mode,
            "db_size_mb": db_size_mb,
            "wal_size_mb": wal_size_mb,
            "connection_ok": connection_ok
        }
    except Exception as e:
        return {
            "status": "red",
            "journal_mode": "unknown",
            "db_size_mb": 0,
            "wal_size_mb": 0,
            "connection_ok": False,
            "error": str(e)
        }

def get_db_row_stats():
    """獲取表筆數統計"""
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
        
        return {
            'needs': {'total': needs_total, 'today_added': needs_today},
            'staging_records': {'total': staging_total, 'today_added': staging_today},
            'admin_audit_log': {'total': audit_total, 'today_added': audit_today}
        }
    except Exception as e:
        print(f"[DB Stats] 統計失敗: {e}")
        return {
            'needs': {'total': 0, 'today_added': 0},
            'staging_records': {'total': 0, 'today_added': 0},
            'admin_audit_log': {'total': 0, 'today_added': 0}
        }

# ==================== 6. 綜合健康檢查 ====================

def get_overall_health():
    """
    取得整體健康狀態（供 Admin 後台使用）
    Single Source of Truth - 所有監控資料統一從此函數獲取
    """
    # 更新快取
    update_freshness_cache()
    
    # 獲取各模組狀態
    system = get_system_status()
    database = get_database_status()
    freshness = get_freshness_status()
    ingest = get_ingest_status()
    consistency = get_consistency_status()
    api_perf = get_api_performance(hours=1)
    db_stats = get_db_row_stats()
    slow_queries = get_slow_queries(limit=5)
    
    # 計算整體狀態
    statuses = [
        system["status"],
        database["status"],
    ]
    
    # 添加 freshness 狀態
    for f in freshness:
        if f['status'] == 'FAIL':
            statuses.append('red')
        elif f['status'] == 'WARN':
            statuses.append('yellow')
        else:
            statuses.append('green')
    
    # 判斷整體狀態
    if "red" in statuses:
        overall = "red"
    elif "yellow" in statuses:
        overall = "yellow"
    else:
        overall = "green"
    
    # 取得今天的日期資訊
    now = datetime.now()
    today = now.strftime('%Y-%m-%d')
    weekday = now.weekday()
    weekday_name = get_weekday_name(weekday)
    
    # 計算 ingest 整體狀態
    ingest_status = "green"
    for source, data in ingest.items():
        if data.get('status') == 'FAIL':
            ingest_status = "red"
        elif data.get('status') == 'WARN' and ingest_status != 'red':
            ingest_status = "yellow"
    
    # 計算 freshness 整體狀態
    freshness_status = "green"
    for f in freshness:
        if f.get('status') == 'FAIL':
            freshness_status = "red"
        elif f.get('status') == 'WARN' and freshness_status != 'red':
            freshness_status = "yellow"
    
    # 計算 api_performance 整體狀態
    api_status = "green"
    if api_perf:
        for api in api_perf:
            if api.get('avg_duration', 0) > 500 or api.get('error_count', 0) > 0:
                api_status = "yellow"
    
    # 取得預期資料日期
    expected_date = (now - timedelta(days=1 if weekday != 0 else 3)).strftime('%Y-%m-%d')
    
    return {
        "version": "2.0",
        "overall_status": overall,
        "check_date": today,
        "weekday": weekday,
        "weekday_name": weekday_name,
        "system": system,
        "database": database,
        "freshness": freshness,
        "freshness_status": freshness_status,
        "data_freshness": {
            "status": freshness_status,
            "today": today,
            "weekday_name": weekday_name,
            "expected_data_date": expected_date,
            "checks": {f['data_source']: {"status": f['status'].lower() if f['status'] else 'unknown', "message": f"Latest: {f.get('latest_business_date', 'N/A')}"} for f in freshness if f.get('data_source')}
        },
        "ingest": ingest,
        "ingest_status": ingest_status,
        "import_status": {
            "status": ingest_status,
            "weekday_name": weekday_name,
            "expected_data_date": expected_date,
            "checks": {source: {"status": data.get('status', 'unknown').lower(), "count": data.get('yesterday_count', 0), "message": f"Latest: {data.get('latest_date', 'N/A')}"} for source, data in ingest.items()}
        },
        "api": {
            "status": api_status
        },
        "api_performance": api_perf,
        "consistency": consistency,
        "db_stats": db_stats,
        "slow_queries": slow_queries,
        "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

# ==================== 7. 裝飾器 ====================

def trace_api_call(endpoint):
    """API 呼叫追蹤裝飾器"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            trace_id = str(uuid.uuid4())[:16]
            start_time = time.time()
            
            try:
                result = f(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)
                
                # 記錄成功
                record_api_metrics(endpoint, 'POST', duration_ms, 200, trace_id=trace_id)
                
                return result
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                
                # 記錄失敗
                record_api_metrics(endpoint, 'POST', duration_ms, 500, trace_id=trace_id)
                
                raise
        return wrapper
    return decorator

# ==================== 8. 快速排查指令 ====================

def get_debug_sql(issue_type):
    """取得建議的排查 SQL"""
    sqls = {
        'missing_import': """
-- 查詢最近 24 小時的匯入事件
SELECT ts, source, status, summary, trace_id
FROM ops_events
WHERE event_type = 'IMPORT'
  AND ts > datetime('now', '-24 hours')
ORDER BY ts DESC;
        """,
        'failed_needs': """
-- 查詢失敗的需求單提交
SELECT ts, actor, status, summary, error_code, trace_id
FROM ops_events
WHERE event_type = 'NEEDS_SUBMIT'
  AND status = 'FAIL'
  AND ts > datetime('now', '-24 hours')
ORDER BY ts DESC;
        """,
        'orphan_needs': """
-- 查詢 A3 孤兒需求單
SELECT n.id, n.product_code, n.customer_code, n.item_name
FROM needs n
LEFT JOIN products p ON n.product_code = p.product_code
WHERE n.product_code != '' 
  AND n.product_code NOT LIKE 'TEMP-P-%'
  AND p.product_code IS NULL
LIMIT 50;
        """,
        'staging_pending': """
-- 查詢 pending 的 staging 數量
SELECT type, status, COUNT(*) as cnt
FROM staging_records
WHERE status = 'pending'
GROUP BY type;
        """
    }
    return sqls.get(issue_type, '-- 未知問題類型')

if __name__ == '__main__':
    # 測試
    print("Observability Module v2.0")
    print("更新資料新鮮度快取...")
    result = update_freshness_cache()
    print(json.dumps(result, indent=2, ensure_ascii=False))
