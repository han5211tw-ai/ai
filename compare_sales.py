#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
比對銷貨原始檔案與資料庫資料
"""

import sqlite3
import csv
import os
from datetime import datetime

DB_PATH = '/Users/aiserver/srv/db/company.db'
CSV_PATH = '/Users/aiserver/srv/sync/OneDrive/ai_source/sales/銷貨0306-0308.csv'

def parse_sales_csv():
    """解析銷貨 CSV 檔案"""
    records = []
    
    # 讀取並轉碼
    with open(CSV_PATH, 'rb') as f:
        content = f.read()
    
    # 嘗試轉碼
    try:
        text = content.decode('utf-8')
    except:
        try:
            text = content.decode('big5')
        except:
            text = content.decode('utf-8', errors='ignore')
    
    # 解析 CSV
    lines = text.strip().split('\n')
    current_header = None
    current_date = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        cols = line.split(',')
        
        # 檢查是否是標題列（以 11503 開頭）
        if cols[0] and cols[0].startswith('11503'):
            current_date = '2026-03-' + cols[0][-2:]  # 1150306 -> 2026-03-06
            current_header = cols
        # 檢查是否是產品資料（以 SE- 開頭）
        elif cols[0] and cols[0].startswith('SE-') and current_header:
            # 提取資料
            product_code = cols[0] if cols[0] else ''
            product_name = cols[7] if len(cols) > 7 else ''
            quantity = cols[14] if len(cols) > 14 else '0'
            amount = cols[16] if len(cols) > 16 else '0'
            
            # 從標題提取業務員和客戶
            salesperson = current_header[4] if len(current_header) > 4 else ''
            customer = current_header[8] if len(current_header) > 8 else ''
            
            records.append({
                'date': current_date,
                'salesperson': salesperson,
                'customer': customer,
                'product_code': product_code,
                'product_name': product_name,
                'quantity': quantity,
                'amount': amount
            })
    
    return records

def get_db_records():
    """取得資料庫中的銷貨記錄"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT date, salesperson, customer_name, product_name, 
               quantity, amount, sales_invoice_no
        FROM sales_history 
        WHERE date IN ('2026-03-06', '2026-03-07', '2026-03-08')
        ORDER BY date, sales_invoice_no
    """)
    
    records = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return records

def compare_records(csv_records, db_records):
    """比對 CSV 和資料庫記錄"""
    
    print("=" * 80)
    print("銷貨資料比對報告")
    print("=" * 80)
    
    # 統計數量
    csv_by_date = {}
    for r in csv_records:
        d = r['date']
        csv_by_date[d] = csv_by_date.get(d, 0) + 1
    
    db_by_date = {}
    for r in db_records:
        d = r['date']
        db_by_date[d] = db_by_date.get(d, 0) + 1
    
    print("\n【數量統計】")
    print("-" * 80)
    for date in ['2026-03-06', '2026-03-07', '2026-03-08']:
        csv_count = csv_by_date.get(date, 0)
        db_count = db_by_date.get(date, 0)
        status = "✅" if csv_count == db_count else "❌"
        print(f"{date}: CSV={csv_count} 筆, DB={db_count} 筆 {status}")
    
    print(f"\n總計: CSV={len(csv_records)} 筆, DB={len(db_records)} 筆")
    
    # 詳細比對
    print("\n【詳細資料比對】")
    print("-" * 80)
    
    # 建立 DB 記錄的查找字典
    db_dict = {}
    for r in db_records:
        key = f"{r['date']}|{r['salesperson']}|{r['product_name']}|{r['amount']}"
        db_dict[key] = r
    
    # 檢查 CSV 記錄是否在 DB 中
    missing_in_db = []
    for r in csv_records:
        key = f"{r['date']}|{r['salesperson']}|{r['product_name']}|{r['amount']}"
        if key not in db_dict:
            missing_in_db.append(r)
    
    if missing_in_db:
        print(f"\n❌ CSV 中有但 DB 中沒有的記錄（共 {len(missing_in_db)} 筆）：")
        for r in missing_in_db[:20]:  # 只顯示前 20 筆
            print(f"  {r['date']} | {r['salesperson']} | {r['product_name']} | {r['amount']}")
        if len(missing_in_db) > 20:
            print(f"  ... 還有 {len(missing_in_db) - 20} 筆")
    else:
        print("\n✅ 所有 CSV 記錄都已存在於 DB 中")
    
    # 檢查 DB 記錄是否在 CSV 中
    csv_dict = {}
    for r in csv_records:
        key = f"{r['date']}|{r['salesperson']}|{r['product_name']}|{r['amount']}"
        csv_dict[key] = r
    
    missing_in_csv = []
    for r in db_records:
        key = f"{r['date']}|{r['salesperson']}|{r['product_name']}|{r['amount']}"
        if key not in csv_dict:
            missing_in_csv.append(r)
    
    if missing_in_csv:
        print(f"\n⚠️  DB 中有但 CSV 中沒有的記錄（共 {len(missing_in_csv)} 筆）：")
        for r in missing_in_csv[:10]:
            print(f"  {r['date']} | {r['salesperson']} | {r['product_name']} | {r['amount']} | {r['sales_invoice_no']}")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    print("正在解析 CSV 檔案...")
    csv_records = parse_sales_csv()
    print(f"CSV 解析完成：{len(csv_records)} 筆記錄")
    
    print("正在查詢資料庫...")
    db_records = get_db_records()
    print(f"資料庫查詢完成：{len(db_records)} 筆記錄")
    
    compare_records(csv_records, db_records)