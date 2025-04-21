from flask import Flask, jsonify, request
import os
from datetime import datetime

# Create app
app = Flask(__name__)

# Simple static data for API responses
AGENTS = [
    {
        "id": 1,
        "name": "John Smith",
        "division": "Charlotte (CLT)",
        "manager": "Patricia Lewis",
        "queue_type": "performance",
        "is_active": True
    },
    {
        "id": 2,
        "name": "Jane Doe",
        "division": "Austin (ATX)",
        "manager": "Vincent Blanchett",
        "queue_type": "training",
        "is_active": True
    },
    {
        "id": 3,
        "name": "Mike Johnson",
        "division": "Charlotte (CLT)",
        "manager": "Frederick Holguin",
        "queue_type": "performance",
        "is_active": False
    }
]

PERFORMANCE_DATA = {
    1: [
        {
            "date": "2023-04-01",
            "leads": 8,
            "close_rate": 28.5,
            "place_rate": 72.3,
            "avg_premium": 3954.21,
            "ppl": 164.32
        },
        {
            "date": "2023-04-08",
            "leads": 7,
            "close_rate": 30.2,
            "place_rate": 68.7,
            "avg_premium": 4102.45,
            "ppl": 172.56
        }
    ],
    2: [
        {
            "date": "2023-04-01",
            "leads": 5,
            "close_rate": 22.4,
            "place_rate": 65.8,
            "avg_premium": 3644.78,
            "ppl": 122.18
        },
        {
            "date": "2023-04-08",
            "leads": 6,
            "close_rate": 25.1,
            "place_rate": 70.2,
            "avg_premium": 3780.33,
            "ppl": 135.45
        }
    ],
    3: [
        {
            "date": "2023-04-01",
            "leads": 7,
            "close_rate": 26.8,
            "place_rate": 71.5,
            "avg_premium": 3835.92,
            "ppl": 155.67
        },
        {
            "date": "2023-04-08",
            "leads": 8,
            "close_rate": 29.3,
            "place_rate": 67.9,
            "avg_premium": 4021.56,
            "ppl": 163.21
        }
    ]
}

# API routes
@app.route('/api/agents', methods=['GET'])
def get_agents():
    return jsonify(AGENTS)

@app.route('/api/agent_details/<int:agent_id>')
def get_agent_details(agent_id):
    # Find agent by ID
    agent = next((a for a in AGENTS if a["id"] == agent_id), None)
    if not agent:
        return jsonify({"error": "Agent not found"}), 404
    
    # Get performance data for this agent
    performances = PERFORMANCE_DATA.get(agent_id, [])
    
    return jsonify({
        'agent': {
            'name': agent["name"],
            'division': agent["division"],
            'manager': agent["manager"],
            'queue_type': agent["queue_type"]
        },
        'performance_data': performances
    })

# Default route returns API info
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return jsonify({
        "status": "ok",
        "message": "CAP API is running",
        "note": "This is a static demo version with sample data.",
        "api_endpoints": [
            "/api/agents",
            "/api/agent_details/<agent_id>"
        ]
    })

# Main entrypoint
if __name__ == '__main__':
    app.run() 