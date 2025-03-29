# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import config # Импортируем наш конфиг

# Инициализируем расширения глобально, но без привязки к приложению
db = SQLAlchemy()

def create_app(config_name='default'):
    """Фабрика для создания экземпляра приложения Flask."""
    app = Flask(__name__)
    app.config.from_object(config[config_name]) # Загружаем конфиг

    # Инициализируем расширения с созданным приложением
    db.init_app(app)

    # Регистрация Blueprints
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # Здесь можно добавить другие Blueprint'ы (например, для API, админки)

    return app