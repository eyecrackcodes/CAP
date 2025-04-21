from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os

# Create a minimal Flask app for Vercel
app = Flask(__name__)

# Check if running on Vercel and configure accordingly
IS_VERCEL = os.environ.get('VERCEL', False)

# Database configuration - Use environment variables for Vercel deployment
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:xe2Gyu!56h6tWQD@db.ndiwwxpixxwwbkpdmmqq.supabase.co:5432/postgres')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure secret key for sessions
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', '12345678900987654321')

# Import only what we need - lazy importing
from models import db, Agent, DailyPerformance, APIKey

# Initialize app
db.init_app(app)

# Create a placeholder route for health check
@app.route('/health')
def health_check():
    return jsonify({"status": "ok", "environment": "Vercel" if IS_VERCEL else "development"})

# Now import the main app - this will pull in the routes
from app import app as main_app

# Copy over all the routes and view functions
for rule in main_app.url_map.iter_rules():
    view_func = main_app.view_functions[rule.endpoint]
    
    # Skip any rules already defined in this app
    if rule.endpoint != 'health_check':
        app.view_functions[rule.endpoint] = view_func
        app.url_map.add(rule)

# Initialize the database
def init_db():
    with app.app_context():
        db.create_all()

# Initialize DB on startup
if not IS_VERCEL:  # Only run init_db when not on Vercel
    init_db()

# Create DB tables if they don't exist - this should be safe
with app.app_context():
    db.create_all()

# This file will be used as the entrypoint for Vercel 