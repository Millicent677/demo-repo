"""
ASGI config for core project.
"""

import os
import django
import socketio

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.core.asgi import get_asgi_application
from tasks.notifications import sio

django_app = get_asgi_application()

# Create ASGI application with Socket.IO mounted at /socket.io
application = socketio.ASGIApp(
    socketio_server=sio,
    other_asgi_app=django_app,
    socketio_path='socket.io'
)
