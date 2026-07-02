#!/bin/bash
cd "$(dirname "$0")"
gunicorn config.wsgi --bind 0.0.0.0:${PORT:-8000}
