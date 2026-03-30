import multiprocessing
import os

# Worker 數量
workers = 4
worker_class = "gthread"
threads = 4

# 綁定
bind = "127.0.0.1:3000"  # 正式環境用 3000

# Timeout（秒）- SSE 串流需要較長 timeout
timeout = 180
keepalive = 5

# 日誌目錄
log_dir = "/Users/aiserver/srv/logs"
os.makedirs(log_dir, exist_ok=True)

# 日誌檔案
accesslog = os.path.join(log_dir, "gunicorn_access.log")
errorlog = os.path.join(log_dir, "gunicorn_error.log")
loglevel = "info"

# 程序名稱
proc_name = "dashboard_site"

# 重新啟動前處理的最大請求數（防記憶體洩漏）
max_requests = 1000
max_requests_jitter = 50

# 前置處理（載入環境）
def on_starting(server):
    """伺服器啟動前執行"""
    print("[Gunicorn] 正在啟動 Dashboard Site...")

def on_reload(server):
    """重新載入時執行"""
    print("[Gunicorn] 重新載入設定...")
