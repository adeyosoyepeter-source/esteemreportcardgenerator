"""
WSGI config for Report Card Generator project.
"""

import os
import sys
from pathlib import Path

# Add django_app to path so config module can be found from anywhere
django_app_dir = Path(__file__).resolve().parent.parent
if str(django_app_dir) not in sys.path:
    sys.path.insert(0, str(django_app_dir))

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
