
import sys
import os
import json
import argparse
import datetime

# Add the engine's source to the Python path
engine_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'JOST_ENGINE_5', 'src'))
if engine_path not in sys.path:
    sys.path.insert(0, engine_path)

from jost_engine.game_setup import setup_game_from_config
from jost_engine.config_manager import load_profile
from jost_engine.data_exporter import DataExporter

def run_simulation_from_web(player_name, bankroll, num_hands, casino_profile, playing_strategy_profile, betting_strategy_profile):
    """
    Runs a blackjack simulation using parameters from the web UI.
    """
    # 1. Create a temporary player profile dictionary
    temp_player_profile = {
        "name": player_name,
        "bankroll": bankroll,
        "num_hands": 1,
        "playing_strategy_path": f"../../src/jost_engine/data/strategies/{playing_strategy_profile}.json",
        "betting_strategy_path": f"../../src/jost_engine/data/betting_strategies/{betting_strategy_profile}.json",
        "counting_strategy_path": "../../src/jost_engine/data/counting_systems/hilo.json"
    }

    # 2. Save this to a temporary file
    temp_profile_dir = os.path.join(engine_path, 'jost_engine', 'data', 'custom', 'players')
    os.makedirs(temp_profile_dir, exist_ok=True)
    temp_profile_filename = "_temp_web_player.json"
    temp_profile_filepath = os.path.join(temp_profile_dir, temp_profile_filename)

    with open(temp_profile_filepath, 'w') as f:
        json.dump(temp_player_profile, f, indent=4)

    # 3. Create the game configuration
    config = {
        "casino": casino_profile,
        "players": [os.path.splitext(temp_profile_filename)[0]] # Engine expects profile name without extension
    }

    # 4. Run the simulation
    game = setup_game_from_config(config)
    if not game or not game.players:
        print(json.dumps({"error": "Failed to set up game from configuration."}))
        cleanup_temp_file(temp_profile_filepath)
        return

    game.run_simulation(num_rounds=num_hands, headless=True)

    # 5. Extract and save results
    results_data = {
        "simulation_timestamp": datetime.datetime.now().isoformat(),
        "player_name": player_name,
        "initial_bankroll": game.players[0].bankroll + sum(hand.bet for hand in game.players[0].hands if hand.bet > 0) - game.total_payouts[player_name],
        "final_bankroll": game.players[0].bankroll,
        "net_gain_loss": game.players[0].bankroll - (game.players[0].bankroll + sum(hand.bet for hand in game.players[0].hands if hand.bet > 0) - game.total_payouts[player_name]),
        "total_wagered": game.total_wagered[player_name],
        "player_edge": (game.total_payouts[player_name] - game.total_wagered[player_name]) / game.total_wagered[player_name] if game.total_wagered[player_name] > 0 else 0,
        "num_hands_simulated": num_hands,
        "casino_rules": game.config,
        "hand_history": game.simulation_logger.get_records()
    }


    results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'simulation_results'))
    os.makedirs(results_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    results_filename = f"simulation_{timestamp}.json"
    results_filepath = os.path.join(results_dir, results_filename)

    DataExporter.export_json(results_data, results_filepath)

    # 7. Clean up the temporary file
    cleanup_temp_file(temp_profile_filepath)

    # 8. Print the path of the results file
    print(results_filepath)

def cleanup_temp_file(filepath):
    """Deletes the temporary player profile."""
    try:
        os.remove(filepath)
    except OSError as e:
        # Log this error instead of printing to stdout, to not corrupt the output path
        with open("run_engine_errors.log", "a") as f:
            f.write(f"Error removing temp file {filepath}: {e}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a blackjack simulation from the command line.")
    parser.add_argument("--player_name", type=str, required=True)
    parser.add_argument("--bankroll", type=int, required=True)
    parser.add_argument("--num_hands", type=int, required=True)
    parser.add_argument("--casino", type=str, required=True)
    parser.add_argument("--playing_strategy", type=str, required=True)
    parser.add_argument("--betting_strategy", type=str, required=True)

    args = parser.parse_args()

    run_simulation_from_web(
        player_name=args.player_name,
        bankroll=args.bankroll,
        num_hands=args.num_hands,
        casino_profile=args.casino,
        playing_strategy_profile=args.playing_strategy,
        betting_strategy_profile=args.betting_strategy
    )
