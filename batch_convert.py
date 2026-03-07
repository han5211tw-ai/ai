#!/usr/bin/env python3
"""
批次轉換 HTML 為 Jinja2 模板（排除 index.html 和 needs_input.html）
"""

import re
from pathlib import Path

DASHBOARD_SITE = Path('/Users/aiserver/.openclaw/workspace/dashboard-site')

# 排除的檔案
EXCLUDE = {'index.html', 'needs_input.html', 'base.html', 'app_shell.html', 'app_shell_test.html'}

def convert_file(html_file):
    """轉換單一檔案"""
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 如果已經是模板，跳過
    if '{% extends' in content:
        print(f"⏭️  已經是模板: {html_file.name}")
        return True
    
    # 提取標題
    title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
    title = title_match.group(1) if title_match else '電腦舖營運系統'
    
    # 提取 body 內容
    body_match = re.search(r'<body[^>]*>(.*?)</body>', content, re.DOTALL | re.IGNORECASE)
    if not body_match:
        print(f"⚠️  無法提取 body: {html_file.name}")
        return False
    
    body_content = body_match.group(1)
    
    # 移除舊導航元素
    body_content = re.sub(r'<nav[^>]*>.*?</nav>', '', body_content, flags=re.DOTALL | re.IGNORECASE)
    body_content = re.sub(r'<header[^>]*>.*?</header>', '', body_content, flags=re.DOTALL | re.IGNORECASE)
    body_content = re.sub(r'<aside[^>]*>.*?</aside>', '', body_content, flags=re.DOTALL | re.IGNORECASE)
    
    # 提取 style（排除全局樣式）
    styles = []
    for match in re.finditer(r'<style[^>]*>(.*?)</style>', content, re.DOTALL | re.IGNORECASE):
        style_content = match.group(1)
        style_content = re.sub(r'html\s*\{[^}]*\}', '', style_content)
        style_content = re.sub(r'body\s*\{[^}]*\}', '', style_content)
        style_content = re.sub(r'\*\s*\{[^}]*\}', '', style_content)
        if style_content.strip():
            styles.append(style_content.strip())
    
    # 提取內嵌 script
    scripts = []
    for match in re.finditer(r'<script[^>]*>(.*?)</script>', content, re.DOTALL | re.IGNORECASE):
        script_content = match.group(1).strip()
        if script_content and not match.group(0).startswith('<script src'):
            scripts.append(script_content)
    
    # 建立模板
    template = f'''{{% extends "base.html" %}}

{{% block title %}}{title}{{% endblock %}}

{{% block page_title %}}{title.replace(' - 電腦舖', '').replace('電腦舖營運系統', '首頁')}{{% endblock %}}

'''
    
    if styles:
        template += f'''{{% block styles %}}
<style>
.container {{ width: 100%; margin: 0; padding: 0; }}
{chr(10).join(styles)}
</style>
{{% endblock %}}

'''
    
    template += f'''{{% block content %}}
<div class="container">
{body_content.strip()}
</div>
{{% endblock %}}
'''
    
    if scripts:
        template += f'''
{{% block scripts %}}
<script>
{chr(10).join(scripts)}
</script>
{{% endblock %}}
'''
    
    # 寫入檔案
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(template)
    
    return True

def main():
    """主程式"""
    html_files = [f for f in DASHBOARD_SITE.glob('*.html') if f.name not in EXCLUDE and not f.name.startswith('needs_input_v') and not f.name.endswith('_backup.html') and not f.name.endswith('_deprecated.html')]
    
    print(f"找到 {len(html_files)} 個檔案需要轉換\n")
    
    success = fail = skip = 0
    
    for html_file in sorted(html_files):
        try:
            if convert_file(html_file):
                if '{% extends' in open(html_file).read():
                    print(f"✅ {html_file.name}")
                    success += 1
                else:
                    skip += 1
            else:
                fail += 1
        except Exception as e:
            print(f"❌ {html_file.name}: {str(e)[:60]}")
            fail += 1
    
    print(f"\n總結: {success} 成功, {fail} 失敗, {skip} 跳過")

if __name__ == '__main__':
    main()