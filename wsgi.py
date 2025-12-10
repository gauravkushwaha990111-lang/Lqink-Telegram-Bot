# /home/gauravwhy/Lqink_bot/wsgi.py (FINAL)

import sys
from main import create_app

# Project directory ko sys.path mein jodna (Optional, but safe)
project_home = '/home/gauravwhy/Lqink_bot' 
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# application variable jise gunicorn dekhta hai
application = create_app()
