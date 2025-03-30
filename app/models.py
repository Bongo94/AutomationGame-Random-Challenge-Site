# app/models.py
from . import db
import json

# Модель для Категорий
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    # Связь с возможными значениями
    values = db.relationship('Value', backref='category', lazy='joined', cascade="all, delete-orphan")
    description = db.Column(db.String(200)) # Описание самой категории

    def __repr__(self):
        return f'<Category {self.name}>'

# Модель для Значений внутри категорий
class Value(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # --- ИЗМЕНЕНИЕ: Разделяем значение и описание ---
    value_core = db.Column(db.String(120), nullable=False) # Основное значение (e.g., "$20000")
    description = db.Column(db.Text, nullable=True) # Описание (e.g., "Можно позволить...")
    # value_str = db.Column(db.String(120), nullable=False) # <-- Удаляем или оставляем для совместимости? Лучше удалить.
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)

    def __repr__(self):
        # Обновляем repr для отображения нового поля
        return f'<Value {self.value_core} (Category: {self.category.name})>'

# Модель для Шаблонов (без изменений)
class Template(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(250))
    config_json = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<Template {self.name}>'

    @property
    def config(self):
        try:
            return json.loads(self.config_json)
        except json.JSONDecodeError:
            return {}

    @config.setter
    def config(self, value):
        self.config_json = json.dumps(value, ensure_ascii=False, indent=2)