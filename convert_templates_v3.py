#!/usr/bin/env python3
"""
HTML to Jinja2 Template Converter - Version 3
使用正規表達式，無需外部套件
"""

import os
import re
from pathlib import Path

DASHBOARD_SITE = Path('/Users/aiserver/.openclaw/workspace/dashboard-site')
TEMPLATES_DIR = DASHBOARD_SITE / 'templates'

def extract_title(content):
    """提取標題"""
    match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else '電腦舖營運系統'

def extract_body_content(content):
    """提取 body 內的內容，移除導航"""
    # 找到 body 標籤
    body_match = re.search(r'<body[^>]*>(.*?)</body>', content, re.IGNORECASE | re.DOTALL)
    if not body_match:
        return content
    
    body_content = body_match.group(1)
    
    # 移除常見的導航元素（簡單版本）
    # 移除 nav 標籤
    body_content = re.sub(r'<nav[^>]*>.*?</nav>', '', body_content, flags=re.IGNORECASE | re.DOTALL)
    # 移除 header 標籤
    body_content = re.sub(r'<header[^>]*>.*?</header>', '', body_content, flags=re.IGNORECASE | re.DOTALL)
    
    return body_content.strip()

def extract_styles(content):
    """提取 style 標籤內的 CSS"""
    styles = []
    for match in re.finditer(r'<style[^>]*>(.*?)</style>', content, re.IGNORECASE | re.DOTALL):
        style_content = match.group(1).strip()
        if style_content:
            styles.append(style_content)
    return '\n\n'.join(styles)

def extract_scripts(content):
    """提取內嵌 script"""
    scripts = []
    for match in re.finditer(r'<script[^>]*>(.*?)</script>', content, re.IGNORECASE | re.DOTALL):
        script_content = match.group(1).strip()
        # 排除外部腳本
        if script_content and not match.group(0).startswith('<script src'):
            scripts.append(script_content)
    return '\n\n'.join(scripts)

def convert_file(html_file):
    """轉換單一檔案"""
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取各部分
    title = extract_title(content)
    body_content = extract_body_content(content)
    styles = extract_styles(content)
    scripts = extract_scripts(content)
    
    # 簡化頁面標題
    page_title = title.replace(' - 電腦舖', '').replace('電腦舖營運系統', '首頁')
    
    # 建立模板
    template_parts = [
        '{% extends "base.html" %}',
        '',
        f'{{% block title %}}{title}{{% endblock %}}',
        f'{{% block page_title %}}{page_title}{{% endblock %}}',
        ''
    ]
    
    if styles:
        template_parts.extend([
            '{% block styles %}',
            '<style>',
            styles,
            '</style>',
            '{% endblock %}',
            ''
        ])
    
    template_parts.extend([
        '{% block content %}',
        body_content,
        '{% endblock %}'
    ])
    
    if scripts:
        template_parts.extend([
            '',
            '{% block scripts %}',
            '<script>',
            scripts,
            '</script>',
            '{% endblock %}'
        ])
    
    return '\n'.join(template_parts)

def main():
    """主程式"""
    TEMPLATES_DIR.mkdir(exist_ok=True)
    
    # 找到所有 HTML 檔案
    html_files = [
        f for f in DASHBOARD_SITE.glob('*.html')
        if not any(x in f.name.lower() for x in [
            'app_shell', 'test', 'backup', 'deprecated', 
            'v1_', 'v2_', 'v3_', 'convert'
        ])
    ]
    
    print(f"找到 {len(html_files)} 個 HTML 檔案\n")
    
    success = fail = 0
    
    for html_file in sorted(html_files):
        try:
            template = convert_file(html_file)
            output_file = TEMPLATES_DIR / html_file.name
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(template)
            
            print(f"✅ {html_file.name}")
            success += 1
        except Exception as e:
            print(f"❌ {html_file.name}: {str(e)[:60]}")
            fail += 1
    
    print(f"\n總結: {success} 成功, {fail} 失敗")

if __name__ == '__main__':
    main()