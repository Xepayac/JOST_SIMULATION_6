
import os
import sys
import json
import logging
from celery import Celery
from celery.signals import worker_ready

# Configure a logger for the Celery worker
# This will also capture logs from the jost_engine library
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("celery_worker.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Get the logger for the game engine
game_engine_logger = logging.getLogger('jost_engine.game')


from jost_engine.game import Game
from jost_engine.player import Player
from jost_engine.dealer import Dealer
from jost_engine.simulation_logger import SimulationLogger
from jost_engine.playing_strategy import BasicPlayingStrategy
from jost_engine.betting_strategy import BettingStrategy as BettingStrategyABC

celery = Celery(
    'frontend.blackjack_simulator.celery_worker',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

@worker_ready.connect
def log_registered_tasks(sender, **kwargs):
    logging.info(f"--- Worker is ready. Registered tasks: {list(sender.app.tasks.keys())} ---")

class RampBettingStrategy(BettingStrategyABC):
    def __init__(self, min_bet: float, ramp: list):
        self.min_bet = min_bet
        self.ramp = sorted(ramp, key=lambda x: x['count_threshold'], reverse=True)

    def get_bet(self, player, game: 'Game') -> float:
        true_count = game.get_true_count()
        for tier in self.ramp:
            if true_count >= tier['count_threshold']:
                return self.min_bet * tier['bet_multiplier']
        return self.min_bet

@celery.task(name='jost_simulation_task')
def run_jost_simulation_task(simulation_config):
    logging.info(f"--- Received Jost Simulation Task ---")
    
    if isinstance(simulation_config, str):
        try:
            simulation_config = json.loads(simulation_config)
        except json.JSONDecodeError:
            logging.error("Failed to parse simulation_config string into a dictionary.")
            return {"error": "Invalid configuration format."}

    try:
        player_details = simulation_config.get("player")
        casino_config = simulation_config.get("casino")
        playing_strategy_name = simulation_config.get("playing_strategy_name") 
        strategy_config = simulation_config.get("strategy")
        betting_strategy_details = simulation_config.get("betting_strategy")
        iterations = simulation_config.get("iterations")

        if not all([player_details, casino_config, playing_strategy_name, strategy_config, betting_strategy_details, iterations is not None]):
            logging.error(f"Incomplete simulation configuration received: {simulation_config}")
            return {"error": "Incomplete simulation configuration."}

        strategy_data = {
            "name": playing_strategy_name,
            "description": strategy_config.get("description", "Strategy loaded from frontend"),
            "strategy": {
                "hard": strategy_config.get("hard", {}),
                "soft": strategy_config.get("soft", {}),
                "pairs": strategy_config.get("pairs", {})
            }
        }
        
        playing_strategy = BasicPlayingStrategy(
            strategy_data=strategy_data,
            strategy_name=playing_strategy_name
        )
        
        bet_ramp_dict = betting_strategy_details.get("bet_ramp", {})
        bet_ramp_list = [
            {'count_threshold': int(k), 'bet_multiplier': v}
            for k, v in bet_ramp_dict.items()
        ]
        
        betting_strategy = RampBettingStrategy(
            min_bet=betting_strategy_details.get("min_bet", 10),
            ramp=bet_ramp_list
        )

        player = Player(
            player_id=1,
            name=player_details.get("name"),
            bankroll=player_details.get("bankroll"),
            playing_strategy=playing_strategy,
            betting_strategy=betting_strategy
        )

        dealer = Dealer()
        
        # --- FEATURE: Pass the log_hands parameter to the game ---
        game_config = casino_config['rules']
        game_config['log_hands'] = simulation_config.get('log_hands', False)

        game = Game(
            players=[player],
            dealer=dealer,
            config=game_config
        )

        logging.info(f"Running simulation for {iterations} rounds.")
        results = game.run_simulation(num_rounds=iterations)

        logging.info("--- Jost Simulation Task Finished ---")
        return json.loads(json.dumps(results, default=str))

    except Exception as e:
        logging.error(f"An unexpected error occurred in the Jost simulation task: {e}", exc_info=True)
        raise
