# app/main/__init__.py
# Удалили: from flask import Blueprint
# Удалили: main = Blueprint('main', __name__)
# Удалили: from . import routes

# Импортируем Blueprint ИЗ routes.py
from .routers import main