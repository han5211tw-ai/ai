#!/usr/bin/env python3
"""
HTML to Jinja2 Template Converter - Version 2
更精確地提取內容並轉換為模板
"""

import os
import re
from pathlib import Path
from bs4 import BeautifulSoup

DASHBOARD_SITE = Path('/Users/aiserver/.openclaw/workspace/dashboard-site')
TEMPLATES_DIR = DASHBOARD_SITE / 'templates'

def convert_html_to_template(html_file):
    """將 HTML 檔案轉換為 Jinja2 模板"""
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    
    # 提取標題
    title_tag = soup.find('title')
    title = title_tag.text if title_tag else '電腦舖營運系統'
    
    # 提取 body 內容
    body = soup.find('body')
    if body:
        # 移除舊的導航元素（常見的導航 class/id）
        for nav in body.find_all(['nav', 'header'], class_=re.compile(r'nav|menu|sidebar|header', re.I)):
            nav.decompose()
        
        body_content = str(body.decode_contents())
    else:
        body_content = content
    
    # 提取所有 style 標籤
    styles = []
    for style in soup.find_all('style'):
        styles.append(style.get_text())
    
    # 提取所有內嵌 script（排除外部引用）
    scripts = []
    for script in soup.find_all('script'):
        if not script.get('src') and script.get_text().strip():
            scripts.append(script.get_text())
    
    # 建立模板
    template = f'''{{% extends "base.html" %}}

{{% block title %}}{title}{{% endblock %}}

{{% block page_title %}}{title.replace(' - 電腦舖', '').replace('電腦舖', '首頁')}{{% endblock %}}

'''
    
    if styles:
        template += f'''{{% block styles %}}
<style>
{chr(10).join(styles)}
</style>
{{% endblock %}}

'''
    
    template += f'''{{% block content %}}
{body_content}
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
    # 確保 templates 資料夾存在
    TEMPLATES_DIR.mkdir(exist_ok=True)
    
    # 找到所有 HTML 檔案（排除測試和備份檔）
    html_files = [
        f for f in DASHBOARD_SITE.glob('*.html')
        if not any(x in f.name.lower() for x in [
            'app_shell', 'test', 'backup', 'deprecated', 
            'v1_', 'v2_', 'v3_', 'convert'
        ])
    ]
    
    print(f"找到 {len(html_files)} 個 HTML 檔案需要轉換\n")
    
    success_count = 0
    fail_count = 0
    
    for html_file in sorted(html_files):
        try:
            template_content = convert_html_to_template(html_file)
            template_file = TEMPLATES_DIR / html_file.name
            
            with open(template_file, 'w', encoding='utf-8') as f:
                f.write(template_content)
            
            print(f"✅ {html_file.name}")
            success_count += 1
        except Exception as e:
            print(f"❌ {html_file.name} - {str(e)[:50]}")
            fail_count += 1
    
    print(f"\n總結: {success_count} 成功, {fail_count} 失敗")
    print(f"模板儲存在: {TEMPLATES_DIR}")

if __name__ == '__main__':
    main()