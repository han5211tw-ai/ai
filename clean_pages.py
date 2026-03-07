#!/usr/bin/env python3
"""
清理 HTML 檔案，轉換為繼承 base.html 的模板
- 移除 <html>, <head>, <body> 標籤
- 移除舊導航和標題
- 改為一般模式（非寬螢幕）
"""

import re
from pathlib import Path

DASHBOARD_SITE = Path('/Users/aiserver/.openclaw/workspace/dashboard-site')

def clean_html_file(html_file):
    """清理單一 HTML 檔案"""
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取標題
    title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
    title = title_match.group(1) if title_match else '電腦舖營運系統'
    
    # 提取 body 內容
    body_match = re.search(r'<body[^>]*>(.*?)</body>', content, re.DOTALL | re.IGNORECASE)
    if not body_match:
        return None
    
    body_content = body_match.group(1)
    
    # 移除舊的導航元素（常見的導航 class/id）
    # 移除 nav 標籤
    body_content = re.sub(r'<nav[^>]*>.*?</nav>', '', body_content, flags=re.DOTALL | re.IGNORECASE)
    # 移除 header 標籤（如果包含導航）
    body_content = re.sub(r'<header[^>]*>.*?</header>', '', body_content, flags=re.DOTALL | re.IGNORECASE)
    # 移除舊的 sidebar
    body_content = re.sub(r'<aside[^>]*>.*?</aside>', '', body_content, flags=re.DOTALL | re.IGNORECASE)
    
    # 提取 style（排除全局 body/html 樣式）
    styles = []
    for match in re.finditer(r'<style[^>]*>(.*?)</style>', content, re.DOTALL | re.IGNORECASE):
        style_content = match.group(1)
        # 過濾掉全局樣式（html, body, * 等）
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
    
    # 建立新模板
    template = f'''{{% extends "base.html" %}}

{{% block title %}}{title}{{% endblock %}}

{{% block page_title %}}{title.replace(' - 電腦舖', '').replace('電腦舖營運系統', '首頁')}{{% endblock %}}

'''
    
    if styles:
        template += f'''{{% block styles %}}
<style>
.container {{ max-width: 95%; margin: 0 auto; padding: 20px; }}
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
    
    return template

def main():
    """主程式"""
    # 找到所有 HTML 檔案（排除 base.html 和特殊檔案）
    html_files = [
        f for f in DASHBOARD_SITE.glob('*.html')
        if f.name not in ['base.html', 'app_shell.html', 'app_shell_test.html']
        and not any(x in f.name.lower() for x in ['backup', 'deprecated', 'v1_', 'v2_', 'v3_'])
    ]
    
    print(f"找到 {len(html_files)} 個 HTML 檔案需要清理\n")
    
    success = fail = 0
    
    for html_file in sorted(html_files):
        try:
            template = clean_html_file(html_file)
            if template:
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(template)
                print(f"✅ {html_file.name}")
                success += 1
            else:
                print(f"⚠️  {html_file.name} - 無法提取內容")
                fail += 1
        except Exception as e:
            print(f"❌ {html_file.name}: {str(e)[:60]}")
            fail += 1
    
    print(f"\n總結: {success} 成功, {fail} 失敗")

if __name__ == '__main__':
    main()