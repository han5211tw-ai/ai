#!/usr/bin/env python3
"""
一次性遷移腳本：重新整理 sales_history 的 sales_invoice_no
問題：v1 匯入的資料每筆都各自一個單號，應該合併
規則：同日期 + 同業務員 + 同客戶名 → 共用同一筆單號
單號格式：{門市代碼}-{YYYYMMDD}-{NNN}
門市代碼由業務員姓名 → staff.store 查對應
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'db', 'company.db')

STORE_CODE_MAP = {
    '豐原門市': 'FY', '豐原': 'FY',
    '潭子門市': 'TZ', '潭子': 'TZ',
    '大雅門市': 'DY', '大雅': 'DY',
    '業務部':   'OW', '-': 'OW', '': 'OW',
}


def run():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 確保欄位存在
    cols = {c[1] for c in conn.execute('PRAGMA table_info(sales_history)')}
    for col, dtype in [('source_doc_no', "TEXT DEFAULT ''"),
                       ('warehouse', "TEXT DEFAULT ''"),
                       ('payment_method', "TEXT DEFAULT ''"),
                       ('deposit_amount', "INTEGER DEFAULT 0")]:
        if col not in cols:
            conn.execute(f"ALTER TABLE sales_history ADD COLUMN {col} {dtype}")
    conn.commit()

    # ── 1. 業務員 → 門市代碼 ──
    staff_store = {}
    try:
        rows = conn.execute("SELECT name, store FROM staff").fetchall()
        # 特例覆蓋：staff 表 store 不準的，手動指定
        STAFF_OVERRIDE = {
            '莊圍迪': 'FY',
        }
        for r in rows:
            name = r['name'].strip()
            if name in STAFF_OVERRIDE:
                staff_store[name] = STAFF_OVERRIDE[name]
            else:
                store = (r['store'] or '').strip()
                code = STORE_CODE_MAP.get(store, '')
                if code:
                    staff_store[name] = code
        print(f'[員工對照] 共 {len(staff_store)} 位')
        for name, code in sorted(staff_store.items()):
            print(f'  {name} → {code}')
    except Exception as e:
        print(f'[員工對照] 查詢失敗: {e}')

    # ── 2. 撈全部資料，按日期+業務+客戶排序 ──
    all_rows = conn.execute("""
        SELECT id, date, salesperson, customer_name, sales_invoice_no
        FROM sales_history
        ORDER BY date ASC, salesperson ASC, customer_name ASC, id ASC
    """).fetchall()
    print(f'\n[資料] 共 {len(all_rows)} 筆')

    if not all_rows:
        print('無資料，結束。')
        conn.close()
        return

    # ── 3. 分組：(date, salesperson, customer_name) → [ids] ──
    groups = []
    current_key = None
    current_ids = []
    for r in all_rows:
        key = (r['date'] or '', (r['salesperson'] or '').strip(),
               (r['customer_name'] or '').strip())
        if key != current_key:
            if current_ids:
                groups.append((current_key, current_ids))
            current_key = key
            current_ids = [r['id']]
        else:
            current_ids.append(r['id'])
    if current_ids:
        groups.append((current_key, current_ids))

    print(f'[分組] {len(all_rows)} 筆 → {len(groups)} 組')

    # ── 4. 產生新單號 ──
    prefix_seq = {}   # 'FY-20260403-' → 下一個序號

    updated_rows = 0
    updated_groups = 0
    for (date_str, salesperson, customer_name), ids in groups:
        # 門市代碼
        store_code = staff_store.get(salesperson, 'FY')

        # 日期 YYYY-MM-DD → YYYYMMDD
        date_compact = (date_str or '').replace('-', '').strip()
        if len(date_compact) < 8:
            date_compact = '00000000'

        prefix = f'{store_code}-{date_compact}-'
        seq = prefix_seq.get(prefix, 1)
        new_no = f'{prefix}{seq:03d}'
        prefix_seq[prefix] = seq + 1

        # 批次 UPDATE
        placeholders = ','.join('?' * len(ids))
        conn.execute(
            f"UPDATE sales_history SET sales_invoice_no=? WHERE id IN ({placeholders})",
            [new_no] + ids
        )
        updated_rows += len(ids)
        updated_groups += 1

        # 印出前 50 組 + 每 200 組
        if updated_groups <= 50 or updated_groups % 200 == 0:
            print(f'  {new_no:22s} ← {len(ids):3d} 筆  '
                  f'({salesperson} / {customer_name or "—"} / {date_str})')

    conn.commit()
    conn.close()
    print(f'\n[完成] {updated_rows} 筆 → {updated_groups} 組單號')


if __name__ == '__main__':
    run()
