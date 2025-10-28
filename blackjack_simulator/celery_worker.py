
import os
import sys
import json
import logging
from celery import Celery
from celery.signals import worker_ready

# Add backend/src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'src')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler()
    ]
)

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
    logging.info("--- Worker is ready. Registered tasks: ---")
    logging.info(sender.app.tasks.keys())
    logging.info("-----------------------------------------")

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
@celery.task(name='jost_simulation_task')
def run_jost_simulation_task(simulation_config):
    """
    Celery task to run the Jost Engine simulation.
    """
    logging.info("--- Starting Jost Simulation Task ---")
    try:
        if not simulation_config:
            logging.error("No simulation configuration provided.")
            return {"error": "No simulation configuration provided."}

        logging.info(f"Received simulation_config: {simulation_config}")

        player_details = simulation_config.get("player")
        casino_config = simulation_config.get("casino")
        strategy_config = simulation_config.get("strategy")
        betting_strategy_details = simulation_config.get("betting_strategy")
        iterations = simulation_config.get("iterations")
        true_count_threshold = simulation_config.get("true_count_threshold", 1)

        if not all([player_details, casino_config, strategy_config, betting_strategy_details, iterations is not None]):
            logging.error(f"Incomplete simulation configuration: {simulation_config}")
            return {"error": "Incomplete simulation configuration."}

        try:
            game_config_for_strategy = {
                "hit_on_soft_17": not casino_config.get("dealer_stands_on_soft_17", True)
            }
            logging.info(f"Creating playing strategy with strategy_config: {strategy_config} and game_config: {game_config_for_strategy}")
            playing_strategy = create_playing_strategy(
                strategy_config=strategy_config,
                game_config=game_config_for_strategy
            )
            logging.info(f"Successfully created playing strategy: {playing_strategy.__class__.__name__}")

            bet_ramp_data = betting_strategy_details.get("bet_ramp", [])
            bet_ramp = []
            if isinstance(bet_ramp_data, dict):
                bet_ramp = [{'count_threshold': int(k), 'bet_multiplier': v} for k, v in bet_ramp_data.items()]
            elif isinstance(bet_ramp_data, list):
                if bet_ramp_data and isinstance(bet_ramp_data[0], str):
                    bet_ramp = [json.loads(item) for item in bet_ramp_data]
                else:
                    bet_ramp = bet_ramp_data

            betting_strategy = RampBettingStrategy(
                min_bet=betting_strategy_details.get("min_bet", 10),
                ramp=bet_ramp
            )

            player = Player(
                player_id=1,
                name=player_details.get("name"),
                bankroll=player_details.get("bankroll"),
                playing_strategy=playing_strategy,
                betting_strategy=betting_strategy
            )

            dealer = Dealer()
            game_logger = SimulationLogger()

            game_config = casino_config.copy()
            game_config['hit_on_soft_17'] = not casino_config.get("dealer_stands_on_soft_17", True)
            game_config['num_decks'] = casino_config.get('deck_count')
            game_config['true_count_threshold'] = true_count_threshold

            game = Game(
                players=[player],
                dealer=dealer,
                config=game_config,
                logger=game_logger
            )

            logging.info(f"Running simulation for {iterations} rounds.")
            results = game.run_simulation(num_rounds=iterations, headless=True)

            logging.info("--- Jost Simulation Task Finished ---")
            return json.loads(json.dumps(results, default=str))

        except SystemExit as e:
            logging.error(f"Caught SystemExit with code: {e.code}", exc_info=True)
            raise
        except Exception as e:
            logging.error(f"Error during simulation setup or execution: {e}", exc_info=True)
            raise

    except Exception as e:
        logging.error(f"An unexpected error occurred in the main task execution: {e}", exc_info=True)
        raise
