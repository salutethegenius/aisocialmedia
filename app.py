import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from openai import OpenAI
import logging
from datetime import datetime
from sqlalchemy import func
import stripe
import threading
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "fallback_secret_key")

from models import Content, ScheduledPost

db.init_app(app)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY")
if not STRIPE_API_KEY or not STRIPE_PUBLISHABLE_KEY:
    raise ValueError("STRIPE_API_KEY or STRIPE_PUBLISHABLE_KEY environment variable is not set")
stripe.api_key = STRIPE_API_KEY

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
    try:
        content_id = request.json['content_id']
        scheduled_time = datetime.fromisoformat(request.json['scheduled_time'])
        platform = request.json['platform']
        
        content = Content.query.get(content_id)
        if not content:
            return jsonify({'error': 'Content not found'}), 404
        
        new_scheduled_post = ScheduledPost(content_id=content_id, scheduled_time=scheduled_time, platform=platform, status='pending')
        db.session.add(new_scheduled_post)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Post scheduled successfully', 'post_id': new_scheduled_post.id}), 200
    except KeyError as e:
        return jsonify({'error': f'Missing required field: {str(e)}'}), 400
    except ValueError as e:
        return jsonify({'error': f'Invalid data format: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error scheduling post: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@app.route('/get_scheduled_posts')
def get_scheduled_posts():
    try:
        scheduled_posts = ScheduledPost.query.all()
        posts_data = []

        for post in scheduled_posts:
            content = Content.query.get(post.content_id)
            if content:
                posts_data.append({
                    'id': post.id,
                    'content_id': post.content_id,
                    'topic': content.topic,
                    'scheduled_time': post.scheduled_time.isoformat(),
                    'platform': post.platform,
                    'status': post.status
                })

        return jsonify(posts_data)
    except Exception as e:
        logger.error(f"Error fetching scheduled posts: {str(e)}")
        return jsonify({'error': 'An error occurred while fetching scheduled posts'}), 500

@app.route('/project_summary')
def project_summary():
    total_credits = db.session.query(func.sum(Content.tokens_used)).scalar() or 0
    project_cost = total_credits * 0.05  # $0.05 per token
    return render_template('project_summary.html', total_credits=total_credits, project_cost=project_cost)

@app.route('/billing', methods=['GET', 'POST'])
def billing():
    if request.method == 'POST':
        try:
            total_credits = db.session.query(func.sum(Content.tokens_used)).scalar() or 0
            amount = int(total_credits * 5)  # $0.05 per token, convert to cents
            
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'unit_amount': amount,
                        'product_data': {
                            'name': 'AI Content Generation',
                            'description': f'Generated content with {total_credits} tokens',
                        },
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=request.host_url + url_for('thank_you', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=request.host_url + url_for('billing', _external=True),
                metadata={'total_credits': total_credits}
            )
            
            return jsonify({'id': checkout_session.id})
        except Exception as e:
            return str(e), 400
    
    total_credits = db.session.query(func.sum(Content.tokens_used)).scalar() or 0
    project_cost = total_credits * 0.05  # $0.05 per token
    
    return render_template('billing.html', total_credits=total_credits, project_cost=project_cost, STRIPE_PUBLISHABLE_KEY=STRIPE_PUBLISHABLE_KEY)

@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.environ.get('STRIPE_WEBHOOK_SECRET')
        )
    except ValueError as e:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        return 'Invalid signature', 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Update all pending scheduled posts to 'paid'
        with app.app_context():
            ScheduledPost.query.filter_by(status='pending').update({ScheduledPost.status: 'paid'})
            db.session.commit()

        logger.info(f"Updated scheduled posts to 'paid' for session {session.id}")

    return '', 200

@app.route('/thank_you')
def thank_you():
    session_id = request.args.get('session_id')
    if session_id:
        try:
            checkout_session = stripe.checkout.Session.retrieve(session_id)
            amount_paid = checkout_session.amount_total / 100  # Convert cents to dollars
            total_credits = checkout_session.metadata.get('total_credits', 0)
            return render_template('thank_you.html', amount_paid=amount_paid, total_credits=total_credits)
        except Exception as e:
            logger.error(f"Error retrieving checkout session: {str(e)}")
    
    return render_template('thank_you.html')

def simulate_posting():
    while True:
        with app.app_context():
            current_time = datetime.utcnow()
            posts_to_publish = ScheduledPost.query.filter(
                ScheduledPost.status == 'paid',
                ScheduledPost.scheduled_time <= current_time
            ).all()

            for post in posts_to_publish:
                # Simulate posting to the platform
                logger.info(f"Simulating post to {post.platform}: Content ID {post.content_id}")
                post.status = 'published'
                db.session.commit()

        time.sleep(60)  # Check every minute

if __name__ == '__main__':
    logger.info("Starting the application...")
    threading.Thread(target=simulate_posting, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
