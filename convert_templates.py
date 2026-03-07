#!/usr/bin/env python3
"""
HTML to Jinja2 Template Converter
將既有 HTML 頁面轉換為繼承 base.html 的模板
"""

import os
import re
from pathlib import Path

DASHBOARD_SITE = Path('/Users/aiserver/.openclaw/workspace/dashboard-site')
TEMPLATES_DIR = DASHBOARD_SITE / 'templates'

def extract_content(html_content):
    """提取 body 內的核心內容"""
    # 移除 DOCTYPE, html, head, body 標籤
    # 提取 body 內的內容
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL | re.IGNORECASE)
    if body_match:
        content = body_match.group(1)
        
        # 移除舊的導航列（如果有）
        # 這裡需要根據實際結構調整
        
        return content.strip()
    
    return html_content

def extract_styles(html_content):
    """提取 style 標籤內的內容"""
    styles = []
    for match in re.finditer(r'<style[^>]*>(.*?)</style>', html_content, re.DOTALL | re.IGNORECASE):
        styles.append(match.group(1).strip())
    return '\n'.join(styles)

def extract_scripts(html_content):
    """提取 script 標籤內的內容（排除外部引用）"""
    scripts = []
    for match in re.finditer(r'<script[^>]*>(.*?)</script>', html_content, re.DOTALL | re.IGNORECASE):
        content = match.group(1).strip()
        if content:  # 只保留內嵌 script
            scripts.append(content)
    return '\n'.join(scripts)

def extract_title(html_content):
    """提取頁面標題"""
    match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
    return match.group(1) if match else '電腦舖營運系統'

def convert_to_template(html_file):
    """將 HTML 檔案轉換為 Jinja2 模板"""
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # 提取各個部分
    title = extract_title(html_content)
    content = extract_content(html_content)
    styles = extract_styles(html_content)
    scripts = extract_scripts(html_content)
    
    # 建立模板內容
    template_content = f'''{{% extends "base.html" %}}

{{% block title %}}{title}{{% endblock %}}

{{% block page_title %}}{title.replace(' - 電腦舖', '')}{{% endblock %}}

{{% block styles %}}
<style>
{styles}
</style>
{{% endblock %}}

{{% block content %}}
{content}
{{% endblock %}}

{{% block scripts %}}
<script>
{scripts}
</script>
{{% endblock %}}
'''
    
    return template_content

def main():
    """主程式：批次處理所有 HTML 檔案"""
    html_files = [
        f for f in DASHBOARD_SITE.glob('*.html')
        if not any(x in f.name.lower() for x in ['app_shell', 'test', 'backup', 'deprecated', 'v1_', 'v2_', 'v3_'])
    ]
    
    print(f"找到 {len(html_files)} 個 HTML 檔案需要轉換")
    
    for html_file in sorted(html_files):
        try:
            template_content = convert_to_template(html_file)
            template_file = TEMPLATES_DIR / html_file.name
            
            with open(template_file, 'w', encoding='utf-8') as f:
                f.write(template_content)
            
            print(f"✅ 已轉換: {html_file.name} -> templates/{html_file.name}")
        except Exception as e:
            print(f"❌ 失敗: {html_file.name} - {e}")

if __name__ == '__main__':
    main()