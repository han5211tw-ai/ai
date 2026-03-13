#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/aiserver/.openclaw/workspace/dashboard-site')

from app import app

# 啟動 Flask
app.run(host='0.0.0.0', port=3000, debug=False, use_reloader=False, threaded=True)