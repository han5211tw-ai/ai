#!/opt/homebrew/bin/python3
import http.server
import socketserver
import os

PORT = 3344
DIRECTORY = "/Users/aiserver/.openclaw/workspace/dashboard-site"

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}")

os.chdir(DIRECTORY)

with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
    print(f"🚀 營運看板已啟動！")
    print(f"📊 請訪問: http://localhost:{PORT}")
    print(f"💻 或: http://127.0.0.1:{PORT}")
    print(f"🛑 按 Ctrl+C 停止服務")
    print("-" * 50)
    httpd.serve_forever()