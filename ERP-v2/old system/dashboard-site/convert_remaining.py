#!/usr/bin/env python3
"""
手動轉換剩餘 HTML 檔案為 Jinja2 模板
"""

import re
from pathlib import Path

DASHBOARD_SITE = Path('/Users/aiserver/.openclaw/workspace/dashboard-site')

FILES_TO_CONVERT = [
    'Accountants.html',
    'Store_Manager.html', 
    'admin.html',
    'boss.html',
    'business.html',
    'customer_search.html',
    'department.html',
    'personal.html',
    'quote_input.html',
    'roster.html',
    'roster_input.html',
    'service_record.html',
    'staging_center_v2.html',
    'store.html',
    'supervision_score.html'
]

def simple_convert(html_file):
    """簡單轉換：保留所有內容，只加上模板標籤"""
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 如果已經是模板，跳過
    if '{% extends' in content:
        return True
    
    # 提取標題
    title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
    title = title_match.group(1) if title_match else '電腦舖營運系統'
    
    # 簡化頁面標題
    page_title = title.replace(' - 電腦舖', '').replace('電腦舖營運系統', '首頁')
    
    # 建立模板 - 保留完整原始內容
    template = f'''{{% extends "base.html" %}}

{{% block title %}}{title}{{% endblock %}}

{{% block page_title %}}{page_title}{{% endblock %}}

{{% block content %}}
<!-- 原始內容開始 -->
{content}
<!-- 原始內容結束 -->
{{% endblock %}}
'''
    
    # 寫入檔案
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(template)
    
    return True

def main():
    print(f"開始轉換 {len(FILES_TO_CONVERT)} 個檔案...\n")
    
    success = fail = 0
    
    for filename in FILES_TO_CONVERT:
        filepath = DASHBOARD_SITE / filename
        if not filepath.exists():
            print(f"⚠️  檔案不存在: {filename}")
            fail += 1
            continue
        
        try:
            if simple_convert(filepath):
                print(f"✅ {filename}")
                success += 1
            else:
                print(f"❌ {filename}")
                fail += 1
        except Exception as e:
            print(f"❌ {filename}: {str(e)[:60]}")
            fail += 1
    
    print(f"\n總結: {success} 成功, {fail} 失敗")

if __name__ == '__main__':
    main()