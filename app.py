import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI
import secrets
import logging
from requests_oauthlib import OAuth1Session
import tweepy
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.secret_key = secrets.token_hex(16)
db.init_app(app)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY")
TWITTER_API_SECRET = os.environ.get("TWITTER_API_SECRET")
TWITTER_CALLBACK_URL = "http://localhost:5000/twitter/callback"

from models import User, Content, ScheduledPost

with app.app_context():
    db.create_all()

jobstores = {
    'default': SQLAlchemyJobStore(url=app.config["SQLALCHEMY_DATABASE_URI"])
}
scheduler = BackgroundScheduler(jobstores=jobstores)
scheduler.start()

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

def post_scheduled_content(scheduled_post_id):
    with app.app_context():
        scheduled_post = ScheduledPost.query.get(scheduled_post_id)
        if scheduled_post and scheduled_post.status == 'pending':
            user = User.query.get(scheduled_post.user_id)
            content = Content.query.get(scheduled_post.content_id)

            if scheduled_post.platform == 'twitter':
                if user.twitter_token and user.twitter_token_secret:
                    auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
                    auth.set_access_token(user.twitter_token, user.twitter_token_secret)
                    api = tweepy.API(auth)
                    try:
                        api.update_status(content.content[:280])
                        scheduled_post.status = 'posted'
                        db.session.commit()
                        logger.info(f"Posted scheduled content {scheduled_post_id} to Twitter")
                    except Exception as e:
                        logger.error(f"Error posting to Twitter: {str(e)}")
                        scheduled_post.status = 'failed'
                        db.session.commit()
                else:
                    logger.error(f"User {user.id} has not connected their Twitter account")
                    scheduled_post.status = 'failed'
                    db.session.commit()
            else:
                logger.error(f"Unsupported platform: {scheduled_post.platform}")
                scheduled_post.status = 'failed'
                db.session.commit()

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
    # Temporarily bypass login check
    # if 'user_id' not in session:
    #     return redirect(url_for('login'))
    
    # Temporary user for testing
    user = User.query.first()
    if not user:
        user = User(username='test_user', email='test@example.com')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()

    contents = Content.query.filter_by(user_id=user.id).all()
    scheduled_posts = ScheduledPost.query.filter_by(user_id=user.id).all()
    return render_template('dashboard.html', user=user, contents=contents, scheduled_posts=scheduled_posts)

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
    
    return jsonify({'success': True})

@app.route('/twitter/login')
def twitter_login():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    oauth = OAuth1Session(TWITTER_API_KEY, client_secret=TWITTER_API_SECRET)
    try:
        resp = oauth.fetch_request_token("https://api.twitter.com/oauth/request_token")
        authorization_url = oauth.authorization_url("https://api.twitter.com/oauth/authorize")
        session['request_token'] = resp.get('oauth_token')
        session['request_token_secret'] = resp.get('oauth_token_secret')
        return redirect(authorization_url)
    except Exception as e:
        logger.error(f"Error during Twitter OAuth: {str(e)}")
        return redirect(url_for('dashboard'))

@app.route('/twitter/callback')
def twitter_callback():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    request_token = session.get('request_token')
    request_token_secret = session.get('request_token_secret')
    
    oauth = OAuth1Session(
        TWITTER_API_KEY,
        client_secret=TWITTER_API_SECRET,
        resource_owner_key=request_token,
        resource_owner_secret=request_token_secret
    )
    
    try:
        oauth_tokens = oauth.fetch_access_token("https://api.twitter.com/oauth/access_token")
        session['twitter_token'] = oauth_tokens.get('oauth_token')
        session['twitter_token_secret'] = oauth_tokens.get('oauth_token_secret')
        
        user = User.query.get(session['user_id'])
        user.twitter_token = session['twitter_token']
        user.twitter_token_secret = session['twitter_token_secret']
        db.session.commit()
        
        return redirect(url_for('dashboard'))
    except Exception as e:
        logger.error(f"Error during Twitter OAuth callback: {str(e)}")
        return redirect(url_for('dashboard'))

@app.route('/schedule_post', methods=['POST'])
def schedule_post():
    # Temporarily bypass login check
    # if 'user_id' not in session:
    #     return jsonify({'error': 'User not logged in'}), 401

    # Use the temporary user for testing
    user = User.query.first()
    if not user:
        return jsonify({'error': 'No user found'}), 404

    content_id = request.json['content_id']
    scheduled_time = datetime.fromisoformat(request.json['scheduled_time'])
    platform = request.json['platform']

    scheduled_post = ScheduledPost(
        user_id=user.id,
        content_id=content_id,
        scheduled_time=scheduled_time,
        platform=platform
    )

    db.session.add(scheduled_post)
    db.session.commit()

    scheduler.add_job(
        post_scheduled_content,
        'date',
        run_date=scheduled_time,
        args=[scheduled_post.id],
        id=f'post_{scheduled_post.id}',
        replace_existing=True
    )

    return jsonify({'success': True, 'id': scheduled_post.id})

@app.route('/get_scheduled_posts')
def get_scheduled_posts():
    # Temporarily bypass login check
    # if 'user_id' not in session:
    #     return jsonify({'error': 'User not logged in'}), 401

    # Use the temporary user for testing
    user = User.query.first()
    if not user:
        return jsonify({'error': 'No user found'}), 404

    scheduled_posts = ScheduledPost.query.filter_by(user_id=user.id).all()
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
    test_db_connection()
    create_user()
    print_all_users()
    app.run(host='0.0.0.0', port=5000)