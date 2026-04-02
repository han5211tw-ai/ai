#!/usr/bin/env python3
"""Convert needs_input.html to Jinja2 template while preserving all functionality"""

import re

with open('/Users/aiserver/.openclaw/workspace/dashboard-site/needs_input.html', 'r') as f:
    content = f.read()

# Extract styles
style_match = re.search(r'<style>(.*?)</style>', content, re.DOTALL)
styles = style_match.group(1) if style_match else ''

# Clean up styles - remove only conflicting global rules
styles = re.sub(r'\*\s*,\s*\*::before\s*,\s*\*::after\s*\{[^}]*\}', '', styles)
styles = re.sub(r'html\s*\{[^}]*\}', '', styles)
styles = re.sub(r'body\s*\{[^}]*\}', '', styles)

# Extract body content
body_match = re.search(r'<body>(.*?)</body>', content, re.DOTALL)
body_content = body_match.group(1) if body_match else ''

# Remove container wrapper but keep all inner content
body_content = re.sub(r'^\s*<div class="container">\s*', '', body_content)
body_content = re.sub(r'\s*</div>\s*$', '', body_content)

# Remove h1 and subtitle (page title is in base.html)
body_content = re.sub(r'<h1>.*?</h1>\s*', '', body_content, flags=re.DOTALL)
body_content = re.sub(r'<p class="subtitle">.*?</p>\s*', '', body_content, flags=re.DOTALL)

# Remove the old login section (base.html handles auth)
body_content = re.sub(r'<div class="login-section[^"]*"[^>]*>.*?</div>\s*', '', body_content, flags=re.DOTALL)

# Extract scripts (excluding external src)
scripts = []
for script_match in re.finditer(r'<script>(.*?)</script>', content, re.DOTALL):
    script_content = script_match.group(1)
    if 'src=' not in content[script_match.start()-50:script_match.start()]:
        # Remove the old DOMContentLoaded login handler
        if 'requireLogin' not in script_content or 'window.onLoginSuccess' in script_content:
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
window.version='20250301-0200';

// 頁面登入成功後的處理
window.onLoginSuccess = function(user) {
    console.log('[NeedsInput] Login success:', user);
    currentUser = user;
    
    // 顯示表單
    document.getElementById('formSection').style.display = 'block';
    document.getElementById('userName').textContent = user.name;
    document.getElementById('userDept').textContent = user.department;
    
    // 莊圍迪特殊處理
    if (user.name === '莊圍迪') {
        document.getElementById('storeSelectorContainer').style.display = 'inline';
        document.getElementById('supervisorStoreSelect').value = '豐原門市';
    } else {
        document.getElementById('storeSelectorContainer').style.display = 'none';
    }
    
    // 初始化表單
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('requestDate').value = today;
    for (let i = 0; i < 5; i++) addProductRow();
    initTransferSelect();
    loadRecentSubmissions();
    loadHistory();
};

''' + '\n\n'.join(scripts) + '''
</script>
{% endblock %}
'''

# Write the new template
with open('/Users/aiserver/.openclaw/workspace/dashboard-site/needs_input.html', 'w') as f:
    f.write(new_template)

print("Converted successfully!")
print(f"Output size: {len(new_template)} bytes")