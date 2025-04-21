import os
import json
import subprocess
from flask import Blueprint, jsonify, request
from datetime import datetime

looker_api = Blueprint('looker_api', __name__)

@looker_api.route('/api/last_sync_time', methods=['GET'])
def get_last_sync_time():
    """Get the timestamp of the last successful Looker sync"""
    try:
        if os.path.exists('last_sync.json'):
            with open('last_sync.json', 'r') as f:
                sync_data = json.load(f)
                return jsonify(sync_data)
        else:
            return jsonify({'last_sync': None, 'record_count': 0})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@looker_api.route('/api/trigger_looker_sync', methods=['POST'])
def trigger_looker_sync():
    """Manually trigger a Looker data sync"""
    try:
        # Run the sync script as a subprocess
        result = subprocess.run(
            ["python", "looker_sync.py"],
            capture_output=True,
            text=True,
            timeout=180  # 3 minute timeout
        )
        
        if result.returncode == 0:
            # Parse the JSON output from the sync script
            sync_result = json.loads(result.stdout)
            return jsonify(sync_result)
        else:
            return jsonify({
                'success': False,
                'error': f"Sync failed: {result.stderr}",
                'timestamp': datetime.now().isoformat()
            }), 500
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': "Sync timed out after 3 minutes. It may still be running in the background.",
            'timestamp': datetime.now().isoformat()
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# Function to register the blueprint with the Flask app
def register_looker_api(app):
    app.register_blueprint(looker_api) 