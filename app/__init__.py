# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate  # <-- Убедись, что этот импорт есть
from config import config

db = SQLAlchemy()
migrate = Migrate()  # <-- Убедись, что этот экземпляр создается

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)  # <-- Убедись, что эта строка вызывается ПОСЛЕ db.init_app()

    # Исправленный импорт Blueprint
    from .main.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app