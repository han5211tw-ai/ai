#!/usr/bin/env python3
# 解析 CSV 並比對 3/8 資料

import csv
import os
import sqlite3

HOME = os.path.expanduser("~")
DB_PATH = os.path.join(HOME, "srv/db/company.db")

# 讀取 CSV
csv_path = "/Users/aiserver/srv/sync/OneDrive/ai_source/sales/archive/sales_20260310_114314.csv"

records = []
current_invoice = None
current_salesperson = None
current_customer = None

with open(csv_path, 'r', encoding='big5', errors='ignore') as f:
    reader = csv.reader(f)
    row_num = 0
    for row in reader:
        row_num += 1
        if not row:
            continue
        
        # 檢查是否為發票行（第一個欄位是日期如 1150308）
        if row[0] and row[0].startswith('1150308'):
            current_invoice = row[0]
            current_salesperson = row[4].strip() if len(row) > 4 else ''
            current_customer = row[8].strip() if len(row) > 8 else ''
        elif current_invoice and len(row) > 0 and row[0] and row[0].strip():  # 產品行（第0欄是產品代碼）
            product_code = row[0].strip()
            # 跳過分隔行（如 1150307, 1150306 等）
            if product_code.startswith('11503'):
                continue
            product_name = row[7].strip() if len(row) > 7 else ''
            quantity = row[14].strip() if len(row) > 14 else ''
            price = row[18].strip() if len(row) > 18 else ''
            amount = row[25].strip() if len(row) > 25 else ''
            
            records.append({
                'invoice': current_invoice,
                'salesperson': current_salesperson,
                'customer': current_customer,
                'product_code': product_code,
                'product_name': product_name,
                'quantity': quantity,
                'price': price,
                'amount': amount
            })

# 讀取資料庫中的 3/8 資料
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("SELECT * FROM sales_history WHERE date = '2026-03-08' ORDER BY invoice_no")
db_records = cursor.fetchall()
conn.close()

# 顯示比對結果
print("=" * 80)
print("比對結果：CSV vs 資料庫 (2026/03/08)")
print("=" * 80)
print(f"\nCSV 產品明細數: {len(records)}")
print(f"資料庫產品明細數: {len(db_records)}")
print()

# 顯示 CSV 的資料
print("-" * 80)
print("【CSV 中的資料】")
print("-" * 80)
for i, r in enumerate(records, 1):
    print(f"{i}. 發票:{r['invoice']} | 業務:{r['salesperson']} | 客戶:{r['customer']}")
    print(f"   產品:{r['product_code']} - {r['product_name']} | 數量:{r['quantity']} | 單價:{r['price']} | 金額:{r['amount']}")

print()
print("-" * 80)
print("【資料庫中的資料】")
print("-" * 80)
for i, r in enumerate(db_records, 1):
    print(f"{i}. 發票:{r['invoice_no']} | 業務:{r['salesperson']} | 客戶:{r['customer_id']}")
    print(f"   產品:{r['product_name']} | 數量:{r['quantity']} | 單價:{r['price']} | 金額:{r['amount']}")

# 找出差異
print()
print("=" * 80)
print("【差異分析】")
print("=" * 80)

# 建立 CSV 的 key 集合（使用發票+產品名稱+金額）
csv_keys = set()
for r in records:
    key = f"{r['invoice']}|{r['product_name']}|{r['amount']}"
    csv_keys.add(key)

# 檢查資料庫中的資料是否在 CSV 中
missing_in_csv = []
for r in db_records:
    key = f"{r['invoice_no']}|{r['product_name']}|{str(r['amount'])}"
    if key not in csv_keys:
        missing_in_csv.append(r)

# 建立資料庫的 key 集合
db_keys = set()
for r in db_records:
    key = f"{r['invoice_no']}|{r['product_name']}|{str(r['amount'])}"
    db_keys.add(key)

# 檢查 CSV 中的資料是否在資料庫中
missing_in_db = []
for r in records:
    key = f"{r['invoice']}|{r['product_name']}|{r['amount']}"
    if key not in db_keys:
        missing_in_db.append(r)

if missing_in_db:
    print(f"\nCSV 中有但資料庫沒有的資料（{len(missing_in_db)} 筆）：")
    for r in missing_in_db:
        print(f"  - 發票:{r['invoice']} | 產品:{r['product_code']} - {r['product_name']} | 金額:{r['amount']}")
else:
    print("\n✓ CSV 中的所有資料都在資料庫中")

if missing_in_csv:
    print(f"\n資料庫中有但 CSV 沒有的資料（{len(missing_in_csv)} 筆）：")
    for r in missing_in_csv:
        print(f"  - 發票:{r['invoice_no']} | 產品:{r['product_id']} - {r['product_name']} | 金額:{r['amount']}")
else:
    print("\n✓ 資料庫中的所有資料都在 CSV 中")
