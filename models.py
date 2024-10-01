from app import db
from werkzeug.security import generate_password_hash
from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    twitter_token = db.Column(db.String(256))
    twitter_token_secret = db.Column(db.String(256))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    tone = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    tokens_used = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

class ScheduledPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    content = db.relationship('Content', backref='scheduled_posts')
    user = db.relationship('User', backref='scheduled_posts')
