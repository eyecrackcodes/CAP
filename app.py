from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import plotly.express as px
import plotly.utils
import json
import pandas as pd
import os
from werkzeug.utils import secure_filename
import uuid
from functools import wraps

# Import the Looker API Blueprint
from looker_api import register_looker_api

# Register the AI Insights Blueprint
from ai_insights import register_ai_insights

app = Flask(__name__)

# Check if running on Vercel and configure accordingly
IS_VERCEL = os.environ.get('VERCEL', False)

# Database configuration - Use environment variables for Vercel deployment
if IS_VERCEL:
    # Use Supabase or any PostgreSQL database suitable for production
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:xe2Gyu!56h6tWQD@db.ndiwwxpixxwwbkpdmmqq.supabase.co:5432/postgres')
else:
    # Local development database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:xe2Gyu!56h6tWQD@db.ndiwwxpixxwwbkpdmmqq.supabase.co:5432/postgres'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the db
from models import db, Agent, DailyPerformance, APIKey
db.init_app(app)

# Configure upload folder - for Vercel, use /tmp for file uploads
if IS_VERCEL:
    UPLOAD_FOLDER = '/tmp'
else:
    UPLOAD_FOLDER = 'uploads'

ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Configure secret key for sessions
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', '12345678900987654321')

# Register the Looker API Blueprint
register_looker_api(app)

# Register the AI Insights Blueprint
register_ai_insights(app)

# API key authentication decorator
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            return jsonify({'error': 'API key is missing'}), 401
            
        key_record = APIKey.query.filter_by(key=api_key, is_active=True).first()
        if not key_record:
            return jsonify({'error': 'Invalid or inactive API key'}), 401
            
        # Update last used timestamp
        key_record.last_used_at = datetime.utcnow()
        db.session.commit()
        
        return f(*args, **kwargs)
    return decorated_function

# API key management routes
@app.route('/api_keys')
def api_keys_page():
    return render_template('api_keys.html')

@app.route('/api/api_keys', methods=['GET'])
def get_api_keys():
    keys = APIKey.query.all()
    return jsonify([{
        'id': key.id,
        'name': key.name,
        'key': key.key,
        'created_at': key.created_at.isoformat(),
        'last_used_at': key.last_used_at.isoformat() if key.last_used_at else None,
        'is_active': key.is_active
    } for key in keys])

@app.route('/api/api_keys', methods=['POST'])
def create_api_key():
    try:
        data = request.form
        name = data.get('name', '').strip()
        
        if not name:
            return jsonify({'error': 'Key name is required'}), 400
            
        # Generate a random API key
        key = str(uuid.uuid4()).replace('-', '')
        
        # Create new key record
        api_key = APIKey(
            key=key,
            name=name
        )
        
        db.session.add(api_key)
        db.session.commit()
        
        return jsonify({
            'message': 'API key created successfully',
            'key': key
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/api_keys/<int:key_id>', methods=['DELETE'])
def delete_api_key(key_id):
    key = APIKey.query.get_or_404(key_id)
    db.session.delete(key)
    db.session.commit()
    return jsonify({'message': 'API key deleted successfully'})

@app.route('/api/api_keys/<int:key_id>/toggle', methods=['POST'])
def toggle_api_key(key_id):
    key = APIKey.query.get_or_404(key_id)
    key.is_active = not key.is_active
    db.session.commit()
    return jsonify({
        'message': f'API key {"activated" if key.is_active else "deactivated"} successfully',
        'is_active': key.is_active
    })

# Example of an API endpoint with key authentication
@app.route('/api/v1/agents', methods=['GET'])
@require_api_key
def api_v1_get_agents():
    agents = Agent.query.all()
    
    return jsonify([{
        'id': agent.id,
        'name': agent.name,
        'division': format_division(agent.division),
        'manager': agent.manager,
        'queue_type': agent.queue_type
    } for agent in agents])

@app.route('/api/v1/performance/add', methods=['POST'])
@require_api_key
def api_v1_add_performance():
    try:
        # Accept JSON payload
        data = request.json
        
        # Validate required fields
        required_fields = ['date', 'agent_id', 'leads_taken', 'close_rate', 'place_rate', 'avg_premium']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Parse date
        try:
            date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Check if agent exists
        agent = Agent.query.get(data['agent_id'])
        if not agent:
            return jsonify({'error': f'Agent with ID {data["agent_id"]} not found'}), 404
        
        # Log agent information for debugging
        print(f"Agent info - ID: {agent.id}, Name: {agent.name}, Division: {agent.division}, Formatted Division: {format_division(agent.division)}")
        
        # Check if record already exists for this date and agent
        existing = DailyPerformance.query.filter_by(
            date=date,
            agent_id=data['agent_id']
        ).first()
        
        if existing:
            # Update existing record
            existing.leads_taken = float(data['leads_taken'])
            existing.close_rate = float(data['close_rate'])
            existing.place_rate = float(data['place_rate'])
            existing.avg_premium = float(data['avg_premium'])
            
            # Optional fields
            if 'talk_time_minutes' in data:
                existing.talk_time_minutes = int(data['talk_time_minutes'])
            if 'notes' in data:
                existing.notes = data['notes']
            
            # Calculate derived fields
            existing.placed_premium_per_lead = existing.calculate_ppl()
            existing.total_daily_premium = existing.calculate_daily_premium()
            
            db.session.commit()
            
            return jsonify({
                'message': 'Performance record updated',
                'id': existing.id
            })
        else:
            # Create new record
            performance = DailyPerformance(
                date=date,
                agent_id=data['agent_id'],
                leads_taken=float(data['leads_taken']),
                close_rate=float(data['close_rate']),
                place_rate=float(data['place_rate']),
                avg_premium=float(data['avg_premium'])
            )
            
            # Optional fields
            if 'talk_time_minutes' in data:
                performance.talk_time_minutes = int(data['talk_time_minutes'])
            if 'notes' in data:
                performance.notes = data['notes']
            
            # Calculate derived fields
            performance.placed_premium_per_lead = performance.calculate_ppl()
            performance.total_daily_premium = performance.calculate_daily_premium()
            
            db.session.add(performance)
            db.session.commit()
            
            return jsonify({
                'message': 'Performance record created',
                'id': performance.id
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
    manager = request.args.get('manager')
    active_only_param = request.args.get('active_only', 'true').lower()
    active_only = active_only_param == 'true'
    
    print(f"Filter params for /api/agents: division='{division}', queue='{queue}', manager='{manager}', active_only={active_only} (from {active_only_param})")
    
    # Build query with filters
    query = Agent.query
    if division:
        print(f"Filtering agents by division: '{division}'")
        # Get all possible database division codes that map to this display value
        division_codes = get_division_codes(division)
        if division_codes:
            # If we found database codes for this display value, filter using them
            print(f"Found matching division codes for agents: {division_codes}")
            query = query.filter(Agent.division.in_(division_codes))
        else:
            # For other values, still use filter_by for exact match or like for partial
            print(f"No exact match found for division '{division}', using LIKE filter")
            query = query.filter(Agent.division.ilike(f"%{division}%"))
    
    if queue:
        print(f"Filtering agents by queue: '{queue}'")
        query = query.filter(Agent.queue_type.ilike(f"%{queue}%"))  # Case-insensitive comparison
    if manager:
        print(f"Filtering agents by manager: '{manager}'")
        query = query.filter_by(manager=manager)
    if active_only:
        print(f"Filtering to active agents only")
        query = query.filter_by(is_active=True)
    
    agents = query.all()
    print(f"Found {len(agents)} agents matching filters")
    
    if len(agents) > 0:
        print(f"First agent: {agents[0].name}, Division: {agents[0].division}, Formatted: {format_division(agents[0].division)}")
    
    # Return agents with formatted division values using the helper function
    return jsonify([{
        'id': agent.id,
        'name': agent.name,
        'division': format_division(agent.division),
        'manager': agent.manager,
        'queue_type': agent.queue_type,
        'is_active': agent.is_active
    } for agent in agents])

@app.route('/api/add_agent', methods=['POST'])
def add_agent():
    try:
        data = request.form
        
        # Get division value and handle standardization
        division = data['division']
        # For consistency, use the format_division function,
        # but only if we need to normalize the data (for example,
        # if user enters "CHA" instead of "Charlotte (CLT)").
        # This prevents creating invalid division codes like "Charlotte (CLT) (CLT)"
        if division in ["Charlotte (CLT)", "Austin (ATX)"]:
            # These are already in the standard format, keep as is
            formatted_division = division
        else:
            # This might be a code like "CHA" or "ATX" that needs formatting
            # Check if it's a known code
            known_division = format_division(division)
            if known_division != division:
                # It was a known code, use the formatted version
                formatted_division = known_division
            else:
                # It wasn't a known code, keep the original
                formatted_division = division
                
        agent = Agent(
            name=data['name'],
            division=formatted_division,
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
    
    # Use the helper function to format the division
    formatted_division = format_division(agent.division)
    
    if not performances:
        return jsonify({
            'agent': {
                'name': agent.name,
                'division': formatted_division,
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
            'division': formatted_division,
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
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # Handle date parameters with better error handling
    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            start_date = (datetime.now() - timedelta(days=30)).date()
    except ValueError:
        print(f"Invalid start_date format: {start_date_str}, using default")
        start_date = (datetime.now() - timedelta(days=30)).date()
    
    try:
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            end_date = datetime.now().date()
    except ValueError:
        print(f"Invalid end_date format: {end_date_str}, using default")
        end_date = datetime.now().date()
    
    print(f"Dashboard filters: division='{division}', queue='{queue}', agent_id='{agent_id}', manager='{manager}'")
    print(f"Date range: {start_date} to {end_date}")

    # Build base query for agents
    agent_query = Agent.query
    if division:
        print(f"Filtering by division: '{division}'")
        # If division is a display name like "Charlotte (CLT)", convert to possible DB values
        division_codes = get_division_codes(division)
        if division_codes:
            # If we found database codes for this display value, filter using them
            print(f"Found matching division codes: {division_codes}")
            agent_query = agent_query.filter(Agent.division.in_(division_codes))
        else:
            # For other values, still use LIKE for flexibility
            print(f"No exact match found for division '{division}', using LIKE filter")
            agent_query = agent_query.filter(Agent.division.ilike(f"%{division}%"))
    
    if queue:
        print(f"Filtering by queue: '{queue}'")
        if queue.lower() in ["training", "train", "t"]:
            agent_query = agent_query.filter(Agent.queue_type.ilike("%training%"))
        elif queue.lower() in ["performance", "perform", "p"]:
            agent_query = agent_query.filter(Agent.queue_type.ilike("%performance%"))
        else:
            agent_query = agent_query.filter(Agent.queue_type.ilike(f"%{queue}%"))
    
    if agent_id:
        print(f"Filtering by agent_id: '{agent_id}'")
        agent_query = agent_query.filter_by(id=agent_id)
    
    if manager:
        print(f"Filtering by manager: '{manager}'")
        agent_query = agent_query.filter(Agent.manager.ilike(f"%{manager}%"))
    
    # Include only active agents by default
    if 'active_only' not in request.args or request.args.get('active_only', 'true').lower() == 'true':
        agent_query = agent_query.filter_by(is_active=True)
        print("Filtering to active agents only")
    
    agents = agent_query.all()
    print(f"Found {len(agents)} agents matching filters")
    
    if len(agents) == 0:
        print("No agents found, returning empty data")
        return jsonify({
            'total_agents': 0,
            'training_agents': 0,
            'performance_agents': 0,
            'avg_ppl': 0,
            'above_target': 0,
            'at_break_even': 0,
            'below_break_even': 0,
            'trend': {
                'dates': [],
                'ppls': []
            },
            'agents': [],
            'date_range': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        })
    
    agent_ids = [agent.id for agent in agents]
    print(f"Agent IDs: {agent_ids}")

    # Get performance data for the filtered agents
    # With PostgreSQL, we need to ensure date comparison works properly
    performance_query = DailyPerformance.query.filter(
        DailyPerformance.agent_id.in_(agent_ids),
        DailyPerformance.date >= start_date,
        DailyPerformance.date <= end_date
    )
    
    # Debug the SQL query
    print(f"Performance query: {str(performance_query)}")
    
    performances = performance_query.all()
    print(f"Found {len(performances)} performance records")

    # Calculate statistics
    total_agents = len(agents)
    training_agents = len([a for a in agents if 'training' in a.queue_type.lower()])
    performance_agents = len([a for a in agents if 'performance' in a.queue_type.lower()])
    
    print(f"Agent counts - Total: {total_agents}, Training: {training_agents}, Performance: {performance_agents}")

    if performances:
        avg_ppl = sum(p.calculate_ppl() for p in performances) / len(performances)
        above_target = len([p for p in performances if p.calculate_ppl() >= 164])
        at_break_even = len([p for p in performances if 130 <= p.calculate_ppl() < 164])
        below_break_even = len([p for p in performances if p.calculate_ppl() < 130])
        
        print(f"Performance stats - Avg PPL: ${avg_ppl:.2f}, Above Target: {above_target}, Break Even: {at_break_even}, Below: {below_break_even}")

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
        
        print(f"Trend data - {len(trend_dates)} dates from {trend_dates[0] if trend_dates else 'none'} to {trend_dates[-1] if trend_dates else 'none'}")
    else:
        print("No performance data found for selected agents and date range")
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
            avg_leads_taken = sum(p.leads_taken for p in agent_perfs) / len(agent_perfs)
            total_premium = sum(p.calculate_daily_premium() for p in agent_perfs)
            print(f"Agent {agent.name} stats - PPL: ${avg_agent_ppl:.2f}, CR: {avg_close_rate:.1f}%, PR: {avg_place_rate:.1f}%, Leads: {avg_leads_taken:.1f}, Total Premium: ${total_premium:.2f}")
        else:
            avg_close_rate = 0
            avg_place_rate = 0
            avg_premium = 0
            avg_agent_ppl = 0
            avg_leads_taken = 0
            total_premium = 0
            print(f"No performance data for agent {agent.name}")

        # Use the helper function to format the division
        formatted_division = format_division(agent.division)

        agent_stats.append({
            'id': agent.id,
            'name': agent.name,
            'division': formatted_division,
            'manager': agent.manager,
            'queue_type': agent.queue_type,
            'is_active': agent.is_active,
            'close_rate': avg_close_rate,
            'place_rate': avg_place_rate,
            'avg_premium': avg_premium,
            'ppl': avg_agent_ppl,
            'leads_taken': avg_leads_taken,
            'total_premium': total_premium
        })

    # No need for second division filter - it was causing issues
    # because division names could be different formats

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

    # Use the helper function to format the division
    formatted_division = format_division(agent.division)

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
            'division': formatted_division,
            'manager': agent.manager,
            'queue_type': agent.queue_type
        },
        'performance_data': daily_data
    })

@app.route('/agent_view')
def agent_view():
    return render_template('agent_view.html')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/import_data')
def import_data_page():
    return render_template('import_data.html')

@app.route('/api/import_data', methods=['POST'])
def import_data():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            print(f"Processing file: {filename}")
            # Determine file type and read accordingly
            if filename.endswith('.csv'):
                df = pd.read_csv(filepath)
            else:
                df = pd.read_excel(filepath)
            
            print(f"Original data shape: {df.shape}")
            print(f"Original columns: {df.columns.tolist()}")
            
            # Clean data before processing
            def clean_data(df):
                # Remove rows that are likely headers or section dividers
                # (rows where all numeric columns have non-numeric values)
                numeric_cols = ['close_rate', 'place_rate', 'avg_premium', 'leads_taken']
                
                # First filter out rows where agent_name is empty or contains header-like text
                df = df[df['agent_name'].notna()]  # Remove rows with empty agent_name
                print(f"After removing empty agent_name rows: {df.shape}")
                
                df = df[~df['agent_name'].astype(str).str.contains('TRAINING|QUEUE|agent|name', case=False)]
                print(f"After removing header-like rows: {df.shape}")
                
                # Rename columns to match expected names if needed
                rename_map = {
                    'Sales Agent': 'agent_name',
                    'Close Rate': 'close_rate',
                    'AP Per Sale': 'avg_premium',
                    'Placed Rate': 'place_rate',
                    'Leads Per Day': 'leads_taken'
                }
                df = df.rename(columns=rename_map)
                print(f"After renaming columns: {df.columns.tolist()}")
                
                # Check if numeric columns contain column names
                for col in numeric_cols:
                    if col in df.columns:
                        # Remove rows where the value is the same as the column name (header rows)
                        df = df[~(df[col].astype(str).str.lower() == col.lower())]
                        df = df[~(df[col].astype(str).str.lower().str.contains('rate|premium|leads|per'))]
                
                print(f"After removing header value rows: {df.shape}")
                
                # Remove % symbols and convert to float
                if 'close_rate' in df.columns:
                    print(f"close_rate before cleaning: {df['close_rate'].head().tolist()}")
                    df['close_rate'] = df['close_rate'].astype(str).str.replace('%', '').str.strip()
                    # Remove any non-numeric rows
                    df = df[pd.to_numeric(df['close_rate'], errors='coerce').notna()]
                    df['close_rate'] = df['close_rate'].astype(float)
                    print(f"close_rate after cleaning: {df['close_rate'].head().tolist()}")
                    
                if 'place_rate' in df.columns:
                    df['place_rate'] = df['place_rate'].astype(str).str.replace('%', '').str.strip()
                    df = df[pd.to_numeric(df['place_rate'], errors='coerce').notna()]
                    df['place_rate'] = df['place_rate'].astype(float)
                
                # Remove $ symbols and convert to float
                if 'avg_premium' in df.columns:
                    print(f"avg_premium before cleaning: {df['avg_premium'].head().tolist()}")
                    df['avg_premium'] = df['avg_premium'].astype(str).str.replace('$', '').str.replace(',', '').str.strip()
                    df = df[pd.to_numeric(df['avg_premium'], errors='coerce').notna()]
                    df['avg_premium'] = df['avg_premium'].astype(float)
                    print(f"avg_premium after cleaning: {df['avg_premium'].head().tolist()}")
                
                # Convert leads_taken to float
                if 'leads_taken' in df.columns:
                    print(f"leads_taken before cleaning: {df['leads_taken'].head().tolist()}")
                    df['leads_taken'] = pd.to_numeric(df['leads_taken'], errors='coerce')
                    df = df[df['leads_taken'].notna()]
                    print(f"leads_taken after cleaning: {df['leads_taken'].head().tolist()}")
                
                print(f"Final data shape after cleaning: {df.shape}")
                print(f"Final columns: {df.columns.tolist()}")
                # Return the cleaned dataframe
                return df
            
            # Clean data
            df = clean_data(df)
            
            # Validate required columns
            required_columns = ['date', 'agent_name', 'leads_taken', 'close_rate', 'place_rate', 'avg_premium']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return jsonify({'error': f'Missing required columns: {", ".join(missing_columns)}'}), 400
            
            # Check if auto-create agents is enabled
            auto_create_agents = request.form.get('auto_create_agents') == 'true'
            agent_division = request.form.get('agent_division', 'Default Division')
            default_manager = request.form.get('agent_manager', 'Default Manager')
            agent_queue = request.form.get('agent_queue', 'training')
            update_existing_info = request.form.get('update_existing_info') == 'true'
            
            # Check if we have manager info in the data
            has_manager_column = 'manager' in df.columns or 'MANAGER' in df.columns
            manager_column = 'manager' if 'manager' in df.columns else ('MANAGER' if 'MANAGER' in df.columns else None)
            
            # Check if we have other agent info in the data
            has_division_column = 'division' in df.columns or 'Site' in df.columns
            division_column = 'division' if 'division' in df.columns else ('Site' if 'Site' in df.columns else None)
            
            has_queue_column = 'queue_type' in df.columns or 'Q' in df.columns
            queue_column = 'queue_type' if 'queue_type' in df.columns else ('Q' if 'Q' in df.columns else None)
            
            # Function to normalize manager names
            def normalize_manager_name(name):
                if pd.isna(name) or not name:
                    return ''
                # Convert to string in case it's not
                name = str(name).strip()
                # Normalize case
                name = name.title()
                # Handle common variations
                name_map = {
                    'Fred Holguin': 'Frederick Holguin',
                    'Fred': 'Frederick Holguin',
                    'Holguin': 'Frederick Holguin',
                    'Vince Blanchett': 'Vincent Blanchett',
                    'Vince': 'Vincent Blanchett',
                    'Blanchett': 'Vincent Blanchett',
                    'Pat Lewis': 'Patricia Lewis',
                    'Patty Lewis': 'Patricia Lewis',
                    'Pat': 'Patricia Lewis',
                    'Lewis': 'Patricia Lewis',
                    'Hajmahmoud': 'Nisrin Hajmahmoud',
                    'Nisrin': 'Nisrin Hajmahmoud'
                    # Add other common variations here
                }
                # Check if this name matches any known variation
                for variation, full_name in name_map.items():
                    if variation.lower() in name.lower():
                        return full_name
                return name
            
            # Apply name normalization if we have manager column
            if manager_column:
                df[manager_column] = df[manager_column].apply(normalize_manager_name)
            
            # Handle possible inconsistent manager names by determining most common manager per agent
            agent_managers = {}
            if manager_column:
                for agent_name, group in df.groupby('agent_name'):
                    if manager_column in group.columns:
                        # Count manager occurrences for this agent
                        manager_counts = {}
                        for manager in group[manager_column].dropna():
                            if manager not in manager_counts:
                                manager_counts[manager] = 0
                            manager_counts[manager] += 1
                        
                        # Get the most common manager for this agent
                        if manager_counts:
                            most_common_manager = max(manager_counts.items(), key=lambda x: x[1])[0]
                            agent_managers[agent_name] = most_common_manager
            
            # Process data
            success_count = 0
            error_count = 0
            errors = []
            created_agents = []
            updated_info_agents = []
            manager_changes = []
            
            for index, row in df.iterrows():
                try:
                    # Look up agent by name
                    agent = Agent.query.filter_by(name=row['agent_name']).first()
                    
                    # Extract agent info from data if available
                    agent_manager = default_manager
                    if row['agent_name'] in agent_managers:
                        # Use the most common manager for this agent
                        agent_manager = agent_managers[row['agent_name']]
                    elif manager_column and pd.notna(row.get(manager_column, '')):
                        agent_manager = row[manager_column]
                    
                    agent_div = agent_division
                    if division_column and pd.notna(row.get(division_column, '')):
                        agent_div = row[division_column]
                    
                    agent_q = agent_queue
                    if queue_column and pd.notna(row.get(queue_column, '')):
                        # Map 'T' to 'training' and 'P' to 'performance'
                        if row[queue_column] == 'T':
                            agent_q = 'training'
                        elif row[queue_column] == 'P':
                            agent_q = 'performance'
                        else:
                            agent_q = row[queue_column]
                    
                    # Auto-create agent if enabled and agent not found
                    if not agent and auto_create_agents:
                        agent = Agent(
                            name=row['agent_name'],
                            division=agent_div,
                            manager=agent_manager,
                            queue_type=agent_q
                        )
                        db.session.add(agent)
                        db.session.flush()  # Get ID without committing
                        created_agents.append(f"{agent.name} (Manager: {agent.manager})")
                    # Update existing agent information if the option is enabled
                    elif agent and update_existing_info:
                        updated_info = False
                        manager_changed = False
                        old_manager = agent.manager
                        
                        if agent.manager != agent_manager:
                            agent.manager = agent_manager
                            updated_info = True
                            manager_changed = True
                            manager_changes.append({
                                'agent_name': agent.name,
                                'change': f"{old_manager} → {agent.manager}"
                            })
                        if agent.division != agent_div:
                            agent.division = agent_div
                            updated_info = True
                        if agent.queue_type != agent_q:
                            agent.queue_type = agent_q
                            updated_info = True
                        
                        if updated_info:
                            update_info = agent.name
                            if manager_changed:
                                update_info = f"{agent.name} (Manager: {old_manager} → {agent.manager})"
                            updated_info_agents.append(update_info)
                    elif not agent:
                        errors.append(f"Row {index+1}: Agent '{row['agent_name']}' not found")
                        error_count += 1
                        continue
                    
                    # Parse date
                    try:
                        if isinstance(row['date'], str):
                            date = datetime.strptime(row['date'], '%Y-%m-%d').date()
                        else:
                            date = row['date'].date() if hasattr(row['date'], 'date') else row['date']
                    except Exception as e:
                        errors.append(f"Row {index+1}: Invalid date format. Use YYYY-MM-DD")
                        error_count += 1
                        continue
                    
                    # Check if data for this agent+date already exists
                    existing = DailyPerformance.query.filter_by(agent_id=agent.id, date=date).first()
                    if existing:
                        # Update existing record
                        existing.leads_taken = float(row['leads_taken'])
                        existing.close_rate = float(row['close_rate'])
                        existing.place_rate = float(row['place_rate'])
                        existing.avg_premium = float(row['avg_premium'])
                        existing.placed_premium_per_lead = existing.calculate_ppl()
                        existing.total_daily_premium = existing.calculate_daily_premium()
                        
                        # Optional fields
                        if 'talk_time_minutes' in row and not pd.isna(row['talk_time_minutes']):
                            existing.talk_time_minutes = int(row['talk_time_minutes'])
                        if 'notes' in row and not pd.isna(row['notes']):
                            existing.notes = row['notes']
                        
                        success_count += 1
                    else:
                        # Create new record
                        performance = DailyPerformance(
                            date=date,
                            agent_id=agent.id,
                            leads_taken=float(row['leads_taken']),
                            close_rate=float(row['close_rate']),
                            place_rate=float(row['place_rate']),
                            avg_premium=float(row['avg_premium'])
                        )
                        
                        # Optional fields
                        if 'talk_time_minutes' in row and not pd.isna(row['talk_time_minutes']):
                            performance.talk_time_minutes = int(row['talk_time_minutes'])
                        if 'notes' in row and not pd.isna(row['notes']):
                            performance.notes = row['notes']
                        
                        # Calculate derived fields
                        performance.placed_premium_per_lead = performance.calculate_ppl()
                        performance.total_daily_premium = performance.calculate_daily_premium()
                        
                        db.session.add(performance)
                        success_count += 1
                
                except Exception as e:
                    errors.append(f"Row {index+1}: {str(e)}")
                    error_count += 1
            
            db.session.commit()
            
            # Prepare response message
            message = f'Import completed: {success_count} records imported successfully, {error_count} errors'
            if created_agents:
                message += f'. Created {len(created_agents)} new agents: {", ".join(created_agents[:5])}'
                if len(created_agents) > 5:
                    message += f' and {len(created_agents) - 5} more'
            
            if updated_info_agents:
                message += f'. Updated info for {len(updated_info_agents)} agents: {", ".join(updated_info_agents[:5])}'
                if len(updated_info_agents) > 5:
                    message += f' and {len(updated_info_agents) - 5} more'
            
            return jsonify({
                'message': message,
                'errors': errors,
                'manager_changes': manager_changes
            })
            
        except Exception as e:
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500
        finally:
            # Clean up uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)
    
    return jsonify({'error': 'Invalid file type. Please upload a CSV or Excel file'}), 400

@app.route('/api/data/reset', methods=['POST'])
def reset_data():
    try:
        reset_type = request.json.get('reset_type', 'performance_only')
        confirm_text = request.json.get('confirm_text', '')
        
        if confirm_text != 'DELETE ALL DATA':
            return jsonify({'error': 'Confirmation text does not match. Please type "DELETE ALL DATA" to confirm.'}), 400
        
        if reset_type == 'performance_only':
            # Delete only performance data
            rows_deleted = db.session.query(DailyPerformance).delete()
            db.session.commit()
            return jsonify({
                'message': f'Successfully deleted all performance data ({rows_deleted} records)',
                'reset_type': 'performance_only'
            })
        elif reset_type == 'complete':
            # Delete all data including agents and API keys
            perf_rows = db.session.query(DailyPerformance).delete()
            agent_rows = db.session.query(Agent).delete()
            api_key_rows = db.session.query(APIKey).delete()
            db.session.commit()
            return jsonify({
                'message': f'Successfully deleted all data: {perf_rows} performance records, {agent_rows} agents, {api_key_rows} API keys',
                'reset_type': 'complete'
            })
        else:
            return jsonify({'error': 'Invalid reset type. Use "performance_only" or "complete"'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error resetting data: {str(e)}'}), 500

@app.route('/api/agents/<int:agent_id>/toggle_active', methods=['POST'])
def toggle_agent_active(agent_id):
    try:
        agent = Agent.query.get_or_404(agent_id)
        agent.is_active = not agent.is_active
        db.session.commit()
        
        status = 'activated' if agent.is_active else 'deactivated'
        return jsonify({
            'message': f'Agent {agent.name} successfully {status}',
            'agent': {
                'id': agent.id,
                'name': agent.name,
                'is_active': agent.is_active
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Define a helper function for division formatting
def format_division(division_code):
    """
    Map database division codes to standardized display values
    
    Args:
        division_code (str): The raw division code from the database
        
    Returns:
        str: The formatted division name for display
    """
    # Division mapping dictionary
    division_map = {
        "CHA": "Charlotte (CLT)",
        "CLT": "Charlotte (CLT)",
        "Charlotte": "Charlotte (CLT)",
        "Charlotte Call Center": "Charlotte (CLT)",
        "AUS": "Austin (ATX)",
        "ATX": "Austin (ATX)",
        "Austin": "Austin (ATX)",
        "Austin Call Center": "Austin (ATX)"
    }
    
    return division_map.get(division_code, division_code)

def get_division_codes(display_value):
    """
    Get all possible database division codes that map to a given display value
    
    Args:
        display_value (str): The formatted division name for display
        
    Returns:
        list: List of database codes that map to this display value
    """
    # Division mapping dictionary (same as in format_division)
    division_map = {
        "CHA": "Charlotte (CLT)",
        "CLT": "Charlotte (CLT)",
        "Charlotte": "Charlotte (CLT)",
        "Charlotte Call Center": "Charlotte (CLT)",
        "AUS": "Austin (ATX)",
        "ATX": "Austin (ATX)",
        "Austin": "Austin (ATX)",
        "Austin Call Center": "Austin (ATX)"
    }
    
    # Find all keys that map to this display value
    codes = [code for code, value in division_map.items() if value == display_value]
    return codes

def init_db():
    with app.app_context():
        db.create_all()
        
        # Add missing columns to agent table if they don't exist
        try:
            inspector = db.inspect(db.engine)
            columns = [column['name'] for column in inspector.get_columns('agent')]
            
            # Add is_active column if missing
            if 'is_active' not in columns:
                print("Adding is_active column to agent table...")
                with db.engine.begin() as conn:
                    conn.execute(db.text("ALTER TABLE agent ADD COLUMN is_active BOOLEAN DEFAULT 1"))
                print("is_active column added successfully.")
                
            # Add created_at column if missing
            if 'created_at' not in columns:
                print("Adding created_at column to agent table...")
                with db.engine.begin() as conn:
                    conn.execute(db.text("ALTER TABLE agent ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
                print("created_at column added successfully.")
                
            # Add last_updated column if missing
            if 'last_updated' not in columns:
                print("Adding last_updated column to agent table...")
                with db.engine.begin() as conn:
                    conn.execute(db.text("ALTER TABLE agent ADD COLUMN last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
                print("last_updated column added successfully.")
                
        except Exception as e:
            print(f"Error during migration: {str(e)}")

# Add a custom template filter for current year
@app.template_filter('current_year')
def current_year_filter(input):
    return datetime.now().year

@app.route('/run_migration')
def run_migration():
    try:
        init_db()
        return jsonify({
            'message': 'Database migration completed successfully.'
        })
    except Exception as e:
        return jsonify({
            'error': f'Migration failed: {str(e)}'
        }), 500

@app.route('/reset_database')
def reset_database():
    try:
        with app.app_context():
            # Drop all tables
            db.drop_all()
            # Recreate all tables
            db.create_all()
            
        return jsonify({
            'message': 'Database has been completely reset. All existing data has been removed and tables recreated.'
        })
    except Exception as e:
        return jsonify({
            'error': f'Database reset failed: {str(e)}'
        }), 500

@app.route("/reset_data", methods=["POST"])
def reset_data_redirect():
    reset_type = request.form.get("reset_type")
    
    if reset_type == "reset_performance":
        # Delete all performance data
        db.session.query(DailyPerformance).delete()
        db.session.commit()
        flash("Performance data has been reset.", "success")
    elif reset_type == "reset_all":
        # Delete all data, including agents
        db.session.query(DailyPerformance).delete()
        db.session.query(Agent).delete()
        db.session.commit()
        flash("All data has been reset.", "success")
    
    return redirect(url_for("home"))

if __name__ == '__main__':
    init_db()
    app.run(debug=True) 