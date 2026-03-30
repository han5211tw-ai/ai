import os

workers     = 4
worker_class = "gthread"
threads     = 4

bind        = "127.0.0.1:8800"

timeout     = 120
keepalive   = 5

log_dir = "/Users/aiserver/srv/logs"
os.makedirs(log_dir, exist_ok=True)

accesslog = os.path.join(log_dir, "erp_v2_access.log")
errorlog  = os.path.join(log_dir, "erp_v2_error.log")
loglevel  = "info"

proc_name    = "erp_v2"
max_requests = 1000
max_requests_jitter = 50

def on_starting(server):
    print("[ERP v2] 啟動中，port 8800…")
