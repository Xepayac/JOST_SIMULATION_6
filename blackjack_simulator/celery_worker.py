
import os
import sys
import json
from celery import Celery
from celery.signals import worker_ready

# Add backend/src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'src')))

# Imports from backend engine
from jost_engine.game import Game
from jost_engine.player import Player
from jost_engine.dealer import Dealer
from jost_engine.simulation_logger import SimulationLogger
from jost_engine.playing_strategy import create_playing_strategy
from jost_engine.betting_strategy import BettingStrategy as BettingStrategyABC

# Celery Configuration
celery = Celery(
    'frontend.blackjack_simulator.celery_worker',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

# --- Diagnostic Logging --- 
@worker_ready.connect
def log_registered_tasks(sender, **kwargs):
    print("--- Worker is ready. Registered tasks: ---")
    print(sender.app.tasks.keys())
    print("-----------------------------------------")

# --- Betting Strategy Class ---
class RampBettingStrategy(BettingStrategyABC):
    """
    A betting strategy that uses a configurable tiered system based on the true count.
    """
    def __init__(self, min_bet: float, ramp: list):
        self.min_bet = min_bet
        # Sort the ramp by count_threshold in descending order for easier processing
        self.ramp = sorted(ramp, key=lambda x: x['count_threshold'], reverse=True)

    def get_bet(self, player, game: 'Game') -> float:
        """
        Determines the bet amount based on the true count and the configured ramp.
        """
        true_count = game.get_true_count()
        
        for tier in self.ramp:
            if true_count >= tier['count_threshold']:
                return self.min_bet * tier['bet_multiplier']
        
        return self.min_bet

# --- Celery Task Definition ---
@celery.task
def run_jost_simulation_task(simulation_config):
    """
    Celery task to run the Jost Engine simulation.
    """
    print("--- Starting Jost Simulation Task ---")
    if not simulation_config:
        return {"error": "No simulation configuration provided."}

    # Extract details from simulation_config
    player_details = simulation_config.get("player")
    casino_config = simulation_config.get("casino")
    strategy_config = simulation_config.get("strategy")
    betting_strategy_details = simulation_config.get("betting_strategy")
    iterations = simulation_config.get("iterations")

    if not all([player_details, casino_config, strategy_config, betting_strategy_details, iterations is not None]):
        return {"error": "Incomplete simulation configuration."}

    # Setup the game from config
    try:
        # Create the playing strategy
        game_config_for_strategy = {
            "hit_on_soft_17": not casino_config.get("dealer_stands_on_soft_17", True)
        }
        playing_strategy = create_playing_strategy(
            strategy_config=strategy_config,
            game_config=game_config_for_strategy
        )

        # Create the betting strategy from the ramp
        betting_strategy = RampBettingStrategy(
            min_bet=betting_strategy_details.get("min_bet", 10),
            ramp=betting_strategy_details.get("bet_ramp", [])
        )

        # Create the player
        player = Player(
            player_id=1,
            name=player_details.get("name"),
            bankroll=player_details.get("bankroll"),
            playing_strategy=playing_strategy,
            betting_strategy=betting_strategy
        )

        # Create the dealer
        dealer = Dealer()

        # Create the simulation logger
        game_logger = SimulationLogger()
        
        # Create the full game config dictionary
        game_config = casino_config.copy()
        game_config['hit_on_soft_17'] = not casino_config.get("dealer_stands_on_soft_17", True)
        game_config['num_decks'] = casino_config.get('deck_count')

        # Create the game object
        game = Game(
            players=[player],
            dealer=dealer,
            config=game_config,
            logger=game_logger
        )

        # Run the simulation
        results = game.run_simulation(num_rounds=iterations, headless=True)

        # Retrieve and return results
        print("--- Jost Simulation Task Finished ---")
        return json.loads(json.dumps(results, default=str))

    except Exception as e:
        print(f"Error during simulation setup or execution: {e}")
        # Raising the exception will mark the task as FAILED and report the error
        raise

