from datetime import datetime
from expenses_tracker import db, login_manager
from flask_login import UserMixin
from sqlalchemy.sql import func

# Automatically set timezone to UTC for consistency

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# User Model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    image = db.Column(db.String(20), nullable=False, default='default.jpg')
    categories = db.relationship('Category', backref='owner', lazy=True)
    incomes = db.relationship('Income', backref='user', lazy=True)
    expenses = db.relationship('Expense', backref='user', lazy=True)

    def __repr__(self):
        return f"User('{self.username}')"

# Topic Model
class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    type = db.Column(db.Enum('income', 'expense', name='topic_type'), nullable=False)

    def __repr__(self):
        return f"Topic('{self.name}', '{self.type}')"

# Category Model
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.Enum('income', 'expense', name='category_type'), nullable=False)
    description = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Changed to nullable=True
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())

    topic = db.relationship('Topic', backref='categories', lazy=True)

    def __repr__(self):
        return f"Category('{self.name}', '{self.type}')"

# Income Model
class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())

    def __repr__(self):
        return f"Income('{self.amount}', '{self.date}')"

# Expense Model
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=func.now(), server_default=func.now())

    category = db.relationship('Category', backref='expenses', lazy=True)

    def __repr__(self):
        return f"Expense('{self.amount}', '{self.date}')"

