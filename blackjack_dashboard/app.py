
from flask import Flask, jsonify, render_template, request

# Initialize the Flask application
app = Flask(__name__)

# --- Main Page Route ---

@app.route('/')
def index():
    """Renders the main dashboard page."""
    # We will create this template in the next step.
    return render_template('index.html')

# --- API Endpoints ---

@app.route('/api/simulation', methods=['POST'])
def run_simulation():
    """
    Placeholder endpoint to run a simulation.
    Later, this will receive simulation parameters, call the JOST_ENGINE_5,
    and return the results.
    """
    # For now, return a dummy success message and the data that was sent.
    data = request.get_json()
    print("Received simulation request:", data)
    return jsonify({
        "status": "success",
        "message": "Simulation would run here.",
        "received_data": data,
        "results": [
            {"player": "Player 1", "profit": 150},
            {"player": "Player 2", "profit": -75}
        ]
    })

@app.route('/api/strategies/playing', methods=['GET'])
def get_playing_strategies():
    """
    Placeholder endpoint to list available playing strategies.
    Later, this will scan a directory for saved strategy files.
    """
    # For now, return a dummy list of strategies.
    dummy_strategies = [
        {"id": "basic_strategy", "name": "Basic Strategy"},
        {"id": "custom_aggressive", "name": "Custom Aggressive"}
    ]
    return jsonify(dummy_strategies)

@app.route('/api/strategies/playing', methods=['POST'])
def save_playing_strategy():
    """
    Placeholder endpoint to save a new playing strategy.
    Later, this will receive strategy data and write it to a JSON file.
    """
    strategy_data = request.get_json()
    print("Received new playing strategy:", strategy_data)
    # For now, just return a success message.
    return jsonify({
        "status": "success",
        "message": f"Playing strategy '{strategy_data.get('name')}' saved successfully."
    })

# --- Run the Application ---

if __name__ == '__main__':
    # Using debug=True enables auto-reloading when code changes.
    app.run(debug=True, port=5000)
