import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI
import secrets
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.secret_key = secrets.token_hex(16)
db.init_app(app)

# OpenAI setup
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

from models import User, Content

with app.app_context():
    db.create_all()

def create_test_user():
    with app.app_context():
        test_user = User.query.filter_by(username='testuser').first()
        if not test_user:
            test_user = User(username='testuser', email='testuser@example.com')
            test_user.set_password('testpassword')
            db.session.add(test_user)
            db.session.commit()
            logger.info("Test user created successfully.")
            logger.info(f"Username: {test_user.username}")
            logger.info(f"Email: {test_user.email}")
            logger.info(f"Password hash: {test_user.password_hash}")
        else:
            logger.info("Test user already exists.")
            logger.info(f"Username: {test_user.username}")
            logger.info(f"Email: {test_user.email}")
            logger.info(f"Password hash: {test_user.password_hash}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        logger.info(f"Login attempt - Username: {username}")
        if user:
            logger.info(f"User found - Username: {user.username}, Email: {user.email}")
            logger.info(f"Stored password hash: {user.password_hash}")
            if check_password_hash(user.password_hash, password):
                logger.info("Password check successful")
                session['user_id'] = user.id
                return redirect(url_for('dashboard'))
            else:
                logger.info("Password check failed")
        else:
            logger.info("User not found")
        return render_template('login.html', error='Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    contents = Content.query.filter_by(user_id=user.id).all()
    return render_template('dashboard.html', user=user, contents=contents)

@app.route('/generate_content', methods=['POST'])
def generate_content():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    topic = request.json['topic']
    tone = request.json['tone']
    
    prompt = f"Generate content about {topic} in a {tone} tone."
    
    try:
        completion = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200
        )
        content = completion.choices[0].message.content
        tokens_used = completion.usage.total_tokens
        
        new_content = Content(user_id=session['user_id'], topic=topic, tone=tone, content=content, tokens_used=tokens_used)
        db.session.add(new_content)
        db.session.commit()
        
        return jsonify({'content': content, 'tokens_used': tokens_used, 'id': new_content.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/update_content', methods=['POST'])
def update_content():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    content_id = request.json['id']
    updated_content = request.json['content']
    
    content = Content.query.get(content_id)
    if content and content.user_id == session['user_id']:
        content.content = updated_content
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'error': 'Content not found or unauthorized'}), 404

if __name__ == '__main__':
    logger.info("Starting the application...")
    create_test_user()
    app.run(host='0.0.0.0', port=5000)
