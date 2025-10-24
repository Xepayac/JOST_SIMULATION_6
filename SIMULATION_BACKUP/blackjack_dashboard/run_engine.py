
import sys
import os
import json
import argparse
import datetime
import traceback
import time
from io import StringIO

# Add the engine's source to the Python path
engine_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'JOST_ENGINE_5', 'src'))
if engine_path not in sys.path:
    sys.path.insert(0, engine_path)

from jost_engine.game_setup import setup_game_from_config

def run_simulation_from_web(player_name, bankroll, num_hands, casino_profile, playing_strategy_profile, betting_strategy_profile, task_id=None, results_filename=None):
    temp_profile_filepath = None
    original_stdout = sys.stdout
    last_reported_progress = -1

    def progress_callback(current_hand, total_hands):
        nonlocal last_reported_progress
        progress = int((current_hand / total_hands) * 100)
        if progress > last_reported_progress:
            print(f"PROGRESS:{progress}", flush=True)
            last_reported_progress = progress

    try:
        start_time = time.time()

        temp_player_profile = {
            "name": player_name,
            "bankroll": bankroll,
            "playing_strategy": {"name": playing_strategy_profile},
            "betting_strategy": {"name": betting_strategy_profile}
        }
        temp_profile_dir = os.path.join(engine_path, 'jost_engine', 'data', 'custom', 'players')
        os.makedirs(temp_profile_dir, exist_ok=True)
        temp_profile_filename = f"_temp_web_player_{task_id or 'local'}.json"
        temp_profile_filepath = os.path.join(temp_profile_dir, temp_profile_filename)
        with open(temp_profile_filepath, 'w') as f:
            json.dump(temp_player_profile, f, indent=4)

        config = {
            "casino": casino_profile,
            "players": [os.path.splitext(temp_profile_filename)[0]]
        }

        sys.stdout = StringIO()
        game = setup_game_from_config(config)
        sys.stdout = original_stdout

        if not game or not game.players:
            raise RuntimeError("Failed to set up game from configuration.")

        game.run_simulation(num_rounds=num_hands, headless=True, progress_callback=progress_callback)

        end_time = time.time()
        actual_player_name = game.players[0].name
        total_wagered = game.total_wagered.get(actual_player_name, 0)
        total_payouts = game.total_payouts.get(actual_player_name, 0)
        final_bankroll = game.players[0].bankroll
        net_gain_loss = final_bankroll - bankroll
        player_edge = (total_payouts - total_wagered) / total_wagered if total_wagered > 0 else 0

        results_data = {
            "total_hands_played": num_hands,
            "simulation_duration_seconds": end_time - start_time,
            "players": {
                actual_player_name: {
                    "Final Bankroll": final_bankroll,
                    "Net Gain/Loss": net_gain_loss,
                    "Hands Played": num_hands,
                    "Average Bet": total_wagered / num_hands if num_hands > 0 else 0,
                    "House Edge (%)": -player_edge * 100
                }
            },
            "hand_history": game.simulation_logger.get_records(),
            "casino_rules": game.config
        }

        results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'simulation_results'))
        os.makedirs(results_dir, exist_ok=True)
        
        if not results_filename:
            results_filename = f"results_{task_id}.json"
        
        results_filepath = os.path.join(results_dir, results_filename)
        
        with open(results_filepath, 'w') as f:
            json.dump(results_data, f, indent=4)

        if os.path.exists(results_filepath):
            # This print statement is used by the Flask app to know where the results are.
            pass
        else:
            raise RuntimeError(f"Failed to save results file at {results_filepath}")

    except Exception as e:
        sys.stdout = original_stdout
        error_info = traceback.format_exc()
        print(error_info, file=sys.stderr, flush=True)
        error_log_path = "run_engine_errors.log"
        with open(error_log_path, "a") as f:
            f.write(f"--- Error on {datetime.datetime.now().isoformat()} ---\n")
            f.write(error_info)
            f.write("--- End of Error ---\n\n")
        sys.exit(1)

    finally:
        cleanup_temp_file(temp_profile_filepath)

def cleanup_temp_file(filepath):
    if not filepath: return
    try:
        os.remove(filepath)
    except OSError:
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--player_name", required=True)
    parser.add_argument("--bankroll", type=int, required=True)
    parser.add_argument("--num_hands", type=int, required=True)
    parser.add_argument("--casino", dest="casino_profile", required=True)
    parser.add_argument("--playing_strategy", dest="playing_strategy_profile", required=True)
    parser.add_argument("--betting_strategy", dest="betting_strategy_profile", required=True)
    parser.add_argument("--task_id", required=False)
    parser.add_argument("--results_filename", required=False)
    args = parser.parse_args()
    run_simulation_from_web(**vars(args))
