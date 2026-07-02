"""
WSGI config for Report Card Generator project.
"""

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DJANGO_APP_DIR = ROOT_DIR / 'django_app'

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(DJANGO_APP_DIR) not in sys.path:
    sys.path.append(str(DJANGO_APP_DIR))

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
