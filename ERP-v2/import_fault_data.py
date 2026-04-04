#!/usr/bin/env python3
"""一次性匯入腳本：從 repair/index.php 的 const APP 解析故障情境，寫入 fault_groups / fault_scenarios"""

import json
import os
import re
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'db', 'company.db')
PHP_PATH = os.path.join(BASE_DIR, 'repair', 'index.php')

def main():
    # 1. 讀取 index.php，擷取 const APP = {...};
    with open(PHP_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    m = re.search(r'const\s+APP\s*=\s*(\{.*?\});', content, re.DOTALL)
    if not m:
        print('ERROR: 找不到 const APP 變數')
        return

    data = json.loads(m.group(1))
    dataset = data.get('dataset', {})
    print(f'解析成功：{len(dataset)} 個群組，{data.get("total_items", "?")} 個情境')

    # 2. 連接資料庫
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL')

    # 建表（冪等）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fault_groups (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            group_key   TEXT UNIQUE,
            label       TEXT,
            icon        TEXT,
            sort_order  INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fault_scenarios (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            group_key   TEXT,
            title       TEXT,
            severity    TEXT,
            steps_json  TEXT,
            causes_json TEXT,
            tests_json  TEXT,
            fix_json    TEXT,
            keywords    TEXT,
            created_at  DATETIME DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (group_key) REFERENCES fault_groups(group_key)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fault_gk ON fault_scenarios(group_key)")

    # 3. 清除舊資料（冪等重跑）
    conn.execute("DELETE FROM fault_scenarios")
    conn.execute("DELETE FROM fault_groups")

    # 4. 匯入群組與情境
    group_count = 0
    scenario_count = 0

    for sort_idx, (group_key, group_data) in enumerate(dataset.items()):
        label = group_data.get('label', group_key)
        icon  = group_data.get('icon', '')
        items = group_data.get('items', [])

        conn.execute(
            "INSERT INTO fault_groups (group_key, label, icon, sort_order) VALUES (?,?,?,?)",
            (group_key, label, icon, sort_idx)
        )
        group_count += 1

        for item in items:
            title    = item.get('title', '')
            severity = item.get('severity', '')
            steps    = json.dumps(item.get('steps', []), ensure_ascii=False)
            causes   = json.dumps(item.get('causes', []), ensure_ascii=False)
            tests    = json.dumps(item.get('tests', []), ensure_ascii=False)
            fix      = json.dumps(item.get('fix', []), ensure_ascii=False)

            # 自動產生 keywords：title + causes 合併
            kw_parts = [title] + item.get('causes', [])
            keywords = ' '.join(kw_parts)

            conn.execute("""
                INSERT INTO fault_scenarios
                  (group_key, title, severity, steps_json, causes_json,
                   tests_json, fix_json, keywords)
                VALUES (?,?,?,?,?,?,?,?)
            """, (group_key, title, severity, steps, causes, tests, fix, keywords))
            scenario_count += 1

    conn.commit()
    conn.close()

    print(f'匯入完成：{group_count} 個群組，{scenario_count} 個情境')


if __name__ == '__main__':
    main()
