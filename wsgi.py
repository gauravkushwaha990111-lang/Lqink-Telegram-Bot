# CODE B: /home/gauravwhy/Lqink_bot/wsgi.py

import sys
# main.py से create_app function import kiya
from main import create_app

# Apne username aur project folder ke naam ka upyog karen
USERNAME = 'gauravwhy' 
PROJECT_FOLDER = 'Lqink_bot' 

# Project directory ko Python path mein jodna
project_home = f'/home/{USERNAME}/{PROJECT_FOLDER}'

if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Flask application ko create_app() function call se lena
application = create_app()