#!/usr/bin/env python3
"""Convert needs_input.html to proper Jinja2 template"""

import re

with open('/Users/aiserver/.openclaw/workspace/dashboard-site/needs_input.html', 'r') as f:
    content = f.read()

# Extract styles between <style> and </style>
style_match = re.search(r'<style>(.*?)</style>', content, re.DOTALL)
styles = style_match.group(1) if style_match else ''

# Remove problematic CSS rules
styles = re.sub(r'\*\s*,\s*\*::before\s*,\s*\*::after\s*\{[^}]*\}', '', styles)
styles = re.sub(r'html[^}]*\}', '', styles)
styles = re.sub(r'body\s*\{[^}]*\}', '', styles)
styles = re.sub(r'\.container\s*\{[^}]*\}', '', styles)
styles = re.sub(r'h1\s*\{[^}]*\}', '', styles)
styles = re.sub(r'\.subtitle\s*\{[^}]*\}', '', styles)

# Extract content between <body> and </body>
body_match = re.search(r'<body>(.*?)</body>', content, re.DOTALL)
body_content = body_match.group(1) if body_match else ''

# Remove container wrapper
body_content = re.sub(r'^\s*<div class="container">', '', body_content)
body_content = re.sub(r'</div>\s*$', '', body_content)

# Remove h1 and subtitle
body_content = re.sub(r'<h1>.*?</h1>\s*', '', body_content, flags=re.DOTALL)
body_content = re.sub(r'<p class="subtitle">.*?</p>\s*', '', body_content, flags=re.DOTALL)

# Extract scripts
scripts = []
for script_match in re.finditer(r'<script>(.*?)</script>', content, re.DOTALL):
    script_content = script_match.group(1)
    if 'src=' not in content[script_match.start()-50:script_match.start()]:
        scripts.append(script_content)

# Build new template
new_template = '''{% extends "base.html" %}

{% block title %}請購調撥需求表 - 電腦舖{% endblock %}

{% block page_title %}請購調撥需求表{% endblock %}

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
with open('/Users/aiserver/.openclaw/workspace/dashboard-site/needs_input.html', 'w') as f:
    f.write(new_template)

print("Converted needs_input.html to Jinja2 template")
print(f"New size: {len(new_template)} bytes")