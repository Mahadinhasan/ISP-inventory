import multiprocessing

# The socket to bind
bind = "unix:/home/ibccl/webserver/mysite/mysite.sock"

# Number of worker processes
workers = multiprocessing.cpu_count() * 2 + 1

# Use Uvicorn workers for ASGI support (required for Django Channels/WebSockets)
worker_class = "uvicorn.workers.UvicornWorker"

# Logging setup
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"

# Maximum number of pending connections
backlog = 2048

# Workers silent for more than this many seconds are killed and restarted
timeout = 120
