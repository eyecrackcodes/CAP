from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import plotly.express as px
import plotly.utils
import json
import pandas as pd

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ppl_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Agent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    division = db.Column(db.String(100), nullable=False)
    manager = db.Column(db.String(100), nullable=False)
    queue_type = db.Column(db.String(50), nullable=False)  # 'training' or 'performance'

class DailyPerformance(db.Model):
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

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/performance_stats')
def get_performance_stats():
    # Get date range from request
    start_date = request.args.get('start_date', default=datetime.now().date() - timedelta(days=30))
    end_date = request.args.get('end_date', default=datetime.now().date())
    
    # Query performance data
    performances = DailyPerformance.query.filter(
        DailyPerformance.date.between(start_date, end_date)
    ).all()
    
    # Calculate statistics
    stats = {
        'total_agents': len(set(p.agent_id for p in performances)),
        'avg_ppl': sum(p.calculate_ppl() for p in performances) / len(performances) if performances else 0,
        'above_target': len([p for p in performances if p.calculate_ppl() >= 164]),
        'at_break_even': len([p for p in performances if 130 <= p.calculate_ppl() < 164]),
        'below_break_even': len([p for p in performances if p.calculate_ppl() < 130])
    }
    
    return jsonify(stats)

@app.route('/api/agent_performance/<int:agent_id>')
def get_agent_performance(agent_id):
    agent = Agent.query.get_or_404(agent_id)
    performances = DailyPerformance.query.filter_by(agent_id=agent_id).order_by(DailyPerformance.date.desc()).limit(30).all()
    
    data = [{
        'date': p.date.strftime('%Y-%m-%d'),
        'ppl': p.calculate_ppl(),
        'leads': p.leads_taken,
        'close_rate': p.close_rate,
        'place_rate': p.place_rate,
        'avg_premium': p.avg_premium,
        'status': p.get_performance_status()
    } for p in performances]
    
    return jsonify(data)

@app.route('/api/agents', methods=['GET'])
def get_agents():
    # Get filter parameters
    division = request.args.get('division')
    queue = request.args.get('queue')
    
    # Build query with filters
    query = Agent.query
    if division:
        query = query.filter_by(division=division)
    if queue:
        query = query.filter(Agent.queue_type.ilike(queue))  # Case-insensitive comparison
    
    agents = query.all()
    return jsonify([{
        'id': agent.id,
        'name': agent.name,
        'division': agent.division,
        'manager': agent.manager,
        'queue_type': agent.queue_type
    } for agent in agents])

@app.route('/api/add_agent', methods=['POST'])
def add_agent():
    try:
        data = request.form
        agent = Agent(
            name=data['name'],
            division=data['division'],
            manager=data['manager'],
            queue_type=data['queue_type']
        )
        db.session.add(agent)
        db.session.commit()
        return jsonify({'message': 'Agent added successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/add_performance', methods=['POST'])
def add_performance():
    try:
        data = request.form
        performance = DailyPerformance(
            date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            agent_id=int(data['agent_id']),
            leads_taken=float(data['leads_taken']),
            close_rate=float(data['close_rate']),
            place_rate=float(data['place_rate']),
            avg_premium=float(data['avg_premium']),
            talk_time_minutes=int(data['talk_time_minutes']) if data['talk_time_minutes'] else None,
            notes=data['notes'] if data['notes'] else None
        )
        
        # Calculate and set derived fields
        performance.placed_premium_per_lead = performance.calculate_ppl()
        performance.total_daily_premium = performance.calculate_daily_premium()
        
        db.session.add(performance)
        db.session.commit()
        return jsonify({'message': 'Performance data added successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/agent_stats/<int:agent_id>')
def get_agent_stats(agent_id):
    agent = Agent.query.get_or_404(agent_id)
    
    # Get date range from request
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    performances = DailyPerformance.query.filter(
        DailyPerformance.agent_id == agent_id,
        DailyPerformance.date.between(start_date, end_date)
    ).order_by(DailyPerformance.date.desc()).all()
    
    if not performances:
        return jsonify({
            'agent': {
                'name': agent.name,
                'division': agent.division,
                'manager': agent.manager
            },
            'stats': None
        })
    
    # Calculate average metrics
    avg_ppl = sum(p.calculate_ppl() for p in performances) / len(performances)
    avg_close_rate = sum(p.close_rate for p in performances) / len(performances)
    avg_place_rate = sum(p.place_rate for p in performances) / len(performances)
    avg_premium = sum(p.avg_premium for p in performances) / len(performances)
    avg_leads = sum(p.leads_taken for p in performances) / len(performances)
    
    # Calculate performance distribution
    above_target = len([p for p in performances if p.calculate_ppl() >= 164])
    at_break_even = len([p for p in performances if 130 <= p.calculate_ppl() < 164])
    below_break_even = len([p for p in performances if p.calculate_ppl() < 130])
    
    return jsonify({
        'agent': {
            'name': agent.name,
            'division': agent.division,
            'manager': agent.manager
        },
        'stats': {
            'avg_ppl': avg_ppl,
            'avg_close_rate': avg_close_rate,
            'avg_place_rate': avg_place_rate,
            'avg_premium': avg_premium,
            'avg_leads': avg_leads,
            'performance_distribution': {
                'above_target': above_target,
                'at_break_even': at_break_even,
                'below_break_even': below_break_even
            },
            'total_days': len(performances)
        }
    })

@app.route('/add_agent')
def add_agent_page():
    return render_template('add_agent.html')

@app.route('/add_performance')
def add_performance_page():
    return render_template('add_performance.html')

@app.route('/api/dashboard_stats')
def get_dashboard_stats():
    # Get filter parameters
    division = request.args.get('division')
    queue = request.args.get('queue')
    agent_id = request.args.get('agent_id')
    manager = request.args.get('manager')
    start_date = datetime.strptime(request.args.get('start_date', datetime.now().date().isoformat()), '%Y-%m-%d').date()
    end_date = datetime.strptime(request.args.get('end_date', datetime.now().date().isoformat()), '%Y-%m-%d').date()

    # Build base query for agents
    agent_query = Agent.query
    if division:
        agent_query = agent_query.filter_by(division=division)
    if queue:
        agent_query = agent_query.filter(Agent.queue_type.ilike(queue))
    if agent_id:
        agent_query = agent_query.filter_by(id=agent_id)
    if manager:
        agent_query = agent_query.filter_by(manager=manager)
    
    agents = agent_query.all()
    agent_ids = [agent.id for agent in agents]

    # Get performance data for the filtered agents
    performances = DailyPerformance.query.filter(
        DailyPerformance.agent_id.in_(agent_ids),
        DailyPerformance.date.between(start_date, end_date)
    ).all()

    # Calculate statistics
    total_agents = len(agents)
    training_agents = len([a for a in agents if a.queue_type.lower() == 'training'])
    performance_agents = len([a for a in agents if a.queue_type.lower() == 'performance'])

    if performances:
        avg_ppl = sum(p.calculate_ppl() for p in performances) / len(performances)
        above_target = len([p for p in performances if p.calculate_ppl() >= 164])
        at_break_even = len([p for p in performances if 130 <= p.calculate_ppl() < 164])
        below_break_even = len([p for p in performances if p.calculate_ppl() < 130])

        # Calculate trend data
        trend_data = {}
        for perf in performances:
            date_str = perf.date.isoformat()
            if date_str not in trend_data:
                trend_data[date_str] = {'total_ppl': 0, 'count': 0}
            trend_data[date_str]['total_ppl'] += perf.calculate_ppl()
            trend_data[date_str]['count'] += 1

        trend_dates = sorted(trend_data.keys())
        trend_ppls = [trend_data[date]['total_ppl'] / trend_data[date]['count'] for date in trend_dates]
    else:
        avg_ppl = 0
        above_target = 0
        at_break_even = 0
        below_break_even = 0
        trend_dates = []
        trend_ppls = []

    # Calculate agent-level statistics
    agent_stats = []
    for agent in agents:
        agent_perfs = [p for p in performances if p.agent_id == agent.id]
        if agent_perfs:
            avg_close_rate = sum(p.close_rate for p in agent_perfs) / len(agent_perfs)
            avg_place_rate = sum(p.place_rate for p in agent_perfs) / len(agent_perfs)
            avg_premium = sum(p.avg_premium for p in agent_perfs) / len(agent_perfs)
            avg_agent_ppl = sum(p.calculate_ppl() for p in agent_perfs) / len(agent_perfs)
        else:
            avg_close_rate = 0
            avg_place_rate = 0
            avg_premium = 0
            avg_agent_ppl = 0

        agent_stats.append({
            'id': agent.id,
            'name': agent.name,
            'division': agent.division,
            'manager': agent.manager,
            'queue_type': agent.queue_type,
            'avg_close_rate': avg_close_rate,
            'avg_place_rate': avg_place_rate,
            'avg_premium': avg_premium,
            'avg_ppl': avg_agent_ppl
        })

    return jsonify({
        'total_agents': total_agents,
        'training_agents': training_agents,
        'performance_agents': performance_agents,
        'avg_ppl': avg_ppl,
        'above_target': above_target,
        'at_break_even': at_break_even,
        'below_break_even': below_break_even,
        'trend': {
            'dates': trend_dates,
            'ppls': trend_ppls
        },
        'agents': agent_stats,
        'date_range': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
    })

@app.route('/api/agent_details/<int:agent_id>')
def get_agent_details(agent_id):
    start_date = datetime.strptime(request.args.get('start_date', datetime.now().date().isoformat()), '%Y-%m-%d').date()
    end_date = datetime.strptime(request.args.get('end_date', datetime.now().date().isoformat()), '%Y-%m-%d').date()

    agent = Agent.query.get_or_404(agent_id)
    performances = DailyPerformance.query.filter(
        DailyPerformance.agent_id == agent_id,
        DailyPerformance.date.between(start_date, end_date)
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

@app.route('/agent_view')
def agent_view():
    return render_template('agent_view.html')

def init_db():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    init_db()
    app.run(debug=True) 