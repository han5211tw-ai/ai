#!/usr/bin/env python3
"""
移除所有頁面中的標題和導航元素
保留 base.html 作為唯一外殼
"""

import re
from pathlib import Path

DASHBOARD_SITE = Path('/Users/aiserver/.openclaw/workspace/dashboard-site')

# 排除的檔案
EXCLUDE = {'base.html', 'app_shell.html', 'app_shell_test.html', 'index.html', 'needs_input.html'}

def remove_headers(html_file):
    """移除標題和導航元素"""
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 如果已經是模板格式
    if '{% extends' in content:
        # 只處理 content block 內的內容
        content_match = re.search(r'{% block content %}(.*?){% endblock %}', content, re.DOTALL)
        if content_match:
            inner_content = content_match.group(1)
            
            # 移除 h1-h6 標題
            inner_content = re.sub(r'<h[1-6][^>]*>.*?</h[1-6]>', '', inner_content, flags=re.DOTALL | re.IGNORECASE)
            
            # 移除 nav 導航
            inner_content = re.sub(r'<nav[^>]*>.*?</nav>', '', inner_content, flags=re.DOTALL | re.IGNORECASE)
            
            # 移除 header（如果包含導航類內容）
            inner_content = re.sub(r'<header[^>]*>.*?</header>', '', inner_content, flags=re.DOTALL | re.IGNORECASE)
            
            # 移除「電腦舖營運系統」標題文字（但保留在 title 中）
            inner_content = re.sub(r'<div[^>]*>\s*🖥️\s*電腦舖營運系統\s*</div>', '', inner_content, flags=re.IGNORECASE)
            inner_content = re.sub(r'<div[^>]*>\s*電腦舖營運系統\s*</div>', '', inner_content, flags=re.IGNORECASE)
            
            # 重建模板
            new_content = re.sub(r'({% block content %}).*?({% endblock %})', 
                                r'\1' + inner_content + r'\2', 
                                content, flags=re.DOTALL)
            
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
    
    return False

def main():
    html_files = [f for f in DASHBOARD_SITE.glob('*.html') if f.name not in EXCLUDE and not f.name.startswith('needs_input_v') and not f.name.endswith('_backup.html') and not f.name.endswith('_deprecated.html')]
    
    print(f"處理 {len(html_files)} 個檔案...\n")
    
    success = fail = 0
    
    for html_file in sorted(html_files):
        try:
            if remove_headers(html_file):
                print(f"✅ {html_file.name}")
                success += 1
            else:
                print(f"⏭️  {html_file.name} (非模板格式)")
                fail += 1
        except Exception as e:
            print(f"❌ {html_file.name}: {str(e)[:60]}")
            fail += 1
    
    print(f"\n總結: {success} 成功, {fail} 跳過")

if __name__ == '__main__':
    main()