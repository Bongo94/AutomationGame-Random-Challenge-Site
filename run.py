# run.py
import os
from app import create_app, db # Импортируем фабрику и db
# Импортируем модели, чтобы Alembic (если будем использовать) их видел
from app.models import Category, Value, Template

# Получаем имя конфигурации из переменной окружения или используем 'default'
config_name = os.getenv('FLASK_CONFIG') or 'default'
app = create_app(config_name)

# Здесь можно настроить Flask CLI команды, например, для миграций
# @app.shell_context_processor
# def make_shell_context():
#     return dict(db=db, Category=Category, Value=Value, Template=Template)

if __name__ == '__main__':
    # Запускаем приложение Flask
    # Хост 0.0.0.0 делает его доступным извне (например, для Docker или на хостинге)
    app.run(host='0.0.0.0')