import multiprocessing

# The socket to bind
bind = "0.0.0.0:8000"

# Number of worker processes
workers = multiprocessing.cpu_count() * 2 + 1

# Use Uvicorn workers for ASGI support (required for Django Channels/WebSockets)
worker_class = "uvicorn.workers.UvicornWorker"

# Logging setup
accesslog = "-"  # Output to stdout
errorlog = "-"   # Output to stderr
loglevel = "info"

# Maximum number of pending connections
backlog = 2048

# Workers silent for more than this many seconds are killed and restarted
timeout = 120
