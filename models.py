from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Agent(db.Model):
    __tablename__ = 'agent'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    division = db.Column(db.String(100), nullable=False)
    manager = db.Column(db.String(100), nullable=False)
    queue_type = db.Column(db.String(50), nullable=False)  # 'training' or 'performance'
    is_active = db.Column(db.Boolean, default=True)  # Track if agent is currently active
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DailyPerformance(db.Model):
    __tablename__ = 'daily_performance'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey('agent.id'), nullable=False)
    
    # Core Metrics
    leads_taken = db.Column(db.Float, nullable=False)
    close_rate = db.Column(db.Float, nullable=False)
    avg_premium = db.Column(db.Float, nullable=False)
    place_rate = db.Column(db.Float, nullable=False)
    
    # Calculated Fields
    placed_premium_per_lead = db.Column(db.Float)
    total_daily_premium = db.Column(db.Float)
    
    # Additional Metrics
    sales_made = db.Column(db.Integer)
    talk_time_minutes = db.Column(db.Integer)
    notes = db.Column(db.Text)

    def calculate_ppl(self):
        """Calculate Placed Premium per Lead"""
        return (self.close_rate / 100) * (self.place_rate / 100) * self.avg_premium

    def calculate_daily_premium(self):
        """Calculate total daily premium"""
        return self.leads_taken * self.calculate_ppl()

    def calculate_annual_comp(self, days_per_year=250):
        """Calculate projected annual compensation"""
        daily_ppl = self.calculate_ppl()
        daily_revenue = daily_ppl * self.leads_taken
        annual_revenue = daily_revenue * days_per_year
        return annual_revenue

    def get_performance_status(self):
        """Get performance status based on PPL"""
        ppl = self.calculate_ppl()
        if ppl >= 164:
            return "Above Target"
        elif ppl >= 130:
            return "Break Even"
        else:
            return "Below Break Even"

class APIKey(db.Model):
    __tablename__ = 'api_key'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<APIKey {self.name}>' 