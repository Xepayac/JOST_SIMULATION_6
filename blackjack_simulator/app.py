
import os
import json
import click
import logging
from logging.handlers import RotatingFileHandler

from flask import Flask
from flask.cli import with_appcontext

# Correctly import all models
from .models import db, Player, Casino, BettingStrategy, PlayingStrategy, Simulation
from .celery_worker import celery
from .config import Config

# --- Correctly locate the project root ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# --- Database Initialization Command ---
def init_db():
    db.drop_all()
    db.create_all()

    # --- Load Default Player ---
    player_path = os.path.join(project_root, 'backend', 'src', 'jost_engine', 'data', 'defaults', 'players', 'master_player.json')
    with open(player_path, 'r') as f:
        player_data = json.load(f)
    default_player = Player(
        name=player_data['name'], 
        bankroll=player_data['bankroll'], 
        is_default=True
    )
    db.session.add(default_player)

    # --- Load Default Casino (CORRECTED) ---
    casino_path = os.path.join(project_root, 'backend', 'src', 'jost_engine', 'data', 'defaults', 'casinos', 'master_casino.json')
    with open(casino_path, 'r') as f:
        casino_data = json.load(f)
    default_casino = Casino(
        name=casino_data['name'],
        deck_count=casino_data['deck_count'],
        # Correctly interpret 'hit_on_soft_17'
        dealer_stands_on_soft_17=not casino_data['hit_on_soft_17'],
        blackjack_payout=casino_data['blackjack_payout'],
        allow_late_surrender=casino_data['allow_late_surrender'],
        allow_early_surrender=casino_data['allow_early_surrender'],
        allow_resplit_to_hands=casino_data['allow_resplit_to_hands'],
        # Correctly interpret 'DAS' for 'allow_double_after_split'
        allow_double_after_split=casino_data['DAS'],
        # Correctly interpret 'double_down_restrictions'
        allow_double_on_any_two="any" in casino_data['double_down_restrictions'],
        reshuffle_penetration=casino_data['reshuffle_penetration'],
        offer_insurance=casino_data['offer_insurance'],
        dealer_checks_for_blackjack=casino_data['dealer_checks_for_blackjack'],
        is_default=True
    )
    db.session.add(default_casino)

    # --- Load Default Betting Strategy (CORRECTED) ---
    betting_path = os.path.join(project_root, 'backend', 'src', 'jost_engine', 'data', 'defaults', 'betting_strategies', 'master_betting_strategy.json')
    with open(betting_path, 'r') as f:
        betting_data = json.load(f)
    default_betting_strategy = BettingStrategy(
        name=betting_data['name'],
        min_bet=betting_data['min_bet'], # Corrected from 'base_bet'
        bet_ramp=json.dumps(betting_data['bet_ramp']),
        is_default=True
    )
    db.session.add(default_betting_strategy)

    # --- Load Default Playing Strategy (CORRECTED) ---
    playing_path = os.path.join(project_root, 'backend', 'src', 'jost_engine', 'data', 'defaults', 'playing_strategies', 'master_playing_strategy.json')
    with open(playing_path, 'r') as f:
        playing_data = json.load(f)
    default_playing_strategy = PlayingStrategy(
        name="master_playing_strategy", # Use the system name
        description=playing_data['description'],
        hard_total_actions=json.dumps(playing_data['strategy']['hard']),
        soft_total_actions=json.dumps(playing_data['strategy']['soft']),
        pair_splitting_actions=json.dumps(playing_data['strategy']['pairs']),
        is_default=True
    )
    db.session.add(default_playing_strategy)

    db.session.commit()


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database with all default profiles.')

# --- DIAGNOSTIC COMMAND ---
@click.command('check-db')
@with_appcontext
def check_db_command():
    """Check the contents of the database."""
    click.echo("--- Checking Database Contents ---")
    
    players = Player.query.all()
    click.echo(f"Found {len(players)} players:")
    for p in players:
        click.echo(f"  - ID: {p.id}, Name: {p.name}, Default: {p.is_default}")

    casinos = Casino.query.all()
    click.echo(f"Found {len(casinos)} casinos:")
    for c in casinos:
        click.echo(f"  - ID: {c.id}, Name: {c.name}, Default: {c.is_default}")

    playing_strategies = PlayingStrategy.query.all()
    click.echo(f"Found {len(playing_strategies)} playing strategies:")
    for ps in playing_strategies:
        click.echo(f"  - ID: {ps.id}, Name: {ps.name}, Default: {ps.is_default}")

    betting_strategies = BettingStrategy.query.all()
    click.echo(f"Found {len(betting_strategies)} betting strategies:")
    for bs in betting_strategies:
        click.echo(f"  - ID: {bs.id}, Name: {bs.name}, Default: {bs.is_default}")

    simulations = Simulation.query.all()
    click.echo(f"Found {len(simulations)} simulations.")

    click.echo("--- Check Complete ---")


# --- Application Factory ---
def create_app(config_class=Config):
    app = Flask(__name__)

    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    app.config.from_object(config_class)

    # --- Initialize Extensions ---
    db.init_app(app)
    # Update celery config
    celery.conf.update(
        broker_url=app.config['CELERY_BROKER_URL'],
        result_backend=app.config['CELERY_RESULT_BACKEND']
    )

    # --- Register Blueprints ---
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    # --- Register Commands ---
    app.cli.add_command(init_db_command)
    app.cli.add_command(check_db_command) # Register the new command

    # --- Configure Logging ---
    log_dir = os.path.join(project_root, 'logs')
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)
    file_handler = RotatingFileHandler(os.path.join(log_dir, 'app.log'), maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('Blackjack Simulator startup')

    return app
