from app import db
from datetime import datetime

class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(200), nullable=False)
    tone = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    tokens_used = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

class ScheduledPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    content = db.relationship('Content', backref='scheduled_posts')
