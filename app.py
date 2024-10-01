import os
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from openai import OpenAI
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")

from models import Content, ScheduledPost

db.init_app(app)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    contents = Content.query.all()
    scheduled_posts = ScheduledPost.query.all()
    return render_template('dashboard.html', contents=contents, scheduled_posts=scheduled_posts)

@app.route('/generate_content', methods=['POST'])
def generate_content():
    topic = request.json['topic']
    tone = request.json['tone']
    
    prompt = f"Generate content about {topic} in a {tone} tone."
    
    try:
        completion = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200
        )
        content = completion.choices[0].message.content
        tokens_used = completion.usage.total_tokens
        
        new_content = Content(topic=topic, tone=tone, content=content, tokens_used=tokens_used)
        db.session.add(new_content)
        db.session.commit()
        
        return jsonify({'content': content, 'tokens_used': tokens_used, 'id': new_content.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/update_content', methods=['POST'])
def update_content():
    content_id = request.json['id']
    updated_content = request.json['content']
    
    content = Content.query.get(content_id)
    if content:
        content.content = updated_content
        db.session.commit()
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Content not found'}), 404

@app.route('/schedule_post', methods=['POST'])
def schedule_post():
    # Dummy response
    return jsonify({'success': True, 'message': 'Post scheduled successfully. Proceeding to billing.'})

@app.route('/get_scheduled_posts')
def get_scheduled_posts():
    scheduled_posts = ScheduledPost.query.all()
    posts_data = []

    for post in scheduled_posts:
        posts_data.append({
            'id': post.id,
            'content_id': post.content_id,
            'scheduled_time': post.scheduled_time.isoformat(),
            'platform': post.platform,
            'status': post.status
        })

    return jsonify(posts_data)

if __name__ == '__main__':
    logger.info("Starting the application...")
    app.run(host='0.0.0.0', port=5000)
