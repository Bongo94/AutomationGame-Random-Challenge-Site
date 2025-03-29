# app/models.py
from . import db # Импортируем db из app/__init__.py
import json

# Модель для Категорий
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    # Связь с возможными значениями
    values = db.relationship('Value', backref='category', lazy='joined', cascade="all, delete-orphan") # Изменили lazy='dynamic' на lazy='joined' (или просто убрать lazy, 'select' по умолчанию)
    # Добавим описание категории, может пригодиться
    description = db.Column(db.String(200))

    def __repr__(self):
        return f'<Category {self.name}>'

# Модель для Значений внутри категорий
class Value(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value_str = db.Column(db.String(120), nullable=False) # Значение как строка
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    # Поля для расширенной логики (можно добавить позже)
    # weight = db.Column(db.Float, default=1.0)
    # is_default = db.Column(db.Boolean, default=True) # Можно ли использовать по умолчанию

    def __repr__(self):
        return f'<Value {self.value_str} (Category: {self.category.name})>'

# Модель для Шаблонов
class Template(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(250))
    # Храним правила как JSON строку
    config_json = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<Template {self.name}>'

    # Свойство для удобного доступа к конфигу как к словарю
    @property
    def config(self):
        try:
            return json.loads(self.config_json)
        except json.JSONDecodeError:
            return {} # Возвращаем пустой словарь в случае ошибки

    @config.setter
    def config(self, value):
        self.config_json = json.dumps(value, ensure_ascii=False, indent=2) # Сохраняем красиво