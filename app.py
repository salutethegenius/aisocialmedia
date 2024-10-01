import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from openai import OpenAI
import logging
from datetime import datetime
from sqlalchemy import func
import stripe

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
    return redirect(url_for('project_summary'))

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
                success_url=request.host_url + url_for('thank_you'),
                cancel_url=request.host_url + url_for('billing'),
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
        # Invalid payload
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return 'Invalid signature', 400

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # Here you can update your database to mark the payment as completed
        # For example, update the ScheduledPost status to 'paid'
        # You may need to store the Stripe session ID with the ScheduledPost to link them

    return '', 200

@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html')

if __name__ == '__main__':
    logger.info("Starting the application...")
    app.run(host='0.0.0.0', port=5000)
