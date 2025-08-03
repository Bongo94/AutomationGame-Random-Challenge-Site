from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data', 'challenges.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

if not os.path.exists(os.path.join(basedir, 'data')):
    os.makedirs(os.path.join(basedir, 'data'))

db = SQLAlchemy(app)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    values = db.relationship('Value', backref='category', lazy=True)

    def __repr__(self):
        return f'<Category {self.name}>'

class Value(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value_str = db.Column(db.String(120), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)


    def __repr__(self):
        return f'<Value {self.value_str} (Category ID: {self.category_id})>'

class Template(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(250))
    config_json = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<Template {self.name}>'

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)