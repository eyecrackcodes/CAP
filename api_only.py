from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime

# Create a minimal Flask API app for Vercel
app = Flask(__name__)

# Database configuration - Use environment variables for Vercel deployment
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:xe2Gyu!56h6tWQD@db.ndiwwxpixxwwbkpdmmqq.supabase.co:5432/postgres')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure secret key for sessions
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', '12345678900987654321')

# Initialize the database
db = SQLAlchemy(app)

# Define minimal models
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

# Basic API routes
@app.route('/api/health')
def health_check():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})

@app.route('/api/agents')
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

@app.route('/api/agents/<int:agent_id>')
def get_agent(agent_id):
    agent = Agent.query.get_or_404(agent_id)
    return jsonify({
        'id': agent.id,
        'name': agent.name,
        'division': agent.division,
        'manager': agent.manager,
        'queue_type': agent.queue_type,
        'is_active': agent.is_active
    })

@app.route('/api/redirected')
def api_redirected():
    return jsonify({
        "message": "You've been redirected to the API-only version. Full app features are not available in this deployment.",
        "status": "API_ONLY"
    })

@app.route('/')
def index():
    return jsonify({
        "message": "This is a minimal API deployment for Vercel. Please use the /api/* endpoints only.",
        "available_endpoints": [
            "/api/health",
            "/api/agents",
            "/api/agents/{id}"
        ]
    })

@app.errorhandler(404)
def page_not_found(e):
    return jsonify({
        "error": "Not Found",
        "message": "This is an API-only deployment. The requested page does not exist."
    }), 404

# Create DB tables if they don't exist
with app.app_context():
    db.create_all()

# Run the app
if __name__ == '__main__':
    app.run(debug=True) 