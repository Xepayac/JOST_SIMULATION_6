
from flask import Flask, jsonify, render_template, request
import os
import json
import subprocess

# Initialize the Flask application
app = Flask(__name__)

# --- Constants ---
STRATEGY_DIR = "JOST_ENGINE_5/src/jost_engine/data/strategies"
BETTING_STRATEGY_DIR = "JOST_ENGINE_5/src/jost_engine/data/betting_strategies"
CASINO_RULES_DIR = "JOST_ENGINE_5/src/jost_engine/data/defaults/casinos"

# --- Helper Functions ---
def get_json_files(directory):
    """Scans a directory and returns a list of JSON file names."""
    files = []
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            files.append(filename)
    return files

def read_json_file(filepath):
    """Reads and parses a JSON file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

# --- Main Page Route ---

@app.route('/')
def index():
    """Renders the main dashboard page."""
    playing_strategies = get_json_files(STRATEGY_DIR)
    betting_strategies = get_json_files(BETTING_STRATEGY_DIR)
    casino_profiles = get_json_files(CASINO_RULES_DIR)
    
    # Load the details of the first casino to display by default
    default_casino_path = os.path.join(CASINO_RULES_DIR, casino_profiles[0]) if casino_profiles else None
    casino_rules = read_json_file(default_casino_path) if default_casino_path else {}

    return render_template(
        'index.html', 
        playing_strategies=playing_strategies,
        betting_strategies=betting_strategies,
        casino_profiles=casino_profiles,
        casino_rules=casino_rules
    )

# --- API Endpoints ---

@app.route('/api/simulation', methods=['POST'])
def run_simulation():
    """
    Receives simulation parameters, calls the run_engine.py bridge script,
    and returns the results from the generated JSON file.
    """
    data = request.get_json()

    try:
        # --- 1. Extract and Clean Parameters ---
        player_name = data.get('player_name', 'DefaultPlayer')
        bankroll = int(data.get('bankroll', 1000))
        num_hands = int(data.get('num_hands', 100))
        
        casino_profile = os.path.splitext(data.get('casino_profile', 'default_casino.json'))[0]
        playing_strategy = os.path.splitext(data.get('playing_strategy', 's17_basic_strategy.json'))[0]
        betting_strategy = os.path.splitext(data.get('betting_strategy', 'flat_bet.json'))[0]

        # --- 2. Construct the Command ---
        command = [
            'python',
            'blackjack_dashboard/run_engine.py',
            '--player_name', player_name,
            '--bankroll', str(bankroll),
            '--num_hands', str(num_hands),
            '--casino', casino_profile,
            '--playing_strategy', playing_strategy,
            '--betting_strategy', betting_strategy
        ]

        # --- 3. Execute the Bridge Script ---
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        results_filepath = result.stdout.strip()

        # --- 4. Read and Return the Results ---
        if os.path.exists(results_filepath):
            with open(results_filepath, 'r') as f:
                simulation_results = json.load(f)
            return jsonify(simulation_results)
        else:
            return jsonify({"status": "error", "message": "Simulation ran, but results file was not found."}), 500

    except subprocess.CalledProcessError as e:
        error_message = e.stderr.strip()
        return jsonify({
            "status": "error", 
            "message": "The simulation engine encountered an error.",
            "details": error_message
        }), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/strategies/playing', methods=['GET'])
def get_playing_strategies():
    """Returns a list of available playing strategies."""
    strategies = get_json_files(STRATEGY_DIR)
    return jsonify(strategies)

@app.route('/api/casinos', methods=['GET'])
def get_casinos():
    """Returns a list of available casino profiles."""
    casinos = get_json_files(CASINO_RULES_DIR)
    return jsonify(casinos)

@app.route('/api/casinos/<string:filename>', methods=['GET'])
def get_casino_rules(filename):
    """Returns the rules for a specific casino."""
    filepath = os.path.join(CASINO_RULES_DIR, filename)
    rules = read_json_file(filepath)
    if rules:
        return jsonify(rules)
    return jsonify({"status": "error", "message": "Casino profile not found"}), 404

# --- Run the Application ---

if __name__ == '__main__':
    app.run(debug=True, port=5000)
