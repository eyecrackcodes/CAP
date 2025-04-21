from flask import Blueprint, jsonify, request, render_template
import re
import json
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import text, func, desc
from models import db, Agent, DailyPerformance
import os
import requests
import logging
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ai_insights_bp = Blueprint('ai_insights', __name__)

# Dictionary of patterns to match and their corresponding database queries
QUERY_PATTERNS = {
    r"(?i).*top.*(agent|performer).*": {
        "query": "get_top_agents",
        "description": "Shows top performing agents based on PPL"
    },
    r"(?i).*worst.*(agent|performer).*": {
        "query": "get_bottom_agents",
        "description": "Shows agents with the lowest PPL"
    },
    r"(?i).*average.*(ppl|per person lead).*": {
        "query": "get_average_ppl",
        "description": "Calculates average PPL across all agents"
    },
    r"(?i).*performance.*(trend|over time).*": {
        "query": "get_performance_trend",
        "description": "Shows performance trend over time"
    },
    r"(?i).*division.*(performance|comparison).*": {
        "query": "get_division_comparison",
        "description": "Compares performance across divisions"
    },
    r"(?i).*highest.*(close rate|conversion).*": {
        "query": "get_highest_close_rate",
        "description": "Identifies agents with highest close rates"
    },
    r"(?i).*(best|top|highest|best performing).*manager.*": {
        "query": "get_top_managers",
        "description": "Shows top performing managers based on team PPL"
    },
    r"(?i).*(worst|bottom|lowest|worst performing).*manager.*": {
        "query": "get_bottom_managers",
        "description": "Shows managers with the lowest team PPL"
    },
    r"(?i).*average.*team.*ppl.*manager.*": {
        "query": "get_manager_ppl",
        "description": "Calculates average PPL by manager"
    },
    r"(?i).*manager.*performance.*": {
        "query": "get_manager_performance",
        "description": "Analyzes performance metrics by manager"
    }
}

# Sample follow-up questions for each query type
FOLLOW_UP_QUESTIONS = {
    "get_top_agents": [
        "What makes these agents successful?",
        "How has their performance changed over time?",
        "Which division has the most top performers?"
    ],
    "get_bottom_agents": [
        "What factors contribute to lower performance?",
        "How can we improve these agents' results?",
        "Are there common patterns among lower performers?"
    ],
    "get_average_ppl": [
        "How has average PPL changed month over month?",
        "Which division exceeds the average PPL most consistently?",
        "What is the target vs. actual PPL comparison?"
    ],
    "get_performance_trend": [
        "What caused the biggest performance changes?",
        "How do seasonal factors affect performance?",
        "Can you break this down by division?"
    ],
    "get_division_comparison": [
        "Which division improved the most this quarter?",
        "What are the key differences between top and bottom divisions?",
        "How do staffing levels correlate with division performance?"
    ],
    "get_highest_close_rate": [
        "What techniques do these agents use?",
        "How does close rate correlate with PPL?",
        "Which division has the best overall close rate?"
    ],
    "get_top_managers": [
        "What strategies do top managers use?",
        "How do their teams' close rates compare?",
        "What's the distribution of performance within their teams?"
    ],
    "get_bottom_managers": [
        "What challenges are these managers facing?",
        "What training might help improve their teams?",
        "Are there specific metrics where their teams underperform?"
    ],
    "get_manager_ppl": [
        "Which managers have made the most improvement?",
        "How consistent is performance across agents within each team?",
        "What's the relationship between team size and performance?"
    ],
    "get_manager_performance": [
        "How do managers compare on different KPIs?",
        "Which managers have the most consistent team performance?",
        "What's the correlation between manager tenure and team results?"
    ]
}

# Anthropic API Integration
def call_anthropic_api(prompt, system_prompt=None):
    """
    Call the Anthropic Claude API with a prompt and optional system prompt
    
    Args:
        prompt (str): The user's query
        system_prompt (str, optional): System instructions for Claude
        
    Returns:
        str: The response from Claude
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not found in environment variables")
        raise ValueError("API key not configured. Please set the ANTHROPIC_API_KEY environment variable.")
    
    if api_key.startswith("sk-"):
        url = "https://api.anthropic.com/v1/messages"
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
        
        # Default system prompt if none provided
        if not system_prompt:
            system_prompt = """You are an AI assistant for a call center analytics dashboard. 
            You analyze performance data for sales agents, focusing on metrics like PPL (Placed Premium per Lead), 
            close rates, and place rates. When analyzing data, be specific, concise, and focus on providing 
            actionable insights. Include both positive observations and areas for improvement."""
        
        # Format the payload with system as a top-level parameter, not as a message role
        payload = {
            "model": "claude-3-opus-20240229",
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1000
        }
        
        try:
            logger.info(f"Sending request to Anthropic API with key starting with: {api_key[:8]}...")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Anthropic API returned status code {response.status_code}")
                logger.error(f"Response body: {response.text}")
                # Fall back to a simple response when the API fails
                return f"I encountered a problem with the AI service (status code: {response.status_code}). Here's what I can tell you: The average PPL is an important metric that measures the revenue generated per lead. It's calculated as close rate × place rate × average premium."
            
            result = response.json()
            if "content" not in result or not result["content"] or not isinstance(result["content"], list):
                logger.error(f"Unexpected response format from Anthropic API: {result}")
                return "I received an unexpected response format from the AI service. Let me share a simpler insight: PPL is a key performance indicator for call center agents."
            
            return result["content"][0]["text"]
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Anthropic API: {str(e)}")
            if response and hasattr(response, 'text'):
                logger.error(f"Response: {response.text}")
            raise Exception(f"Error calling AI service: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in Anthropic API call: {str(e)}")
            logger.error(traceback.format_exc())
            raise Exception(f"Unexpected error in AI service: {str(e)}")
    else:
        logger.error("Invalid API key format. API key should start with 'sk-'")
        raise ValueError("Invalid API key format. Please check your ANTHROPIC_API_KEY environment variable.")

def get_agent_data_summary():
    """Generate a summary of agent data for context in AI queries"""
    # Import db here to avoid circular imports
    
    logger.info("Getting agent data summary")
    
    try:
        # Get counts
        agent_count = Agent.query.filter_by(is_active=True).count()
        logger.info(f"Found {agent_count} active agents")
        
        division_counts = db.session.query(Agent.division, func.count(Agent.id)).\
            filter_by(is_active=True).\
            group_by(Agent.division).all()
        logger.info(f"Division counts: {division_counts}")
        
        # Get performance summary
        now = datetime.now().date()
        thirty_days_ago = now - timedelta(days=30)
        
        # For PostgreSQL, explicitly cast the calculation
        avg_ppl_query = db.session.query(
            func.avg(
                (DailyPerformance.close_rate/100.0) * 
                (DailyPerformance.place_rate/100.0) * 
                DailyPerformance.avg_premium
            )
        ).filter(DailyPerformance.date >= thirty_days_ago)
        
        logger.info(f"PPL query: {str(avg_ppl_query)}")
        avg_ppl = avg_ppl_query.scalar() or 0
        logger.info(f"Average PPL calculated: {avg_ppl}")
        
        # Get performance metrics summary
        metrics_summary = db.session.query(
            func.avg(DailyPerformance.close_rate).label('avg_close_rate'),
            func.avg(DailyPerformance.place_rate).label('avg_place_rate'),
            func.avg(DailyPerformance.avg_premium).label('avg_premium'),
            func.avg(DailyPerformance.leads_taken).label('avg_leads')
        ).filter(DailyPerformance.date >= thirty_days_ago).first()
        
        if metrics_summary:
            avg_close_rate = metrics_summary.avg_close_rate or 0
            avg_place_rate = metrics_summary.avg_place_rate or 0
            avg_premium = metrics_summary.avg_premium or 0
            avg_leads = metrics_summary.avg_leads or 0
        else:
            avg_close_rate = avg_place_rate = avg_premium = avg_leads = 0
        
        # Create summary text
        summary = f"""
        Current Data Summary (Last 30 Days):
        - Total Active Agents: {agent_count}
        - Divisions: {", ".join([f"{div[0]} ({div[1]} agents)" for div in division_counts])}
        - Average PPL: ${avg_ppl:.2f}
        - Average Close Rate: {avg_close_rate:.1f}%
        - Average Place Rate: {avg_place_rate:.1f}%
        - Average Premium: ${avg_premium:.2f}
        - Average Leads per Day: {avg_leads:.1f}
        - Target PPL: $164
        - Break-even PPL: $130
        - Daily Leads Goal: 8
        """
        
        logger.info("Successfully generated data summary")
        return summary
    except Exception as e:
        logger.error(f"Error generating agent data summary: {str(e)}")
        logger.error(traceback.format_exc())
        return "Error generating data summary"

# Helper function to analyze the question and generate a SQL query
def analyze_question(question):
    """
    Analyze a natural language question and extract key information to generate a SQL query.
    This is a basic implementation that can be improved with more advanced NLP techniques.
    """
    question = question.lower()
    
    # Dictionary to track what we've identified in the question
    query_info = {
        'target': None,         # What data we're looking for (agents, managers, performance metrics)
        'metric': None,         # Which metric to analyze (PPL, close rate, etc.)
        'filter_division': None, # Filter by division
        'filter_manager': None, # Filter by manager
        'filter_queue': None,   # Filter by queue type
        'time_period': 30,      # Default to last 30 days
        'comparison': None,     # Comparison type (above/below target, comparison between divisions)
        'limit': 5,             # Default to top/bottom 5 results
        'sort_direction': 'DESC'# Default to descending order (highest first)
    }
    
    # Extract metrics
    metrics = {
        'ppl': ['ppl', 'placed premium per lead', 'placed premium', 'premium per lead'],
        'close_rate': ['close rate', 'close percentage', 'closing percentage', 'close', 'closes'],
        'place_rate': ['place rate', 'placement rate', 'place percentage', 'placement'],
        'avg_premium': ['average premium', 'avg premium', 'premium', 'average policy premium'],
        'leads': ['leads', 'lead count', 'number of leads', 'lead volume'],
    }
    
    for metric_key, terms in metrics.items():
        if any(term in question for term in terms):
            query_info['metric'] = metric_key
            break
    
    # If no specific metric found, default to PPL
    if not query_info['metric']:
        query_info['metric'] = 'ppl'
    
    # Extract target (what we're looking for)
    if any(x in question for x in ['manager', 'team lead', 'supervisor', 'team']):
        query_info['target'] = 'managers'
    elif any(x in question for x in ['who', 'which agent', 'top agent', 'best agent', 'worst agent']):
        query_info['target'] = 'agents'
    elif any(x in question for x in ['division', 'location', 'site', 'charlotte', 'austin']):
        query_info['target'] = 'divisions'
    elif any(x in question for x in ['average', 'avg', 'mean']):
        query_info['target'] = 'average'
    else:
        query_info['target'] = 'agents'  # Default
    
    # Extract time period
    time_periods = {
        7: ['week', 'last 7 days', '7 days'],
        14: ['two weeks', 'last 14 days', '14 days', 'fortnight'],
        30: ['month', 'last 30 days', '30 days', 'last month'],
        90: ['quarter', 'last 90 days', '90 days', 'last quarter', 'three months']
    }
    
    for days, terms in time_periods.items():
        if any(term in question for term in terms):
            query_info['time_period'] = days
            break
    
    # Extract division filter
    if 'charlotte' in question or 'cha' in question or 'clt' in question:
        query_info['filter_division'] = 'CHA'
    elif 'austin' in question or 'aus' in question or 'atx' in question:
        query_info['filter_division'] = 'AUS'
    
    # Extract queue type filter
    if 'training' in question or 'train' in question:
        query_info['filter_queue'] = 'training'
    elif 'performance' in question or 'perform' in question:
        query_info['filter_queue'] = 'performance'
    
    # Extract comparison
    if 'above target' in question or 'above break even' in question or 'exceeding' in question:
        query_info['comparison'] = 'above_target'
    elif 'below target' in question or 'below break even' in question or 'under' in question:
        query_info['comparison'] = 'below_target'
    elif 'compare' in question:
        query_info['comparison'] = 'compare'
        
        # If comparing divisions
        if 'charlotte' in question and 'austin' in question:
            query_info['target'] = 'divisions'
            query_info['comparison'] = 'compare_divisions'
    
    # Extract sort direction
    if any(x in question for x in ['top', 'best', 'highest', 'most']):
        query_info['sort_direction'] = 'DESC'
    elif any(x in question for x in ['bottom', 'worst', 'lowest', 'least']):
        query_info['sort_direction'] = 'ASC'
    
    # Extract limit (how many results to return)
    limit_match = re.search(r'top (\d+)', question)
    if limit_match:
        query_info['limit'] = int(limit_match.group(1))
    else:
        limit_match = re.search(r'(\d+) best', question)
        if limit_match:
            query_info['limit'] = int(limit_match.group(1))
    
    return query_info

# Generate dynamic SQL based on the question analysis
def generate_sql(query_info):
    """Generate SQL based on the analyzed question"""
    # Define the date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=query_info['time_period'])
    
    # Format dates for PostgreSQL
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    # Log the date range
    logger.info(f"Query date range: {start_date_str} to {end_date_str}")
    
    # Base SQL for agent performance aggregation
    if query_info['target'] == 'agents':
        sql = """
        SELECT 
            a.id,
            a.name,
            a.division,
            a.manager,
            a.queue_type,
            a.is_active,
            AVG(p.close_rate) as avg_close_rate,
            AVG(p.place_rate) as avg_place_rate,
            AVG(p.avg_premium) as avg_premium,
            AVG(p.leads_taken) as avg_leads_taken,
            SUM(p.leads_taken) as total_leads,
            (AVG(p.close_rate / 100) * AVG(p.place_rate / 100) * AVG(p.avg_premium)) as ppl
        FROM agent a
        JOIN daily_performance p ON a.id = p.agent_id
        WHERE p.date BETWEEN :start_date AND :end_date
        """
        
        # Add filters
        if query_info['filter_division']:
            # Handle multiple division formats
            if query_info['filter_division'] == 'CHA':
                sql += " AND (a.division ILIKE '%charlotte%' OR a.division ILIKE '%cha%' OR a.division = 'CLT')"
            elif query_info['filter_division'] == 'AUS':
                sql += " AND (a.division ILIKE '%austin%' OR a.division ILIKE '%aus%' OR a.division = 'ATX')"
            else:
                sql += f" AND a.division ILIKE '%{query_info['filter_division']}%'"
        
        if query_info['filter_manager']:
            sql += f" AND a.manager ILIKE '%{query_info['filter_manager']}%'"
        
        if query_info['filter_queue']:
            sql += f" AND a.queue_type ILIKE '%{query_info['filter_queue']}%'"
        
        # Active agents only - adapted for PostgreSQL boolean format
        sql += " AND a.is_active = True"
        
        # Group by agent
        sql += " GROUP BY a.id, a.name, a.division, a.manager, a.queue_type, a.is_active"
        
        # Add comparison conditions
        if query_info['comparison'] == 'above_target':
            sql += " HAVING (AVG(p.close_rate / 100) * AVG(p.place_rate / 100) * AVG(p.avg_premium)) >= 164"
        elif query_info['comparison'] == 'below_target':
            sql += " HAVING (AVG(p.close_rate / 100) * AVG(p.place_rate / 100) * AVG(p.avg_premium)) < 130"
        
        # Add sorting
        if query_info['metric'] == 'ppl':
            sql += f" ORDER BY ppl {query_info['sort_direction']}"
        elif query_info['metric'] == 'close_rate':
            sql += f" ORDER BY avg_close_rate {query_info['sort_direction']}"
        elif query_info['metric'] == 'place_rate':
            sql += f" ORDER BY avg_place_rate {query_info['sort_direction']}"
        elif query_info['metric'] == 'avg_premium':
            sql += f" ORDER BY avg_premium {query_info['sort_direction']}"
        elif query_info['metric'] == 'leads':
            sql += f" ORDER BY avg_leads_taken {query_info['sort_direction']}"
        
        # Add limit
        sql += f" LIMIT {query_info['limit']}"
    
    # SQL for manager performance aggregation
    elif query_info['target'] == 'managers':
        sql = """
        SELECT 
            a.manager,
            COUNT(DISTINCT a.id) as agent_count,
            AVG(p.close_rate) as avg_close_rate,
            AVG(p.place_rate) as avg_place_rate,
            AVG(p.avg_premium) as avg_premium,
            AVG(p.leads_taken) as avg_leads_taken,
            SUM(p.leads_taken) as total_leads,
            (AVG(p.close_rate / 100) * AVG(p.place_rate / 100) * AVG(p.avg_premium)) as ppl,
            -- Count agents per manager that are above target
            SUM(CASE WHEN (p.close_rate / 100 * p.place_rate / 100 * p.avg_premium) >= 164 THEN 1 ELSE 0 END) as agents_above_target,
            -- Count agents per manager that are at break even
            SUM(CASE WHEN (p.close_rate / 100 * p.place_rate / 100 * p.avg_premium) BETWEEN 130 AND 163.99 THEN 1 ELSE 0 END) as agents_at_break_even,
            -- Count agents per manager that are below break even  
            SUM(CASE WHEN (p.close_rate / 100 * p.place_rate / 100 * p.avg_premium) < 130 THEN 1 ELSE 0 END) as agents_below_break_even
        FROM agent a
        JOIN daily_performance p ON a.id = p.agent_id
        WHERE p.date BETWEEN :start_date AND :end_date
        AND a.is_active = True
        AND a.manager IS NOT NULL
        AND a.manager != ''
        """
        
        # Add filters
        if query_info['filter_division']:
            if query_info['filter_division'] == 'CHA':
                sql += " AND (a.division ILIKE '%charlotte%' OR a.division ILIKE '%cha%' OR a.division = 'CLT')"
            elif query_info['filter_division'] == 'AUS':
                sql += " AND (a.division ILIKE '%austin%' OR a.division ILIKE '%aus%' OR a.division = 'ATX')"
            else:
                sql += f" AND a.division ILIKE '%{query_info['filter_division']}%'"
        
        if query_info['filter_manager']:
            sql += f" AND a.manager ILIKE '%{query_info['filter_manager']}%'"
        
        if query_info['filter_queue']:
            sql += f" AND a.queue_type ILIKE '%{query_info['filter_queue']}%'"
        
        # Group by manager
        sql += " GROUP BY a.manager"
        
        # Add comparison conditions
        if query_info['comparison'] == 'above_target':
            sql += " HAVING ppl >= 164"
        elif query_info['comparison'] == 'below_target':
            sql += " HAVING ppl < 130"
        
        # Add sorting based on metric
        if query_info['metric'] == 'ppl':
            sql += f" ORDER BY ppl {query_info['sort_direction']}"
        elif query_info['metric'] == 'close_rate':
            sql += f" ORDER BY avg_close_rate {query_info['sort_direction']}"
        elif query_info['metric'] == 'place_rate':
            sql += f" ORDER BY avg_place_rate {query_info['sort_direction']}"
        elif query_info['metric'] == 'avg_premium':
            sql += f" ORDER BY avg_premium {query_info['sort_direction']}"
        elif query_info['metric'] == 'leads':
            sql += f" ORDER BY avg_leads_taken {query_info['sort_direction']}"
        else:
            # Default sort by manager PPL
            sql += f" ORDER BY ppl {query_info['sort_direction']}"
        
        # Add limit
        sql += f" LIMIT {query_info['limit']}"
    
    # SQL for division performance comparison
    elif query_info['target'] == 'divisions':
        sql = """
        SELECT 
            a.division,
            COUNT(DISTINCT a.id) as agent_count,
            AVG(p.close_rate) as avg_close_rate,
            AVG(p.place_rate) as avg_place_rate,
            AVG(p.avg_premium) as avg_premium,
            SUM(p.leads_taken) as total_leads,
            (AVG(p.close_rate / 100) * AVG(p.place_rate / 100) * AVG(p.avg_premium)) as ppl
        FROM agent a
        JOIN daily_performance p ON a.id = p.agent_id
        WHERE p.date BETWEEN :start_date AND :end_date
        AND a.is_active = 1
        """
        
        # Add filters
        if query_info['filter_division']:
            sql += f" AND a.division = '{query_info['filter_division']}'"
        
        if query_info['filter_manager']:
            sql += f" AND a.manager = '{query_info['filter_manager']}'"
        
        if query_info['filter_queue']:
            sql += f" AND a.queue_type LIKE '%{query_info['filter_queue']}%'"
        
        # Group by division
        sql += " GROUP BY a.division"
        
        # Add sorting
        if query_info['metric'] == 'ppl':
            sql += f" ORDER BY ppl {query_info['sort_direction']}"
        elif query_info['metric'] == 'close_rate':
            sql += f" ORDER BY avg_close_rate {query_info['sort_direction']}"
        elif query_info['metric'] == 'place_rate':
            sql += f" ORDER BY avg_place_rate {query_info['sort_direction']}"
        elif query_info['metric'] == 'avg_premium':
            sql += f" ORDER BY avg_premium {query_info['sort_direction']}"
        elif query_info['metric'] == 'leads':
            sql += f" ORDER BY total_leads {query_info['sort_direction']}"
        elif query_info['metric'] == 'agent_count':
            sql += f" ORDER BY agent_count {query_info['sort_direction']}"
    
    # SQL for average performance metrics across all agents
    elif query_info['target'] == 'average':
        sql = """
        SELECT 
            COUNT(DISTINCT a.id) as agent_count,
            AVG(p.close_rate) as avg_close_rate,
            AVG(p.place_rate) as avg_place_rate,
            AVG(p.avg_premium) as avg_premium,
            SUM(p.leads_taken) as total_leads,
            (AVG(p.close_rate / 100) * AVG(p.place_rate / 100) * AVG(p.avg_premium)) as ppl
        FROM agent a
        JOIN daily_performance p ON a.id = p.agent_id
        WHERE p.date BETWEEN :start_date AND :end_date
        AND a.is_active = 1
        """
        
        # Add filters
        if query_info['filter_division']:
            sql += f" AND a.division = '{query_info['filter_division']}'"
        
        if query_info['filter_manager']:
            sql += f" AND a.manager = '{query_info['filter_manager']}'"
        
        if query_info['filter_queue']:
            sql += f" AND a.queue_type LIKE '%{query_info['filter_queue']}%'"
    
    return sql, {'start_date': start_date, 'end_date': end_date}

def process_ai_query(question):
    """
    Process a natural language question about agent data using Anthropic's Claude API
    
    Args:
        question (str): The user's question about agent data
        
    Returns:
        dict: Response containing answer and any visualization data
    """
    # Import db here to avoid circular imports
    
    logger.info(f"Processing AI query: {question}")
    
    try:
        # Check if ANTHROPIC_API_KEY is available
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.error("ANTHROPIC_API_KEY not found in environment variables")
            return {
                "answer": "Error: API key not configured. Please set the ANTHROPIC_API_KEY environment variable.",
                "chart_data": None,
                "follow_up_questions": [],
                "type": "error"
            }
        
        # First, try to match with our basic patterns to determine query type
        query_type = None
        for pattern, info in QUERY_PATTERNS.items():
            if re.match(pattern, question):
                query_type = info["query"]
                description = info["description"]
                break
        
        # Analyze the question to determine what data to fetch
        query_info = analyze_question(question)
        
        # Get performance data based on the analysis
        sql, params = generate_sql(query_info)
        logger.info(f"Generated SQL: {sql}")
        logger.info(f"SQL params: {params}")
        
        # Execute the query
        data_results = []
        try:
            with db.engine.connect() as conn:
                result = conn.execute(text(sql), params)
                rows = result.fetchall()
                
                # Convert result to list of dicts
                for row in rows:
                    result_dict = {}
                    for column, value in row._mapping.items():
                        result_dict[column] = value
                    data_results.append(result_dict)
                
                logger.info(f"Query returned {len(data_results)} results")
        except Exception as e:
            logger.error(f"Database query error: {str(e)}")
            logger.error(traceback.format_exc())
            data_results = []
    except Exception as e:
        logger.error(f"Error analyzing question: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "answer": f"An error occurred while analyzing your question: {str(e)}",
            "chart_data": None,
            "follow_up_questions": [],
            "type": "error"
        }
    
    # Get data summary for context
    try:
        data_summary = get_agent_data_summary()
    except Exception as e:
        logger.error(f"Error getting data summary: {str(e)}")
        logger.error(traceback.format_exc())
        data_summary = "Error getting data summary"
    
    # Format the results for Claude
    formatted_results = json.dumps(data_results, indent=2, default=str)
    
    # Prepare the prompt for Claude
    system_prompt = """You are an AI assistant for a call center analytics dashboard. 
    You analyze performance data for sales agents, focusing on metrics like PPL (Placed Premium per Lead), 
    close rates, place rates, and average premiums.

    Important metrics and targets:
    - PPL (Placed Premium per Lead) = (close_rate/100 * place_rate/100 * avg_premium)
    - Target PPL: $164
    - Break-even PPL: $130
    
    RESPONSE GUIDELINES - FOLLOW THESE EXACTLY:
    1. Keep responses concise - maximum 5-6 short sentences
    2. Focus on the most critical data insights that drive business decisions
    3. Always include key metrics with $ and % symbols properly formatted
    4. When comparing performance, clearly state who/what is above or below targets
    5. Use bullet points for multiple insights
    6. Skip pleasantries and obvious statements
    7. Calculate any missing metrics if you have sufficient data, especially for manager-level analysis
    8. For manager questions, analyze team size, agent distribution, and overall performance
    9. Always provide concrete numbers rather than vague statements
    10. Maximum length: 600 characters
    
    If given data about agents by manager, always:
    - Calculate average team PPL for each manager
    - Note how many agents per manager are above/at/below targets
    - Compare manager performance against targets
    - Identify specific strengths of top managers

    Do not mention the structure of the query or technical aspects in your response."""
    
    prompt = f"""
    User Question: {question}
    
    Current Data Summary:
    {data_summary}
    
    Query Results:
    {formatted_results}
    
    Please provide a natural language analysis of this data that answers the user's question.
    Include relevant metrics, comparisons to targets, and any patterns or insights you observe.
    For follow-up suggestions, focus on logical next questions based on this analysis.
    """
    
    # Call Claude API for the response
    try:
        logger.info("Calling Anthropic API")
        claude_response = call_anthropic_api(prompt, system_prompt)
        logger.info("Received response from Anthropic API")
        
        # Determine chart data if applicable
        chart_data = None
        if len(data_results) > 0 and (query_type == "get_top_agents" or query_type == "get_bottom_agents"):
            chart_data = {
                'type': 'bar',
                'data': {
                    'labels': [record.get('name', '') for record in data_results[:5]],
                    'datasets': [{
                        'label': 'PPL ($)',
                        'data': [float(record.get('ppl', 0)) for record in data_results[:5]],
                        'backgroundColor': ['rgba(54, 162, 235, 0.7)'] * 5,
                        'borderColor': ['rgba(54, 162, 235, 1)'] * 5,
                        'borderWidth': 1
                    }]
                },
                'options': {
                    'scales': {
                        'y': {
                            'beginAtZero': True,
                            'title': {
                                'display': True,
                                'text': 'Placed Premium per Lead ($)'
                            }
                        },
                        'x': {
                            'title': {
                                'display': True,
                                'text': 'Agents'
                            }
                        }
                    },
                    'plugins': {
                        'title': {
                            'display': True,
                            'text': f"Agent PPL Comparison",
                            'font': {
                                'size': 16
                            }
                        }
                    }
                }
            }
        elif query_type == "get_performance_trend":
            # Create line chart for performance trend
            chart_data = {
                'type': 'line',
                'data': {
                    'labels': [record.get('date', '') for record in data_results],
                    'datasets': [{
                        'label': 'PPL Trend',
                        'data': [float(record.get('ppl', 0)) for record in data_results],
                        'fill': False,
                        'borderColor': 'rgba(75, 192, 192, 1)',
                        'tension': 0.1
                    }]
                }
            }
        
        # Get follow-up questions based on the query type
        followups = []
        if query_type and query_type in FOLLOW_UP_QUESTIONS:
            followups = FOLLOW_UP_QUESTIONS[query_type]
            random.shuffle(followups)
            followups = followups[:3]  # Limit to 3 follow-ups
        
        return {
            "answer": claude_response,
            "chart_data": chart_data,
            "follow_up_questions": followups,
            "type": query_type
        }
    except Exception as e:
        logger.error(f"Error processing with Claude API: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Fall back to basic response if Claude fails
        fallback_response = "I'm having trouble analyzing this data right now. Here are some basic insights:"
        
        if data_results:
            if query_type and 'agents' in query_type:
                agent_count = len(data_results)
                fallback_response += f"\n\nI found {agent_count} agents matching your criteria."
                if 'top' in question.lower():
                    top_agent = data_results[0] if data_results else None
                    if top_agent and 'name' in top_agent and 'ppl' in top_agent:
                        fallback_response += f" The top performer is {top_agent['name']} with a PPL of ${top_agent['ppl']:.2f}."
            elif query_type and 'average' in query_type:
                if data_results and 'ppl' in data_results[0]:
                    avg_ppl = data_results[0]['ppl']
                    fallback_response += f"\n\nThe average PPL is ${avg_ppl:.2f}."
                    if avg_ppl >= 164:
                        fallback_response += " This is above the target of $164."
                    elif avg_ppl >= 130:
                        fallback_response += " This is below the target of $164, but above the break-even point of $130."
                    else:
                        fallback_response += " This is below the break-even point of $130."
        else:
            fallback_response += "\n\nI couldn't find any data matching your query. Try broadening your search criteria or check if the filters are correct."
        
        # Get default follow-up questions
        default_followups = [
            "Who are the top performing agents?",
            "What's the average PPL across all agents?",
            "Compare Austin and Charlotte divisions"
        ]
        
        return {
            "answer": fallback_response,
            "chart_data": None,
            "follow_up_questions": default_followups,
            "type": "fallback"
        }

@ai_insights_bp.route('/api/ai_insights', methods=['POST'])
def process_ai_query_endpoint():
    """API endpoint to process AI queries."""
    # Import db here to avoid circular imports
    
    try:
        data = request.json
        question = data.get('question', '')
        
        if not question:
            return jsonify({"error": "No question provided"}), 400
        
        # Process the question using AI
        try:
            response = process_ai_query(question)
            return jsonify(response)
        except Exception as e:
            logger.error(f"Error processing AI query: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({
                "answer": f"Failed to process your question: {str(e)}. Please try again.",
                "chart_data": None,
                "follow_up_questions": [],
                "type": "error"
            }), 500
    except Exception as e:
        logger.error(f"Unexpected error in AI insights endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

# Add route for AI Insights page
@ai_insights_bp.route('/ai_insights')
def ai_insights_page():
    """Render the AI Insights page."""
    return render_template('ai_insights.html')

def register_ai_insights(app):
    """Register the AI Insights blueprint with the Flask app"""
    app.register_blueprint(ai_insights_bp) 