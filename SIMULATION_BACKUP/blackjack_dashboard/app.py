
from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
import os
import json
import subprocess
import re
import uuid
import threading
from collections import defaultdict
from datetime import datetime
import logging
import traceback
from sqlalchemy import exc

# --- Logging Configuration ---
logging.basicConfig(filename='db_error.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s:%(message)s')

# --- Task Management ---
tasks = defaultdict(lambda: {'status': 'unknown', 'progress': 0, 'result': None})

# Initialize the Flask application
app = Flask(__name__)

# --- Development-specific settings to prevent caching --- 
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# --- Database Configuration ---
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'simulations.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Database Models ---
class SimulationRun(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    player_name = db.Column(db.String(80), nullable=False)
    bankroll = db.Column(db.Integer, nullable=False)
    num_hands = db.Column(db.Integer, nullable=False)
    casino_profile = db.Column(db.String(120), nullable=False)
    playing_strategy = db.Column(db.String(120), nullable=False)
    betting_strategy = db.Column(db.String(120), nullable=False)
    results_filename = db.Column(db.String(255), nullable=True) 

# --- Constants ---
STRATEGY_DIR = "JOST_ENGINE_5/src/jost_engine/data/strategies"
BETTING_STRATEGY_DIR = "JOST_ENGINE_5/src/jost_engine/data/betting_strategies"
CASINO_RULES_DIR = "JOST_ENGINE_5/src/jost_engine/data/defaults/casinos"
CUSTOM_PLAYING_STRATEGY_DIR = "JOST_ENGINE_5/src/jost_engine/data/custom/playing"
CUSTOM_BETTING_STRATEGY_DIR = "JOST_ENGINE_5/src/jost_engine/data/custom/betting"
RESULTS_DIR = os.path.join(basedir, "simulation_results")


# --- Helper Functions ---
def get_json_files_from_dirs(directories):
    files = set()
    for directory in directories:
        if os.path.exists(directory):
            for filename in os.listdir(directory):
                if filename.endswith(".json"):
                    files.add(filename)
    return sorted(list(files))

def find_strategy_file(filename):
    default_path = os.path.join(STRATEGY_DIR, filename)
    custom_path = os.path.join(CUSTOM_PLAYING_STRATEGY_DIR, filename)
    if os.path.exists(custom_path):
        return custom_path
    if os.path.exists(default_path):
        return default_path
    return None

def read_json_file(filepath):
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def transform_strategy_for_frontend(strategy_data):
    if "hard_totals" not in strategy_data:
        return strategy_data
    flat_strategy = {}
    dealer_map = { "2": "2", "3": "3", "4": "4", "5": "5", "6": "6", "7": "7", "8": "8", "9": "9", "10": "T", "11": "A" }
    dealer_order = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "11"]
    def expand_range(key):
        if '-' not in key:
            return [key]
        start, end = key.split('-')
        start_idx = dealer_order.index(start)
        end_idx = dealer_order.index(end)
        return dealer_order[start_idx:end_idx + 1]

    for category_key, player_hands in strategy_data.items():
        if category_key not in ["hard_totals", "soft_totals", "pairs"]:
            continue
        for player_hand, moves in player_hands.items():
            if category_key == "soft_totals":
                frontend_key = f"A{player_hand}"
            elif category_key == "pairs":
                if player_hand == "T": frontend_key = "TT"
                elif player_hand == "A": frontend_key = "AA"
                else: frontend_key = f"{player_hand}{player_hand}"
            else:
                frontend_key = str(player_hand)
            if frontend_key not in flat_strategy:
                flat_strategy[frontend_key] = {}
            for dealer_range, action in moves.items():
                expanded_dealers = expand_range(str(dealer_range))
                for dealer_card in expanded_dealers:
                    frontend_dealer_card = dealer_map.get(dealer_card)
                    if frontend_dealer_card:
                        flat_strategy[frontend_key][frontend_dealer_card] = action
    return flat_strategy

def transform_strategy_for_engine(flat_strategy):
    engine_strategy = {"hard_totals": {}, "soft_totals": {}, "pairs": {}}
    dealer_order = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'A']
    dealer_map_to_engine = {'T': '10', 'A': '11'}

    for player_hand, moves in flat_strategy.items():
        category, hand_key = None, None
        if player_hand.startswith('A') and len(player_hand) > 1 and player_hand != 'AA':
            category, hand_key = "soft_totals", player_hand.replace('A', '')
        elif len(player_hand) == 2 and player_hand[0] == player_hand[1]:
            category, hand_key = "pairs", player_hand[0]
        else:
            category, hand_key = "hard_totals", player_hand

        if not moves: continue
        
        engine_moves = {}
        start_range_card = dealer_order[0]
        current_action = moves.get(start_range_card)

        for i in range(1, len(dealer_order)):
            dealer_card = dealer_order[i]
            next_action = moves.get(dealer_card)
            if next_action != current_action:
                end_range_card = dealer_order[i-1]
                start_engine, end_engine = dealer_map_to_engine.get(start_range_card, start_range_card), dealer_map_to_engine.get(end_range_card, end_range_card)
                range_key = f"{start_engine}-{end_engine}" if start_engine != end_engine else start_engine
                engine_moves[range_key] = current_action
                start_range_card, current_action = dealer_card, next_action

        end_range_card = dealer_order[-1]
        start_engine, end_engine = dealer_map_to_engine.get(start_range_card, start_range_card), dealer_map_to_engine.get(end_range_card, end_range_card)
        range_key = f"{start_engine}-{end_engine}" if start_engine != end_engine else start_engine
        engine_moves[range_key] = current_action
        
        engine_strategy[category][hand_key] = engine_moves
    return engine_strategy

def save_strategy_file(directory, filename, data):
    if '..' in filename or '/' in filename or '\\' in filename:
        raise ValueError("Invalid filename.")
    if not filename.endswith('.json'):
        filename += '.json'
    os.makedirs(directory, exist_ok=True)
    filepath = os.path.join(directory, filename)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)
    return filepath

def run_simulation_background(task_id, data):
    with app.app_context():
        tasks[task_id]['status'] = 'running'
        tasks[task_id]['progress'] = 0
        try:
            player_name = data.get('player_name', 'DefaultPlayer')
            bankroll = int(data.get('bankroll', 1000))
            num_hands = int(data.get('num_hands', 100))
            casino_profile_raw = data.get('casino_profile', 'default_casino.json')
            playing_strategy_raw = data.get('playing_strategy', 's17_basic_strategy.json')
            betting_strategy_raw = data.get('betting_strategy', 'flat_bet.json')
            
            casino_profile = os.path.splitext(casino_profile_raw)[0]
            playing_strategy = os.path.splitext(playing_strategy_raw)[0]
            betting_strategy = os.path.splitext(betting_strategy_raw)[0]

            simulation_id = str(uuid.uuid4())
            results_filename = f"results_{simulation_id}.json"
            
            command = [
                'python', 'blackjack_dashboard/run_engine.py',
                '--player_name', player_name, '--bankroll', str(bankroll),
                '--num_hands', str(num_hands), '--casino', casino_profile,
                '--playing_strategy', playing_strategy, '--betting_strategy', betting_strategy,
                '--task_id', task_id, '--results_filename', results_filename
            ]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
            for line in process.stdout:
                if line.startswith("PROGRESS:"):
                    try:
                        progress = int(line.split(":")[1].strip())
                        tasks[task_id]['progress'] = progress
                    except (ValueError, IndexError):
                        pass
            process.wait()

            if process.returncode == 0:
                results_filepath = os.path.join(RESULTS_DIR, results_filename)
                if os.path.exists(results_filepath):
                    with open(results_filepath, 'r') as f:
                        simulation_results = json.load(f)
                    
                    tasks[task_id]['result'] = simulation_results
                    
                    logging.info("Attempting to save simulation run to the database.")
                    try:
                        new_run = SimulationRun(
                            id=simulation_id,
                            player_name=player_name, bankroll=bankroll, num_hands=num_hands,
                            casino_profile=casino_profile_raw, playing_strategy=playing_strategy_raw,
                            betting_strategy=betting_strategy_raw, results_filename=results_filename
                        )
                        db.session.add(new_run)
                        db.session.commit()
                        logging.info(f"Successfully saved simulation run {simulation_id} to the database.")
                    except exc.SQLAlchemyError as e:
                        logging.error(f"DATABASE ERROR: A {type(e).__name__} occurred: {e}")
                        logging.error(traceback.format_exc())
                        db.session.rollback()
                    tasks[task_id]['status'] = 'complete'
                    tasks[task_id]['progress'] = 100

                else:
                    tasks[task_id]['status'] = 'error'
                    tasks[task_id]['error'] = "Simulation ran, but results file was not found."
            else:
                stderr_output = process.stderr.read()
                tasks[task_id]['status'] = 'error'
                tasks[task_id]['error'] = stderr_output.strip()

        except Exception as e:
            tasks[task_id]['status'] = 'error'
            tasks[task_id]['error'] = str(e)

@app.route('/')
def index():
    playing_strategies = get_json_files_from_dirs([STRATEGY_DIR, CUSTOM_PLAYING_STRATEGY_DIR])
    betting_strategies = get_json_files_from_dirs([BETTING_STRATEGY_DIR, CUSTOM_BETTING_STRATEGY_DIR])
    casino_profiles = get_json_files_from_dirs([CASINO_RULES_DIR])
    default_casino_path = os.path.join(CASINO_RULES_DIR, casino_profiles[0]) if casino_profiles else None
    casino_rules = read_json_file(default_casino_path) if default_casino_path else {}
    return render_template(
        'index.html',
        playing_strategies=playing_strategies,
        betting_strategies=betting_strategies,
        casino_profiles=casino_profiles,
        casino_rules=casino_rules
    )

@app.route('/history')
def history():
    return render_template('history.html')
    
@app.route('/studio')
def studio():
    return render_template('studio.html')

@app.route('/api/simulation', methods=['POST'])
def start_simulation_endpoint():
    data = request.get_json()
    task_id = str(uuid.uuid4())
    thread = threading.Thread(target=run_simulation_background, args=(task_id, data))
    thread.start()
    return jsonify({"status": "running", "task_id": task_id})

@app.route('/api/simulation/progress/<task_id>', methods=['GET'])
def get_simulation_progress(task_id):
    task = tasks[task_id]
    return jsonify({'status': task['status'], 'progress': task.get('progress', 0), 'error': task.get('error')})

@app.route('/api/simulation/results/<task_id>', methods=['GET'])
def get_simulation_results(task_id):
    task = tasks.get(task_id)
    if not task or task['status'] != 'complete':
        return jsonify({"status": "error", "message": "Results not available or task not complete."}), 404
    return jsonify(task.get('result'))

@app.route('/api/history', methods=['GET'])
def get_history():
    try:
        runs = db.session.query(SimulationRun).order_by(SimulationRun.timestamp.desc()).all()
        history_data = []
        for run in runs:
            final_bankroll, net_gain_loss = 'N/A', 'N/A'
            if run.results_filename:
                results_path = os.path.join(RESULTS_DIR, run.results_filename)
                if os.path.exists(results_path):
                    with open(results_path, 'r') as f:
                        try:
                            results = json.load(f)
                            # Ensure 'players' and player_name key exist
                            if 'players' in results and run.player_name in results['players']:
                                player_stats = results['players'][run.player_name]
                                final_bankroll = player_stats.get('Final Bankroll', 'N/A')
                                net_gain_loss = player_stats.get('Net Gain/Loss', 'N/A')
                            else:
                                logging.warning(f"Player '{run.player_name}' not found in results file: {run.results_filename}")
                        except json.JSONDecodeError:
                            logging.error(f"Could not decode JSON for {run.results_filename}")

            history_data.append({
                'id': run.id,
                'date': run.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'player_name': run.player_name,
                'playing_strategy': run.playing_strategy,
                'betting_strategy': run.betting_strategy,
                'initial_bankroll': run.bankroll,
                'rounds_played': run.num_hands,
                'final_bankroll': final_bankroll,
                'net_gain_loss': net_gain_loss,
                'outcome': 'Win' if isinstance(net_gain_loss, (int, float)) and net_gain_loss > 0 else 'Loss' if isinstance(net_gain_loss, (int, float)) else 'Tie/Error',
            })
        return jsonify(history_data)
    except Exception as e:
        logging.error(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/history/<string:run_id>', methods=['GET'])
def get_history_run_details(run_id):
    try:
        run = db.session.get(SimulationRun, run_id)
        if not run:
            return jsonify({"status": "error", "message": "Run not found."}), 404
        
        if not run.results_filename:
            return jsonify({"status": "error", "message": "No results file associated with this run."}), 404

        results_path = os.path.join(RESULTS_DIR, run.results_filename)
        if not os.path.exists(results_path):
             return jsonify({"status": "error", "message": "Results file not found."}), 404
             
        with open(results_path, 'r') as f:
            results_data = json.load(f)
        return jsonify(results_data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/history/<string:run_id>', methods=['DELETE'])
def delete_history_run(run_id):
    try:
        run_to_delete = db.session.get(SimulationRun, run_id)
        if not run_to_delete:
            return jsonify({"status": "error", "message": "Run not found."}), 404
        
        if run_to_delete.results_filename:
            results_path = os.path.join(RESULTS_DIR, run_to_delete.results_filename)
            if os.path.exists(results_path):
                os.remove(results_path)

        db.session.delete(run_to_delete)
        db.session.commit()
        return jsonify({"status": "success", "message": f"Run {run_id} deleted."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/history', methods=['DELETE'])
def delete_all_history():
    try:
        runs = db.session.query(SimulationRun).all()
        for run in runs:
            if run.results_filename:
                results_path = os.path.join(RESULTS_DIR, run.results_filename)
                if os.path.exists(results_path):
                    os.remove(results_path)
            db.session.delete(run)
        db.session.commit()
        return jsonify({"status": "success", "message": f"All simulation runs and their results have been deleted."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/strategies/playing', methods=['GET'])
def get_playing_strategies():
    default_files = {f for f in get_json_files_from_dirs([STRATEGY_DIR])}
    custom_files = {f for f in get_json_files_from_dirs([CUSTOM_PLAYING_STRATEGY_DIR])}
    all_files = sorted(list(default_files | custom_files))
    
    strategy_list = [
        {'name': filename, 'is_custom': filename in custom_files}
        for filename in all_files
    ]
    return jsonify(strategy_list)

@app.route('/api/strategies/playing/<string:filename>', methods=['GET'])
def get_playing_strategy_data(filename):
    filepath = find_strategy_file(filename)
    if not filepath:
        return jsonify({"status": "error", "message": "Strategy file not found."}), 404
    strategy_data = read_json_file(filepath)
    if not strategy_data:
        return jsonify({"status": "error", "message": "Could not read or parse strategy file."}), 500
    transformed_data = transform_strategy_for_frontend(strategy_data)
    return jsonify(transformed_data)

@app.route('/api/strategies/playing', methods=['POST'])
def create_playing_strategy():
    try:
        data = request.get_json()
        strategy_name = data.get('name')
        flat_strategy_data = data.get('strategy')
        if not strategy_name or not isinstance(flat_strategy_data, dict):
            return jsonify({"status": "error", "message": "Invalid data format. 'name' and 'strategy' fields are required."}), 400
        
        engine_formatted_strategy = transform_strategy_for_engine(flat_strategy_data)
        
        filepath = save_strategy_file(CUSTOM_PLAYING_STRATEGY_DIR, strategy_name, engine_formatted_strategy)
        return jsonify({"status": "success", "message": f"Playing strategy '{strategy_name}' saved successfully."}), 201
    except (ValueError, TypeError) as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"An unexpected error occurred: {e}"}), 500

@app.route('/api/strategies/playing/<string:filename>', methods=['DELETE'])
def delete_playing_strategy(filename):
    if '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({"status": "error", "message": "Invalid filename."}), 400

    custom_path = os.path.join(CUSTOM_PLAYING_STRATEGY_DIR, filename)
    
    if not os.path.exists(custom_path):
        return jsonify({"status": "error", "message": "Strategy not found or it is a default strategy that cannot be deleted."}), 404
    
    try:
        os.remove(custom_path)
        return jsonify({"status": "success", "message": f"Strategy '{filename}' deleted successfully."})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error deleting file: {e}"}), 500

@app.route('/api/strategies/betting', methods=['GET'])
def get_betting_strategies():
    directories = [BETTING_STRATEGY_DIR, CUSTOM_BETTING_STRATEGY_DIR]
    return jsonify(get_json_files_from_dirs(directories))

@app.route('/api/strategies/betting', methods=['POST'])
def create_betting_strategy():
    try:
        data = request.get_json()
        strategy_name = data.get('name')
        strategy_data = data.get('strategy')
        if not strategy_name or not isinstance(strategy_data, dict):
            return jsonify({"status": "error", "message": "Invalid data format. 'name' and 'strategy' fields are required."}), 400
        filepath = save_strategy_file(CUSTOM_BETTING_STRATEGY_DIR, strategy_name, strategy_data)
        return jsonify({"status": "success", "message": f"Betting strategy saved to {filepath}"}), 201
    except (ValueError, TypeError) as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"An unexpected error occurred: {e}"}), 500

@app.route('/api/casinos', methods=['GET'])
def get_casinos():
    return jsonify(get_json_files_from_dirs([CASINO_RULES_DIR]))

@app.route('/api/casinos/<string:filename>', methods=['GET'])
def get_casino_rules(filename):
    filepath = os.path.join(CASINO_RULES_DIR, filename)
    rules = read_json_file(filepath)
    if rules:
        return jsonify(rules)
    return jsonify({"status": "error", "message": "Casino profile not found"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
