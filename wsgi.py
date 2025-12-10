# /home/gauravwhy/Lqink_bot/wsgi.py (FINAL & CLEAN for Railway)

import sys
from main import create_app

# application variable jise gunicorn dekhta hai.
# Railway yahan se Flask application ko load karega.
application = create_app()
