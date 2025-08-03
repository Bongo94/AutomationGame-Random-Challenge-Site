import os

basedir = os.path.abspath(os.path.dirname(__file__))
datadir = os.path.join(basedir, 'data')

if not os.path.exists(datadir):
    os.makedirs(datadir)

class Config:
    """Базовый класс конфигурации."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_AS_ASCII = False

class DevelopmentConfig(Config):
    """Конфигурация для разработки."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(datadir, 'challenges.db')

class ProductionConfig(Config):
    """Конфигурация для продакшена."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(datadir, 'challenges_prod.db')

# Словарь для выбора конфигурации по имени
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}