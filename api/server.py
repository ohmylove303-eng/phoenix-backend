from flask import Flask, jsonify
from flask_cors import CORS
import sys
import os
import time

# Add project root for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.state import load_state

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return "Phoenix API Online ⚡"

@app.route('/health')
def health():
    return jsonify({
        "status": "online",
        "timestamp": time.time()
    })

@app.route('/api/market')
@app.route('/api/state')
def get_market():
    """
    Non-blocking Market Data Endpoint.
    Reads from state.json (Atomic Read).
    """
    start = time.time()
    state = load_state()
    duration_ms = (time.time() - start) * 1000
    
    if not state:
        return jsonify({"error": "Engine warming up...", "status": "WAITING"}), 200
    
    # Inject API Process Time
    state['_meta']['api_latency_ms'] = round(duration_ms, 3)
    
    return jsonify(state)

if __name__ == '__main__':
    # Threaded=True is fine here because we are IO bound (file read is fast)
    # But usually we want a WSGI server for prod. For this MVP, Flask dev server is fine.
    app.run(host='0.0.0.0', port=5002, debug=True, threaded=True)
