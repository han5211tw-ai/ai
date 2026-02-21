#!/opt/homebrew/bin/python3
"""
Sales Parser V7.0 - Robust Version
Compatible with multiple Excel formats
"""
import sqlite3
import pandas as pd
import os
import re
from datetime import datetime

# --- 環境變數 ---
HOME = os.path.expanduser("~")
DB_PATH = os.path.join(HOME, "srv/db/company.db")
SALES_DIR = os.path.join(HOME, "srv/sync/OneDrive/ai_source/sales")
INVOICE_MATH_TOL = 10  # 驗算容錯範圍

def clean_str(val):
    """清理字串，移除空格和 .0 後輟"""
    s = str(val).strip() if pd.notnull(val) else ""
    if s.endswith('.0'): 
        s = s[:-2]
    return s

def is_invoice(val):
    """識別單號：9位以上數字，開頭為1或2"""
    s = clean_str(val)
    return s.isdigit() and len(s) >= 9 and (s.startswith("1") or s.startswith("2"))

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def find_column_mapping(row):
    """
    動態識別欄位位置
    回傳: {'invoice': col_idx, 'qty': col_idx, 'price': col_idx, 'amount': col_idx} 或 None
    """
    vals = [clean_str(x) for x in row.values if clean_str(x) != '']
    
    # 1. 找單號位置
    invoice_col = None
    for j, val in enumerate(row):
        if is_invoice(val):
            invoice_col = j
            break
    
    if invoice_col is None:
        return None
    
    # 2. 收集所有數字欄位（排除單號）
    num_cols = []
    for j, val in enumerate(row):
        if j == invoice_col:
            continue
        s = clean_str(val)
        # 是數字且不是單號格式
        if re.match(r'^-?\d+(\.\d+)?$', s.replace(',', '')) and not is_invoice(s):
            try:
                num_cols.append((j, float(s.replace(',', ''))))
            except:
                pass
    
    if len(num_cols) < 3:
        return None
    
    # 3. 找出數量、單價、金額
    # 策略：找符合「數量 × 單價 ≈ 金額」的組合
    best_match = None
    best_error = float('inf')
    
    # 通常數量是最小的正整數，金額是最大的
    for i, (qty_col, qty_val) in enumerate(num_cols):
        if qty_val <= 0 or qty_val > 1000:  # 數量應該是小正整數
            continue
        for j, (price_col, price_val) in enumerate(num_cols):
            if j == i or price_val < 0:
                continue
            for k, (amt_col, amt_val) in enumerate(num_cols):
                if k == i or k == j or amt_val < 0:
                    continue
                # 驗算
                calculated = qty_val * price_val
                error = abs(calculated - amt_val)
                if error <= INVOICE_MATH_TOL and error < best_error:
                    best_error = error
                    best_match = {
                        'invoice': invoice_col,
                        'qty': qty_col,
                        'price': price_col,
                        'amount': amt_col
                    }
    
    return best_match

def detect_file_format(df):
    """
    檢測整個檔案的欄位格式
    回傳: {'invoice': col, 'qty': col, 'price': col, 'amount': col}
    """
    # 取樣前 20 行有單號的資料來判斷格式
    mappings = []
    for i in range(min(20, len(df))):
        mapping = find_column_mapping(df.iloc[i])
        if mapping:
            mappings.append(mapping)
    
    if not mappings:
        return None
    
    # 統計最常見的格式
    from collections import Counter
    format_strs = [f"{m['invoice']},{m['qty']},{m['price']},{m['amount']}" for m in mappings]
    most_common = Counter(format_strs).most_common(1)[0][0]
    
    # 解析回字典
    parts = most_common.split(',')
    return {
        'invoice': int(parts[0]),
        'qty': int(parts[1]),
        'price': int(parts[2]),
        'amount': int(parts[3])
    }

# --- 1. 建立業務對照表 ---
def build_salesperson_map():
    """從業務銷貨明細檔案建立單號→業務員對照表"""
    print(f"🕵️ 建立業務員單號索引...")
    sales_map = {}
    
    files = [f for f in os.listdir(SALES_DIR) 
             if any(k in f for k in ["業務銷貨明細", "銷貨-4"]) 
             and f.endswith(('.xlsx', '.csv'))]
    
    for file in files:
        if file.startswith('~$'):
            continue
        try:
            df = pd.read_excel(os.path.join(SALES_DIR, file), header=None)
            current_staff = "Unknown"
            
            for _, row in df.iterrows():
                vals = [clean_str(x) for x in row.values if clean_str(x) != '']
                row_str = "".join(vals)
                
                # 識別業務員
                if "業務人員" in row_str:
                    match = re.search(r"業務人員[：:]?\s*[a-zA-Z0-9-]*\s*([\u4e00-\u9fa5]{2,4})", row_str)
                    if match:
                        current_staff = match.group(1)
                    else:
                        for v in vals:
                            if "業務人員" not in v and len(v) > 1:
                                current_staff = v.split()[-1]
                                break
                
                if "LIS" in row_str:
                    current_staff = "劉育仕"
                
                # 記錄單號
                for v in vals:
                    if is_invoice(v):
                        sales_map[v] = current_staff
                        
        except Exception as e:
            print(f"  警告：處理 {file} 時發生錯誤: {e}")
            continue
    
    print(f"   ✅ 索引完成，共 {len(sales_map)} 筆單號")
    return sales_map

# --- 2. 解析銷貨明細 ---
def parse_sales_details(conn, sales_map):
    """解析客戶銷貨明細檔案"""
    print("📦 解析銷貨明細...")
    
    # 建立資料表
    conn.execute('''CREATE TABLE IF NOT EXISTS sales_history (
        invoice_no TEXT, date TEXT, customer_id TEXT, salesperson TEXT,
        product_code TEXT, product_name TEXT, quantity INTEGER,
        price INTEGER, amount INTEGER, updated_at DATETIME
    )''')
    
    files = [f for f in os.listdir(SALES_DIR)
             if any(k in f for k in ["客戶銷貨明細", "銷貨-2"])
             and f.endswith(('.xlsx', '.csv'))]
    
    total = 0
    now_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for file in files:
        if file.startswith('~$'):
            continue
            
        print(f"   處理: {file}")
        try:
            df = pd.read_excel(os.path.join(SALES_DIR, file), header=None)
            
            # 檢測檔案格式
            col_map = detect_file_format(df)
            if not col_map:
                print(f"   ⚠️ 無法識別 {file} 的欄位格式")
                continue
            
            print(f"   格式: 單號[{col_map['invoice']}] 數量[{col_map['qty']}] 單價[{col_map['price']}] 金額[{col_map['amount']}]")
            
            c_id, c_inv, c_date = None, None, None
            batch = []
            
            for i, row in df.iterrows():
                vals = [clean_str(x) for x in row.values if clean_str(x) != '']
                row_str = "".join(vals)
                
                # 跳過合計行
                if any(x in row_str for x in ['合計', '總計', '小計']):
                    continue
                
                # 抓取客戶編號
                if "客戶名稱" in row_str:
                    for v in vals:
                        if "客戶名稱" not in v and "-" in v:
                            parts = v.split(maxsplit=1)
                            if len(parts) > 0 and '-' in parts[0]:
                                c_id = parts[0]
                
                # 抓取單號和日期
                new_inv = False
                val_at_invoice_col = clean_str(row.iloc[col_map['invoice']]) if col_map['invoice'] < len(row) else ""
                
                if is_invoice(val_at_invoice_col):
                    c_inv = val_at_invoice_col
                    new_inv = True
                
                # 找日期
                for v in vals:
                    if re.match(r'\d{4}[-/]\d{2}[-/]\d{2}', v):
                        c_date = v.replace('/', '-')
                        break
                
                if not c_inv:
                    continue
                
                # 抓取數值
                try:
                    qty = float(clean_str(row.iloc[col_map['qty']]).replace(',', ''))
                    price = float(clean_str(row.iloc[col_map['price']]).replace(',', ''))
                    amt = float(clean_str(row.iloc[col_map['amount']]).replace(',', ''))
                except:
                    continue
                
                # 驗算
                if abs(qty * price - amt) > INVOICE_MATH_TOL:
                    continue
                
                # 抓取產品編號
                p_code = ""
                for j in range(col_map['invoice'] + 1, col_map['qty']):
                    if j < len(row):
                        v = clean_str(row.iloc[j])
                        if v and not re.match(r'^-?\d', v.replace(',', '')) and len(v) > 2:
                            p_code = v
                            break
                
                # 抓取產品名稱（下一行）
                p_name = ""
                if i + 1 < len(df):
                    next_row = df.iloc[i + 1]
                    next_vals = [clean_str(x) for x in next_row.values if clean_str(x) != '']
                    for nv in next_vals:
                        if re.search(r'[\u4e00-\u9fa5]', nv) and "合計" not in nv and len(nv) > 3:
                            p_name = nv
                            break
                
                if not p_name:
                    p_name = p_code
                
                # 對照業務員
                staff = sales_map.get(c_inv, "Unknown")
                
                # ERP 漏印單號防呆
                if staff == "Unknown" and c_inv.isdigit() and len(c_inv) >= 9:
                    prefix = c_inv[:-4]
                    seq = int(c_inv[-4:])
                    for offset in range(1, 10):
                        if seq - offset <= 0:
                            break
                        prev_inv = f"{prefix}{(seq - offset):04d}"
                        if prev_inv in sales_map:
                            staff = sales_map[prev_inv]
                            break
                
                batch.append((
                    c_inv, c_date, c_id, staff, p_code, p_name,
                    int(qty), int(price), int(amt), now_ts
                ))
            
            # 批次寫入
            if batch:
                inv_set = set(t[0] for t in batch)
                conn.executemany(
                    "DELETE FROM sales_history WHERE invoice_no = ?",
                    [(inv,) for inv in inv_set]
                )
                conn.executemany(
                    'INSERT INTO sales_history VALUES (?,?,?,?,?,?,?,?,?,?)',
                    batch
                )
                total += len(batch)
                print(f"   ✓ 同步 {len(batch)} 筆")
                
        except Exception as e:
            print(f"   ❌ 錯誤 {file}: {e}")
            continue
    
    print(f"🎉 完畢！共同步 {total} 筆交易")

def main():
    conn = get_db_connection()
    try:
        parse_sales_details(conn, build_salesperson_map())
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    main()