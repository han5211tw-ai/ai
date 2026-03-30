#!/usr/bin/env python3
"""Clean service_record.html to pure Jinja2 template"""

import re

with open('/Users/aiserver/.openclaw/workspace/dashboard-site/service_record.html', 'r') as f:
    content = f.read()

# Extract the parts we need
# 1. Get styles between <style> and </style>
style_match = re.search(r'<style>(.*?)</style>', content, re.DOTALL)
styles = style_match.group(1) if style_match else ''

# Remove problematic CSS rules that conflict with base.html
styles = re.sub(r'\*\s*\{[^}]*\}', '', styles)  # Remove * { margin: 0... }
styles = re.sub(r'html[^}]*\}', '', styles)  # Remove html rules
styles = re.sub(r'body\s*\{[^}]*\}', '', styles)  # Remove body rules
styles = re.sub(r'\.container\s*\{[^}]*\}', '', styles)  # Remove .container
styles = re.sub(r'h1\s*\{[^}]*\}', '', styles)  # Remove h1
styles = re.sub(r'\.subtitle\s*\{[^}]*\}', '', styles)  # Remove .subtitle

# 2. Get content between <body> and </body>
body_match = re.search(r'<body>(.*?)</body>', content, re.DOTALL)
body_content = body_match.group(1) if body_match else ''

# Remove <div class="container"> wrapper
body_content = re.sub(r'^\s*<div class="container">', '', body_content)
body_content = re.sub(r'</div>\s*$', '', body_content)

# Remove h1 and subtitle (already in base.html page_title)
body_content = re.sub(r'<h1>.*?</h1>\s*', '', body_content, flags=re.DOTALL)
body_content = re.sub(r'<p class="subtitle">.*?</p>\s*', '', body_content, flags=re.DOTALL)

# 3. Get scripts between <script> and </script> (excluding auth_ui.js)
scripts = []
for script_match in re.finditer(r'<script>(.*?)</script>', content, re.DOTALL):
    script_content = script_match.group(1)
    # Skip if it's just loading external script
    if 'src=' not in content[script_match.start()-50:script_match.start()]:
        scripts.append(script_content)

# Build new template
new_template = '''{% extends "base.html" %}

{% block title %}外勤服務紀錄 - 電腦舖{% endblock %}

{% block page_title %}外勤服務紀錄{% endblock %}

{% block styles %}
<style>
''' + styles.strip() + '''
</style>
{% endblock %}

{% block content %}
''' + body_content.strip() + '''
{% endblock %}

{% block scripts %}
<script>
''' + '\n\n'.join(scripts) + '''
</script>
{% endblock %}
'''

# Write cleaned file
with open('/Users/aiserver/.openclaw/workspace/dashboard-site/service_record.html', 'w') as f:
    f.write(new_template)

print("Cleaned service_record.html")
print(f"New size: {len(new_template)} bytes")