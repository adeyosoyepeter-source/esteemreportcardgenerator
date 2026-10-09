"""Allow the Django config package to be imported from the repository root."""

import sys
from pathlib import Path


_DJANGO_APP_DIR = Path(__file__).resolve().parent.parent / "django_app"
_DJANGO_CONFIG_DIR = _DJANGO_APP_DIR / "config"

if str(_DJANGO_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_DJANGO_APP_DIR))

__path__.append(str(_DJANGO_CONFIG_DIR))
