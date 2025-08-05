# Configuración de Gunicorn para evitar timeouts
import multiprocessing
import os

# Configuración básica
bind = "0.0.0.0:8080"

# Configuración de workers más conservadora para Heroku
# Heroku tiene limitaciones de memoria, usar menos workers
workers = int(os.environ.get('WEB_CONCURRENCY', 2))
worker_class = "sync"
worker_connections = 1000

# Configuración de timeouts
timeout = 120
keepalive = 2
max_requests = 1000
max_requests_jitter = 100

# Configuración de logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Configuración de procesos
preload_app = True
reload = False

# Configuración de seguridad
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190 