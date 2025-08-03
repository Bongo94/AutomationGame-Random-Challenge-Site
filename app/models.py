from . import db
import json

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    values = db.relationship('Value', backref='category', lazy='joined', cascade="all, delete-orphan")
    description = db.Column(db.String(200))
    display_group = db.Column(db.String(100), nullable=True, index=True)


    def __repr__(self):
        return f'<Category {self.name} (Group: {self.display_group})>'

class Value(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value_core = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)

    def __repr__(self):
        return f'<Value {self.value_core} (Category: {self.category.name})>'

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