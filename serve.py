import os
from waitress import serve
from app import app

port = int(os.environ.get('HTTP_PLATFORM_PORT', 5001))
serve(app, host='127.0.0.1', port=port)
