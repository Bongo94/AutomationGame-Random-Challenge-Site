# app.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

# Определяем базовую директорию проекта
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)

# Конфигурация для SQLAlchemy
# Указываем путь к файлу базы данных SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data', 'challenges.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Отключаем ненужное отслеживание

# Создаем папку data, если её нет
if not os.path.exists(os.path.join(basedir, 'data')):
    os.makedirs(os.path.join(basedir, 'data'))

# Инициализируем расширение SQLAlchemy
db = SQLAlchemy(app)

# --- Модели данных будут здесь ---

# --- Маршруты Flask будут здесь ---


# app.py (продолжение)

# Модель для Категорий (bodies, classifications, etc.)
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False) # Имя категории (e.g., 'bodies')
    # Связь с возможными значениями для этой категории
    values = db.relationship('Value', backref='category', lazy=True)

    def __repr__(self):
        return f'<Category {self.name}>'

# Модель для Значений внутри категорий (e.g., 'Седан (до 2.5)', 'Ралли', 100, 'AWD')
class Value(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value_str = db.Column(db.String(120), nullable=False) # Само значение как строка
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    # Можно добавить поле для веса, если нужно для random.choices
    # weight = db.Column(db.Float, default=1.0)

    def __repr__(self):
        return f'<Value {self.value_str} (Category ID: {self.category_id})>'

# Модель для Шаблонов (пока упрощенная)
# Будем хранить конфигурацию правил в JSON-поле для гибкости на старте
class Template(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(250))
    # Храним правила как JSON: {'category_id': {'count': 1, 'type': 'random', 'values': [val_id1, val_id2]...}, ...}
    # Или проще: {'category_name': {'count': 1, ...}, ...} - может быть удобнее
    config_json = db.Column(db.Text, nullable=False) # Используем Text для хранения JSON строки

    def __repr__(self):
        return f'<Template {self.name}>'

if __name__ == '__main__':
    # Создаем таблицы перед первым запуском (если их нет)
    # Важно: делать это внутри `with app.app_context():`
    with app.app_context():
        db.create_all()
    app.run(debug=True) # debug=True удобно для разработки