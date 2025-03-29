# config.py
import os

# Базовая директория проекта
basedir = os.path.abspath(os.path.dirname(__file__))
# Директория для данных (БД, JSON)
datadir = os.path.join(basedir, 'data')

# Убедимся, что папка data существует
if not os.path.exists(datadir):
    os.makedirs(datadir)

class Config:
    """Базовый класс конфигурации."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess' # Важно для сессий, форм и т.д.
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_AS_ASCII = False # Чтобы русские буквы в JSON ответах были читаемы

class DevelopmentConfig(Config):
    """Конфигурация для разработки."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(datadir, 'challenges.db')

class ProductionConfig(Config):
    """Конфигурация для продакшена."""
    DEBUG = False
    # Для продакшена лучше использовать PostgreSQL или MySQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(datadir, 'challenges_prod.db')
    # Здесь можно добавить другие настройки для продакшена

# Словарь для выбора конфигурации по имени
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}