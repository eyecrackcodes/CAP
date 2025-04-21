from flask import Flask, jsonify

# Create bare minimum Flask app
app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({
        "status": "ok",
        "message": "Minimal API is running"
    })

@app.route('/api/status')
def status():
    return jsonify({
        "status": "ok",
        "version": "1.0.0"
    }) 