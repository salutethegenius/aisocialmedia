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

def test_db_connection():
    try:
        with app.app_context():
            db.session.execute('SELECT 1')
        logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")

def create_user():
    with app.app_context():
        logger.info(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
        logger.info("Attempting to create user...")
        try:
            user = User.query.filter_by(username='ken').first()
            if not user:
                user = User(username='ken', email='ken@example.com')
                user.set_password('1234')
                db.session.add(user)
                db.session.commit()
                logger.info("User created successfully.")
            else:
                logger.info("User already exists.")
            logger.info(f"Username: {user.username}")
            logger.info(f"Email: {user.email}")
            logger.info(f"Password hash: {user.password_hash}")
        except Exception as e:
            logger.error(f"Error creating/retrieving user: {str(e)}")

def print_all_users():
    with app.app_context():
        logger.info("Printing all users in the database:")
        users = User.query.all()
        for user in users:
            logger.info(f"User ID: {user.id}, Username: {user.username}, Email: {user.email}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        logger.info(f"Login attempt - Username: {username}")
        logger.info(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
        
        try:
            user = User.query.filter_by(username=username).first()
            logger.info(f"Database query result: {user}")
            
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
        except Exception as e:
            logger.error(f"Error during login process: {str(e)}")
        
        return render_template('login.html', error='Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    # Temporary: Create a sample user and content for demonstration
    user = User(username='Demo User', email='demo@example.com')
    contents = [
        Content(topic='AI in Healthcare', tone='Informative', content='AI is revolutionizing healthcare...', tokens_used=100),
        Content(topic='Sustainable Energy', tone='Professional', content='Renewable energy sources are becoming...', tokens_used=120)
    ]
    return render_template('dashboard.html', user=user, contents=contents)

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
        
        return jsonify({'content': content, 'tokens_used': tokens_used, 'id': 0})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/update_content', methods=['POST'])
def update_content():
    content_id = request.json['id']
    updated_content = request.json['content']
    
    # For demonstration, just return success without actually updating anything
    return jsonify({'success': True})

if __name__ == '__main__':
    logger.info("Starting the application...")
    test_db_connection()
    create_user()
    print_all_users()
    app.run(host='0.0.0.0', port=5000)
