from flask import Flask, jsonify
import os

# Create an ultra-minimal Flask API app for Vercel
app = Flask(__name__)

# Sample static data instead of database connection
AGENTS = [
    {"id": 1, "name": "John Doe", "division": "Charlotte (CLT)", "manager": "Patricia Lewis", "queue_type": "performance", "is_active": True},
    {"id": 2, "name": "Jane Smith", "division": "Austin (ATX)", "manager": "Vincent Blanchett", "queue_type": "training", "is_active": True},
    {"id": 3, "name": "Mike Johnson", "division": "Charlotte (CLT)", "manager": "Patricia Lewis", "queue_type": "performance", "is_active": False}
]

# API routes with static responses
@app.route('/api/health')
def health_check():
    return jsonify({"status": "ok"})

@app.route('/api/agents')
def get_agents():
    return jsonify(AGENTS)

@app.route('/api/agents/<int:agent_id>')
def get_agent(agent_id):
    agent = next((a for a in AGENTS if a["id"] == agent_id), None)
    if agent:
        return jsonify(agent)
    return jsonify({"error": "Agent not found"}), 404

@app.route('/')
def index():
    return jsonify({
        "message": "This is a minimal API deployment for Vercel.",
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
        "message": "The requested resource does not exist."
    }), 404

# Run the app
if __name__ == '__main__':
    app.run(debug=True) 