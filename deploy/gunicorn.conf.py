# Gunicorn config for ytclip
bind = "127.0.0.1:5000"
workers = 2
threads = 2
timeout = 300  # 5 min for long downloads
graceful_timeout = 60
max_requests = 100
max_requests_jitter = 20
accesslog = "/var/log/ytclip_access.log"
errorlog = "/var/log/ytclip_error.log"
capture_output = True
