"""Production entry point:  gunicorn wsgi:app"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
from app import create_app  # noqa: E402

app = create_app()
