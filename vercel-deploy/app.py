from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os

# Create app
app = Flask(__name__)

# Use the Supabase connection string from Vercel environment variables
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:xe2Gyu!56h6tWQD@db.ndiwwxpixxwwbkpdmmqq.supabase.co:5432/postgres')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', '12345678900987654321')

# Initialize database
db = SQLAlchemy(app)

# Define models inline to avoid dependencies
class Agent(db.Model):
    __tablename__ = 'agent'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    division = db.Column(db.String(100), nullable=False)
    manager = db.Column(db.String(100), nullable=False)
    queue_type = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DailyPerformance(db.Model):
    __tablename__ = 'daily_performance'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey('agent.id'), nullable=False)
    leads_taken = db.Column(db.Float, nullable=False)
    close_rate = db.Column(db.Float, nullable=False)
    avg_premium = db.Column(db.Float, nullable=False)
    place_rate = db.Column(db.Float, nullable=False)
    placed_premium_per_lead = db.Column(db.Float)
    total_daily_premium = db.Column(db.Float)
    sales_made = db.Column(db.Integer)
    talk_time_minutes = db.Column(db.Integer)
    notes = db.Column(db.Text)

    def calculate_ppl(self):
        """Calculate Placed Premium per Lead"""
        return (self.close_rate / 100) * (self.place_rate / 100) * self.avg_premium

class APIKey(db.Model):
    __tablename__ = 'api_key'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

# Just a minimal index page
@app.route('/')
def index():
    return jsonify({
        "status": "ok",
        "message": "CAP API is running",
        "endpoints": [
            "/api/agents",
            "/api/agent_details/<agent_id>"
        ]
    })

# API routes
@app.route('/api/agents', methods=['GET'])
def get_agents():
    agents = Agent.query.all()
    return jsonify([{
        'id': agent.id,
        'name': agent.name,
        'division': agent.division,
        'manager': agent.manager,
        'queue_type': agent.queue_type,
        'is_active': agent.is_active
    } for agent in agents])

@app.route('/api/agent_details/<int:agent_id>')
def get_agent_details(agent_id):
    agent = Agent.query.get_or_404(agent_id)
    performances = DailyPerformance.query.filter(
        DailyPerformance.agent_id == agent_id
    ).order_by(DailyPerformance.date).all()

    daily_data = [{
        'date': perf.date.strftime('%Y-%m-%d'),
        'leads': perf.leads_taken,
        'close_rate': perf.close_rate,
        'place_rate': perf.place_rate,
        'avg_premium': perf.avg_premium,
        'ppl': perf.calculate_ppl()
    } for perf in performances]

    return jsonify({
        'agent': {
            'name': agent.name,
            'division': agent.division,
            'manager': agent.manager,
            'queue_type': agent.queue_type
        },
        'performance_data': daily_data
    })

# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})

# Main entrypoint
if __name__ == '__main__':
    app.run() 